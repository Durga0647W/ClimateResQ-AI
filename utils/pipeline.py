"""Nine-stage ClimateResQ AI processing pipeline."""
import json, uuid
from datetime import datetime
from database.models import Report, Incident, AuditLog, EvidenceSource
from services.quality_service import check_quality
from services.extraction_service import extract_information
from services.completeness_service import check_completeness
from services.evidence_service import verify_evidence
from services.similarity_service import find_similar_reports
from services.clustering_service import cluster_report
from services.confidence_service import calculate_confidence
from services.severity_service import calculate_severity
from services.priority_service import calculate_priority
from prompts.safety_prompt import get_safety_recommendations

def _log(db, entity_type, entity_id, action, detail=""):
    db.add(AuditLog(entity_type=entity_type, entity_id=entity_id, action=action, detail=detail))

def run_pipeline(description, location, timestamp, source_type, people_affected, db, image_path=None, reporter_id=None):
    report_id=f"REP-{uuid.uuid4().hex[:6].upper()}"
    incident_id=f"INC-{uuid.uuid4().hex[:6].upper()}"
    results={"report_id":report_id,"incident_id":incident_id,"stages":{}}
    report=Report(report_id=report_id,description=description,location=location,
                  timestamp=timestamp,source_type=source_type,people_affected=people_affected,
                  image_path=image_path,status="PROCESSING",reporter_id=reporter_id)
    db.add(report); db.commit()
    _log(db,"report",report_id,"SUBMITTED",f"Source: {source_type}")

    results["stages"]["1_input"]={"status":"OK","report_id":report_id}
    
    extracted=extract_information(description,location,str(timestamp),people_affected)
    results["stages"]["3_extraction"]=extracted
    
    quality=check_quality(description,location,timestamp,extracted.get("incident_type"))
    report.quality_status=quality["status"]; report.quality_notes="; ".join(quality["issues"]); db.commit()
    results["stages"]["2_quality"]=quality
    if quality["status"]=="REJECTED":
        report.status="REJECTED"; db.commit()
        _log(db,"report",report_id,"REJECTED",report.quality_notes)
        results["final_status"]="REJECTED"; return results
        
    completeness=check_completeness(extracted)
    results["stages"]["4_completeness"]=completeness

    evidence=verify_evidence(extracted)
    results["stages"]["5_evidence"]=evidence
    for source in evidence.get("sources",[]):
        db.add(EvidenceSource(incident_id=incident_id,source_name=source["source"],
                              source_type=source["type"],content=source["content"],
                              agreement="SUPPORTING"))
    db.commit()

    existing=db.query(Report).filter(Report.report_id!=report_id).limit(250).all()
    existing_dicts=[{"report_id":r.report_id,"description":r.description,"location":r.location or ""} for r in existing]
    similar, corroborating, duplicates = find_similar_reports(description,location or "",existing_dicts)
    results["stages"]["6_similarity"]={"similar_reports":similar,"count":len(similar), "corroborating_count": len(corroborating), "duplicate_count": len(duplicates)}

    try:
        age_hours=max(0,(datetime.utcnow()-timestamp).total_seconds()/3600) if isinstance(timestamp,datetime) else 1.0
    except Exception: age_hours=1.0
    confidence=calculate_confidence(source_type, len(corroborating), quality["score"],
        completeness["score"],completeness["contradictions"],age_hours)
    results["stages"]["7_confidence"]=confidence

    ppl=extracted.get("people_affected")
    if ppl is None: ppl=people_affected or 0
    severity=calculate_severity(extracted.get("incident_type","Other"),ppl,
        extracted.get("severity_indicators",[]),description)
    priority=calculate_priority(severity["level"],confidence["score"],confidence["label"],ppl,
        len(corroborating),description)
    results["stages"]["8_severity"]=severity
    results["stages"]["8_priority"]=priority

    cluster, was_added = cluster_report(report, extracted, priority, severity, confidence, db)
    
    incident=Incident(
        incident_id=cluster.cluster_id.replace("CLU-","INC-") + f"-{report.report_id}", # ensure unique ID for the report's incident record
        report_id=report_id,
        incident_type=extracted.get("incident_type","Other"),
        location=location or "Unknown",
        event_time=str(timestamp),
        people_affected=ppl,
        impact=extracted.get("impact"),
        description=description,
        severity_indicators=json.dumps(extracted.get("severity_indicators",[])),
        entities=json.dumps(extracted.get("entities",[])),
        missing_info=json.dumps(completeness.get("missing", [])),
        contradictions=json.dumps(completeness.get("contradictions", [])),
        completeness_score=completeness["score"],
        completeness_status=completeness["status"],
        evidence_score=float(confidence["breakdown"].get("evidence", 0.0)),
        evidence_summary="Extracted automatically from pipeline.",
        confidence=confidence["score"],
        confidence_breakdown=json.dumps(confidence["breakdown"]),
        severity=severity["level"],
        priority=str(priority["level"]),
        priority_reasons=json.dumps(priority["reasons"]),
        cluster_id=cluster.cluster_id
    )
    db.add(incident)
    
    # Store evidence against the cluster if it's new
    if not was_added:
        for source in evidence.get("sources",[]):
            db.add(EvidenceSource(incident_id=cluster.cluster_id,source_name=source["source"],
                                  source_type=source["type"],content=source["content"],
                                  agreement="SUPPORTING"))

    _log(db,"incident_cluster",cluster.cluster_id,"CREATED_OR_UPDATED",
         f"Severity:{severity['level']} Priority:{priority['level']} Confidence:{confidence['score']:.2f}")
    report.status="PROCESSED"; db.commit()
    results["stages"]["9_dashboard"]={"cluster_id":cluster.cluster_id,"severity":severity["level"],
        "priority":priority["level"],"confidence":confidence["score"],"verification_status":cluster.status, "was_added": was_added}
    results["final_status"]="PROCESSED"; results["cluster_id"]=cluster.cluster_id
    return results
