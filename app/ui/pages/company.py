"""Company Workspace — the shared company context/data layer for the OS."""

import pandas as pd
import streamlit as st

from app.core.company_analysis import analyze_sales_dataset
from app.core.company_workspace import (
    clear_workspace,
    list_datasets,
    load_company_profile,
    save_company_profile,
    save_dataset,
)
from app.core.company_context import (
    company_name,
    get_active_company,
)
from app.core.approval import create_approval_request
from app.database.db import log_analysis
from app.ui.shared import set_current_investigation
from app.ui.theme import page_header


def _build_company_synthesis(analysis, profile):
    insights = analysis.get("insights", [])

    metrics = analysis.get(
        "metrics",
        {},
    )

    breakdowns = analysis.get(
        "breakdowns",
        {},
    )

    top_product = (
        (breakdowns.get("products") or [{}])[0]
        .get("name")
    )

    top_region = (
        (breakdowns.get("regions") or [{}])[0]
        .get("name")
    )

    top_channel = (
        (breakdowns.get("channels") or [{}])[0]
        .get("name")
    )

    actions = []

    if top_product:
        actions.append(
            f"Prioritize {top_product} and investigate "
            "how to scale its strongest demand drivers."
        )

    if top_region:
        actions.append(
            f"Review {top_region} performance and identify "
            "the next regional growth opportunity."
        )

    if top_channel:
        actions.append(
            f"Evaluate {top_channel} as a growth channel "
            "while monitoring acquisition efficiency."
        )

    if not actions:
        actions.append(
            "Upload more business data so the OS can produce "
            "evidence-backed recommendations."
        )

    return {
        "executive_summary": (
            f"{profile.get('name', 'The company')} has "
            f"{metrics.get('orders', 0):,} analyzed orders "
            f"and {metrics.get('total_units', 0):,} units, "
            f"with net sales of "
            f"₹{metrics.get('net_sales', 0):,.2f}."
        ),
        "key_insights": insights,
        "risks": analysis.get(
            "limitations",
            [],
        ),
        "recommended_actions": actions[:3],
    }


def _save_analysis_as_os_state(analysis, profile):
    task_id = (
        "company-"
        + pd.Timestamp.now().strftime(
            "%Y%m%d%H%M%S%f"
        )
    )

    synthesis = _build_company_synthesis(
        analysis,
        profile,
    )

    result = {
        "metrics": {
            "company_analysis": analysis,
            "required_agents": ["analyst"],
            "investigation_questions": [
                "What does the uploaded company data tell us about performance?"
            ],
        },
        "company_analysis": analysis,
    }

    item = {
        "task_id": task_id,
        "query": (
            f"Analyze "
            f"{profile.get('name', 'company')} "
            "from the uploaded workspace data"
        ),
        "result": result,
        "synthesis": synthesis,
        "timestamp": pd.Timestamp.now(
            tz="UTC"
        ).isoformat(),
    }

    set_current_investigation(item)

    log_analysis(
        query_text=item["query"],
        metrics_calculated=analysis.get(
            "metrics",
            {},
        ),
        insights=synthesis,
        model="Company Workspace Analyst",
        tools_used={
            "source": "uploaded_company_dataset"
        },
        user_approval=0,
        result=result,
        synthesis=synthesis,
        task_id=task_id,
        context_type="company",
    )

    create_approval_request(
        task_id=task_id,
        summary=synthesis["executive_summary"],
    )

    return item


def _show_analysis(analysis):
    if not analysis:
        return

    st.markdown(
        "### 05 · Company Intelligence Report"
    )

    st.caption(
        f"Computed from "
        f"{analysis.get('dataset') or analysis.get('filename') or 'uploaded business data'} "
        "using verified uploaded business data. "
        "This result is now shared with the rest of the OS."
    )

    metrics = analysis.get(
        "metrics",
        {},
    )

    items = [
        ("Orders", metrics.get("orders")),
        ("Units", metrics.get("total_units")),
        ("Net Sales", metrics.get("net_sales")),
        ("Discounts", metrics.get("discounts")),
        (
            "Average Order Value",
            metrics.get("average_order_value"),
        ),
    ]

    visible = [
        item
        for item in items
        if item[1] is not None
    ]

    if visible:
        cols = st.columns(
            min(5, len(visible))
        )

        for col, (label, value) in zip(
            cols,
            visible,
        ):
            if isinstance(value, float):
                col.metric(
                    label,
                    f"₹{value:,.2f}",
                )
            else:
                col.metric(
                    label,
                    f"{value:,}",
                )

    breakdowns = analysis.get(
        "breakdowns",
        {},
    )

    for key, title in [
        ("products", "Product Performance"),
        ("regions", "Regional Performance"),
        ("channels", "Marketing Channel Performance"),
    ]:
        rows = breakdowns.get(
            key,
            [],
        )

        if rows:
            st.markdown(
                f"**{title}**"
            )

            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True,
            )

    monthly = breakdowns.get(
        "monthly",
        [],
    )

    if monthly:
        st.markdown(
            "**Monthly Net Sales**"
        )

        monthly_df = pd.DataFrame(
            monthly
        )

        if (
            "month" in monthly_df.columns
            and "sales" in monthly_df.columns
        ):
            st.line_chart(
                monthly_df.set_index("month")[
                    "sales"
                ]
            )

    declining_products = breakdowns.get(
        "declining_products",
        [],
    )

    declining_regions = breakdowns.get(
        "declining_regions",
        [],
    )

    if declining_products:
        st.markdown(
            "**Products needing attention**"
        )

        st.dataframe(
            pd.DataFrame(declining_products),
            use_container_width=True,
            hide_index=True,
        )

    if declining_regions:
        st.markdown(
            "**Regions needing attention**"
        )

        st.dataframe(
            pd.DataFrame(declining_regions),
            use_container_width=True,
            hide_index=True,
        )

    if analysis.get("insights"):
        st.markdown(
            "**Key Insights**"
        )

        for insight in analysis["insights"]:
            st.markdown(
                f"- {insight}"
            )

    if analysis.get("limitations"):
        st.markdown(
            "**Data Limitations**"
        )

        for limitation in analysis["limitations"]:
            st.markdown(
                f"- {limitation}"
            )


def render():
    profile = load_company_profile()

    page_header(
        "COMPANY WORKSPACE",
        "The shared company brain",
        "Profile + uploaded datasets feed Financials, Intelligence, "
        "Approvals, History and Commander in real time.",
    )

    if profile.get("name"):
        st.success(
            f"ACTIVE COMPANY · {profile['name']}"
        )

    # --------------------------------------------------------
    # Company profile
    # --------------------------------------------------------

    st.markdown(
        "### 01 · Company Profile"
    )

    with st.form("company_profile_form"):

        c1, c2 = st.columns(2)

        with c1:
            name = st.text_input(
                "Company name",
                profile.get("name", ""),
                placeholder="Acme Inc.",
            )

            industry = st.text_input(
                "Industry",
                profile.get("industry", ""),
            )

            models = [
                "B2B",
                "B2C",
                "B2B2C",
                "Marketplace",
                "Other",
            ]

            current = profile.get(
                "model",
                "B2B",
            )

            model = st.selectbox(
                "Business model",
                models,
                index=(
                    models.index(current)
                    if current in models
                    else 0
                ),
            )

            markets = st.text_input(
                "Markets / geography",
                profile.get("markets", ""),
            )

        with c2:
            sizes = [
                "1–10",
                "11–50",
                "51–200",
                "201–1000",
                "1000+",
            ]

            current_size = profile.get(
                "size",
                sizes[0],
            )

            size = st.selectbox(
                "Company size",
                sizes,
                index=(
                    sizes.index(current_size)
                    if current_size in sizes
                    else 0
                ),
            )

            products = st.text_area(
                "Products / services",
                profile.get("products", ""),
                height=100,
            )

            goals = st.text_area(
                "Current business goals",
                profile.get("goals", ""),
                height=100,
            )

        description = st.text_area(
            "Brief about the company",
            profile.get("description", ""),
            height=120,
        )

        competitors = st.text_input(
            "Main competitors",
            profile.get("competitors", ""),
        )

        if st.form_submit_button(
            "Save Company Profile",
            type="primary",
            use_container_width=True,
        ):
            save_company_profile(
                {
                    "name": name,
                    "industry": industry,
                    "model": model,
                    "markets": markets,
                    "size": size,
                    "products": products,
                    "goals": goals,
                    "description": description,
                    "competitors": competitors,
                }
            )

            st.success(
                "Company context updated. "
                "All connected pages will use it on their next render."
            )

            st.rerun()

    # --------------------------------------------------------
    # Company data
    # --------------------------------------------------------

    st.markdown(
        "### 02 · Company Data"
    )

    uploaded = st.file_uploader(
        "Upload sales, finance, customer, marketing, "
        "product or other business data",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True,
    )

    if uploaded and st.button(
        "Import datasets",
        type="primary",
        use_container_width=True,
    ):
        for file in uploaded:
            try:
                info = save_dataset(file)

                st.success(
                    f"Imported {info['filename']} — "
                    f"{info['rows']:,} rows × "
                    f"{info['columns']} columns."
                )

            except Exception as exc:
                st.error(
                    f"Could not import {file.name}: {exc}"
                )

        st.rerun()

    # --------------------------------------------------------
    # Data sources
    # --------------------------------------------------------

    datasets = list_datasets()

    if datasets:
        st.markdown(
            "### 03 · Data Sources"
        )

        for dataset in datasets:
            meta = dataset["metadata"]

            with st.expander(
                f"{dataset['filename']} · "
                f"{meta.get('rows', 0):,} rows × "
                f"{meta.get('columns', 0)} columns"
            ):
                st.write(
                    "Columns:",
                    ", ".join(
                        meta.get(
                            "column_names",
                            [],
                        )
                    ),
                )

                st.write(
                    "Numeric:",
                    ", ".join(
                        meta.get(
                            "numeric_columns",
                            [],
                        )
                    )
                    or "None detected",
                )

                st.write(
                    "Missing values:",
                    meta.get(
                        "missing_values",
                        0,
                    ),
                )

                st.write(
                    "Duplicate rows:",
                    meta.get(
                        "duplicate_rows",
                        0,
                    ),
                )

                if st.button(
                    f"Analyze and connect {dataset['filename']}",
                    type="primary",
                    key=f"analyze_{dataset['id']}",
                ):
                    try:
                        analysis = analyze_sales_dataset(
                            dataset["path"]
                        )

                        st.session_state[
                            "company_analysis"
                        ] = analysis

                        _save_analysis_as_os_state(
                            analysis,
                            load_company_profile(),
                        )

                        st.success(
                            "Company intelligence saved to "
                            "History and connected to the OS approval flow."
                        )

                        st.rerun()

                    except Exception as exc:
                        st.error(
                            f"Analysis failed: {exc}"
                        )

        latest = st.session_state.get(
            "company_analysis"
        )

        if latest:
            _show_analysis(latest)

        else:
            ctx = get_active_company()

            latest = ctx.get(
                "analysis"
            )

            if latest:
                latest = (
                    latest.get(
                        "company_analysis"
                    )
                    or latest.get(
                        "result",
                        {},
                    ).get(
                        "company_analysis"
                    )
                    or latest
                )

                _show_analysis(latest)

    else:
        st.info(
            "No company datasets yet. "
            "Upload a sales or finance dataset "
            "to activate the workspace."
        )

    # --------------------------------------------------------
    # Connected OS
    # --------------------------------------------------------

    st.markdown(
        "### 04 · Connected OS"
    )

    st.caption(
        "The active company is not isolated: its latest verified "
        "analysis is used by Financials, Intelligence, History, "
        "Commander and Approvals."
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Financials", "LIVE")
    c2.metric("Intelligence", "CONNECTED")
    c3.metric("History", "PERSISTED")
    c4.metric("Approvals", "READY")

    # --------------------------------------------------------
    # Workspace controls
    # --------------------------------------------------------

    st.markdown(
        "### 06 · Workspace Controls"
    )

    if st.button(
        "Reset Company Workspace",
        type="secondary",
    ):
        st.session_state.confirm_company_reset = True

    if st.session_state.get(
        "confirm_company_reset"
    ):
        st.warning(
            "This deletes the company profile "
            "and uploaded company datasets."
        )

        a, b = st.columns(2)

        with a:
            if st.button(
                "Confirm reset",
                type="primary",
            ):
                clear_workspace()

                st.session_state.confirm_company_reset = False
                st.session_state.pop(
                    "company_analysis",
                    None,
                )
                st.session_state.pop(
                    "current_investigation",
                    None,
                )

                st.rerun()

        with b:
            if st.button("Cancel"):
                st.session_state.confirm_company_reset = False
                st.rerun()