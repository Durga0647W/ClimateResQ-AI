VERIFICATION_SYSTEM = """You are a disaster information verification specialist.
Compare incident data against supporting evidence. Do not invent information.
Return only valid JSON."""

def build_verification_prompt(incident, sources):
    sources_text = "\n".join(
        f"- [{s['source']}]: {s['content']}" for s in sources
    )
    return f"""Verify this incident against supporting evidence.

INCIDENT:
Type: {incident.get('incident_type')}
Location: {incident.get('location')}
Description: {incident.get('description')}
People Affected: {incident.get('people_affected')}
Severity Indicators: {incident.get('severity_indicators')}

SUPPORTING SOURCES:
{sources_text or "No supporting sources available."}

Return JSON:
{{
  "agreement_score": 0.0,
  "agreements": [],
  "disagreements": [],
  "evidence_summary": "",
  "recommendation": "VERIFIED|NEEDS_REVIEW|CONFLICTING"
}}"""
