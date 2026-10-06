"""AI Company OS — multi-page command interface."""

import streamlit as st

from app.ui.theme import inject_theme
from app.ui.pages import (
    command_center,
    intelligence,
    agents,
    financials,
    approvals,
    history,
    system,
    company,
)

st.set_page_config(
    page_title="AI Company OS",
    page_icon="N",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_theme()

PAGES = {
    "Command Center": command_center.render,
    "Company Workspace": company.render,
    "Intelligence": intelligence.render,
    "Agents": agents.render,
    "Financials": financials.render,
    "Approvals": approvals.render,
    "History": history.render,
    "System": system.render,
}

ICONS = {
    "Command Center": "⌂",
    "Company Workspace": "⌘",
    "Intelligence": "◈",
    "Agents": "◌",
    "Financials": "$",
    "Approvals": "✓",
    "History": "◷",
    "System": "⚙",
}


def render_navigation():
    if "page" not in st.session_state:
        st.session_state.page = "Command Center"

    st.markdown(
        """
        <div class="main-nav">
            <div class="nav-brand">
                <div class="nav-mark">N</div>
                <div>
                    <div class="nav-title">AI COMPANY OS</div>
                    <div class="nav-subtitle">NVIDIA INTELLIGENCE LAYER</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    names = list(PAGES.keys())
    columns = st.columns(len(names))

    for column, name in zip(columns, names):
        with column:
            active = st.session_state.page == name
            if st.button(
                f"{ICONS[name]}  {name}",
                key=f"main_nav_{name}",
                use_container_width=True,
                type="primary" if active else "secondary",
            ):
                st.session_state.page = name
                st.rerun()

    st.markdown(
        """
        <div class="nav-status">
            <span class="status-dot"></span>
            SYSTEM ONLINE
            <span class="status-separator">•</span>
            NEMOTRON CONNECTED
        </div>
        """,
        unsafe_allow_html=True,
    )


render_navigation()
st.markdown("<div class='nav-divider'></div>", unsafe_allow_html=True)
PAGES[st.session_state.page]()
