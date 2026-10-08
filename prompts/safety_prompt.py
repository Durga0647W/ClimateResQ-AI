SAFETY_RECOMMENDATIONS = {
    "Flood": ["Move to higher ground if water is rising.","Do not walk or drive through floodwaters.","Disconnect electrical appliances.","Follow official evacuation instructions.","Move vulnerable people to safety first."],
    "Cyclone": ["Stay indoors away from windows.","Avoid coastal and open areas.","Monitor official warnings.","Secure loose objects.","Move to a designated cyclone shelter if advised."],
    "Landslide": ["Avoid unstable slopes and hillside roads.","Evacuate if ordered.","Stay away from affected roads.","Watch for cracking or rumbling sounds.","Report blocked roads."],
    "Heavy Rainfall": ["Avoid low-lying areas and underpasses.","Do not cross flooded roads or streams.","Stay updated with weather alerts.","Keep drainage around your home clear."],
    "Storm Surge": ["Evacuate coastal areas when warned.","Move to higher ground before surge arrives.","Do not return until authorities declare it safe.","Avoid beaches and seafront areas."],
    "Urban Flooding": ["Avoid waterlogged streets.","Keep documents in waterproof bags.","Report blocked drains.","Do not let children play in floodwater."],
    "Infrastructure Damage": ["Avoid damaged bridges and roads.","Follow diversion routes.","Report damage to emergency services."],
    "Evacuation": ["Follow official evacuation routes.","Carry essential documents and medicines.","Do not return until cleared.","Register at relief camps if needed."],
    "Fire": ["Evacuate immediately if instructed.", "Do not use elevators.", "Stay low if there is smoke.", "Call emergency services.", "Do not re-enter the building."],
    "Earthquake": ["Drop, Cover, and Hold On.", "Stay away from glass and windows.", "If outdoors, move away from buildings and trees.", "Expect aftershocks.", "Do not use elevators."],
    "Storm": ["Stay indoors away from windows.", "Avoid coastal and open areas.", "Monitor official warnings.", "Secure loose objects.", "Move to a designated shelter if advised."],
    "Power Disruption": ["Use flashlights instead of candles to avoid fire hazards.", "Keep refrigerators closed to preserve food.", "Disconnect appliances to avoid power surge damage when power returns.", "Do not use gas stoves for heating."],
}

def get_safety_recommendations(incident_type):
    # case-insensitive search
    for k, v in SAFETY_RECOMMENDATIONS.items():
        if k.lower() == incident_type.lower():
            return v
    return ["Follow official emergency instructions.","Stay away from affected areas.","Contact local emergency services if in danger."]
