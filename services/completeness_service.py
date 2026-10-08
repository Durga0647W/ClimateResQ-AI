FIELD_WEIGHTS = {
    "location": 0.30, 
    "incident_type": 0.25, 
    "impact": 0.20,
    "event_time": 0.10, 
    "people_affected": 0.10, 
    "severity_indicators": 0.05
}

def check_completeness(extracted):
    score, missing = 0.0, list(extracted.get("missing_information", []))
    contradictions = list(extracted.get("contradictions", []))
    
    for field, weight in FIELD_WEIGHTS.items():
        val = extracted.get(field)
        
        # Consider a field missing if it is empty, None, or a generic placeholder
        is_missing = False
        if val in [None, "", [], "null"]:
            is_missing = True
        elif isinstance(val, str) and val.lower() in ["unknown", "other", "none"]:
            is_missing = True
            
        if not is_missing:
            score += weight
        else:
            label = field.replace("_", " ").title()
            if not any(label.lower() in str(m).lower() for m in missing):
                missing.append(f"{label} not provided")
                
    score = round(score, 2)
    status = "COMPLETE" if score >= 0.80 else "PARTIALLY COMPLETE" if score >= 0.50 else "INCOMPLETE"
    
    return {"score": score, "status": status, "missing": missing, "contradictions": contradictions}
