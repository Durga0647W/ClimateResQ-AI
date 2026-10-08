"""SIMULATED supporting sources. Replace with real APIs in production."""
SUPPORTING_SOURCES = [
    {"id":"SS-001","source":"Demo Weather Service","type":"weather","location":"Chennai","content":"Heavy rainfall alert: 150mm expected in 24 hours. Red alert issued for northern Chennai districts.","severity":"HIGH","date":"2026-10-06"},
    {"id":"SS-002","source":"Demo Govt Alert","type":"government","location":"Red Hills, Chennai","content":"Flood warning: Red Hills reservoir discharge increased. Low-lying areas advised to evacuate.","severity":"HIGH","date":"2026-10-06"},
    {"id":"SS-003","source":"Demo News Media","type":"news","location":"Kakinada","content":"Cyclone Mandous intensifies. Expected landfall near Kakinada coast within 18 hours.","severity":"CRITICAL","date":"2026-10-06"},
    {"id":"SS-004","source":"Demo Weather Service","type":"weather","location":"Vizag Port Area","content":"Cyclone wind speed alert: 120-150 km/h near Visakhapatnam coast.","severity":"HIGH","date":"2026-10-05"},
    {"id":"SS-005","source":"Demo Govt Alert","type":"government","location":"Rajahmundry","content":"NH-16 bridge stress monitoring elevated. Vehicles above 5T restricted.","severity":"MEDIUM","date":"2026-10-05"},
    {"id":"SS-006","source":"Demo Weather Service","type":"weather","location":"Tambaram, Chennai","content":"Moderate rainfall: 60mm in 12 hours. Minor waterlogging possible.","severity":"LOW","date":"2026-10-06"},
    {"id":"SS-007","source":"Demo News Media","type":"news","location":"Warangal","content":"Flood relief camps set up by district administration. 500 people sheltered.","severity":"MEDIUM","date":"2026-10-05"},
    {"id":"SS-008","source":"Demo Govt Alert","type":"government","location":"Vijayawada","content":"Krishna River water level rising. Flood warning for low-lying areas.","severity":"HIGH","date":"2026-10-06"},
    {"id":"SS-009","source":"Demo Weather Service","type":"weather","location":"Coimbatore","content":"Heavy rain warning for Nilgiris and adjoining districts. Landslide risk.","severity":"HIGH","date":"2026-10-06"},
    {"id":"SS-010","source":"Demo News Media","type":"news","location":"Madurai","content":"Vaigai dam shutter open. Downstream areas alerted.","severity":"MEDIUM","date":"2026-10-05"},
]

def get_relevant_sources(location: str, incident_type: str) -> list:
    loc_lower = (location or "").lower()
    results = []
    for s in SUPPORTING_SOURCES:
        if (s["location"].lower() in loc_lower or loc_lower in s["location"].lower()
            or any(w in s["content"].lower() for w in loc_lower.split(",")[:1] if w)):
            results.append(s)
    if not results:
        type_map = {
            "Cyclone": ["SS-003","SS-004"],
            "Flood": ["SS-001","SS-002","SS-008"],
            "Landslide": ["SS-009"],
            "Infrastructure Damage": ["SS-005"],
        }
        results = [s for s in SUPPORTING_SOURCES if s["id"] in type_map.get(incident_type, [])]
    return results[:3]
