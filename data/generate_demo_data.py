"""Generate 250 SIMULATED disaster reports for demonstration/testing."""
import csv, random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

LOCATIONS = [
    "Red Hills, Chennai","Tambaram, Chennai","Velachery, Chennai",
    "Koyambedu, Chennai","Anna Nagar, Chennai","Adyar, Chennai",
    "Vizag Port Area","Kakinada","Rajahmundry","Vijayawada",
    "Warangal","Nizamabad","Guntur","Nellore","Tirupati",
    "Kodaikanal","Ooty","Coimbatore","Madurai","Tiruchirappalli"
]
INCIDENT_TYPES = [
    "Flood","Cyclone","Landslide","Heavy Rainfall","Storm Surge",
    "Urban Flooding","Road Blockage","Infrastructure Damage",
    "Power Disruption","Evacuation"
]
SOURCE_TYPES = ["Citizen","Social Media","NGO","Government Alert","News Media"]

TEMPLATES = {
    "Flood": [
        "Floodwaters have entered residential areas near {loc}. Approximately {n} people are stranded.",
        "Severe flooding reported at {loc}. Roads submerged, vehicles stuck.",
        "Water level rising rapidly near {loc}. {n} households affected.",
        "Flash flood warning near {loc}. Residents evacuating.",
    ],
    "Cyclone": [
        "Cyclone approaching {loc}. Winds at high speed, trees uprooted.",
        "Severe cyclonic storm hitting {loc}. {n} people moved to shelters.",
        "Cyclone damage reported at {loc}. Rooftops blown off.",
    ],
    "Landslide": [
        "Landslide blocks main highway near {loc}. Traffic disrupted.",
        "Hillside collapse reported near {loc}. {n} people missing.",
        "Mudslide at {loc} following heavy rainfall. Roads cut off.",
    ],
    "Heavy Rainfall": [
        "Heavy rainfall continuing at {loc} for the past 12 hours.",
        "Incessant rain at {loc}. Low-lying areas at risk.",
        "Red alert issued for {loc} due to heavy rainfall.",
    ],
    "Urban Flooding": [
        "Waterlogging reported in {loc}. Drainage system overwhelmed.",
        "Streets flooded in {loc}. Commuters stranded.",
        "{n} homes waterlogged in {loc} due to blocked drains.",
    ],
    "Infrastructure Damage": [
        "Bridge damaged at {loc}. Emergency vehicles cannot pass.",
        "Power lines down at {loc}. {n} households without electricity.",
        "Road collapse reported near {loc}.",
    ],
    "Road Blockage": [
        "NH-{n} blocked near {loc} due to debris.",
        "Major road at {loc} closed. Traffic diverted.",
    ],
    "Storm Surge": [
        "Storm surge hitting coastal area near {loc}. {n} fishermen alerted.",
        "Coastal flooding due to storm surge near {loc}.",
    ],
    "Power Disruption": [
        "Power outage in {loc}. {n} areas affected.",
        "Electricity supply disrupted near {loc} due to storm.",
    ],
    "Evacuation": [
        "Evacuation underway at {loc}. {n} residents moved to relief camps.",
        "Emergency evacuation ordered for {loc}.",
    ],
}

def random_desc(itype, loc):
    return random.choice(TEMPLATES.get(itype, ["Incident reported at {loc}."])).format(
        loc=loc, n=random.randint(5, 500)
    )

def gen_timestamp(days_back=30):
    return datetime.utcnow() - timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59)
    )

reports = []
counter = 1

def add(desc, loc, itype, source, people=None, quality="GOOD", notes=""):
    global counter
    reports.append({
        "report_id": f"REP-{counter:04d}",
        "description": desc,
        "location": loc,
        "timestamp": gen_timestamp().isoformat(),
        "source_type": source,
        "people_affected": people if people is not None else random.randint(0, 300),
        "quality_status": quality,
        "quality_notes": notes,
        "incident_type": itype,
        "scenario": notes or "general",
    })
    counter += 1

# Deliberate review/demo cases
for _ in range(5):
    add(
        "Heavy rainfall has caused severe flooding near Red Hills. Water has entered houses and the main road is blocked. Around 60 people are affected.",
        "Red Hills, Chennai", "Flood", random.choice(SOURCE_TYPES), 60, "GOOD",
        "CASE1_high_confidence_flood"
    )

add("Flooding at Red Hills area. Several homes submerged. Road impassable.",
    "Red Hills, Chennai", "Flood", "Social Media", 60, "GOOD", "CASE1_high_confidence_flood")
add("Something happened near the water area. People were there.",
    "Unknown coastal area", "Flood", "Citizen", None, "NEEDS_IMPROVEMENT", "CASE2_low_confidence")
add("Bad weather somewhere in the city.", "",
    "Heavy Rainfall", "Citizen", None, "REJECTED", "CASE2_low_confidence")
add("Flood water entered houses near Red Hills.", "Red Hills, Chennai", "Flood", "Citizen", 60, "GOOD", "CASE3_duplicate")
add("Several homes in Red Hills are under water.", "Red Hills, Chennai", "Flood", "Social Media", 55, "GOOD", "CASE3_duplicate")
add("Flooding reported near Red Hills residential area.", "Red Hills, Chennai", "Flood", "NGO", 65, "GOOD", "CASE3_duplicate")
add("Cyclone wind speed at Vizag Port is 120 km/h. Minimal damage so far.",
    "Vizag Port Area", "Cyclone", "Government Alert", 200, "GOOD", "CASE4_conflicting")
add("Cyclone at Vizag is catastrophic. 500 people displaced. Speed over 200 km/h.",
    "Vizag Port Area", "Cyclone", "Social Media", 500, "GOOD", "CASE4_conflicting")
add("Flood in Chennai.", "", "Flood", "Citizen", None, "NEEDS_IMPROVEMENT", "CASE5_incomplete")
add("Landslide on highway.", "Unknown", "Landslide", "Social Media", None, "NEEDS_IMPROVEMENT", "CASE5_incomplete")
add("Severe Cyclone Mandous approaching Kakinada coast. Winds exceeding 180 km/h. Storm surge of 3-5 metres expected. 2000 people evacuated. Hospital and schools shut.",
    "Kakinada", "Cyclone", "Government Alert", 2000, "GOOD", "CASE6_high_severity_cyclone")
add("Bridge on NH-16 near Rajahmundry partially damaged due to floodwaters. Traffic diverted. Around 150 vehicles stranded.",
    "Rajahmundry", "Infrastructure Damage", "NGO", 150, "GOOD", "CASE7_medium_infra")
add("Minor waterlogging near Tambaram market area. Drains overflowing. About 20 shops affected.",
    "Tambaram, Chennai", "Urban Flooding", "Citizen", 20, "GOOD", "CASE8_low_severity")

while counter <= 250:
    loc, itype, src = random.choice(LOCATIONS), random.choice(INCIDENT_TYPES), random.choice(SOURCE_TYPES)
    ppl, desc = random.randint(0, 500), random_desc(itype, loc)
    q = random.choices(["GOOD", "NEEDS_IMPROVEMENT", "REJECTED"], weights=[0.70, 0.20, 0.10])[0]
    notes = "general"
    if q == "NEEDS_IMPROVEMENT":
        if random.random() < 0.5:
            loc, notes = "", "missing_location"
        else:
            desc, notes = desc[:15], "short_description"
    add(desc, loc, itype, src, ppl, q, notes)

out = Path(__file__).resolve().parent / "demo_reports.csv"
with out.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "report_id","description","location","timestamp","source_type",
        "people_affected","quality_status","quality_notes","incident_type","scenario"
    ])
    writer.writeheader()
    writer.writerows(reports)

print(f"Generated {len(reports)} SIMULATED demo reports -> {out}")
