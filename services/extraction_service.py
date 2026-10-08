import re
from prompts.extraction_prompt import build_extraction_prompt, EXTRACTION_SYSTEM
from services.llm_service import call_llm, parse_json_response

FALLBACK_TYPES = {
    "Flood": ["flood", "flooding", "waterlogging", "water level rising", "inundation"],
    "Cyclone / Storm": ["cyclone", "cyclonic", "tropical storm", "severe storm", "storm surge", "storm"],
    "Fire": ["fire", "wildfire", "blaze", "burning"],
    "Landslide": ["landslide", "mudslide", "slope collapse"],
    "Power Disruption": ["power outage", "electricity outage", "electricity supply disrupted", "power disruption", "blackout"],
    "Road Blockage": ["road block", "road blocked", "impassable"],
    "Evacuation": ["evacuation", "evacuate"],
    "Heavy Rainfall": ["heavy rain", "heavy rainfall", "downpour"]
}

def _fallback_extract(description, location, timestamp, people_affected=None):
    desc_lower = description.lower()
    itype = "Other"
    
    # Check multi-word and single-word keywords accurately
    for category, keywords in FALLBACK_TYPES.items():
        if any(kw in desc_lower for kw in keywords):
            itype = category
            break
            
    if itype == "Other" and "water" in desc_lower:
        itype = "Flood"
    nums = re.findall(r"\b(\d+)\b", description)
    ppl = people_affected if people_affected is not None else (int(nums[0]) if nums else None)
    indicators = []
    if any(w in desc_lower for w in ["severe","major","critical","extreme","catastrophic"]):
        indicators.append("High severity language")
    if any(w in desc_lower for w in ["road","blocked","impassable"]):
        indicators.append("Road access blocked")
    if any(w in desc_lower for w in ["evacuate","shelter","stranded"]):
        indicators.append("Evacuation required")
    missing = []
    if not location: missing.append("Location not specified")
    if ppl is None: missing.append("Number of people affected unknown")
    return {
        "incident_type": itype, "location": location or "Unknown",
        "event_time": str(timestamp), "people_affected": ppl,
        "impact": f"Incident reported: {description[:150]}",
        "description": description[:300],
        "severity_indicators": indicators, "entities": [location] if location else [],
        "missing_information": missing, "contradictions": [], "_demo_mode": True,
    }

def extract_information(description, location, timestamp, people_affected=None):
    result = call_llm(EXTRACTION_SYSTEM, build_extraction_prompt(description, location, timestamp), 600)
    if result["mode"] == "nvidia" and result["text"]:
        parsed = parse_json_response(result["text"])
        if parsed and "incident_type" in parsed:
            parsed["_demo_mode"] = False
            if people_affected is not None and not parsed.get("people_affected"):
                parsed["people_affected"] = people_affected
            return parsed
    return _fallback_extract(description, location, timestamp, people_affected)
