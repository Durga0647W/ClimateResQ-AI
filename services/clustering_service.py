import json
import uuid
from datetime import datetime
from services.location_service import normalize_location
from database.models import IncidentCluster, Report
from config.settings import SIMILARITY_THRESHOLD
from services.similarity_service import find_similar_reports

def are_disaster_types_compatible(t1, t2):
    t1 = t1.lower().strip()
    t2 = t2.lower().strip()
    if t1 == t2:
        return True
    
    compatible_sets = [
        {"flood", "urban flooding", "waterlogging", "inundation"},
        {"cyclone", "storm", "tropical storm", "storm surge", "heavy rainfall", "cyclone / storm"},
        {"power disruption", "power outage", "blackout"},
        {"fire", "wildfire", "blaze"},
        {"landslide", "mudslide", "slope collapse"}
    ]
    
    for s in compatible_sets:
        if t1 in s and t2 in s:
            return True
            
    return False

def are_locations_conflicting(loc1, loc2):
    l1 = normalize_location(loc1)
    l2 = normalize_location(loc2)
    
    if not l1 or not l2 or l1 == "unknown" or l2 == "unknown":
        return False
        
    if l1 != l2 and l1 not in l2 and l2 not in l1:
        return True
        
    return False

def calculate_cluster_score(report1_loc, report1_type, report1_time, report2_loc, report2_type, report2_time, text_similarity):
    # Hard Gates
    if not are_disaster_types_compatible(report1_type, report2_type):
        return -1.0 # Immediate rejection
        
    if are_locations_conflicting(report1_loc, report2_loc):
        return -1.0 # Immediate rejection

    # Location match
    l1 = normalize_location(report1_loc)
    l2 = normalize_location(report2_loc)
    loc_score = 0.0
    if l1 and l2 and l1 != "unknown" and l2 != "unknown" and (l1 == l2 or l1 in l2 or l2 in l1):
        loc_score = 0.35
        
    # Type match (already passed compatibility, but we give points)
    type_score = 0.25
    
    # Temporal match
    try:
        t1 = datetime.fromisoformat(report1_time) if isinstance(report1_time, str) else report1_time
        t2 = datetime.fromisoformat(report2_time) if isinstance(report2_time, str) else report2_time
        hours_diff = abs((t1 - t2).total_seconds()) / 3600
        if hours_diff <= 24:
            time_score = 0.20
        elif hours_diff <= 72:
            time_score = 0.20 * (1 - (hours_diff - 24) / 48)
        else:
            return -1.0 # Too far apart in time
    except Exception:
        time_score = 0.0
        
    text_score = text_similarity * 0.20
    
    # Ensure time alone doesn't cluster unknown locations
    if loc_score == 0.0 and text_score < 0.10:
        return -1.0
        
    return loc_score + type_score + time_score + text_score

def find_best_cluster(new_report, new_extracted, db):
    clusters = db.query(IncidentCluster).filter(IncidentCluster.status == "PENDING").all()
    if not clusters:
        return None, 0.0, []
        
    best_cluster = None
    best_score = 0.0
    best_reasons = []
    
    new_loc = new_extracted.get("location") or new_report.location or "unknown"
    new_type = new_extracted.get("incident_type", "Other")
    new_time = new_extracted.get("event_time") or new_report.timestamp
    
    # Text similarity against reports in clusters
    all_reports = db.query(Report).filter(Report.cluster_id.isnot(None)).all()
    report_dicts = [{"report_id": r.report_id, "description": r.description, "location": r.location, "cluster_id": r.cluster_id} for r in all_reports]
    matches, _, _ = find_similar_reports(new_report.description, new_loc, report_dicts)
    similar_texts = matches
    
    cluster_text_sim = {}
    for sim in similar_texts:
        cid = next((r["cluster_id"] for r in report_dicts if r["report_id"] == sim["report_id"]), None)
        if cid:
            cluster_text_sim[cid] = max(cluster_text_sim.get(cid, 0), sim["similarity_score"])
            
    for cluster in clusters:
        text_sim = cluster_text_sim.get(cluster.cluster_id, 0.0)
        
        # Compare against all reports in cluster to be safe
        cluster_reports = [r for r in report_dicts if r["cluster_id"] == cluster.cluster_id]
        
        # We calculate the score against the cluster's aggregate data, 
        # but could also take the max score against individual reports.
        # For simplicity, we use the cluster's aggregate fields, but we already have text_sim maxed.
        score = calculate_cluster_score(new_loc, new_type, new_time, cluster.display_location, cluster.disaster_type, cluster.latest_report_at, text_sim)
        
        if score > best_score and score >= 0.65:
            best_score = score
            best_cluster = cluster
            
            reasons_list = []
            l1 = normalize_location(new_loc)
            l2 = cluster.canonical_location
            
            if l1 and l2 and l1 != "unknown" and l2 != "unknown" and (l1 == l2 or l1 in l2 or l2 in l1):
                reasons_list.append(f"Same normalized locality: {l2}")
            else:
                reasons_list.append("Location could not be reliably normalized.")
                
            reasons_list.append(f"Compatible disaster type: {cluster.disaster_type}")
            
            reasons_list.append("Reports submitted within similar time window")
            
            if text_sim >= SIMILARITY_THRESHOLD:
                reasons_list.append("High textual similarity")
                
            best_reasons = reasons_list
                
    return best_cluster, best_score, best_reasons

def cluster_report(report, extracted_info, priority_info, severity_info, confidence_info, db):
    best_cluster, score, reasons = find_best_cluster(report, extracted_info, db)
    
    loc = extracted_info.get("location") or report.location or "unknown"
    disaster_type = extracted_info.get("incident_type", "Other")
    
    if best_cluster:
        report.cluster_id = best_cluster.cluster_id
        
        related = json.loads(best_cluster.related_report_ids or "[]")
        if report.report_id not in related:
            related.append(report.report_id)
        best_cluster.related_report_ids = json.dumps(related)
        best_cluster.report_count = len(related)
        
        if report.timestamp > best_cluster.latest_report_at:
            best_cluster.latest_report_at = report.timestamp
            
        # Priority 1 is highest urgency, 5 is lowest.
        try:
            curr_pri = int(best_cluster.priority)
            new_pri = int(priority_info["level"])
            if new_pri < curr_pri:
                best_cluster.priority = str(new_pri)
        except (ValueError, TypeError):
            best_cluster.priority = str(priority_info["level"])
            
        sev_levels = {"CRITICAL": 5, "HIGH": 4, "MODERATE": 3, "LOW": 2, "UNKNOWN": 1}
        curr_sev = sev_levels.get(best_cluster.severity, 0)
        new_sev = sev_levels.get(severity_info["level"], 0)
        if new_sev > curr_sev:
            best_cluster.severity = severity_info["level"]
            
        old_reasons = json.loads(best_cluster.clustering_reasons or "[]")
        for r in reasons:
            if r not in old_reasons:
                old_reasons.append(r)
        best_cluster.clustering_reasons = json.dumps(old_reasons)
            
        return best_cluster, True
    else:
        cluster_id = f"CLU-{uuid.uuid4().hex[:6].upper()}"
        report.cluster_id = cluster_id
        
        new_cluster = IncidentCluster(
            cluster_id=cluster_id,
            canonical_location=normalize_location(loc),
            display_location=loc,
            disaster_type=disaster_type,
            latest_report_at=report.timestamp,
            report_count=1,
            status="PENDING",
            priority=str(priority_info["level"]),
            severity=severity_info["level"],
            confidence=confidence_info["score"],
            related_report_ids=json.dumps([report.report_id]),
            clustering_reasons=json.dumps(["Initial report for incident"])
        )
        db.add(new_cluster)
        return new_cluster, False
