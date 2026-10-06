import streamlit as st
from app.ui.theme import page_header
from app.database.db import clear_all_os_state

def render():
    page_header("SYSTEM", "OS controls", "Manage generated state and reset the operating environment.")
    st.markdown("### Factory Reset")
    st.warning("This removes company profile, uploaded company datasets, investigations, approvals and action history. It does not remove source code or .env files.")
    if st.button("Factory Reset AI Company OS", type="secondary", use_container_width=True):
        st.session_state.confirm_factory_reset=True
    if st.session_state.get("confirm_factory_reset"):
        a,b=st.columns(2)
        with a:
            if st.button("Confirm factory reset", type="primary", use_container_width=True):
                clear_all_os_state()
                for key in ["company_analysis","current_investigation","confirm_factory_reset","confirm_company_reset"]:
                    st.session_state.pop(key, None)
                st.success("OS state reset. Company financials and graphs are now empty until new data is connected.")
                st.rerun()
        with b:
            if st.button("Cancel", use_container_width=True):
                st.session_state.confirm_factory_reset=False
                st.rerun()
