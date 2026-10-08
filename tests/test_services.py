from services.quality_service import check_quality
from services.completeness_service import check_completeness
from services.severity_service import calculate_severity
from services.priority_service import calculate_priority

def test_quality_good():
    r=check_quality("Severe flood water has rapidly entered many homes near Red Hills causing panic.", "Red Hills, Chennai", "2026-10-07", "Flood")
    assert r["status"] == "GOOD"
    assert r["score"] >= 0.70

def test_quality_rejected():
    r=check_quality("Bad", "", None, None)
    assert r["status"] == "REJECTED"

def test_completeness():
    r=check_completeness({
        "incident_type":"Flood","location":"Chennai","description":"Flood",
        "event_time":"today","people_affected":50,"impact":"homes flooded",
        "severity_indicators":["water rising"]
    })
    assert r["score"] == 1.00
    assert r["status"] == "COMPLETE"

def test_severity():
    r=calculate_severity("Cyclone",2000,["High severity language"],
                         "Catastrophic cyclone affecting hospital")
    assert r["level"] == "CRITICAL"

def test_priority():
    # severity, confidence, confidence_label, people_affected, evidence_count, description
    r=calculate_priority("CRITICAL", 0.9, "High", 500, 3, "Hospital evacuation underway")
    assert r["level"] == 1
