HIGH_SEVERITY_TYPES={"Cyclone","Flood","Landslide","Storm Surge","Evacuation"}
MEDIUM_SEVERITY_TYPES={"Heavy Rainfall","Urban Flooding","Infrastructure Damage","Road Blockage"}
CRITICAL_KEYWORDS=["catastrophic","destroyed","collapsed","2000","1000","dead","trapped","fatalities"]
HIGH_KEYWORDS=["severe","critical","major","extreme","500", "evacuate"]
MODERATE_KEYWORDS=["moderate","significant","blocked","affected","disrupted","100","200","150"]

def calculate_severity(incident_type, people_affected, indicators, description):
    combined=(description or "").lower()+" "+" ".join(indicators or []).lower()
    score,reasons=0,[]
    
    if incident_type in HIGH_SEVERITY_TYPES: score+=40; reasons.append(f"{incident_type} is a high-severity type")
    elif incident_type in MEDIUM_SEVERITY_TYPES: score+=20; reasons.append(f"{incident_type} is a moderate-severity type")
    else: score+=10
    
    ppl=people_affected or 0
    if ppl>=1000: score+=50; reasons.append(f"{ppl} people affected")
    elif ppl>=500: score+=35; reasons.append(f"{ppl} people affected")
    elif ppl>=100: score+=20; reasons.append(f"{ppl} people affected")
    elif ppl>=20: score+=10; reasons.append(f"{ppl} people affected")
    elif ppl>0: score+=5
    
    if any(k in combined for k in CRITICAL_KEYWORDS): score+=30; reasons.append("Critical-severity language detected")
    elif any(k in combined for k in HIGH_KEYWORDS): score+=20; reasons.append("High-severity language detected")
    elif any(k in combined for k in MODERATE_KEYWORDS): score+=10; reasons.append("Moderate-severity language detected")
    
    if any(w in combined for w in ["road","bridge","power","hospital","school"]):
        score+=10; reasons.append("Critical infrastructure affected")
        
    if score >= 90:
        level = "CRITICAL"
    elif score >= 70:
        level = "HIGH"
    elif score >= 40:
        level = "MODERATE"
    elif score > 0:
        level = "LOW"
    else:
        level = "UNKNOWN"
        
    return {"level":level,"score":min(100,score),"reasons":reasons}
