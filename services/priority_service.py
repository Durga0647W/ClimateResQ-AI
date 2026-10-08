from config.settings import LOW_CONFIDENCE_THRESH

def calculate_priority(severity, confidence, confidence_label, people_affected, evidence_count, description):
    reasons = []
    
    # Base mapping on Severity and Confidence Level
    if severity == "CRITICAL":
        if confidence_label in ["High", "Medium"]:
            level = 1
            reasons.append("Critical severity with sufficient confidence")
        else:
            level = 2
            reasons.append("Critical severity but low confidence")
            
    elif severity == "HIGH":
        if confidence_label in ["High", "Medium"]:
            level = 2
            reasons.append("High severity with sufficient confidence")
        else:
            level = 3
            reasons.append("High severity but low confidence")
            
    elif severity == "MODERATE":
        if confidence_label in ["High", "Medium"]:
            level = 3
            reasons.append("Moderate severity with sufficient confidence")
        else:
            level = 4
            reasons.append("Moderate severity with low confidence")
            
    else:  # LOW or UNKNOWN
        if confidence_label in ["High", "Medium"]:
            level = 4
            reasons.append("Low severity with sufficient confidence")
        else:
            level = 5
            reasons.append("Low severity with low confidence")
            
    # Do not arbitrarily lower or raise priority just based on report counts.
    # The confidence score already accounts for evidence counts.
    return {
        "level": level,
        "score": level, # Keep 'score' for compatibility if needed, though 'level' is the true priority rank
        "reasons": reasons,
        "needs_human_verification": True # ALWAYS true
    }
