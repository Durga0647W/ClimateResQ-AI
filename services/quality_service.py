import string

def check_quality(description, location, timestamp, incident_type=None):
    score = 1.0
    issues = []
    
    desc = (description or "").strip()
    loc = (location or "").strip()
    itype = (incident_type or "").strip()
    
    if len(desc) < 20:
        score -= 0.40
        issues.append("Text length < 20 characters")
    elif len(desc) < 50:
        score -= 0.20
        issues.append("Text length < 50 characters")
        
    if not loc or len(loc) < 3:
        score -= 0.20
        issues.append("No location detected")
        
    if not itype or itype.lower() in ["unknown", "other", "none"]:
        score -= 0.15
        issues.append("No disaster type detected")
        
    if desc:
        punc_count = sum(1 for c in desc if c in string.punctuation)
        upper_count = sum(1 for c in desc if c.isupper())
        if len(desc) > 0 and (punc_count / len(desc) > 0.2 or upper_count / len(desc) > 0.5):
            score -= 0.10
            issues.append("Excessive punctuation/capitalization")
            
    if not timestamp:
        score -= 0.05
        issues.append("No time reference")
        
    score = max(0.0, round(score, 2))
    
    if score < 0.40:
        label = "Poor"
    elif score < 0.70:
        label = "Fair"
    else:
        label = "Good"
        
    # Maintain original keys for backward compatibility but add the new precise ones
    return {"status": "GOOD" if label == "Good" else ("REJECTED" if label == "Poor" else "NEEDS_IMPROVEMENT"),
            "issues": issues, "score": score, "label": label}
