from data.supporting_sources import get_relevant_sources
from prompts.verification_prompt import build_verification_prompt, VERIFICATION_SYSTEM
from services.llm_service import call_llm, parse_json_response

def _fallback_evidence(incident, sources):
    if not sources:
        return {"agreement_score":0.4,"agreements":[],"disagreements":[],
                "evidence_summary":"No supporting sources found.","recommendation":"NEEDS_REVIEW","_demo_mode":True}
    agreements, disagreements = [], []
    loc = (incident.get("location") or "").lower()
    itype = (incident.get("incident_type") or "").lower()
    for s in sources:
        content = s["content"].lower()
        if any(w in content for w in itype.split()):
            agreements.append(f"{s['source']}: corroborates incident type")
        if loc and loc.split(",")[0].strip() in content:
            agreements.append(f"{s['source']}: confirms location")
    score = min(0.95, 0.4 + len(agreements)*0.15)
    return {"agreement_score":round(score,2),"agreements":agreements[:4],
            "disagreements":disagreements,
            "evidence_summary":f"Found {len(sources)} supporting source(s) with {len(agreements)} agreement point(s).",
            "recommendation":"VERIFIED" if score > 0.6 else "NEEDS_REVIEW","_demo_mode":True}

def verify_evidence(incident):
    sources = get_relevant_sources(incident.get("location",""), incident.get("incident_type",""))
    result = call_llm(VERIFICATION_SYSTEM, build_verification_prompt(incident, sources), 400)
    evidence = None
    if result["mode"] == "nvidia" and result["text"]:
        parsed = parse_json_response(result["text"])
        if parsed and "agreement_score" in parsed:
            parsed["_demo_mode"] = False
            evidence = parsed
    if not evidence:
        evidence = _fallback_evidence(incident, sources)
    evidence["sources"] = sources
    return evidence
