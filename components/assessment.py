import json
import streamlit as st
from database.models import Report, Incident

def render_assessment_details(cluster, dbx):
    r_ids = json.loads(cluster.related_report_ids or "[]")
    if not r_ids:
        return
        
    rep = dbx.query(Report).filter(Report.report_id == r_ids[0]).first()
    inc = dbx.query(Incident).filter(Incident.report_id == r_ids[0]).first()
    
    if not rep or not inc:
        return
        
    with st.expander("🔍 View AI Assessment Details"):
        st.info("The following deterministic calculations and AI extractions are provided for decision support. AI recommendation is advisory. Final verification must be performed by an authorized responder.")
        
        breakdown = json.loads(inc.confidence_breakdown) if inc.confidence_breakdown else {}
        
        # 1. REPORT QUALITY
        st.markdown("### Report Quality")
        q_score = breakdown.get("quality", "Not available")
        st.markdown(f"**Score:** {q_score}")
        st.markdown(f"**Label:** {rep.quality_status}")
        
        issues = rep.quality_notes.split("; ") if rep.quality_notes else []
        issues = [i for i in issues if i.strip()]
        if not issues:
            st.markdown("✓ No quality issues detected")
        else:
            for issue in issues:
                st.markdown(f"⚠ {issue}")
                
        st.markdown("---")
        
        # 2. COMPLETENESS
        st.markdown("### Completeness")
        st.markdown(f"**COMPLETENESS SCORE: {inc.completeness_score:.2f}**")
        
        missing = json.loads(inc.missing_info) if inc.missing_info else []
        missing_lower = [m.lower() for m in missing]
        
        fields = [
            ("Location", 0.30),
            ("Incident Type", 0.25),
            ("Impact", 0.20),
            ("Event Time", 0.10),
            ("People Affected", 0.10),
            ("Severity Indicators", 0.05)
        ]
        
        total_comp = 0.0
        for name, weight in fields:
            # Check if this field is in the missing list
            is_missing = any(name.lower() in m for m in missing_lower)
            if not is_missing:
                st.markdown(f"{name:<20} {weight:.2f} ✓")
                total_comp += weight
            else:
                st.markdown(f"{name:<20} 0.00 ✗")
                
        st.markdown(f"**Total:** {total_comp:.2f} (may have minor rounding differences with stored {inc.completeness_score:.2f})")
        
        st.markdown("---")
        
        # 3. EVIDENCE / CORROBORATION
        st.markdown("### Corroborating Reports")
        ev_count = cluster.report_count - 1
        st.markdown(f"**Related reports:** {ev_count}")
        st.markdown(f"**Evidence score:** {inc.evidence_score:.2f}")
        st.markdown(f"**Calculation:** min({ev_count} × 0.25, 1.0) = {inc.evidence_score:.2f}")
        st.caption("Corroborating reports increase confidence but do not establish ground truth.")
        
        st.markdown("---")
        
        # 4. CONSISTENCY
        st.markdown("### Consistency")
        cons_score = breakdown.get("consistency", "Not available")
        contradictions = json.loads(inc.contradictions) if inc.contradictions else []
        c_count = len(contradictions)
        
        st.markdown(f"**Consistency flags:** {c_count}")
        st.markdown(f"**Consistency score:** {cons_score}")
        if cons_score != "Not available":
            st.markdown(f"**Calculation:** max(0.0, 1.0 - 0.25 × {c_count}) = {cons_score}")
        
        if c_count == 0:
            st.markdown("✓ No contradictions detected")
        else:
            for c in contradictions:
                st.markdown(f"⚠ {c}")
                
        st.markdown("---")
        
        # 5. CONFIDENCE CALCULATION
        st.markdown("### Confidence Calculation")
        
        try:
            comp_contrib = 0.35 * inc.completeness_score
            ev_contrib = 0.30 * inc.evidence_score
            qual_contrib = 0.25 * float(q_score)
            cons_contrib = 0.10 * float(cons_score)
            total_conf = comp_contrib + ev_contrib + qual_contrib + cons_contrib
            
            st.markdown(f"**Completeness:** 0.35 × {inc.completeness_score:.2f} = {comp_contrib:.3f}")
            st.markdown(f"**Evidence:** 0.30 × {inc.evidence_score:.2f} = {ev_contrib:.3f}")
            st.markdown(f"**Quality:** 0.25 × {float(q_score):.2f} = {qual_contrib:.3f}")
            st.markdown(f"**Consistency:** 0.10 × {float(cons_score):.2f} = {cons_contrib:.3f}")
            st.markdown("--------------------------------")
            st.markdown(f"**Final confidence:** {total_conf:.3f} (Stored as {inc.confidence:.3f})")
            
            if inc.confidence >= 0.75: label = "HIGH"
            elif inc.confidence >= 0.50: label = "MEDIUM"
            elif inc.confidence >= 0.30: label = "LOW"
            else: label = "VERY LOW"
            
            st.markdown(f"**Confidence level:** {label}")
        except Exception:
            st.markdown(f"**Final confidence:** {inc.confidence}")
            
        st.markdown("---")
        
        # 6. PLAIN LANGUAGE EXPLANATION
        st.markdown("### Confidence Explanation")
        st.write("Confidence is based on report completeness, report quality, corroborating reports and internal consistency.")
        
        st.write("**Confidence was increased by:**")
        if inc.completeness_score >= 0.8: st.write("• Complete incident information")
        if q_score != "Not available" and float(q_score) >= 0.7: st.write("• Good report quality")
        if ev_count > 0: st.write(f"• {ev_count} corroborating report(s)")
        if c_count == 0: st.write("• No consistency conflicts")
        
        st.write("**Confidence was limited by:**")
        for m in missing:
            st.write(f"• {m} is missing")
        if q_score != "Not available" and float(q_score) < 0.7: st.write("• Poor or fair report quality")
        if ev_count == 0: st.write("• No corroborating reports")
        for c in contradictions:
            st.write(f"• Contradiction: {c}")
            
        st.markdown("---")
        
        # 7. AI-ESTIMATED SEVERITY
        st.markdown("### AI-Estimated Severity")
        st.markdown(f"**AI-ESTIMATED SEVERITY:** {inc.severity}")
        
        st.write("**Relevant extracted information:**")
        if inc.incident_type: st.write(f"• Incident type: {inc.incident_type}")
        if inc.impact: st.write(f"• Impact: {inc.impact}")
        if inc.people_affected is not None: st.write(f"• Approximately {inc.people_affected} people affected")
        indicators = json.loads(inc.severity_indicators) if inc.severity_indicators else []
        for ind in indicators:
            st.write(f"• {ind}")
            
        st.caption("AI-Estimated Severity is an AI assessment of the submitted report. It is not confirmed ground truth.")
        
        st.markdown("---")
        
        # 8. PRIORITY CALCULATION
        st.markdown("### Priority Assessment")
        st.markdown(f"**AI-Estimated Severity:** {inc.severity}")
        st.markdown(f"**Confidence:** {label if 'label' in locals() else 'Unknown'}")
        st.markdown(f"**Priority:** {inc.priority}")
        
        try:
            reasons = json.loads(inc.priority_reasons)
            if reasons:
                st.markdown("**Reason:**")
                for r in reasons:
                    st.markdown(f"• {r}")
        except Exception:
            pass
            
        st.markdown("---")
        
        # 9. AI RECOMMENDATION
        st.markdown("### AI Recommendation")
        rec = "LIKELY VALID" if inc.confidence > 0.6 else "NEEDS REVIEW"
        st.markdown(f"**AI RECOMMENDATION:** {rec}")
        st.write("**Basis:**")
        st.write(f"• Confidence: {inc.confidence:.0%}")
        if float(q_score) >= 0.7: st.write("• Good report quality")
        if inc.completeness_score >= 0.8: st.write("• Complete incident information")
        if ev_count > 0: st.write(f"• {ev_count} corroborating report(s)")
        if c_count == 0: st.write("• No consistency conflicts")
        
        st.caption("AI recommendation is advisory. Final verification must be performed by an authorized responder.")
