import streamlit as st

from app.ui.theme import page_header
from app.ui.shared import current_investigation, investigation_view
from app.core.approval import get_approval
from app.core.action_engine import get_task_actions


def render():
    page_header(
        "APPROVALS",
        "Human control center",
        "Every recommended action remains behind an explicit human approval gate.",
    )

    item = current_investigation()
    if not item:
        st.info("No active investigation. Load one from History or create a new one in Intelligence.")
        return

    approval = get_approval(item["task_id"])
    actions = get_task_actions(item["task_id"])

    if approval:
        a, b, c = st.columns(3)
        a.metric("APPROVAL", approval["status"].upper())
        b.metric("ACTIONS", len(actions))
        c.metric("EXECUTED", sum(x["status"] == "executed" for x in actions))

    investigation_view(item)
