import streamlit as st

from app.ui.theme import page_header
from app.ui.shared import current_investigation


AGENT_CATALOG = [
    ("Commander", "CEO orchestrator", "Routes the business question, selects specialists, and coordinates the investigation."),
    ("Analyst", "Business intelligence", "Computes deterministic metrics, financial signals, trends, and evidence."),
    ("Marketing", "Market intelligence", "Analyzes positioning, competitors, opportunities, and customer-facing strategy."),
    ("HR & Operations", "Operations intelligence", "Evaluates operational risks, organizational considerations, and execution priorities."),
    ("Nemotron", "Executive synthesis", "Combines specialist evidence into an executive-level decision brief."),
]


def render():
    page_header(
        "AGENTS",
        "Agent network",
        "The full AI Company OS network is visible here, whether or not every specialist participated in the latest investigation.",
    )

    item = current_investigation()
    used = {}
    if item:
        for response in item["result"].get("metrics", {}).get("agent_responses", []):
            used[response.get("agent", "").lower()] = response

    cols = st.columns(3)
    for i, (name, role, capability) in enumerate(AGENT_CATALOG):
        with cols[i % 3]:
            key = name.lower().replace(" & ", " ")
            response = used.get(key) or used.get(name.lower())
            status = response.get("status", "available") if response else "available"
            badge = "ACTIVE" if response else "READY"
            st.markdown(
                f'<div class="grid-card"><div class="metric-label">{role.upper()}</div>'
                f'<div class="metric-value" style="font-size:20px">{name}</div>'
                f'<div class="metric-note">{badge} · {status}</div>'
                f'<p class="muted" style="margin-top:12px">{capability}</p></div>',
                unsafe_allow_html=True,
            )

    if not item:
        st.info("No active investigation. The complete agent network is ready.")
        return

    st.markdown(
        '<div class="section-head"><div class="section-title">Latest participation</div>'
        '<div class="section-sub">Specialists used by the current Commander run</div></div>',
        unsafe_allow_html=True,
    )
    for response in item["result"].get("metrics", {}).get("agent_responses", []):
        with st.expander(f"{response['agent'].title()} · {response['status']}"):
            for finding in response.get("findings", []):
                st.markdown(f"- {finding.get('finding', finding)}")
            for recommendation in response.get("recommendations", []):
                st.markdown(f"- {recommendation}")
