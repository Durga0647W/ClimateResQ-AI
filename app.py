import json, os
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st

from database.database import init_db, get_db
from database.models import Incident, IncidentCluster, Report, VerificationRecord
from data.generate_demo_data import out as demo_csv
from utils.pipeline import run_pipeline
from services.assistant_service import answer_question
from services.llm_service import is_demo_mode
from config.settings import NVIDIA_MODEL

root = Path(__file__).resolve().parent

st.set_page_config(page_title="ClimateResQ AI", page_icon="🌪️", layout="wide", initial_sidebar_state="expanded")
init_db()

# ---------- styling ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: Inter, sans-serif; }
.stApp { background: #07111f; color: #edf4ff; }
section[data-testid="stSidebar"] { background: #0a1728; border-right: 1px solid #18304b; }
.brand { font-size: 28px; font-weight: 800; letter-spacing: -1px; }
.brand span { color: #55d6be; }
.subtitle { color:#8fa7bf; font-size:13px; margin-bottom:20px; }
.card { background:#0d1d30; border:1px solid #1b3856; border-radius:16px; padding:18px; margin-bottom:14px; }
.hero { background:linear-gradient(135deg,#0c2236,#102d43); border:1px solid #1d4965; border-radius:20px; padding:28px; margin-bottom:20px; }
.hero h1 { font-size:38px; margin:0 0 8px; }
.muted { color:#91a9bf; }
.badge { display:inline-block; padding:4px 9px; border-radius:999px; font-size:11px; font-weight:700; }
.high { background:#4b1720; color:#ff8d98; }
.medium { background:#4a3513; color:#ffc65a; }
.low { background:#12352b; color:#6ee7b7; }
.metric { font-size:30px; font-weight:800; }
.metric-label { color:#89a1b9; font-size:12px; text-transform:uppercase; letter-spacing:.7px; }
.stage { border-left:3px solid #3d7ea6; padding:10px 14px; margin:7px 0; background:#0b1a2b; border-radius:0 10px 10px 0; }
.small { font-size:12px; color:#8ea7bf; }
</style>
""", unsafe_allow_html=True)

def db():
    return get_db()

def badge(level):
    level=(level or "LOW").lower()
    return f'<span class="badge {level}">{level.upper()}</span>'

def fmt_dt(dt):
    if not dt: return "N/A"
    try:
        from datetime import datetime
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return str(dt)

def json_load(v, default):
    try: return json.loads(v) if v else default
    except Exception: return default

st.session_state.setdefault("authenticated", False)
st.session_state.setdefault("role", None)
st.session_state.setdefault("user_id", None)

if not st.session_state["authenticated"]:
    st.markdown('<div class="hero"><h1>ClimateResQ AI Login</h1></div>', unsafe_allow_html=True)
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if username == "citizen" and password == "citizen123":
                st.session_state["authenticated"] = True
                st.session_state["role"] = "citizen"
                st.session_state["user_id"] = "citizen_demo"
                st.rerun()
            elif username == "responder" and password == "responder123":
                st.session_state["authenticated"] = True
                st.session_state["role"] = "responder"
                st.session_state["user_id"] = "responder_01"
                st.rerun()
            else:
                st.error("Invalid credentials.")
    st.stop()

with st.sidebar:
    st.markdown('<div class="brand">Climate<span>ResQ</span> AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">AI-powered disaster information verification & response</div>', unsafe_allow_html=True)
    
    st.markdown(f"**Logged in as:**<br>{'Citizen' if st.session_state['role'] == 'citizen' else 'Authorized Responder'}<br>*{st.session_state['user_id']}*", unsafe_allow_html=True)
    if st.button("Logout"):
        st.session_state["authenticated"] = False
        st.session_state["role"] = None
        st.session_state["user_id"] = None
        st.rerun()

    mode = "DEMO / FALLBACK" if is_demo_mode() else "NVIDIA GENAI"
    st.info(f"Model mode: {mode}\n\n{NVIDIA_MODEL if not is_demo_mode() else 'Deterministic fallback active'}")
    
    if st.session_state["role"] == "citizen":
        nav_options = ["🏠 Command Center","📝 Report Disaster","📋 My Reports","🚨 Verified Incidents","🤖 AI Assistant","ℹ️ How It Works"]
    else:
        nav_options = ["📊 Command Center","📥 Incoming Reports","🔎 Verification Center","🚨 Active Incidents","📈 Analytics","📝 Audit Logs","🤖 AI Assistant","ℹ️ How It Works"]
        
    page = st.radio("Navigate", nav_options)
    st.markdown("---")
    st.caption("SDG 13 · Climate Action")
    st.caption("Human-in-the-loop decision support")

dbx=db()

if page=="🏠 Command Center":
    reports = dbx.query(Report).filter(Report.reporter_id==st.session_state["user_id"]).all()
    incidents = dbx.query(IncidentCluster).all()
    pending = sum(1 for r in reports if r.status != "PROCESSED")
    verified = sum(1 for i in incidents if i.status == "VERIFIED" or i.status == "AUTO_VERIFIED")
    st.markdown('<div class="hero"><h1>Citizen Safety Command Center</h1><div class="muted">Track your reports and view verified public incidents.</div></div>', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    c1.markdown(f'<div class="card"><div class="metric">{len(reports)}</div><div class="metric-label">My Reports</div></div>',unsafe_allow_html=True)
    c2.markdown(f'<div class="card"><div class="metric">{pending}</div><div class="metric-label">Pending My Reports</div></div>',unsafe_allow_html=True)
    c3.markdown(f'<div class="card"><div class="metric">{verified}</div><div class="metric-label">Public Verified Incidents</div></div>',unsafe_allow_html=True)
    st.subheader("Basic Safety Information")
    st.info("In case of immediate danger, contact local emergency services. ClimateResQ AI is a decision-support system.")

elif page=="📊 Command Center":
    total_reports = dbx.query(Report).count()
    incidents=dbx.query(IncidentCluster).order_by(IncidentCluster.created_at.desc()).all()
    total=len(incidents)
    high=sum(1 for i in incidents if i.priority=="HIGH")
    pending=sum(1 for i in incidents if i.status=="PENDING")
    verified=sum(1 for i in incidents if i.status=="VERIFIED" or i.status=="AUTO_VERIFIED")
    rejected=sum(1 for i in incidents if i.status=="REJECTED")
    escalated=sum(1 for i in incidents if i.status=="ESCALATED")
    
    st.markdown('<div class="hero"><h1>Responder Command Center</h1><div class="muted">Manage and verify disaster intelligence across all active reports.</div></div>', unsafe_allow_html=True)
    
    # Show the cluster summary
    st.markdown(f'''
    <div style="display:flex; justify-content:space-between; margin-bottom:20px; background:#1b3856; padding:15px; border-radius:10px;">
        <div style="text-align:center;"><b>RAW REPORTS</b><br><span style="font-size:24px; color:#6ee7b7;">{total_reports}</span></div>
        <div style="text-align:center;"><b>ACTIVE INCIDENT CLUSTERS</b><br><span style="font-size:24px; color:#55d6be;">{total}</span></div>
        <div style="text-align:center;"><b>PENDING VERIFICATION</b><br><span style="font-size:24px; color:#ffc65a;">{pending}</span></div>
        <div style="text-align:center;"><b>RELATED REPORTS CONSOLIDATED</b><br><span style="font-size:24px; color:#ff8d98;">{total_reports - total}</span></div>
    </div>
    ''', unsafe_allow_html=True)
    
    st.subheader("Priority incident feed")
    if incidents:
        rows=[]
        for i in incidents[:12]:
            rows.append({"Cluster ID":i.cluster_id,"Type":i.disaster_type,"Location":i.display_location,
                         "Priority":i.priority,"Severity":i.severity,"Confidence":f"{i.confidence:.0%}",
                         "Status":i.status,"Reports":i.report_count})
        import pandas as pd
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
    else:
        st.warning("No incidents yet. Use Report Disaster or seed the demo dataset.")
        if st.button("Load demo dataset", type="primary"):
            from database.seed import seed
            seed(250); st.rerun()

elif page=="📝 Report Disaster":
    st.markdown('<div class="hero"><h1>Submit Disaster Report</h1><div class="muted">Every submission passes through the ClimateResQ AI verification pipeline.</div></div>', unsafe_allow_html=True)
    with st.form("report_form"):
        c1,c2=st.columns(2)
        with c1:
            source=st.selectbox("Report source",["Citizen","Social Media","NGO","Government Alert","News Media"])
            location=st.text_input("Location",placeholder="e.g. Red Hills, Chennai")
            people=st.number_input("People affected (if known)",min_value=0,value=0)
        with c2:
            from datetime import datetime
            event_time=st.datetime_input("Incident time",value=datetime.now())
            st.caption("For this academic prototype, uploads are optional and the text pipeline is primary.")
        description=st.text_area("What happened?",height=170,placeholder="Describe the incident, damage, people affected, access conditions, etc.")
        submitted=st.form_submit_button("Run ClimateResQ AI Pipeline",type="primary",use_container_width=True)
    if submitted:
        if not description.strip():
            st.error("Please provide a report description.")
        else:
            with st.spinner("Running verification pipeline..."):
                from utils.pipeline import run_pipeline
                result=run_pipeline(description,location,event_time,source,int(people),dbx, reporter_id=st.session_state["user_id"])
            if result["final_status"]=="REJECTED":
                st.error("Report rejected during report-quality validation.")
                st.json(result["stages"]["2_quality"])
            else:
                st.success(f"Report processed. Assigned to Cluster {result['cluster_id']}.")
                st.session_state["last_result"]=result
                st.rerun()
    result=st.session_state.get("last_result")
    if result:
        if result["stages"]["9_dashboard"].get("was_added"):
            st.info("Added to existing incident cluster.")
        else:
            st.success("New incident cluster created.")
            
        st.subheader("Pipeline analysis")
        labels=[
            ("1. Report Input","1_input"),("2. Report Quality Check","2_quality"),
            ("3. GenAI Information Extraction","3_extraction"),("4. Completeness & Consistency","4_completeness"),
            ("5. Evidence & Cross-Source Verification","5_evidence"),("6. Similarity & Duplicate Detection","6_similarity"),
            ("7. Credibility / Confidence","7_confidence"),("8. Severity & Priority","8_severity"),("9. Responder Dashboard","9_dashboard")]
        for label,key in labels:
            with st.expander(label,expanded=(key in ["6_similarity","7_confidence","9_dashboard"])):
                st.json(result["stages"].get(key,{}))

elif page=="📋 My Reports":
    st.markdown('<div class="hero"><h1>My Reports</h1><div class="muted">View the status of reports you have submitted.</div></div>', unsafe_allow_html=True)
    reports = dbx.query(Report).filter(Report.reporter_id==st.session_state["user_id"]).order_by(Report.created_at.desc()).all()
    if not reports:
        st.info("You haven't submitted any reports yet.")
    for r in reports:
        with st.container():
            st.markdown(f'<div class="card"><b>{r.report_id}</b> <span class="muted"> · {r.location} · {fmt_dt(r.timestamp)}</span><br><span class="small">{r.description}</span><br><br><b>Status:</b> {r.status}</div>',unsafe_allow_html=True)
            if r.status == "PROCESSED" and r.cluster_id:
                inc = dbx.query(IncidentCluster).filter(IncidentCluster.cluster_id == r.cluster_id).first()
                if inc:
                    st.write(f"**Linked to Incident:** {inc.cluster_id}")
                    st.write(f"**Incident:** {inc.disaster_type} — {inc.display_location}")
                    st.write(f"**Incident Status:** {inc.status}")

elif page=="🚨 Verified Incidents" or page=="🚨 Active Incidents":
    st.markdown(f'<div class="hero"><h1>{"Verified Public Incidents" if page=="🚨 Verified Incidents" else "Active Incidents"}</h1><div class="muted">Browse consolidated incidents based on your access level.</div></div>', unsafe_allow_html=True)
    if page == "🚨 Verified Incidents":
        incidents=dbx.query(IncidentCluster).filter((IncidentCluster.status=="VERIFIED") | (IncidentCluster.status=="AUTO_VERIFIED")).order_by(IncidentCluster.created_at.desc()).all()
    else:
        incidents=dbx.query(IncidentCluster).order_by(IncidentCluster.created_at.desc()).all()
        
    if not incidents:
        st.info("No incidents to display.")
    else:
        types=["All"]+sorted(set(i.disaster_type for i in incidents))
        chosen=st.selectbox("Filter by incident type",types)
        filtered=[i for i in incidents if chosen=="All" or i.disaster_type==chosen]
        for i in filtered[:30]:
            with st.container():
                st.markdown(f'<div class="card"><b>🚨 {i.disaster_type}</b> &nbsp; {badge(i.priority)} <br><span class="muted">📍 {i.display_location} | 🕒 Latest report: {fmt_dt(i.latest_report_at)} | 📊 {i.report_count} supporting citizen reports</span></div>',unsafe_allow_html=True)
                with st.expander("View incident intelligence"):
                    a,b,c=st.columns(3)
                    a.metric("Confidence",f"{i.confidence:.0%}")
                    b.metric("Severity",i.severity)
                    c.metric("Priority",i.priority)
                    st.write("**Status:**",i.status)
                    if i.status == "VERIFIED":
                        st.write("✅ Verified by authorized responder")
                    import json
                    try:
                        reasons = json.loads(i.clustering_reasons)
                        st.write("**Why reports were grouped:**")
                        for r in reasons:
                            st.write(f"✓ {r}")
                    except Exception: pass
                    
                from components.assessment import render_assessment_details
                render_assessment_details(i, dbx)

elif page=="🔎 Verification Center":
    if st.session_state.get("role") != "responder":
        st.error("Only authorized responders can verify incidents.")
        st.stop()
        
    total_reports = dbx.query(Report).count()
    total = dbx.query(IncidentCluster).count()
    pending_count = dbx.query(IncidentCluster).filter(IncidentCluster.status=="PENDING").count()
    
    st.markdown('<div class="hero"><h1>Human Verification Center</h1><div class="muted">Review clustered incident recommendations and manually verify.</div></div>', unsafe_allow_html=True)
    
    # Top bar
    st.markdown(f'''
    <div style="display:flex; justify-content:space-between; margin-bottom:20px; background:#1b3856; padding:15px; border-radius:10px;">
        <div style="text-align:center;"><b>RAW REPORTS</b><br><span style="font-size:24px; color:#6ee7b7;">{total_reports}</span></div>
        <div style="text-align:center;"><b>ACTIVE INCIDENT CLUSTERS</b><br><span style="font-size:24px; color:#55d6be;">{total}</span></div>
        <div style="text-align:center;"><b>PENDING VERIFICATION</b><br><span style="font-size:24px; color:#ffc65a;">{pending_count}</span></div>
        <div style="text-align:center;"><b>RELATED REPORTS CONSOLIDATED</b><br><span style="font-size:24px; color:#ff8d98;">{total_reports - total}</span></div>
    </div>
    ''', unsafe_allow_html=True)
    
    pending = dbx.query(IncidentCluster).filter(IncidentCluster.status=="PENDING").all()
    sort_by = st.selectbox("Sort by:", ["Newest", "Highest Priority", "Highest Severity", "Most Related Reports"], index=0)
    
    def cluster_sort_key(c):
        prio = {"P1": 1, "P2": 2, "P3": 3, "P4": 4, "P5": 5}.get(c.priority, 9)
        sev = {"HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(c.severity, 9)
        ts = c.latest_report_at.timestamp() * -1 if c.latest_report_at else 0
        
        if sort_by == "Newest":
            return (ts, prio, sev)
        elif sort_by == "Highest Priority":
            return (prio, sev, ts)
        elif sort_by == "Highest Severity":
            return (sev, prio, ts)
        elif sort_by == "Most Related Reports":
            return (-c.report_count, ts)
            
        return (ts, prio, sev)
        
    pending = sorted(pending, key=cluster_sort_key)
    
    if not pending:
        st.success("No incidents currently waiting for human verification.")
    
    for i in pending:
        import json
        from datetime import datetime
        
        # Get all reports in this cluster
        r_ids = json.loads(i.related_report_ids or "[]")
        reports = dbx.query(Report).filter(Report.report_id.in_(r_ids)).order_by(Report.timestamp.desc()).all()
        if not reports: continue
        
        latest_report = reports[0]
        
        # Self-Verification Prevention
        has_self_report = any(r.reporter_id == st.session_state["user_id"] for r in reports)
        
        with st.expander(f"🚨 {i.canonical_location.upper()} | {i.disaster_type} | {len(reports)} related reports | {i.priority}", expanded=False):
            st.markdown(f"**Confidence:** {i.confidence:.0%} | **Severity:** {i.severity} | **Priority:** {badge(i.priority)}", unsafe_allow_html=True)
            
            st.markdown("### Primary / latest report:")
            st.markdown(f"**{latest_report.report_id}** — Submitted at {fmt_dt(latest_report.timestamp)}<br>_{latest_report.description}_", unsafe_allow_html=True)
            
            if len(reports) > 1:
                st.markdown("### Related reports:")
                for r in reports[1:]:
                    st.markdown(f"**{r.report_id}** — Submitted at {fmt_dt(r.timestamp)}<br>_{r.description}_", unsafe_allow_html=True)
                    
            st.markdown("### Cluster explanation:")
            try:
                reasons = json.loads(i.clustering_reasons)
                st.write(f"{len(reports)} likely related reports grouped because:")
                for r in reasons:
                    st.write(f"✓ {r}")
            except Exception: pass
            
            st.markdown("---")
            from components.assessment import render_assessment_details
            render_assessment_details(i, dbx)
            
            st.markdown("### Final Responder Decision")
            notes=st.text_area("Responder Notes",key=f"notes_{i.id}")
            x,y,z=st.columns(3)
            
            from database.models import VerificationRecord
            
            if x.button("✓ VERIFY INCIDENT",key=f"verify_{i.id}",type="primary"):
                if has_self_report:
                    st.error("You cannot verify a report submitted by your own account.")
                else:
                    i.status="VERIFIED"; i.verified_by=st.session_state["user_id"]; i.verified_at=datetime.utcnow()
                    dbx.add(VerificationRecord(incident_id=i.cluster_id,action="VERIFIED",notes=notes,performed_by=st.session_state["user_id"]))
                    dbx.commit(); st.rerun()
            if y.button("✕ REJECT",key=f"reject_{i.id}"):
                if has_self_report:
                    st.error("You cannot verify a report submitted by your own account.")
                else:
                    i.status="REJECTED"; i.verified_by=st.session_state["user_id"]; i.verified_at=datetime.utcnow()
                    dbx.add(VerificationRecord(incident_id=i.cluster_id,action="REJECTED",notes=notes,performed_by=st.session_state["user_id"]))
                    dbx.commit(); st.rerun()
            if z.button("⚠️ ESCALATE",key=f"escalate_{i.id}"):
                if has_self_report:
                    st.error("You cannot verify a report submitted by your own account.")
                else:
                    i.status="ESCALATED"; i.verified_by=st.session_state["user_id"]; i.verified_at=datetime.utcnow()
                    dbx.add(VerificationRecord(incident_id=i.cluster_id,action="ESCALATED",notes=notes,performed_by=st.session_state["user_id"]))
                    dbx.commit(); st.rerun()

elif page=="📥 Incoming Reports":
    st.markdown('<div class="hero"><h1>Incoming Reports</h1><div class="muted">Raw incoming disaster reports from all sources.</div></div>', unsafe_allow_html=True)
    reports = dbx.query(Report).order_by(Report.created_at.desc()).limit(50).all()
    if reports:
        for r in reports:
            st.markdown(f'<div class="card"><b>{r.report_id}</b> ({r.source_type}) - {r.status}<br><span class="muted">{r.location} | Reporter: {r.reporter_id} | {fmt_dt(r.timestamp)}</span><br><span class="small">{r.description}</span></div>', unsafe_allow_html=True)

elif page=="📝 Audit Logs":
    st.markdown('<div class="hero"><h1>Audit Logs & Verification Records</h1><div class="muted">History of responder verification actions.</div></div>', unsafe_allow_html=True)
    from database.models import VerificationRecord
    records = dbx.query(VerificationRecord).order_by(VerificationRecord.created_at.desc()).limit(50).all()
    if records:
        for r in records:
            st.markdown(f'<div class="card"><b>Incident Cluster: {r.incident_id}</b> | Action: {r.action} | Responder: {r.performed_by} | {fmt_dt(r.created_at)}<br><span class="small">Notes: {r.notes}</span></div>', unsafe_allow_html=True)

elif page=="📈 Analytics":
    from components.analytics import render_analytics
    render_analytics(dbx)

elif page=="🤖 AI Assistant":
    st.markdown('<div class="hero"><h1>ClimateResQ AI Assistant</h1><div class="muted">Ask about incidents in the database or request clearly labelled general safety guidance.</div></div>', unsafe_allow_html=True)
    if "chat" not in st.session_state: st.session_state.chat=[]
    for role,msg in st.session_state.chat:
        with st.chat_message(role): st.markdown(msg)
    q=st.chat_input("Ask: Which incidents need verification?")
    if q:
        st.session_state.chat.append(("user",q))
        with st.spinner("Checking incident context..."):
            from services.assistant_service import answer_question
            ans=answer_question(q, dbx, st.session_state.get('user_id'), st.session_state.get('role'), st.session_state.chat)
        st.session_state.chat.append(("assistant",ans["answer"]))
        st.rerun()

elif page=="ℹ️ How It Works":
    st.markdown('<div class="hero"><h1>How ClimateResQ AI Works</h1><div class="muted">A non-agentic, human-in-the-loop GenAI pipeline for disaster information validation.</div></div>',unsafe_allow_html=True)
    stages=[
        ("1","Citizen submits report","Citizen / app / web text report with location and timestamp."),
        ("2","AI processes report","Legibility and extraction of incident details."),
        ("3","Evidence and similarity analysis","Compare with independent sources and group similar reports into INCIDENT CLUSTERS."),
        ("4","Confidence/severity/priority","Transparent scoring prioritizes response needs based on the cluster."),
        ("5","Pending human verification","AI does not make the final verification decision. Only authorized responders can verify disaster clusters."),
        ("6","Authorized responder review","Responder evaluates clustered reports together as one event."),
        ("7","Verified / Rejected / Escalated","Final decision recorded in audit log. All related reports adopt the cluster status.")
    ]
    for n,title,desc in stages:
        st.markdown(f'<div class="stage"><b>{n}. {title}</b><br><span class="small">{desc}</span></div>',unsafe_allow_html=True)
    st.divider()
    st.subheader("GenAI vs deterministic components")
    st.markdown('''
**Important:** ClimateResQ AI is not an autonomous agent. It is a decision-support pipeline with human verification.
- **AI does not make the final verification decision.**
- **Only authorized responders can verify disaster clusters.**
- **Raw reports are organized into incidents deterministically via location/time/text similarity.**
''')
    from data.generate_demo_data import out as demo_csv
    st.subheader("Demo data")
    if demo_csv.exists():
        st.success(f"250 simulated reports are available in `{demo_csv.relative_to(root)}`.")
    st.caption("All demo incidents are explicitly simulated and should not be presented as real disaster alerts.")

dbx.close()
