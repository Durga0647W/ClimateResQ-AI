from config.settings import CONFIDENCE_WEIGHTS

SOURCE_RELIABILITY = {
    "Government Alert":0.95, "NGO":0.85, "News Media":0.75,
    "Social Media":0.55, "Citizen":0.65
}

def calculate_confidence(source_type, evidence_count, quality_score, completeness_score, contradictions, report_age_hours=1.0):
    # Calculate components
    ev_score = min(evidence_count * 0.25, 1.0)
    consistency_score = max(0.0, 1.0 - (len(contradictions) * 0.25))
    
    # Weights according to approved specification
    w_comp = 0.35
    w_ev = 0.30
    w_qual = 0.25
    w_cons = 0.10
    
    # Calculate final confidence score
    score = (
        (w_comp * completeness_score) + 
        (w_ev * ev_score) + 
        (w_qual * quality_score) + 
        (w_cons * consistency_score)
    )
    score = round(min(1.0, max(0.0, score)), 2)
    
    # Labels
    if score >= 0.75:
        label = "High"
    elif score >= 0.50:
        label = "Medium"
    elif score >= 0.30:
        label = "Low"
    else:
        label = "Very Low"
        
    breakdown = {
        "completeness": round(completeness_score, 2),
        "evidence": round(ev_score, 2),
        "quality": round(quality_score, 2),
        "consistency": round(consistency_score, 2)
    }
    
    reasons = []
    if completeness_score >= 0.8: reasons.append("Complete information provided")
    if ev_score > 0: reasons.append(f"{evidence_count} corroborating report(s)")
    if quality_score >= 0.7: reasons.append("Good report quality")
    if consistency_score == 1.0: reasons.append("No contradictions detected")
    
    if ev_score == 0: reasons.append("No corroborating reports")
    if len(contradictions) > 0: reasons.append(f"{len(contradictions)} contradiction(s) found")
    
    return {"score": score, "label": label, "breakdown": breakdown, "reasons": reasons}
