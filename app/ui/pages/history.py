import streamlit as st
from app.ui.theme import page_header
from app.database.db import get_recent_analyses, clear_analysis_history, clear_action_history, clear_approval_history
from app.ui.shared import load_investigation_by_task


def render():
    page_header("HISTORY","Institutional memory","Every connected Company Workspace analysis and AI investigation is persisted here.")
    history=get_recent_analyses(limit=50)
    if st.button("Clear all OS history",type="secondary"): st.session_state.confirm_clear_history=True
    if st.session_state.get("confirm_clear_history"):
        st.warning("This removes saved investigations, approvals and action history. Company datasets and .env are not touched.")
        a,b=st.columns(2)
        with a:
            if st.button("Confirm clear history",type="primary"):
                clear_analysis_history(); clear_action_history(); clear_approval_history(); st.session_state.current_investigation=None; st.session_state.confirm_clear_history=False; st.rerun()
        with b:
            if st.button("Cancel"): st.session_state.confirm_clear_history=False; st.rerun()
    if not history: st.info("No previous analyses yet."); return
    for item in history:
        ts=(item.get("created_at") or item.get("timestamp") or "").replace("T"," ")[:19]
        query=item.get("query_text",""); insights=item.get("insights") or {}; badge="COMPANY" if item.get("context_type")=="company" else "GENERAL"
        with st.expander(f"{badge} · {ts} · {query[:80]}"):
            st.markdown(f'<div class="panel"><div class="eyebrow">{badge} · {item.get("model","NVIDIA Nemotron")}</div><h4>{query}</h4><p>{insights.get("executive_summary","No summary available.")}</p></div>',unsafe_allow_html=True)
            a,b=st.columns(2)
            with a:
                st.markdown("**Key insights**")
                for x in insights.get("key_insights",insights.get("key_findings",[])): st.markdown(f"- {x}")
            with b:
                st.markdown("**Risks / limitations**")
                for x in insights.get("risks",[]): st.markdown(f"- {x}")
            if st.button("Load as active investigation",key=f"load_{item['id']}"):
                load_investigation_by_task(item["task_id"]); st.rerun()
            with st.expander("Recommendations"):
                for i,x in enumerate(insights.get("recommended_actions",[]),1): st.markdown(f"{i}. {x}")
            with st.expander("Verified data"):
                st.json(item.get("result") or {})
