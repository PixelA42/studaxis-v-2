"""
Studaxis – Error Handling UI Layer

A unified error presentation system providing:
  - Inline error components (for AI Chat, Quiz, Flashcards, Storage)
  - Toast notifications (non-blocking alerts)
  - Blocking error modals (critical system issues)
  - Data corruption warning modal
  - Cloud infrastructure error cards (Teacher Dashboard)

This module is UI-only. No backend retry logic, AI inference handling,
database repair, or AWS error management is implemented here.

Placeholder variables are used for unknown technical values:
  - [AI_TIMEOUT_LIMIT]
  - [SYNC_RETRY_INTERVAL]
  - [ERROR_CODE]
  - [CORRUPTED_FILE_NAME]
"""

from __future__ import annotations

from html import escape
from typing import Any, Literal
from uuid import uuid4

import streamlit as st


# ── Placeholder Constants ─────────────────────────────────────────────────────

PLACEHOLDER_AI_TIMEOUT_LIMIT = "[AI_TIMEOUT_LIMIT]"
PLACEHOLDER_SYNC_RETRY_INTERVAL = "[SYNC_RETRY_INTERVAL]"
PLACEHOLDER_ERROR_CODE = "[ERROR_CODE]"
PLACEHOLDER_CORRUPTED_FILE_NAME = "[CORRUPTED_FILE_NAME]"
PLACEHOLDER_LAST_SYNC_TIME = "[LAST_SYNC_TIME]"
PLACEHOLDER_PENDING_ITEMS_COUNT = "[PENDING_ITEMS_COUNT]"
PLACEHOLDER_ERROR_MESSAGE = "[ERROR_MESSAGE]"
PLACEHOLDER_STUDENT_NAME = "[STUDENT_NAME]"
PLACEHOLDER_API_ENDPOINT = "[API_ENDPOINT]"

# Toast display duration placeholder (actual value depends on implementation)
TOAST_LIFETIME_MS = "[TOAST_LIFETIME_MS]"  # Expected: ~4000-6000ms


# ── CSS Injection ─────────────────────────────────────────────────────────────

def inject_error_css() -> None:
    """
    Inject error-specific CSS styles into the Streamlit app.
    Call once at app initialization or page render.
    """
    if st.session_state.get("_error_css_injected"):
        return

    st.session_state["_error_css_injected"] = True
    # Error styles are provided by the global theme stylesheet.
    # Keeping this as a no-op avoids duplicating a second large CSS block.


_ERROR_CSS = ""


# ── Type Definitions ──────────────────────────────────────────────────────────

ErrorSeverity = Literal["error", "warning", "info"]
ToastType = Literal["error", "warning", "info", "success"]


# ── Helper Functions ──────────────────────────────────────────────────────────

def _safe(text: Any, fallback: str = "") -> str:
    """Escape HTML in user-provided text."""
    if text is None or text == "":
        return escape(fallback)
    return escape(str(text))


def _get_error_icon(severity: ErrorSeverity) -> str:
    """Return appropriate icon for error severity."""
    icons = {
        "error": "⚠️",
        "warning": "⚡",
        "info": "ℹ️",
    }
    return icons.get(severity, "⚠️")


# ── INLINE ERROR COMPONENT ────────────────────────────────────────────────────

def render_inline_error(
    title: str,
    message: str,
    *,
    severity: ErrorSeverity = "error",
    hint: str | None = None,
    show_retry: bool = True,
    retry_key: str | None = None,
) -> bool:
    """
    Render an inline error message for use inside components.
    
    Use for:
      - AI Chat response failures
      - Quiz submission errors
      - Flashcards loading errors
      - Storage manager warnings
    
    Args:
        title: Short headline describing the problem
        message: Detailed description of the error
        severity: "error", "warning", or "info"
        hint: Optional hint text for recovery actions
        show_retry: Whether to show a retry button
        retry_key: Unique key for the retry button (auto-generated if None)
    
    Returns:
        True if retry button was clicked, False otherwise
    """
    inject_error_css()
    
    variant_class = "" if severity == "error" else f"error-inline--{severity}"
    icon = _get_error_icon(severity)
    
    hint_html = ""
    if hint:
        hint_html = f'<p class="error-inline__hint">{_safe(hint)}</p>'
    
    st.markdown(
        f"""
        <div class="error-inline {variant_class}" role="alert" aria-live="assertive">
            <div class="error-inline__icon" aria-hidden="true">{icon}</div>
            <div class="error-inline__content">
                <p class="error-inline__title">{_safe(title)}</p>
                <p class="error-inline__message">{_safe(message)}</p>
                {hint_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    if show_retry:
        key = retry_key or f"error_retry_{uuid4().hex[:8]}"
        return st.button(
            "🔄 Retry",
            key=key,
            type="primary",
            help="Try the operation again",
        )
    
    return False


# ── AI ERROR TIMEOUT UI ───────────────────────────────────────────────────────

def render_ai_timeout_error(
    *,
    timeout_limit: str = PLACEHOLDER_AI_TIMEOUT_LIMIT,
    on_retry_key: str = "ai_timeout_retry",
    on_cancel_key: str = "ai_timeout_cancel",
) -> tuple[bool, bool]:
    """
    Render the AI response timeout UI state.
    
    Display when AI inference exceeds the timeout limit.
    
    Args:
        timeout_limit: The timeout value (placeholder or actual)
        on_retry_key: Button key for retry action
        on_cancel_key: Button key for cancel action
    
    Returns:
        Tuple of (retry_clicked, cancel_clicked)
    """
    inject_error_css()
    
    st.markdown(
        f"""
        <div class="error-ai-timeout" role="alert" aria-live="polite">
            <div class="error-ai-timeout__icon" aria-hidden="true">⏱️</div>
            <h3 class="error-ai-timeout__title">AI response taking longer than expected</h3>
            <p class="error-ai-timeout__message">
                The AI has exceeded the expected response time of {_safe(timeout_limit)}.
            </p>
            <p class="error-ai-timeout__hint">
                You can retry or simplify your question.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    col1, col2 = st.columns(2)
    with col1:
        retry_clicked = st.button(
            "🔄 Retry response",
            key=on_retry_key,
            type="primary",
            use_container_width=True,
            help="Try generating the AI response again",
        )
    with col2:
        cancel_clicked = st.button(
            "✕ Cancel request",
            key=on_cancel_key,
            use_container_width=True,
            help="Stop waiting for the AI response",
        )
    
    return retry_clicked, cancel_clicked


# ── SYNC / NETWORK ERROR BANNER ───────────────────────────────────────────────

def render_sync_error_banner(
    *,
    is_offline: bool = False,
    error_message: str | None = None,
    pending_items_count: str = PLACEHOLDER_PENDING_ITEMS_COUNT,
    last_sync_time: str = PLACEHOLDER_LAST_SYNC_TIME,
    show_pending_details: bool = False,
    pending_items: list[str] | None = None,
) -> None:
    """
    Render a sync/network error banner.
    
    Display when network connection fails or sync cannot complete.
    
    Args:
        is_offline: Whether the device is currently offline
        error_message: Optional specific error message
        pending_items_count: Number of pending sync items
        last_sync_time: Last successful sync timestamp
        show_pending_details: Whether to show expandable pending items
        pending_items: List of pending item descriptions
    """
    inject_error_css()
    
    if is_offline:
        banner_class = "error-sync-banner error-sync-banner--offline"
        icon = "📡"
        title = "Connection lost"
        message = error_message or "Changes will sync automatically when network is restored."
        status_text = "Offline"
    else:
        banner_class = "error-sync-banner"
        icon = "🔄"
        title = "Sync error"
        message = error_message or f"Unable to sync changes. Will retry in {PLACEHOLDER_SYNC_RETRY_INTERVAL}."
        status_text = "Sync Failed"
    
    st.markdown(
        f"""
        <div class="{banner_class}" role="status" aria-live="polite">
            <div class="error-sync-banner__icon" aria-hidden="true">{icon}</div>
            <div class="error-sync-banner__content">
                <p class="error-sync-banner__title">{_safe(title)}</p>
                <p class="error-sync-banner__message">{_safe(message)}</p>
            </div>
            <div class="error-sync-banner__status">
                <span class="error-sync-banner__dot"></span>
                {status_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    if show_pending_details:
        with st.expander("View pending sync items", expanded=False):
            items = pending_items or [
                f"Quiz attempt — {PLACEHOLDER_LAST_SYNC_TIME}",
                f"Chat history update — {PLACEHOLDER_LAST_SYNC_TIME}",
                f"Flashcard progress — {PLACEHOLDER_LAST_SYNC_TIME}",
            ]
            
            items_html = "".join(
                f'<li class="error-sync-pending__item"><span class="error-sync-pending__item-icon">📄</span>{_safe(item)}</li>'
                for item in items
            )
            
            st.markdown(
                f"""
                <div class="error-sync-pending">
                    <div class="error-sync-pending__header">
                        <span class="error-sync-pending__label">Pending items</span>
                        <span class="error-sync-pending__count">{_safe(pending_items_count)}</span>
                    </div>
                    <ul class="error-sync-pending__list" role="list">
                        {items_html}
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ── DATA CORRUPTION WARNING MODAL ─────────────────────────────────────────────

def render_data_corruption_modal(
    *,
    corrupted_file: str = PLACEHOLDER_CORRUPTED_FILE_NAME,
    on_repair_key: str = "corruption_repair",
    on_restore_key: str = "corruption_restore",
    on_continue_key: str = "corruption_continue",
) -> tuple[bool, bool, bool]:
    """
    Render a blocking modal for data corruption warnings.
    
    Display when local files become corrupted and require attention.
    
    Args:
        corrupted_file: Name/path of the corrupted file
        on_repair_key: Button key for repair action
        on_restore_key: Button key for restore backup action
        on_continue_key: Button key for continue in limited mode
    
    Returns:
        Tuple of (repair_clicked, restore_clicked, continue_clicked)
    """
    inject_error_css()
    
    st.markdown(
        f"""
        <div class="error-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="corruption-modal-title">
            <div class="error-modal error-corruption-modal">
                <div class="error-modal__illustration" aria-hidden="true">⚠️</div>
                <h2 id="corruption-modal-title" class="error-modal__title">Local data issue detected</h2>
                <p class="error-modal__content">
                    A data integrity issue was found that may affect your study progress.
                </p>
                <div class="error-modal__detail">
                    <p class="error-modal__detail-label">File affected</p>
                    <p class="error-modal__detail-value">{_safe(corrupted_file)}</p>
                </div>
                <div class="error-modal__recovery">
                    The system will attempt automatic repair.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("---")
    st.markdown("##### Choose a recovery option:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        repair_clicked = st.button(
            "🔧 Repair Data",
            key=on_repair_key,
            type="primary",
            use_container_width=True,
            help="Attempt to repair the corrupted data",
        )
    
    with col2:
        restore_clicked = st.button(
            "📦 Restore Backup",
            key=on_restore_key,
            use_container_width=True,
            help="Restore from the last known good backup",
        )
    
    with col3:
        continue_clicked = st.button(
            "▶️ Limited Mode",
            key=on_continue_key,
            use_container_width=True,
            help="Continue with limited functionality",
        )
    
    return repair_clicked, restore_clicked, continue_clicked


# ── CLOUD INFRASTRUCTURE ERROR CARD (Teacher Dashboard) ──────────────────────

def render_cloud_error_card(
    title: str,
    message: str,
    *,
    error_code: str = PLACEHOLDER_ERROR_CODE,
    api_endpoint: str | None = None,
    on_retry_key: str = "cloud_error_retry",
    on_refresh_key: str = "cloud_error_refresh",
) -> tuple[bool, bool]:
    """
    Render an error card for cloud infrastructure errors in the Teacher Dashboard.
    
    Use for:
      - API failures
      - Sync failures
      - Data fetch failures
    
    Args:
        title: Error headline (e.g., "Unable to load student analytics")
        message: Detailed error description
        error_code: Technical error code
        api_endpoint: Optional API endpoint that failed
        on_retry_key: Button key for retry action
        on_refresh_key: Button key for refresh dashboard action
    
    Returns:
        Tuple of (retry_clicked, refresh_clicked)
    """
    inject_error_css()
    
    endpoint_html = ""
    if api_endpoint:
        endpoint_html = f'<span class="error-cloud-card__code">{_safe(api_endpoint)}</span>'
    
    st.markdown(
        f"""
        <div class="error-cloud-card" role="alert" aria-live="assertive">
            <div class="error-cloud-card__header">
                <div class="error-cloud-card__icon" aria-hidden="true">⚠️</div>
                <div class="error-cloud-card__title-wrap">
                    <h3 class="error-cloud-card__title">{_safe(title)}</h3>
                    <p class="error-cloud-card__subtitle">
                        Error code: <span class="error-cloud-card__code">{_safe(error_code)}</span>
                        {endpoint_html}
                    </p>
                </div>
            </div>
            <p class="error-cloud-card__message">{_safe(message)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        retry_clicked = st.button(
            "🔄 Retry loading",
            key=on_retry_key,
            type="primary",
            use_container_width=True,
            help="Retry the failed operation",
        )
    
    with col2:
        refresh_clicked = st.button(
            "🔃 Refresh dashboard",
            key=on_refresh_key,
            use_container_width=True,
            help="Refresh the entire dashboard",
        )
    
    return retry_clicked, refresh_clicked


# ── TOAST NOTIFICATION SYSTEM ─────────────────────────────────────────────────

def _init_toast_state() -> None:
    """Initialize toast notification state in session."""
    if "error_toasts" not in st.session_state:
        st.session_state.error_toasts = []


def add_toast(
    title: str,
    message: str,
    *,
    toast_type: ToastType = "error",
) -> str:
    """
    Add a toast notification to the queue.
    
    Toasts appear in the top-right corner of the screen.
    Expected lifetime: ~4-6 seconds (placeholder: [TOAST_LIFETIME_MS])
    
    Args:
        title: Toast headline
        message: Toast message content
        toast_type: "error", "warning", "info", or "success"
    
    Returns:
        Unique toast ID for potential dismissal
    """
    _init_toast_state()
    
    toast_id = uuid4().hex[:8]
    st.session_state.error_toasts.append({
        "id": toast_id,
        "title": title,
        "message": message,
        "type": toast_type,
    })
    
    return toast_id


def dismiss_toast(toast_id: str) -> None:
    """Remove a toast by ID."""
    _init_toast_state()
    st.session_state.error_toasts = [
        t for t in st.session_state.error_toasts if t["id"] != toast_id
    ]


def clear_all_toasts() -> None:
    """Clear all toast notifications."""
    st.session_state.error_toasts = []


def render_toast_container() -> None:
    """
    Render the toast notification container.
    
    Call this once per page render, typically at the end of the page layout.
    Toasts will appear in the top-right corner.
    
    Note: Toast auto-dismissal requires JavaScript which is not available
    in Streamlit. Consider using st.toast() for native toast support,
    or implement manual dismissal buttons.
    """
    inject_error_css()
    _init_toast_state()
    
    toasts = st.session_state.get("error_toasts", [])
    if not toasts:
        return
    
    toast_icons = {
        "error": ("⚠️", "error"),
        "warning": ("⚡", "warning"),
        "info": ("ℹ️", "info"),
        "success": ("✓", "success"),
    }
    
    toasts_html = ""
    for toast in toasts:
        icon, icon_class = toast_icons.get(toast["type"], ("⚠️", "error"))
        toasts_html += f"""
        <div class="error-toast" role="alert" aria-live="polite" data-toast-id="{toast['id']}">
            <div class="error-toast__icon error-toast__icon--{icon_class}" aria-hidden="true">{icon}</div>
            <div class="error-toast__content">
                <p class="error-toast__title">{_safe(toast['title'])}</p>
                <p class="error-toast__message">{_safe(toast['message'])}</p>
            </div>
        </div>
        """
    
    st.markdown(
        f"""
        <div class="error-toast-container" role="region" aria-label="Notifications">
            {toasts_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Provide dismiss buttons in sidebar or inline
    if toasts:
        with st.sidebar:
            st.markdown("#### Active Notifications")
            for toast in toasts:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.caption(f"{toast['title']}")
                with col2:
                    if st.button("✕", key=f"dismiss_{toast['id']}", help="Dismiss"):
                        dismiss_toast(toast["id"])
                        st.rerun()


# ── CONVENIENCE TOAST FUNCTIONS ───────────────────────────────────────────────

def toast_sync_retry_scheduled() -> str:
    """Show toast for scheduled sync retry."""
    return add_toast(
        "Sync retry scheduled",
        f"Will attempt to sync again in {PLACEHOLDER_SYNC_RETRY_INTERVAL}.",
        toast_type="info",
    )


def toast_temporary_server_issue() -> str:
    """Show toast for temporary server issues."""
    return add_toast(
        "Temporary server issue",
        "The server is experiencing issues. Please try again shortly.",
        toast_type="warning",
    )


def toast_ai_retry_recommended() -> str:
    """Show toast recommending AI retry."""
    return add_toast(
        "AI retry recommended",
        "The AI response may have been incomplete. Consider retrying your question.",
        toast_type="info",
    )


def toast_connection_restored() -> str:
    """Show toast when connection is restored."""
    return add_toast(
        "Connection restored",
        "Your device is back online. Syncing changes...",
        toast_type="success",
    )


# ── GENERIC ERROR MODAL ───────────────────────────────────────────────────────

def render_error_modal(
    title: str,
    message: str,
    *,
    error_code: str | None = None,
    detail_label: str | None = None,
    detail_value: str | None = None,
    recovery_message: str | None = None,
    primary_action_label: str = "Try Again",
    primary_action_key: str = "error_modal_primary",
    secondary_action_label: str | None = "Dismiss",
    secondary_action_key: str = "error_modal_secondary",
) -> tuple[bool, bool]:
    """
    Render a generic blocking error modal.
    
    Args:
        title: Modal headline
        message: Main error description
        error_code: Optional error code to display
        detail_label: Label for detail section
        detail_value: Value for detail section
        recovery_message: Optional recovery hint message
        primary_action_label: Text for primary button
        primary_action_key: Key for primary button
        secondary_action_label: Text for secondary button (None to hide)
        secondary_action_key: Key for secondary button
    
    Returns:
        Tuple of (primary_clicked, secondary_clicked)
    """
    inject_error_css()
    
    detail_html = ""
    if detail_label and detail_value:
        detail_html = f"""
        <div class="error-modal__detail">
            <p class="error-modal__detail-label">{_safe(detail_label)}</p>
            <p class="error-modal__detail-value">{_safe(detail_value)}</p>
        </div>
        """
    
    recovery_html = ""
    if recovery_message:
        recovery_html = f'<div class="error-modal__recovery">{_safe(recovery_message)}</div>'
    
    error_code_text = f" ({_safe(error_code)})" if error_code else ""
    
    st.markdown(
        f"""
        <div class="error-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="error-modal-title">
            <div class="error-modal">
                <div class="error-modal__illustration" aria-hidden="true">⚠️</div>
                <h2 id="error-modal-title" class="error-modal__title">{_safe(title)}{error_code_text}</h2>
                <p class="error-modal__content">{_safe(message)}</p>
                {detail_html}
                {recovery_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("---")
    
    if secondary_action_label:
        col1, col2 = st.columns(2)
        with col1:
            primary_clicked = st.button(
                primary_action_label,
                key=primary_action_key,
                type="primary",
                use_container_width=True,
            )
        with col2:
            secondary_clicked = st.button(
                secondary_action_label,
                key=secondary_action_key,
                use_container_width=True,
            )
    else:
        primary_clicked = st.button(
            primary_action_label,
            key=primary_action_key,
            type="primary",
            use_container_width=True,
        )
        secondary_clicked = False
    
    return primary_clicked, secondary_clicked
