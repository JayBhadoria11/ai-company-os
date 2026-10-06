import streamlit as st
import pandas as pd

from app.ui.theme import page_header, spline_core
from app.ui.shared import (
    financial_report,
    kpis,
    financial_chart,
    current_investigation,
    load_latest_investigation,
    clear_current_investigation,
)
from app.core.company_context import get_active_company, company_name


def render():
    ctx = get_active_company()
    active = ctx["active"]
    name = company_name() if active else None

    page_header(
        "COMMAND CENTER",
        "Run the company from one intelligence layer",
        (
            f"{name} is the active company context across the OS."
            if name
            else
            "Executive control surface for financial health, investigations, "
            "decisions, and agent orchestration."
        ),
    )

    # --------------------------------------------------------
    # System status
    # --------------------------------------------------------

    a, b, c, d = st.columns(4)

    item = current_investigation()

    a.metric("SYSTEM", "ONLINE")
    b.metric(
        "ACTIVE INVESTIGATION",
        "YES" if item else "NONE",
    )
    c.metric("NEMOTRON", "CONNECTED")
    d.metric(
        "COMPANY",
        "LIVE" if active else "DEFAULT",
    )

    # --------------------------------------------------------
    # Hero
    # --------------------------------------------------------

    left, right = st.columns([1.35, 1])

    with left:
        st.markdown(
            """
            <div class="hero">
                <div class="eyebrow">AI BUSINESS OPERATING SYSTEM</div>
                <div class="hero-title">
                    Understand the business.<br>
                    Decide with intelligence.
                </div>
                <div class="hero-copy">
                    Deterministic analytics establish facts.
                    Commander coordinates agents.
                    NVIDIA Nemotron turns evidence into decisions.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        spline_core()

    # --------------------------------------------------------
    # Company status
    # --------------------------------------------------------

    if active:
        st.success(
            f"LIVE COMPANY PULSE · {name} · "
            f"{len(ctx['datasets'])} dataset(s) connected"
        )

    # --------------------------------------------------------
    # Investigation controls
    # --------------------------------------------------------

    x, y = st.columns(2)

    with x:
        if st.button(
            "Load latest investigation",
            use_container_width=True,
        ):
            if load_latest_investigation():
                st.rerun()
            else:
                st.info("No saved investigation exists.")

    with y:
        if st.button(
            "Clear active investigation",
            use_container_width=True,
        ):
            clear_current_investigation()
            st.rerun()

    # --------------------------------------------------------
    # Financial / company pulse
    # --------------------------------------------------------

    report = financial_report()

    if not report:
        st.info(
            "No company financial data connected. "
            "Upload and analyze data in Company Workspace "
            "to generate live metrics and charts."
        )
        return

    st.markdown(
        """
        <div class="section-head">
            <div class="section-title">Company Pulse</div>
            <div class="section-sub">
                Verified metrics from the active operating dataset
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    kpis(report.get("summary", {}))

    if report.get("source") == "company_workspace":
        st.caption(
            "These figures are live from Company Workspace; "
            "missing expense/cost fields are intentionally not fabricated."
        )

    # --------------------------------------------------------
    # Financial signal
    # --------------------------------------------------------

    st.markdown(
        """
        <div class="section-head">
            <div class="section-title">Financial Signal</div>
            <div class="section-sub">
                Live performance timeline
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    financial_chart(report)

    # --------------------------------------------------------
    # Financial data table
    # --------------------------------------------------------

    monthly = pd.DataFrame(
        report.get("monthly_breakdown", [])
    )

    if not monthly.empty:
        st.markdown("### Financial Data")

        show = monthly.copy()

        if "month" in show.columns:
            show["month"] = pd.to_datetime(
                show["month"],
                errors="coerce",
            ).dt.strftime("%b %Y")

        rename = {
            "month": "Month",
            "revenue": "Net Sales",
            "net_sales": "Net Sales",
            "sales": "Net Sales",
            "expenses": "Expenses",
            "profit": "Profit",
            "profit_margin_pct": "Profit Margin %",
            "revenue_growth_pct": "Growth %",
        }

        show = show.rename(
            columns={
                key: value
                for key, value in rename.items()
                if key in show.columns
            }
        )

        for column in show.columns:
            if column != "Month":
                show[column] = pd.to_numeric(
                    show[column],
                    errors="coerce",
                ).round(2)

        st.dataframe(
            show,
            use_container_width=True,
            hide_index=True,
        )

    # --------------------------------------------------------
    # Active intelligence
    # --------------------------------------------------------

    if item:
        synthesis = item.get(
            "synthesis",
            {},
        )

        st.markdown(
            """
            <div class="section-head">
                <div class="section-title">Active Intelligence</div>
                <div class="section-sub">
                    The investigation currently loaded into the operating session
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        summary = synthesis.get(
            "executive_summary",
            "No executive summary available.",
        )

        st.markdown(
            f"""
            <div class="panel panel-lime">
                <div class="eyebrow">EXECUTIVE SUMMARY</div>
                <p>{summary}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )