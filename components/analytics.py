import streamlit as st
import pandas as pd
import json
from collections import Counter
from database.models import Report, IncidentCluster, Incident

def render_analytics(db):
    if st.session_state.get("role") != "responder":
        st.error("Only authorized responders can view Analytics.")
        st.stop()
        
    st.markdown('<div class="hero"><h1>Responder Analytics</h1><div class="muted">Overview of system performance.</div></div>', unsafe_allow_html=True)
    
    reports = db.query(Report).all()
    clusters = db.query(IncidentCluster).all()
    incidents = db.query(Incident).all()
    
    if not reports:
        st.info("No data available.")
        return
        
    # 1. SYSTEM OVERVIEW
    total_raw_reports = len(reports)
    total_clusters = len(clusters)
    pending_clusters = sum(1 for c in clusters if c.status == "PENDING")
    verified_clusters = sum(1 for c in clusters if c.status in ("VERIFIED", "AUTO_VERIFIED"))
    rejected_clusters = sum(1 for c in clusters if c.status == "REJECTED")
    
    st.markdown("### System Overview")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Raw Reports", total_raw_reports)
    c2.metric("Total Incident Clusters", total_clusters)
    c3.metric("Pending Verification", pending_clusters)
    c4.metric("Verified Clusters", verified_clusters)
    c5.metric("Rejected Clusters", rejected_clusters)
    
    # 2. DISASTER TYPE DISTRIBUTION
    st.markdown("### Incident Overview")
    col_ov1, col_ov2 = st.columns(2)
    
    with col_ov1:
        st.markdown("**Disaster Type Distribution**")
        types = [c.disaster_type for c in clusters if c.disaster_type]
        if types:
            type_counts = Counter(types)
            df_types = pd.DataFrame(type_counts.items(), columns=["Disaster Type", "Count"]).set_index("Disaster Type")
            st.bar_chart(df_types)
        else:
            st.write("No data available")
            
    # 3. VERIFICATION STATUS
    with col_ov2:
        st.markdown("**Verification Status**")
        if clusters:
            status_counts = Counter([c.status for c in clusters])
            df_status = pd.DataFrame(status_counts.items(), columns=["Status", "Count"]).set_index("Status")
            st.bar_chart(df_status)
        else:
            st.write("No data available")
            
    # AI Assessment
    st.markdown("### AI Assessment")
    col_ai1, col_ai2 = st.columns(2)
    
    with col_ai1:
        st.markdown("**Confidence Distribution**")
        conf_labels = []
        for c in clusters:
            if c.confidence >= 0.75: conf_labels.append("High")
            elif c.confidence >= 0.50: conf_labels.append("Medium")
            elif c.confidence >= 0.30: conf_labels.append("Low")
            else: conf_labels.append("Very Low")
            
        if conf_labels:
            conf_counts = Counter(conf_labels)
            df_conf = pd.DataFrame(conf_counts.items(), columns=["Confidence", "Count"]).set_index("Confidence")
            st.bar_chart(df_conf)
            avg_conf = sum(c.confidence for c in clusters) / len(clusters)
            st.write(f"**Average Confidence:** {avg_conf:.0%}")
        else:
            st.write("No data available")
            
    with col_ai2:
        st.markdown("**AI-Estimated Severity Distribution**")
        if clusters:
            sev_counts = Counter([c.severity or "UNKNOWN" for c in clusters])
            df_sev = pd.DataFrame(sev_counts.items(), columns=["Severity", "Count"]).set_index("Severity")
            st.bar_chart(df_sev)
        else:
            st.write("No data available")
            
    # 4. PRIORITY DISTRIBUTION
    st.markdown("### Responder Prioritization")
    st.markdown("**Responder Priority Distribution**")
    if clusters:
        pri_counts = Counter([str(c.priority) for c in clusters])
        df_pri = pd.DataFrame(pri_counts.items(), columns=["Priority", "Count"]).set_index("Priority")
        st.bar_chart(df_pri)
    else:
        st.write("No data available")
        
    # 7. CLUSTERING ANALYSIS
    st.markdown("### Incident Clustering")
    if clusters:
        single_report = sum(1 for c in clusters if c.report_count == 1)
        multi_report = sum(1 for c in clusters if c.report_count > 1)
        grouped_reports = sum(c.report_count for c in clusters if c.report_count > 1)
        avg_reports = total_raw_reports / len(clusters) if len(clusters) > 0 else 0
        
        st.write(f"- **Total raw reports:** {total_raw_reports}")
        st.write(f"- **Total incident clusters:** {total_clusters}")
        st.write(f"- **Single-report clusters:** {single_report}")
        st.write(f"- **Multi-report clusters:** {multi_report}")
        st.write(f"- **Reports grouped into multi-report clusters:** {grouped_reports}")
        st.write(f"- **Average reports per incident cluster:** {avg_reports:.2f}")
        st.caption("Multiple related reports may be consolidated into a single incident cluster to reduce duplicate handling.")
    else:
        st.write("No data available")
        
    # 9. ASSESSMENT SCORE OVERVIEW
    st.markdown("### Assessment Score Overview")
    if incidents:
        qualities = []
        consistencies = []
        completenesses = []
        evidences = []
        confidences = []
        
        for inc in incidents:
            if inc.confidence_breakdown:
                try:
                    bd = json.loads(inc.confidence_breakdown)
                    if "quality" in bd: qualities.append(float(bd["quality"]))
                    if "consistency" in bd: consistencies.append(float(bd["consistency"]))
                except Exception:
                    pass
            completenesses.append(inc.completeness_score)
            evidences.append(inc.evidence_score)
            confidences.append(inc.confidence)
            
        avg_qual = (sum(qualities) / len(qualities)) if qualities else None
        avg_comp = (sum(completenesses) / len(completenesses)) if completenesses else None
        avg_evid = (sum(evidences) / len(evidences)) if evidences else None
        avg_cons = (sum(consistencies) / len(consistencies)) if consistencies else None
        avg_conf = (sum(confidences) / len(confidences)) if confidences else None
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.write(f"**Average Quality:** {f'{avg_qual:.0%}' if avg_qual is not None else 'No data available'}")
            st.write(f"**Average Completeness:** {f'{avg_comp:.0%}' if avg_comp is not None else 'No data available'}")
            st.write(f"**Average Evidence:** {f'{avg_evid:.0%}' if avg_evid is not None else 'No data available'}")
            st.write(f"**Average Consistency:** {f'{avg_cons:.0%}' if avg_cons is not None else 'No data available'}")
            st.write(f"**Average Confidence:** {f'{avg_conf:.0%}' if avg_conf is not None else 'No data available'}")
            
        st.caption("Averages are based on analyzed records only.")
    else:
        st.write("No data available")
        
    # 8. LOCATION ANALYSIS
    st.markdown("### Top Incident Locations")
    if clusters:
        loc_counts = Counter([c.canonical_location.title() if c.canonical_location else "Unknown" for c in clusters])
        top_locs = loc_counts.most_common(10)
        
        table_data = []
        for loc, count in top_locs:
            # Count the reports in this location
            # canonical_location matching
            loc_clusters = [c for c in clusters if (c.canonical_location.title() if c.canonical_location else "Unknown") == loc]
            rep_count = sum(c.report_count for c in loc_clusters)
            table_data.append({"Location": loc, "Incident Clusters": count, "Reports": rep_count})
            
        st.table(pd.DataFrame(table_data))
    else:
        st.write("No data available")
        
    st.markdown("---")
    st.caption("Analytics are calculated from the current ClimateResQ AI database.")
    st.caption("AI-estimated severity and confidence are decision-support indicators and do not replace authorized responder verification.")
