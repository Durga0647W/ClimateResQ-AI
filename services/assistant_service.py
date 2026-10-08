import re
import json
from prompts.assistant_prompt import ASSISTANT_SYSTEM, build_assistant_prompt
from prompts.safety_prompt import get_safety_recommendations
from services.llm_service import call_llm, parse_json_response, is_demo_mode
from database.models import IncidentCluster, Report

SUPPORTED_DISASTERS = [
    "Flood", "Cyclone", "Fire", "Landslide", "Earthquake", "Storm", 
    "Heavy Rainfall", "Power Disruption", "Urban Flooding", "Storm Surge"
]
KNOWN_LOCATIONS = ["tambaram", "chennai", "kakinada", "coimbatore", "delhi", "red hills", "ooty"]

# --- DB TOOLS ---

def count_reports(db, status=None, disaster_type=None, location=None):
    query = db.query(Report)
    if status:
        query = query.filter(Report.status.ilike(f"%{status}%"))
    if disaster_type:
        query = query.filter(Report.description.ilike(f"%{disaster_type}%"))
    if location:
        query = query.filter(Report.location.ilike(f"%{location}%"))
    
    count = query.count()
    status_str = f" {status.lower()}" if status else ""
    dt_str = f" {disaster_type.lower()}" if disaster_type else ""
    loc_str = f" associated with {location.title()}" if location else ""
    return f"There are {count}{status_str}{dt_str} reports{loc_str}."

def count_incident_clusters(db, status=None, disaster_type=None, location=None):
    query = db.query(IncidentCluster)
    if status:
        query = query.filter(IncidentCluster.status.ilike(f"%{status}%"))
    if disaster_type:
        query = query.filter(IncidentCluster.disaster_type.ilike(f"%{disaster_type}%"))
    if location:
        query = query.filter(IncidentCluster.canonical_location.ilike(f"%{location}%"))
        
    count = query.count()
    status_str = f" {status.lower()}" if status else ""
    dt_str = f" {disaster_type.lower()}" if disaster_type else ""
    loc_str = f" in {location.title()}" if location else ""
    return f"There are {count}{status_str}{dt_str} incident clusters{loc_str}."

def list_reports(db, status=None, disaster_type=None, location=None, limit=10):
    query = db.query(Report)
    if status: query = query.filter(Report.status.ilike(f"%{status}%"))
    if disaster_type: query = query.filter(Report.description.ilike(f"%{disaster_type}%"))
    if location: query = query.filter(Report.location.ilike(f"%{location}%"))
    
    results = query.limit(limit).all()
    status_str = f" {status.lower()}" if status else ""
    dt_str = f" {disaster_type.lower()}" if disaster_type else ""
    loc_str = f" in {location.title()}" if location else ""
    desc = f"{status_str}{dt_str} reports{loc_str}".strip()
    
    if not results: return f"There are currently no matching {desc}."
    
    res = f"Found {len(results)} matching {desc}:\n"
    for r in results:
        res += f"- {r.report_id} in {r.location} (Status: {r.status})\n"
    return res

def list_incident_clusters(db, status=None, disaster_type=None, location=None, limit=10):
    query = db.query(IncidentCluster)
    if status: query = query.filter(IncidentCluster.status.ilike(f"%{status}%"))
    if disaster_type: query = query.filter(IncidentCluster.disaster_type.ilike(f"%{disaster_type}%"))
    if location: query = query.filter(IncidentCluster.canonical_location.ilike(f"%{location}%"))
    
    results = query.limit(limit).all()
    status_str = f" {status.lower()}" if status else ""
    dt_str = f" {disaster_type.lower()}" if disaster_type else ""
    loc_str = f" in {location.title()}" if location else ""
    desc = f"{status_str}{dt_str} incident clusters{loc_str}".strip()

    if not results: return f"There are currently no matching {desc}."
    
    res = f"Found {len(results)} matching {desc}:\n"
    for c in results:
        res += f"- {c.cluster_id}: {c.disaster_type} in {c.display_location} (Status: {c.status})\n"
    return res

def get_database_summary(db):
    reports = db.query(Report).count()
    clusters = db.query(IncidentCluster).count()
    high = db.query(IncidentCluster).filter_by(priority="HIGH").count()
    pending = db.query(IncidentCluster).filter_by(status="PENDING").count()
    verified = db.query(IncidentCluster).filter_by(status="VERIFIED").count()
    return f"Current database: {reports} raw reports, {clusters} incident clusters total, {high} high-priority, {pending} pending verification, {verified} verified."

def get_cluster_explanation(db, cluster_id):
    c = db.query(IncidentCluster).filter(IncidentCluster.cluster_id.ilike(f"%{cluster_id}%")).first()
    if not c: return f"Could not find cluster {cluster_id}."
    try:
        reasons = json.loads(c.clustering_reasons)
        res = f"Reports for {c.cluster_id} were grouped because:\n"
        for r in reasons: res += f"- {r}\n"
        return res
    except:
        return f"Explanation not available for {c.cluster_id}."

def get_my_reports(db, user_id):
    if not user_id: return "You are not logged in."
    reports = db.query(Report).filter(Report.reporter_id == user_id).all()
    if not reports: return "You haven't submitted any reports yet."
    res = f"You have submitted {len(reports)} reports:\n"
    for r in reports[:5]:
        res += f"- {r.report_id}: {r.location} ({r.status})\n"
    return res

# --- INTENT ROUTING ---

def determine_intent(q, chat_history):
    ql = q.lower()
    
    out_of_scope_patterns = ["cricket", "football", "poem", "bitcoin", "capital of", "weather", "stock price", "who won"]
    for p in out_of_scope_patterns:
        if p in ql:
            if "weather" in ql:
                return "UNKNOWN_RELATED", "weather"
            return "OUT_OF_SCOPE", None

    if "predict exactly where a cyclone will hit" in ql or "predict exactly" in ql:
        return "UNSUPPORTED_CAPABILITY", None

    safety_patterns = ["what should i do", "what do i do", "how do i stay safe", "how can i stay safe", "where should i go", "where can i take shelter", "what precautions", "where should i move", "how do i survive", "how can i protect myself"]
    if any(p in ql for p in safety_patterns):
        return "GENERAL_SAFETY", None
        
    if "how many incidents have multiple reports" in ql or "duplicate reports" in ql or "more than one report" in ql or "consolidated" in ql:
        return "MULTI_REPORT", None
        
    if "give me the database summary" in ql or "how many total reports are there" in ql or "what is the current system status" in ql or "database summary" in ql or ("how many reports and incidents" in ql):
        return "DATABASE_SUMMARY", None
        
    if "why were these reports grouped" in ql or "how does clustering work" in ql or "why are duplicate reports grouped" in ql or ("why" in ql and ("verified" in ql or "grouped" in ql or "cluster" in ql)):
        if "these" in ql or "clu-" in ql or "this" in ql:
            return "CLUSTER_EXPLANATION", None
        return "PROJECT_EXPLANATION", "clustering"
        
    if "latest incidents" in ql or "newest incidents" in ql or "show the latest" in ql:
        return "LATEST_INCIDENTS", None
        
    if "my report" in ql or "what happened to my report" in ql:
        return "MY_REPORTS", None
        
    if "what is climateresq" in ql or "what problem does" in ql or "normalize locations" in ql or "human-in-the-loop" in ql or "sdg 13" in ql or "citizens verify" in ql:
        return "PROJECT_EXPLANATION", None

    # Determine if it's a structured database query
    operation = None
    if "how many" in ql or "count" in ql:
        operation = "COUNT"
    elif "show" in ql or "list" in ql or "which" in ql or "are there" in ql:
        operation = "LIST"
        
    entity = None
    if "report" in ql:
        entity = "REPORT"
    elif "incident" in ql or "cluster" in ql:
        entity = "INCIDENT_CLUSTER"
        
    status = None
    if "verified" in ql:
        status = "VERIFIED"
    elif "pending" in ql or "need verification" in ql or "needs verification" in ql:
        status = "PENDING"
        
    disaster_type = None
    for d in SUPPORTED_DISASTERS:
        if d.lower() in ql:
            disaster_type = d.upper()
            break
            
    location = None
    for l in KNOWN_LOCATIONS:
        if l in ql:
            location = l.title()
            break

    if operation and entity:
        params = {
            "operation": operation,
            "entity": entity,
            "status": status,
            "disaster_type": disaster_type,
            "location": location
        }
        return "STRUCTURED_QUERY", params
        
    if entity == "REPORT" or entity == "INCIDENT_CLUSTER":
        # Missing operation, fallback to list if appropriate
        params = {
            "operation": "LIST",
            "entity": entity,
            "status": status,
            "disaster_type": disaster_type,
            "location": location
        }
        return "STRUCTURED_QUERY", params
        
    if location or disaster_type:
        # User gave a location or disaster type but didn't specify entity.
        # Default to listing incident clusters.
        params = {
            "operation": "LIST",
            "entity": "INCIDENT_CLUSTER",
            "status": status,
            "disaster_type": disaster_type,
            "location": location
        }
        return "STRUCTURED_QUERY", params

    return "UNKNOWN", None

def execute_intent_formatted(intent, param, q, db, user_id, role, chat_history):
    if intent == "OUT_OF_SCOPE":
        return "Sorry, I can only assist with ClimateResQ AI, disaster incidents, report verification, incident clustering, and disaster safety guidance."
        
    if intent == "UNKNOWN_RELATED":
        if param == "weather":
            return "I don't have weather information available in the current ClimateResQ AI system."
        return "I don't have matching information in the current ClimateResQ AI database."
        
    if intent == "UNSUPPORTED_CAPABILITY":
        return "That capability is not currently available in ClimateResQ AI."
        
    if intent == "GENERAL_SAFETY":
        ql = q.lower()
        dtype = None
        for d in SUPPORTED_DISASTERS:
            if d.lower() in ql:
                dtype = d
                break
        if not dtype:
            if "water" in ql or "inundation" in ql or "flooded" in ql: dtype = "Flood"
            elif "power outage" in ql or "blackout" in ql: dtype = "Power Disruption"
            elif "mudslide" in ql: dtype = "Landslide"
            elif "blaze" in ql or "wildfire" in ql: dtype = "Fire"
            
        if not dtype:
            return "What type of disaster are you asking about — flood, cyclone, fire, landslide, earthquake, or another event?"
            
        header = f"### {dtype.title()} Safety Guidance\n\nIf you are in or near a {dtype.lower()}:\n\n"
        body = "\n".join("• " + x for x in get_safety_recommendations(dtype))
        footer = f"\n\nThis is general safety guidance. If you want, I can separately check verified {dtype.lower()} incidents currently recorded by ClimateResQ AI."
        return header + body + footer
        
    if intent == "MULTI_REPORT":
        clusters = db.query(IncidentCluster).filter(IncidentCluster.report_count > 1).all()
        if not clusters: return "There are no incident clusters containing multiple reports."
        return f"There are {len(clusters)} incident clusters containing multiple reports."
        
    if intent == "DATABASE_SUMMARY":
        return "According to the current ClimateResQ AI database:\n" + get_database_summary(db)
        
    if intent == "LATEST_INCIDENTS":
        incs = db.query(IncidentCluster).order_by(IncidentCluster.created_at.desc()).limit(5).all()
        if not incs: return "No incidents found."
        res = "Here are the latest incidents:\n"
        for i in incs: res += f"- {i.cluster_id}: {i.disaster_type} in {i.display_location} (Reported at {i.latest_report_at})\n"
        return res

    if intent == "STRUCTURED_QUERY":
        operation = param["operation"]
        entity = param["entity"]
        status = param["status"]
        disaster_type = param["disaster_type"]
        location = param["location"]
        
        if entity == "REPORT":
            if operation == "COUNT":
                return count_reports(db, status, disaster_type, location)
            else:
                return list_reports(db, status, disaster_type, location)
        else: # INCIDENT_CLUSTER
            if operation == "COUNT":
                return count_incident_clusters(db, status, disaster_type, location)
            else:
                return list_incident_clusters(db, status, disaster_type, location)

    if intent == "MY_REPORTS":
        if role != "citizen": return "This feature is primarily for citizens checking their reports."
        return "According to the current ClimateResQ AI database:\n" + get_my_reports(db, user_id)
        
    if intent == "PROJECT_EXPLANATION":
        if param == "clustering" or "clustering" in q.lower() or "grouped" in q.lower() or "duplicate" in q.lower():
            return "CLIMATERESQ AI:\nIncident clustering works by grouping reports based on normalized location, disaster type, temporal proximity, and textual similarity to identify duplicates and consolidate them into a single verifiable incident."
        if "normalize" in q.lower():
            return "CLIMATERESQ AI:\nWe normalize locations to ensure variations like 'Tambaram' and 'Tambaram Chennai' resolve to the same canonical location, preventing duplicate clusters."
        if "human-in-the-loop" in q.lower() or "citizens verify" in q.lower():
            return "CLIMATERESQ AI:\nClimateResQ AI acts as a decision support system, not an autonomous agent. Only authorized responders can verify incidents to ensure data credibility. Citizens cannot verify incidents to prevent false or malicious confirmations."
        if "sdg 13" in q.lower():
            return "CLIMATERESQ AI:\nSDG 13 stands for Climate Action. ClimateResQ AI supports this goal by building resilience and adaptive capacity to climate-related hazards and natural disasters."
        return "CLIMATERESQ AI:\nClimateResQ AI is an AI-powered disaster information verification and response platform. It consolidates messy, duplicate citizen reports into structured incident clusters for authorized responders to verify."
        
    if intent == "CLUSTER_EXPLANATION":
        ql = q.lower()
        cid = None
        m = re.search(r'clu-[0-9a-f]+', ql)
        if m: cid = m.group(0).upper()
        
        if not cid and chat_history:
            for role_msg, msg in reversed(chat_history):
                m = re.search(r'CLU-[0-9A-F]+', msg)
                if m:
                    cid = m.group(0)
                    break
                    
        if not cid:
            return "Please specify the cluster ID (e.g., CLU-1234)."
            
        return "According to the current ClimateResQ AI database:\n" + get_cluster_explanation(db, cid)
        
    return "I’m not sure what you're asking. You can ask me about incidents, reports, verification, clustering, safety guidance, or how ClimateResQ AI works."

def answer_question(question, db, user_id=None, role=None, chat_history=None):
    intent, param = determine_intent(question, chat_history)
    answer = execute_intent_formatted(intent, param, question, db, user_id, role, chat_history)
    
    # If GenAI is enabled, we can optionally use it to rephrase the output, 
    # but the prompt strongly dictates strict formatting and deterministic outputs 
    # for routing, constraints and counts.
    # We will use GenAI only if the intent is UNKNOWN to try and answer based on a broad DB context.
    if intent == "UNKNOWN" and not is_demo_mode():
        ctx = get_database_summary(db)
        result = call_llm(ASSISTANT_SYSTEM, build_assistant_prompt(question, ctx), 500)
        if result["text"]:
            return {"answer": result["text"], "mode": result["mode"], "context_used": True}
            
    return {"answer": answer, "mode": "intent_router", "context_used": True}
