EXTRACTION_SYSTEM = """You are a disaster information extraction specialist.
Extract structured data from unstructured disaster reports.
Only use information explicitly present. Do not invent missing details.
Return only valid JSON."""

def build_extraction_prompt(report_text, location, timestamp):
    return f"""Extract structured disaster information.

REPORT:
{report_text}

PROVIDED LOCATION: {location}
PROVIDED TIMESTAMP: {timestamp}

Return JSON with:
incident_type, location, event_time, people_affected, impact, description,
severity_indicators, entities, missing_information, contradictions.
Use null for unknown fields."""
