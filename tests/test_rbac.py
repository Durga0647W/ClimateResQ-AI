import sys
from pathlib import Path
from streamlit.testing.v1 import AppTest
from database.database import init_db, get_db
from database.models import Report, IncidentCluster, VerificationRecord
from utils.pipeline import run_pipeline
from services.location_service import normalize_location
from datetime import datetime, timedelta
import pytest
import json

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    db = get_db()
    db.query(VerificationRecord).delete()
    db.query(IncidentCluster).delete()
    db.query(Report).delete()
    db.commit()
    yield db
    db.query(VerificationRecord).delete()
    db.query(IncidentCluster).delete()
    db.query(Report).delete()
    db.commit()
    db.close()

def test_location_normalization():
    assert normalize_location("Tambaram") == "tambaram"
    assert normalize_location("Tambaram, Chennai") == "tambaram"
    assert normalize_location("Tambaram Chennai") == "tambaram"
    assert normalize_location("Tambaram, Chennai, Tamil Nadu") == "tambaram"
    assert normalize_location("Anna Nagar, Chennai") == "anna nagar"
    assert normalize_location("Adyar, Chennai") == "adyar"
    assert normalize_location("Chennai") == "chennai" # Fallback if only stopword exists

def test_different_localities_remain_different():
    assert normalize_location("Tambaram, Chennai") != normalize_location("Adyar, Chennai")

def test_login_and_logout():
    at = AppTest.from_file(str(root / "app.py")).run(timeout=10)
    # Login as citizen
    at.text_input[0].input("citizen").run()
    at.text_input[1].input("citizen123").run()
    at.button[0].click().run()
    assert at.session_state["authenticated"] == True
    assert at.session_state["role"] == "citizen"

def test_citizen_cannot_access_verification_center():
    at = AppTest.from_file(str(root / "app.py")).run(timeout=10)
    at.text_input[0].input("citizen").run()
    at.text_input[1].input("citizen123").run()
    at.button[0].click().run()
    assert "🔎 Verification Center" not in at.radio[0].options

def test_responder_can_access_verification_center():
    at = AppTest.from_file(str(root / "app.py")).run(timeout=10)
    at.text_input[0].input("responder").run()
    at.text_input[1].input("responder123").run()
    at.button[0].click().run()
    assert "🔎 Verification Center" in at.radio[0].options

def test_ai_status_pending(setup_db):
    result = run_pipeline("Huge fire in the building with people inside.", "Tambaram", datetime.utcnow(), "Citizen", 10, setup_db, reporter_id="citizen_demo")
    
    cluster = setup_db.query(IncidentCluster).filter(IncidentCluster.cluster_id == result["cluster_id"]).first()
    assert cluster is not None
    assert cluster.status == "PENDING"
    assert cluster.report_count == 1

def test_similar_flood_reports_clustered(setup_db):
    res1 = run_pipeline("Water level rising fast in Tambaram", "Tambaram", datetime.utcnow(), "Citizen", 0, setup_db)
    res2 = run_pipeline("Flooding in Tambaram Chennai", "Tambaram, Chennai", datetime.utcnow() + timedelta(minutes=5), "Citizen", 0, setup_db)
    
    assert res1["cluster_id"] == res2["cluster_id"]
    cluster = setup_db.query(IncidentCluster).filter(IncidentCluster.cluster_id == res1["cluster_id"]).first()
    assert cluster.report_count == 2
    
def test_different_disaster_types_not_clustered(setup_db):
    res1 = run_pipeline("Water level rising fast in Tambaram", "Tambaram", datetime.utcnow(), "Citizen", 0, setup_db)
    res2 = run_pipeline("Major fire outbreak in Tambaram", "Tambaram", datetime.utcnow() + timedelta(minutes=5), "Citizen", 0, setup_db)
    
    assert res1["cluster_id"] != res2["cluster_id"]

def test_responder_cannot_verify_own_report(setup_db):
    at = AppTest.from_file(str(root / "app.py")).run(timeout=10)
    at.text_input[0].input("responder").run()
    at.text_input[1].input("responder123").run()
    at.button[0].click().run()
    
    rep = Report(report_id="REP-999", description="Self report", reporter_id="responder_01", location="Test", timestamp=datetime.utcnow())
    inc = IncidentCluster(cluster_id="CLU-999", canonical_location="test", display_location="Test", disaster_type="Fire", status="PENDING", related_report_ids='["REP-999"]', latest_report_at=datetime.utcnow(), priority="P1", severity="HIGH")
    rep.cluster_id = "CLU-999"
    setup_db.add(rep)
    setup_db.add(inc)
    setup_db.commit()

    at.radio[0].set_value("🔎 Verification Center").run()
    
    verify_btn = next((b for b in at.button if b.label == "✓ VERIFY INCIDENT"), None)
    assert verify_btn is not None
    verify_btn.click().run()
    
    assert any("You cannot verify a report submitted by your own account" in str(e.value) for e in at.error)
    setup_db.refresh(inc)
    assert inc.status == "PENDING"

def test_public_verified_incidents(setup_db):
    inc = IncidentCluster(cluster_id="CLU-VERIFIED", canonical_location="testloc", display_location="TestLoc", disaster_type="Fire", status="VERIFIED", confidence=0.9, severity="HIGH", priority="P1")
    setup_db.add(inc)
    setup_db.commit()

    at = AppTest.from_file(str(root / "app.py")).run(timeout=10)
    at.text_input[0].input("citizen").run()
    at.text_input[1].input("citizen123").run()
    at.button[0].click().run()
    
    at.radio[0].set_value("🚨 Verified Incidents").run()
    found = False
    for m in at.markdown:
        if m.value and "Fire" in m.value and "TestLoc" in m.value:
            found = True
    assert found

def test_kakinada_coimbatore_different_type_no_cluster(setup_db):
    res1 = run_pipeline("Severe cyclonic storm hitting Kakinada. 330 people moved to shelters.", "Kakinada", datetime.utcnow(), "Citizen", 330, setup_db)
    res2 = run_pipeline("Electricity supply disrupted near Coimbatore due to storm.", "Coimbatore", datetime.utcnow() + timedelta(minutes=5), "Citizen", 0, setup_db)
    assert res1["cluster_id"] != res2["cluster_id"]

def test_unknown_location_no_match(setup_db):
    res1 = run_pipeline("Flooding in the streets.", "unknown", datetime.utcnow(), "Citizen", 0, setup_db)
    res2 = run_pipeline("Water level rising fast.", "unknown", datetime.utcnow() + timedelta(minutes=5), "Citizen", 0, setup_db)
    assert res1["cluster_id"] != res2["cluster_id"]

def test_tambaram_chennai_clusters_with_tambaram(setup_db):
    res1 = run_pipeline("Water level rising fast in Tambaram", "Tambaram", datetime.utcnow(), "Citizen", 0, setup_db)
    res2 = run_pipeline("Flooding in Tambaram Chennai", "Tambaram, Chennai", datetime.utcnow() + timedelta(minutes=5), "Citizen", 0, setup_db)
    assert res1["cluster_id"] == res2["cluster_id"]

def test_tambaram_flood_tambaram_fire_no_cluster(setup_db):
    res1 = run_pipeline("Water level rising fast in Tambaram", "Tambaram", datetime.utcnow(), "Citizen", 0, setup_db)
    res2 = run_pipeline("Major fire outbreak in Tambaram", "Tambaram", datetime.utcnow() + timedelta(minutes=5), "Citizen", 0, setup_db)
    assert res1["cluster_id"] != res2["cluster_id"]

def test_tambaram_flood_coimbatore_flood_no_cluster(setup_db):
    res1 = run_pipeline("Water level rising fast in Tambaram", "Tambaram", datetime.utcnow(), "Citizen", 0, setup_db)
    res2 = run_pipeline("Water level rising fast in Coimbatore", "Coimbatore", datetime.utcnow() + timedelta(minutes=5), "Citizen", 0, setup_db)
    assert res1["cluster_id"] != res2["cluster_id"]

def test_latest_report_updates_when_joining_cluster(setup_db):
    t1 = datetime.utcnow() - timedelta(minutes=10)
    t2 = datetime.utcnow()
    res1 = run_pipeline("Water level rising fast in Tambaram", "Tambaram", t1, "Citizen", 0, setup_db)
    res2 = run_pipeline("Flooding in Tambaram Chennai", "Tambaram, Chennai", t2, "Citizen", 0, setup_db)
    assert res1["cluster_id"] == res2["cluster_id"]
    cluster = setup_db.query(IncidentCluster).filter(IncidentCluster.cluster_id == res1["cluster_id"]).first()
    assert cluster.latest_report_at == t2

def test_no_raw_html_in_cluster_headers():
    at = AppTest.from_file(str(root / "app.py")).run(timeout=10)
    at.text_input[0].input("responder").run()
    at.text_input[1].input("responder123").run()
    at.button[0].click().run()
    
    # Just verify the page loads and check if any raw span is found in expander labels
    at.radio[0].set_value("🔎 Verification Center").run()
    for e in at.expander:
        assert "<span" not in e.label
        assert "class=\"badge" not in e.label

def test_general_safety_intent_flood(setup_db):
    from services.assistant_service import answer_question
    ans = answer_question("Where should I go during a flood?", setup_db)
    assert "safety guidance" in ans["answer"].lower()
    assert "higher ground" in ans["answer"].lower()

def test_general_safety_intent_cyclone(setup_db):
    from services.assistant_service import answer_question
    ans = answer_question("How do I stay safe during a cyclone?", setup_db)
    assert "safety guidance" in ans["answer"].lower()
    assert "indoors" in ans["answer"].lower()

def test_general_safety_intent_fire(setup_db):
    from services.assistant_service import answer_question
    ans = answer_question("What should I do during a fire?", setup_db)
    assert "safety guidance" in ans["answer"].lower()
    assert "evacuate" in ans["answer"].lower()

def test_general_safety_intent_landslide(setup_db):
    from services.assistant_service import answer_question
    ans = answer_question("Where can I take shelter during a landslide?", setup_db)
    assert "safety guidance" in ans["answer"].lower()
    assert "unstable" in ans["answer"].lower()

def test_general_safety_intent_earthquake(setup_db):
    from services.assistant_service import answer_question
    ans = answer_question("What should I do during an earthquake?", setup_db)
    assert "safety guidance" in ans["answer"].lower()
    assert "drop, cover" in ans["answer"].lower()

def test_general_safety_intent_storm(setup_db):
    from services.assistant_service import answer_question
    ans = answer_question("Where should I go during a storm?", setup_db)
    assert "safety guidance" in ans["answer"].lower()
    assert "indoors" in ans["answer"].lower()

def test_general_safety_intent_heavy_rainfall(setup_db):
    from services.assistant_service import answer_question
    ans = answer_question("What precautions should I take during heavy rainfall?", setup_db)
    assert "safety guidance" in ans["answer"].lower()
    assert "low-lying" in ans["answer"].lower()

def test_general_safety_intent_power_disruption(setup_db):
    from services.assistant_service import answer_question
    ans = answer_question("What should I do during a power outage?", setup_db)
    assert "safety guidance" in ans["answer"].lower()
    assert "flashlights" in ans["answer"].lower()

def test_safety_and_current_incident(setup_db):
    from services.assistant_service import answer_question
    ans = answer_question("What should I do if I am in Tambaram during flooding?", setup_db)
    # The new requirement specifies it should NOT query the DB automatically
    assert "safety guidance" in ans["answer"].lower()
    assert "separately check" in ans["answer"].lower()

def test_safety_ambiguous_disaster(setup_db):
    from services.assistant_service import answer_question
    ans = answer_question("What should I do during this disaster?", setup_db)
    assert "What type of disaster" in ans["answer"]

def test_assistant_verified_incident_query(setup_db):
    from services.assistant_service import answer_question
    ans = answer_question("Which incidents are verified?", setup_db)
    assert "verified incident" in ans["answer"].lower() or "no matching verified incident" in ans["answer"].lower()
    
def test_assistant_pending_incident_query(setup_db):
    from services.assistant_service import answer_question
    ans = answer_question("Which incidents need verification?", setup_db)
    assert "pending incident" in ans["answer"].lower() or "no matching pending incident" in ans["answer"].lower()
    
def test_assistant_latest_incident_query(setup_db):
    from services.assistant_service import answer_question
    ans = answer_question("Show the latest incidents", setup_db)
    assert "latest incidents" in ans["answer"].lower() or "no incidents" in ans["answer"].lower()
    
def test_assistant_multi_report_query(setup_db):
    from services.assistant_service import answer_question
    ans = answer_question("How many incidents have multiple reports?", setup_db)
    assert "multiple reports" in ans["answer"].lower()

def test_assistant_location_query(setup_db):
    from services.assistant_service import answer_question
    ans = answer_question("What is happening in Tambaram right now?", setup_db)
    assert "tambaram" in ans["answer"].lower() or "matching incident cluster" in ans["answer"].lower()
    
def test_assistant_disaster_type_query(setup_db):
    from services.assistant_service import answer_question
    ans = answer_question("Are there any flood incidents?", setup_db)
    assert "flood" in ans["answer"].lower() or "matching incident cluster" in ans["answer"].lower()

def test_assistant_cluster_explanation_query(setup_db):
    from services.assistant_service import answer_question
    ans = answer_question("Why were these reports grouped? CLU-1234", setup_db)
    assert "grouped because" in ans["answer"].lower() or "could not find cluster" in ans["answer"].lower()

def test_assistant_citizen_privacy(setup_db):
    from services.assistant_service import answer_question
    ans = answer_question("What happened to my report?", setup_db, user_id="citizen1", role="citizen")
    assert "submitted" in ans["answer"].lower() or "haven't submitted" in ans["answer"].lower()

    ans_resp = answer_question("What happened to my report?", setup_db, user_id="resp1", role="responder")
    assert "primarily for citizens" in ans_resp["answer"].lower()

def test_assistant_project_explanation(setup_db):
    from services.assistant_service import answer_question
    ans = answer_question("What is ClimateResQ AI?", setup_db)
    assert "climateresq ai is an ai-powered disaster" in ans["answer"].lower()

def test_assistant_unsupported_question(setup_db):
    from services.assistant_service import answer_question
    ans = answer_question("Who won the cricket match?", setup_db)
    assert "sorry, i can only assist with" in ans["answer"].lower()

def test_assistant_unknown_related(setup_db):
    from services.assistant_service import answer_question
    ans = answer_question("Tell me about the weather in Delhi", setup_db)
    assert "don't have weather information" in ans["answer"].lower()
    
    ans2 = answer_question("What is happening in Delhi right now?", setup_db)
    assert "matching incident cluster" in ans2["answer"].lower()

def test_assistant_follow_up_context(setup_db):
    from services.assistant_service import answer_question
    history = [("user", "Tell me about CLU-9999"), ("assistant", "Cluster CLU-9999 is a flood.")]
    ans = answer_question("Why were these reports grouped?", setup_db, chat_history=history)
    assert "clu-9999" in ans["answer"].lower() or "could not find cluster" in ans["answer"].lower()

def test_user_queries_routing(setup_db):
    from services.assistant_service import answer_question
    
    # 1. "how do i survive floods?"
    ans = answer_question("how do i survive floods?", setup_db)
    assert "safety guidance" in ans["answer"].lower()
    
    # 2. "what should i do during a flood?"
    ans = answer_question("what should i do during a flood?", setup_db)
    assert "safety guidance" in ans["answer"].lower()
    
    # 3. "how can i stay safe during a cyclone?"
    ans = answer_question("how can i stay safe during a cyclone?", setup_db)
    assert "safety guidance" in ans["answer"].lower()
    
    # 4. "what should i do during an earthquake?"
    ans = answer_question("what should i do during an earthquake?", setup_db)
    assert "safety guidance" in ans["answer"].lower()
    
    # 5. "what should i do if there is a fire?"
    ans = answer_question("what should i do if there is a fire?", setup_db)
    assert "safety guidance" in ans["answer"].lower()
    
    # 6. "show me flood incidents"
    ans = answer_question("show me flood incidents", setup_db)
    assert "flood" in ans["answer"].lower() or "no matching incident clusters" in ans["answer"].lower()
    
    # 7. "how many flood incidents are there?"
    ans = answer_question("how many flood incidents are there?", setup_db)
    # the user said this should route to DATABASE_QUERY, which we mapped to DATABASE_SUMMARY
    assert "database" in ans["answer"].lower() or "flood" in ans["answer"].lower()
    
    # 8. "show verified flood incidents"
    ans = answer_question("show verified flood incidents", setup_db)
    assert "verified" in ans["answer"].lower()
    
    # 9. "are there flood incidents near Tambaram?"
    ans = answer_question("are there flood incidents near Tambaram?", setup_db)
    assert "tambaram" in ans["answer"].lower()
    
    # 10. "why was this incident verified?"
    ans = answer_question("why was this incident verified? CLU-123", setup_db)
    assert "could not find cluster" in ans["answer"].lower() or "grouped because" in ans["answer"].lower()
    
    # 11. "what is ClimateResQ AI?"
    ans = answer_question("what is ClimateResQ AI?", setup_db)
    assert "climateresq ai is an ai-powered disaster" in ans["answer"].lower()
    
    # 12. "what is the weather today?"
    ans = answer_question("what is the weather today?", setup_db)
    assert "don't have weather information" in ans["answer"].lower()

def test_structured_db_query(setup_db):
    from services.assistant_service import answer_question
    
    # 1. "which incidents are verified?"
    # -> LIST + INCIDENT_CLUSTER + VERIFIED
    ans1 = answer_question("which incidents are verified?", setup_db)
    assert "verified incident" in ans1["answer"].lower() or "no matching incident clusters" in ans1["answer"].lower()

    # 2. "how many reports are pending?"
    # -> COUNT + REPORT + PENDING
    ans2 = answer_question("how many reports are pending?", setup_db)
    assert "reports" in ans2["answer"].lower() and "there are" in ans2["answer"].lower()
    
    # 3. "how many incidents are pending?"
    # -> COUNT + INCIDENT_CLUSTER + PENDING
    ans3 = answer_question("how many incidents are pending?", setup_db)
    assert "incident clusters" in ans3["answer"].lower() and "pending" in ans3["answer"].lower()
    
    # 4. "how many reports are there in Chennai?"
    # -> COUNT + REPORT + Chennai
    ans4 = answer_question("how many reports are there in Chennai?", setup_db)
    assert "reports associated with chennai" in ans4["answer"].lower()
    
    # 5. "how many incidents are there in Chennai?"
    # -> COUNT + INCIDENT_CLUSTER + Chennai
    ans5 = answer_question("how many incidents are there in Chennai?", setup_db)
    assert "incident clusters in chennai" in ans5["answer"].lower()
    
    # 6. "show verified incidents in Chennai"
    # -> LIST + INCIDENT_CLUSTER + VERIFIED + Chennai
    ans6 = answer_question("show verified incidents in Chennai", setup_db)
    assert "matching" in ans6["answer"].lower() and "incident clusters" in ans6["answer"].lower()
    
    # 7. "how many flood reports are there?"
    # -> COUNT + REPORT + FLOOD
    ans7 = answer_question("how many flood reports are there?", setup_db)
    assert "reports" in ans7["answer"].lower()
    
    # 8. "how many flood incidents are there?"
    # -> COUNT + INCIDENT_CLUSTER + FLOOD
    ans8 = answer_question("how many flood incidents are there?", setup_db)
    assert "incident clusters" in ans8["answer"].lower()
    
    # 9. "how many pending flood reports are there in Chennai?"
    # -> COUNT + REPORT + PENDING + FLOOD + Chennai
    ans9 = answer_question("how many pending flood reports are there in Chennai?", setup_db)
    assert "reports associated with chennai" in ans9["answer"].lower()
    
    # 10. "give me the database summary"
    # -> DATABASE_SUMMARY
    ans10 = answer_question("give me the database summary", setup_db)
    assert "current database" in ans10["answer"].lower()
