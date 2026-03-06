"""
Studaxis - Teacher Dashboard Error UI Helpers

Provides error handling UI components for the AWS-hosted teacher dashboard.
Integrates with the existing alert-strip pattern while adding new components.

This module is UI-only. No backend retry logic or AWS error management.
"""

from __future__ import annotations

from html import escape
from typing import Any, Literal

import streamlit as st


# ── Placeholder Constants ─────────────────────────────────────────────────────

PLACEHOLDER_ERROR_CODE = "[ERROR_CODE]"
PLACEHOLDER_API_ENDPOINT = "[API_ENDPOINT]"
PLACEHOLDER_RETRY_INTERVAL = "[RETRY_INTERVAL]"
PLACEHOLDER_SYNC_TIME = "[SYNC_TIME]"


# ── Helper Functions ──────────────────────────────────────────────────────────

def _safe(text: Any, fallback: str = "") -> str:
    """Escape HTML in user-provided text."""
    if text is None or text == "":
        return escape(fallback)
    return escape(str(text))


# ── CSS Injection ─────────────────────────────────────────────────────────────

def inject_error_css() -> None:
    """
    Inject error-specific CSS styles for the teacher dashboard.
    Call once at app initialization.
    """
    if st.session_state.get("_teacher_error_css_injected"):
        return

    st.session_state["_teacher_error_css_injected"] = True
    st.markdown(_ERROR_CSS, unsafe_allow_html=True)


_ERROR_CSS = """
<style>
/* ═══════════════════════════════════════════════════════════════
   TEACHER DASHBOARD ERROR UI COMPONENTS
   ═══════════════════════════════════════════════════════════════ */

/* ── Cloud Error Card ───────────────────────────────────────────── */

.error-cloud-card {
    border-radius: 18px;
    padding: 20px 22px;
    background: rgba(255, 255, 255, 0.85);
    border: 1px solid #e2e8f0;
    border-left: 4px solid #FA5C5C;
    box-shadow: 0 14px 36px rgba(15, 23, 42, 0.07);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    margin: 16px 0;
}

.error-cloud-card__header {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    margin-bottom: 12px;
}

.error-cloud-card__icon {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(250, 92, 92, 0.1);
    color: #FA5C5C;
    font-size: 18px;
    flex-shrink: 0;
}

.error-cloud-card__title-wrap {
    flex: 1;
}

.error-cloud-card__title {
    margin: 0;
    font-size: 16px;
    font-weight: 700;
    color: #0F172A;
}

.error-cloud-card__subtitle {
    margin: 2px 0 0 0;
    font-size: 12px;
    color: #64748B;
}

.error-cloud-card__message {
    margin: 0 0 16px 0;
    font-size: 14px;
    color: #64748B;
    line-height: 1.55;
}

.error-cloud-card__code {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    background: rgba(248, 250, 252, 0.9);
    font-size: 12px;
    font-family: "SF Mono", "Consolas", monospace;
    color: #475569;
}

/* ── Inline Error Banner ────────────────────────────────────────── */

.error-inline-banner {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    border-radius: 10px;
    background: rgba(250, 92, 92, 0.08);
    border: 1px solid rgba(250, 92, 92, 0.28);
    margin: 12px 0;
}

.error-inline-banner__icon {
    font-size: 18px;
    flex-shrink: 0;
}

.error-inline-banner__content {
    flex: 1;
}

.error-inline-banner__title {
    margin: 0;
    font-size: 13px;
    font-weight: 600;
    color: #7F1D1D;
}

.error-inline-banner__message {
    margin: 2px 0 0 0;
    font-size: 12px;
    color: #64748B;
}

/* Warning variant */
.error-inline-banner--warning {
    background: rgba(245, 158, 11, 0.08);
    border-color: rgba(245, 158, 11, 0.28);
}

.error-inline-banner--warning .error-inline-banner__title {
    color: #92400E;
}

/* ── API Error State ────────────────────────────────────────────── */

.error-api-state {
    text-align: center;
    padding: 40px 20px;
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.7);
    border: 1px solid #e2e8f0;
    margin: 20px 0;
}

.error-api-state__icon {
    font-size: 48px;
    margin-bottom: 16px;
    opacity: 0.8;
}

.error-api-state__title {
    margin: 0 0 8px 0;
    font-size: 18px;
    font-weight: 700;
    color: #0F172A;
}

.error-api-state__message {
    margin: 0 0 20px 0;
    font-size: 14px;
    color: #64748B;
    max-width: 400px;
    margin-left: auto;
    margin-right: auto;
}

/* ── Sync Error Indicator ───────────────────────────────────────── */

.error-sync-indicator {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 999px;
    background: rgba(250, 92, 92, 0.1);
    border: 1px solid rgba(250, 92, 92, 0.28);
    font-size: 11px;
    font-weight: 600;
    color: #FA5C5C;
}

.error-sync-indicator__dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #FA5C5C;
    animation: sync-error-pulse 1.5s ease-in-out infinite;
}

@keyframes sync-error-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}
</style>
"""


# ── Cloud Infrastructure Error Card ───────────────────────────────────────────

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
    Render an error card for cloud infrastructure errors.
    
    Use for:
      - API failures (AppSync, API Gateway, Lambda)
      - Sync failures (S3, DynamoDB)
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
        endpoint_html = f' · <span class="error-cloud-card__code">{_safe(api_endpoint)}</span>'
    
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


# ── Inline Error Banner ───────────────────────────────────────────────────────

def render_inline_error_banner(
    title: str,
    message: str,
    *,
    severity: Literal["error", "warning"] = "error",
) -> None:
    """
    Render a compact inline error banner.
    
    Args:
        title: Short error headline
        message: Brief description
        severity: "error" or "warning"
    """
    inject_error_css()
    
    variant_class = "" if severity == "error" else "error-inline-banner--warning"
    icon = "⚠️" if severity == "error" else "⚡"
    
    st.markdown(
        f"""
        <div class="error-inline-banner {variant_class}" role="alert">
            <span class="error-inline-banner__icon">{icon}</span>
            <div class="error-inline-banner__content">
                <p class="error-inline-banner__title">{_safe(title)}</p>
                <p class="error-inline-banner__message">{_safe(message)}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── API Error State ───────────────────────────────────────────────────────────

def render_api_error_state(
    title: str = "Unable to connect to service",
    message: str | None = None,
    *,
    on_retry_key: str = "api_error_retry",
) -> bool:
    """
    Render a full-width API error state with retry button.
    
    Args:
        title: Error headline
        message: Error description
        on_retry_key: Button key for retry
    
    Returns:
        True if retry was clicked
    """
    inject_error_css()
    
    default_message = (
        "The service is temporarily unavailable. "
        f"Will retry automatically in {PLACEHOLDER_RETRY_INTERVAL}."
    )
    
    st.markdown(
        f"""
        <div class="error-api-state" role="alert">
            <div class="error-api-state__icon">🔌</div>
            <h3 class="error-api-state__title">{_safe(title)}</h3>
            <p class="error-api-state__message">{_safe(message or default_message)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        return st.button(
            "🔄 Retry Now",
            key=on_retry_key,
            type="primary",
            use_container_width=True,
        )


# ── Sync Error Indicator ──────────────────────────────────────────────────────

def render_sync_error_indicator(
    student_id: str,
    error_message: str = "Sync failed",
) -> None:
    """
    Render a compact sync error indicator for student rows.
    
    Args:
        student_id: Student identifier
        error_message: Brief error description
    """
    inject_error_css()
    
    st.markdown(
        f"""
        <div class="error-sync-indicator" title="{_safe(error_message)} for {_safe(student_id)}">
            <span class="error-sync-indicator__dot"></span>
            Sync Error
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Alert Strip Helpers (matching existing pattern) ───────────────────────────

def alert_strip_error(message: str) -> None:
    """Render a critical error alert strip."""
    st.markdown(
        f'<div class="alert-strip alert-crit">❌ {_safe(message)}</div>',
        unsafe_allow_html=True,
    )


def alert_strip_warning(message: str) -> None:
    """Render a warning alert strip."""
    st.markdown(
        f'<div class="alert-strip alert-warn">⚠️ {_safe(message)}</div>',
        unsafe_allow_html=True,
    )


def alert_strip_info(message: str) -> None:
    """Render an info alert strip."""
    st.markdown(
        f'<div class="alert-strip alert-info">ℹ️ {_safe(message)}</div>',
        unsafe_allow_html=True,
    )


def alert_strip_success(message: str) -> None:
    """Render a success alert strip."""
    st.markdown(
        f'<div class="alert-strip alert-ok">✅ {_safe(message)}</div>',
        unsafe_allow_html=True,
    )


# ── AWS Service Error Handlers ────────────────────────────────────────────────

def render_s3_error(
    bucket: str,
    operation: str = "read",
    error_code: str = PLACEHOLDER_ERROR_CODE,
) -> bool:
    """
    Render S3-specific error card.
    
    Returns:
        True if retry was clicked
    """
    retry, _ = render_cloud_error_card(
        title=f"S3 {operation} failed",
        message=f"Unable to {operation} from bucket '{bucket}'. Check bucket permissions and region configuration.",
        error_code=error_code,
        api_endpoint=f"s3://{bucket}",
        on_retry_key=f"s3_error_retry_{bucket}",
        on_refresh_key=f"s3_error_refresh_{bucket}",
    )
    return retry


def render_dynamodb_error(
    table: str,
    operation: str = "query",
    error_code: str = PLACEHOLDER_ERROR_CODE,
) -> bool:
    """
    Render DynamoDB-specific error card.
    
    Returns:
        True if retry was clicked
    """
    retry, _ = render_cloud_error_card(
        title=f"DynamoDB {operation} failed",
        message=f"Unable to {operation} table '{table}'. Check table status and IAM permissions.",
        error_code=error_code,
        api_endpoint=f"dynamodb://{table}",
        on_retry_key=f"ddb_error_retry_{table}",
        on_refresh_key=f"ddb_error_refresh_{table}",
    )
    return retry


def render_appsync_error(
    operation: str = "query",
    error_code: str = PLACEHOLDER_ERROR_CODE,
) -> bool:
    """
    Render AppSync-specific error card.
    
    Returns:
        True if retry was clicked
    """
    retry, _ = render_cloud_error_card(
        title=f"AppSync {operation} failed",
        message="Unable to complete GraphQL operation. Check API endpoint and authentication.",
        error_code=error_code,
        api_endpoint=PLACEHOLDER_API_ENDPOINT,
        on_retry_key=f"appsync_error_retry_{operation}",
        on_refresh_key=f"appsync_error_refresh_{operation}",
    )
    return retry


def render_bedrock_error(
    model: str = "Claude",
    error_code: str = PLACEHOLDER_ERROR_CODE,
) -> bool:
    """
    Render Bedrock AI service error card.
    
    Returns:
        True if retry was clicked
    """
    retry, _ = render_cloud_error_card(
        title=f"AI generation failed ({model})",
        message="Unable to generate AI content. Check Bedrock model access and quotas.",
        error_code=error_code,
        api_endpoint="bedrock:InvokeModel",
        on_retry_key=f"bedrock_error_retry_{model}",
        on_refresh_key=f"bedrock_error_refresh_{model}",
    )
    return retry
