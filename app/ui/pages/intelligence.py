import streamlit as st

from app.ui.theme import page_header
from app.ui.shared import (
    current_investigation,
    run_investigation,
    investigation_view,
    load_latest_investigation,
    clear_current_investigation,
)
from app.core.company_context import (
    get_active_company,
    company_context_text,
    company_name,
)


def render():
    ctx = get_active_company()

    name = (
        ctx["profile"].get("name")
        if ctx["active"]
        else None
    )

    page_header(
        "INTELLIGENCE",
        "Ask the company anything",
        (
            f"Nemotron answers against the live {name} workspace context."
            if name
            else
            "Commander turns a business question into a coordinated "
            "multi-agent investigation."
        ),
    )

    # --------------------------------------------------------
    # Live company context
    # --------------------------------------------------------

    if ctx["active"]:
        st.success(
            f"LIVE CONTEXT · {company_name()} · "
            f"{len(ctx['datasets'])} dataset(s) · latest analysis connected"
        )

        with st.expander(
            "What the OS currently knows",
            expanded=False,
        ):
            st.code(
                company_context_text(7000)
            )

    # --------------------------------------------------------
    # Investigation controls
    # --------------------------------------------------------

    item = current_investigation()

    a, b = st.columns(2)

    with a:
        if st.button(
            "New investigation",
            type="primary",
            use_container_width=True,
        ):
            clear_current_investigation()
            st.rerun()

    with b:
        if st.button(
            "Load latest saved",
            use_container_width=True,
        ):
            if load_latest_investigation():
                st.rerun()
            else:
                st.info(
                    "No saved investigation exists."
                )

    # --------------------------------------------------------
    # Commander prompt
    # --------------------------------------------------------

    st.markdown(
        """
        <div class="panel panel-violet">
            <div class="eyebrow">NEMOTRON COMMANDER</div>
            <h3>What should the company investigate?</h3>
            <p class="muted">
                Ask questions about sales, products, regions, channels,
                customers, trends, risks or strategy.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    q = st.text_area(
        "Business question",
        placeholder=(
            f"For example: Which product is strongest for "
            f"{name or 'our company'}, and what should we do next?"
        ),
        height=130,
        label_visibility="collapsed",
        key="intel_query",
    )

    # --------------------------------------------------------
    # Run investigation
    # --------------------------------------------------------

    if st.button(
        "Run AI Investigation",
        type="primary",
        disabled=not q.strip(),
        use_container_width=True,
    ):
        with st.spinner(
            "Commander is using the live company context "
            "and NVIDIA Nemotron..."
        ):
            try:
                run_investigation(q)

                st.success(
                    "Investigation completed and saved to OS History."
                )

                st.rerun()

            except Exception as exc:
                st.error(
                    f"Investigation failed: {exc}"
                )

    # --------------------------------------------------------
    # Investigation result
    # --------------------------------------------------------

    item = current_investigation()

    if item:
        investigation_view(item)
    else:
        st.info(
            "No active investigation. "
            "Start a new investigation or load one from History."
        )