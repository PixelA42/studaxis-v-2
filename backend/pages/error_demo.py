"""
Studaxis – Error UI Component Demo Page

This page demonstrates all error handling UI components available in the system.
Use this as a reference for integrating error UI into other pages.

NOTE: This is a development/demo page and should not be exposed to end users.
"""

from __future__ import annotations

import streamlit as st

from error_ui import (
    PLACEHOLDER_AI_TIMEOUT_LIMIT,
    PLACEHOLDER_CORRUPTED_FILE_NAME,
    PLACEHOLDER_ERROR_CODE,
    PLACEHOLDER_PENDING_ITEMS_COUNT,
    PLACEHOLDER_SYNC_RETRY_INTERVAL,
    add_toast,
    clear_all_toasts,
    inject_error_css,
    render_ai_timeout_error,
    render_cloud_error_card,
    render_data_corruption_modal,
    render_error_modal,
    render_inline_error,
    render_sync_error_banner,
    render_toast_container,
    toast_ai_retry_recommended,
    toast_connection_restored,
    toast_sync_retry_scheduled,
    toast_temporary_server_issue,
)


def show_error_demo() -> None:
    """Render the error UI demo page."""
    theme = st.session_state.get("theme", "light")
    theme_class = "theme-dark" if theme == "dark" else ""

    inject_error_css()

    st.markdown(
        f'<div class="dashboard-root {theme_class}">',
        unsafe_allow_html=True,
    )

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="dashboard-header-card">
            <div class="db-icon-chip db-icon-chip--red" aria-hidden="true">⚠️</div>
            <div style="flex:1">
                <div class="dashboard-welcome-name">Error UI Component Demo</div>
                <div class="dashboard-welcome-sub">Development reference for error handling patterns</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Back button
    if st.button("← Back to Dashboard", key="error_demo_back"):
        st.session_state.page = "dashboard"
        st.rerun()

    st.markdown("---")

    # ── Section 1: Inline Errors ──────────────────────────────────────────────
    st.markdown("### 1. Inline Error Components")
    st.markdown(
        "Used inside components such as AI Chat, Quiz submission, Flashcards loading, Storage manager."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Error Severity (Default)**")
        retry_clicked = render_inline_error(
            title="AI response timed out",
            message="Please try again.",
            severity="error",
            hint="You can retry or simplify your question.",
            show_retry=True,
            retry_key="demo_inline_error_retry",
        )
        if retry_clicked:
            st.success("Retry button clicked!")

    with col2:
        st.markdown("**Warning Severity**")
        render_inline_error(
            title="Storage space running low",
            message="Consider clearing unused textbooks to free up space.",
            severity="warning",
            hint="Go to Settings → Storage to manage files.",
            show_retry=False,
        )

    st.markdown("**Info Severity**")
    render_inline_error(
        title="Sync paused",
        message="Syncing is paused while you're on a metered connection.",
        severity="info",
        show_retry=False,
    )

    st.markdown("---")

    # ── Section 2: AI Timeout Error ───────────────────────────────────────────
    st.markdown("### 2. AI Error Timeout UI")
    st.markdown(
        f"Display when AI inference exceeds {PLACEHOLDER_AI_TIMEOUT_LIMIT}."
    )

    with st.expander("Show AI Timeout Error UI", expanded=False):
        retry, cancel = render_ai_timeout_error(
            timeout_limit=PLACEHOLDER_AI_TIMEOUT_LIMIT,
            on_retry_key="demo_ai_retry",
            on_cancel_key="demo_ai_cancel",
        )
        if retry:
            st.success("Retry response clicked!")
        if cancel:
            st.info("Cancel request clicked!")

    st.markdown("---")

    # ── Section 3: Sync/Network Error Banner ──────────────────────────────────
    st.markdown("### 3. Sync / Network Error Banner")
    st.markdown(
        "Used when network connection fails or sync cannot complete."
    )

    tab1, tab2 = st.tabs(["Sync Error", "Offline Mode"])

    with tab1:
        render_sync_error_banner(
            is_offline=False,
            error_message=f"Unable to sync changes. Will retry in {PLACEHOLDER_SYNC_RETRY_INTERVAL}.",
            pending_items_count=PLACEHOLDER_PENDING_ITEMS_COUNT,
            show_pending_details=True,
        )

    with tab2:
        render_sync_error_banner(
            is_offline=True,
            error_message="Changes will sync automatically when network is restored.",
            show_pending_details=False,
        )

    st.markdown("---")

    # ── Section 4: Data Corruption Warning Modal ──────────────────────────────
    st.markdown("### 4. Data Corruption Warning Modal")
    st.markdown(
        "Blocking modal shown when local files become corrupted."
    )

    if st.button("Show Data Corruption Modal", key="demo_show_corruption"):
        st.session_state.show_corruption_demo = True
        st.rerun()

    if st.session_state.get("show_corruption_demo"):
        repair, restore, continue_limited = render_data_corruption_modal(
            corrupted_file=PLACEHOLDER_CORRUPTED_FILE_NAME,
            on_repair_key="demo_corruption_repair",
            on_restore_key="demo_corruption_restore",
            on_continue_key="demo_corruption_continue",
        )
        if repair:
            st.success("Repair Data clicked!")
            st.session_state.show_corruption_demo = False
            st.rerun()
        if restore:
            st.success("Restore Backup clicked!")
            st.session_state.show_corruption_demo = False
            st.rerun()
        if continue_limited:
            st.info("Continue with Limited Mode clicked!")
            st.session_state.show_corruption_demo = False
            st.rerun()

    st.markdown("---")

    # ── Section 5: Cloud Infrastructure Error Card ────────────────────────────
    st.markdown("### 5. Cloud Infrastructure Error Card (Teacher Dashboard)")
    st.markdown(
        "For API failures, sync failures, and data fetch failures."
    )

    retry_load, refresh_dash = render_cloud_error_card(
        title="Unable to load student analytics",
        message="The analytics service is temporarily unavailable. Please try again in a few moments.",
        error_code=PLACEHOLDER_ERROR_CODE,
        api_endpoint="/api/v1/analytics/students",
        on_retry_key="demo_cloud_retry",
        on_refresh_key="demo_cloud_refresh",
    )
    if retry_load:
        st.success("Retry loading clicked!")
    if refresh_dash:
        st.info("Refresh dashboard clicked!")

    st.markdown("---")

    # ── Section 6: Toast Notifications ────────────────────────────────────────
    st.markdown("### 6. Toast Notifications")
    st.markdown(
        "Small toast alerts for non-blocking problems. Position: top-right corner."
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Sync Retry", key="demo_toast_sync"):
            toast_sync_retry_scheduled()
            st.rerun()

    with col2:
        if st.button("Server Issue", key="demo_toast_server"):
            toast_temporary_server_issue()
            st.rerun()

    with col3:
        if st.button("AI Retry", key="demo_toast_ai"):
            toast_ai_retry_recommended()
            st.rerun()

    with col4:
        if st.button("Connected", key="demo_toast_connected"):
            toast_connection_restored()
            st.rerun()

    col5, col6 = st.columns(2)

    with col5:
        if st.button("Custom Error Toast", key="demo_toast_custom"):
            add_toast(
                "Custom error",
                "This is a custom error toast message.",
                toast_type="error",
            )
            st.rerun()

    with col6:
        if st.button("Clear All Toasts", key="demo_toast_clear"):
            clear_all_toasts()
            st.rerun()

    st.markdown("---")

    # ── Section 7: Generic Error Modal ────────────────────────────────────────
    st.markdown("### 7. Generic Error Modal")
    st.markdown(
        "A customizable blocking error modal for various error scenarios."
    )

    if st.button("Show Generic Error Modal", key="demo_show_generic_modal"):
        st.session_state.show_generic_modal_demo = True
        st.rerun()

    if st.session_state.get("show_generic_modal_demo"):
        primary, secondary = render_error_modal(
            title="Something went wrong",
            message="An unexpected error occurred while processing your request.",
            error_code=PLACEHOLDER_ERROR_CODE,
            detail_label="Technical details",
            detail_value="StackTrace: error_ui.demo.unexpected_error",
            recovery_message="Our team has been notified. Please try again.",
            primary_action_label="Try Again",
            primary_action_key="demo_generic_primary",
            secondary_action_label="Dismiss",
            secondary_action_key="demo_generic_secondary",
        )
        if primary or secondary:
            st.session_state.show_generic_modal_demo = False
            st.rerun()

    st.markdown("---")

    # ── Placeholder Reference ─────────────────────────────────────────────────
    st.markdown("### Placeholder Variables Reference")
    st.markdown(
        """
        The following placeholders are used for unknown technical values:

        | Placeholder | Description |
        |-------------|-------------|
        | `[AI_TIMEOUT_LIMIT]` | Maximum AI response wait time |
        | `[SYNC_RETRY_INTERVAL]` | Time between sync retry attempts |
        | `[ERROR_CODE]` | Technical error code |
        | `[CORRUPTED_FILE_NAME]` | Name of affected file |
        | `[PENDING_ITEMS_COUNT]` | Number of pending sync items |
        | `[TOAST_LIFETIME_MS]` | Toast auto-dismiss duration (~4-6 seconds) |
        """
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # Render toast container at the end
    render_toast_container()


if __name__ == "__main__":
    show_error_demo()
