"""
Shared notification UI for Studaxis dashboards.

This module implements a placeholder-driven notification experience for:
  - Student Local Application
  - Teacher Cloud Dashboard preview

It is intentionally UI-only. No realtime transport, websocket, AWS AppSync,
SNS, or backend delivery logic is implemented here.
"""

from __future__ import annotations

from copy import deepcopy
from html import escape
from typing import Any

import streamlit as st


_DEFAULT_UNREAD_COUNT = "[UNREAD_COUNT]"
_DEFAULT_MESSAGE = "[NOTIFICATION_MESSAGE]"
_DEFAULT_TIMESTAMP = "[NOTIFICATION_TIMESTAMP]"
_DEFAULT_EVENT = "[NOTIFICATION_EVENT]"
_DEFAULT_STUDENT_NAME = "[STUDENT_NAME]"

_STUDENT_NOTIFICATIONS: list[dict[str, Any]] = [
    {
        "id": "student-assignment",
        "icon": "📝",
        "category": "New assignment available",
        "message": _DEFAULT_MESSAGE,
        "timestamp": _DEFAULT_TIMESTAMP,
        "status": "unread",
        "priority": "medium",
        "event": "New assignment available",
        "accent": "assignment",
        "details": "Assignment alert details: [NOTIFICATION_EVENT]",
    },
    {
        "id": "student-quiz-feedback",
        "icon": "✅",
        "category": "Quiz feedback available",
        "message": _DEFAULT_MESSAGE,
        "timestamp": _DEFAULT_TIMESTAMP,
        "status": "unread",
        "priority": "medium",
        "event": "Quiz feedback available",
        "accent": "feedback",
        "details": "Feedback summary placeholder for the selected quiz attempt.",
    },
    {
        "id": "student-streak-reminder",
        "icon": "🔥",
        "category": "Streak reminder",
        "message": _DEFAULT_MESSAGE,
        "timestamp": _DEFAULT_TIMESTAMP,
        "status": "read",
        "priority": "low",
        "event": "Streak reminder",
        "accent": "reminder",
        "details": "Reminder details placeholder for the current study streak.",
    },
    {
        "id": "student-sync-completed",
        "icon": "☁️",
        "category": "Sync completed",
        "message": _DEFAULT_MESSAGE,
        "timestamp": _DEFAULT_TIMESTAMP,
        "status": "read",
        "priority": "low",
        "event": "Sync completed",
        "accent": "sync",
        "details": "Last successful sync details placeholder.",
    },
    {
        "id": "student-sync-pending",
        "icon": "⏳",
        "category": "Sync pending",
        "message": _DEFAULT_MESSAGE,
        "timestamp": _DEFAULT_TIMESTAMP,
        "status": "unread",
        "priority": "high",
        "event": "Sync pending",
        "accent": "sync-pending",
        "details": "Pending sync details placeholder.",
    },
    {
        "id": "student-ai-insight",
        "icon": "💡",
        "category": "AI insight generated",
        "message": _DEFAULT_MESSAGE,
        "timestamp": _DEFAULT_TIMESTAMP,
        "status": "unread",
        "priority": "medium",
        "event": "AI insight generated",
        "accent": "insight",
        "details": "AI-generated study insight placeholder.",
    },
]

_TEACHER_NOTIFICATIONS: list[dict[str, Any]] = [
    {
        "id": "teacher-student-joined",
        "icon": "👤",
        "category": "New student joined class",
        "student_name": _DEFAULT_STUDENT_NAME,
        "event": _DEFAULT_EVENT,
        "message": _DEFAULT_MESSAGE,
        "timestamp": _DEFAULT_TIMESTAMP,
        "status": "unread",
        "priority": "medium",
        "accent": "student",
        "details": "Roster update placeholder for a newly joined student.",
    },
    {
        "id": "teacher-quiz-completed",
        "icon": "📘",
        "category": "Student completed quiz",
        "student_name": _DEFAULT_STUDENT_NAME,
        "event": _DEFAULT_EVENT,
        "message": _DEFAULT_MESSAGE,
        "timestamp": _DEFAULT_TIMESTAMP,
        "status": "unread",
        "priority": "medium",
        "accent": "feedback",
        "details": "Quiz completion placeholder for teacher review.",
    },
    {
        "id": "teacher-sync-pending",
        "icon": "🔄",
        "category": "Sync pending from student device",
        "student_name": _DEFAULT_STUDENT_NAME,
        "event": _DEFAULT_EVENT,
        "message": _DEFAULT_MESSAGE,
        "timestamp": _DEFAULT_TIMESTAMP,
        "status": "read",
        "priority": "high",
        "accent": "sync-pending",
        "details": "Pending student-device sync placeholder.",
    },
    {
        "id": "teacher-assignment-submission",
        "icon": "📥",
        "category": "Assignment submissions",
        "student_name": _DEFAULT_STUDENT_NAME,
        "event": _DEFAULT_EVENT,
        "message": _DEFAULT_MESSAGE,
        "timestamp": _DEFAULT_TIMESTAMP,
        "status": "unread",
        "priority": "high",
        "accent": "assignment",
        "details": "Submission review placeholder.",
    },
    {
        "id": "teacher-weekly-summary",
        "icon": "📊",
        "category": "Weekly progress summary available",
        "student_name": _DEFAULT_STUDENT_NAME,
        "event": _DEFAULT_EVENT,
        "message": _DEFAULT_MESSAGE,
        "timestamp": _DEFAULT_TIMESTAMP,
        "status": "read",
        "priority": "low",
        "accent": "insight",
        "details": "Weekly summary placeholder for the teacher dashboard.",
    },
]

_ROLE_DEFAULTS: dict[str, list[dict[str, Any]]] = {
    "student": _STUDENT_NOTIFICATIONS,
    "teacher": _TEACHER_NOTIFICATIONS,
}


def _inject_notification_css() -> None:
    """Emit notification-specific styling once per session."""
    if st.session_state.get("_notification_css_injected"):
        return

    st.session_state["_notification_css_injected"] = True
    st.markdown(
        """
        <style>
        [data-testid="stPopover"] > button {
            min-height: 44px;
            border-radius: 999px;
            border: 1px solid rgba(148, 163, 184, 0.28);
            background: rgba(255, 255, 255, 0.82);
            box-shadow: 0 10px 26px rgba(15, 23, 42, 0.08);
            color: #0F172A;
            font-weight: 700;
        }

        [data-testid="stPopover"] > button:hover {
            border-color: rgba(0, 168, 232, 0.42);
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.12);
        }

        .notification-panel {
            border-radius: 18px;
            padding: 6px 2px 2px 2px;
            color: #0F172A;
        }

        .notification-panel--dark {
            color: #E5E7EB;
        }

        .notification-panel__eyebrow {
            margin: 0;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #64748B;
        }

        .notification-panel--dark .notification-panel__eyebrow {
            color: #94A3B8;
        }

        .notification-panel__title {
            margin: 4px 0 2px 0;
            font-size: 18px;
            font-weight: 700;
            color: inherit;
        }

        .notification-panel__subtitle {
            margin: 0;
            font-size: 13px;
            line-height: 1.5;
            color: #64748B;
        }

        .notification-panel--dark .notification-panel__subtitle {
            color: #94A3B8;
        }

        .notification-panel__hint {
            margin: 10px 0 0 0;
            padding: 10px 12px;
            border-radius: 12px;
            border: 1px dashed rgba(148, 163, 184, 0.35);
            background: rgba(248, 250, 252, 0.9);
            color: #475569;
            font-size: 12px;
        }

        .notification-panel--dark .notification-panel__hint {
            background: rgba(15, 23, 42, 0.72);
            color: #CBD5E1;
            border-color: rgba(148, 163, 184, 0.25);
        }

        .notification-item {
            position: relative;
            border-radius: 18px;
            margin: 12px 0;
            padding: 16px 16px 14px 18px;
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid rgba(226, 232, 240, 0.92);
            box-shadow: 0 14px 34px rgba(15, 23, 42, 0.07);
            overflow: hidden;
        }

        .notification-item::before {
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 5px;
            background: #CBD5E1;
        }

        .notification-panel--dark .notification-item {
            background: rgba(15, 23, 42, 0.88);
            border-color: rgba(148, 163, 184, 0.26);
            box-shadow: 0 16px 36px rgba(2, 6, 23, 0.35);
        }

        .notification-item--unread {
            background:
                linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 248, 240, 0.94));
        }

        .notification-panel--dark .notification-item--unread {
            background:
                linear-gradient(180deg, rgba(30, 41, 59, 0.98), rgba(15, 23, 42, 0.96));
        }

        .notification-item--priority-low::before { background: #CBD5E1; }
        .notification-item--priority-medium::before { background: #FDBA74; }
        .notification-item--priority-high::before { background: #FB7185; }

        .notification-item__top {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 12px;
        }

        .notification-item__main {
            display: flex;
            gap: 12px;
            min-width: 0;
            flex: 1 1 auto;
        }

        .notification-item__icon {
            width: 40px;
            height: 40px;
            border-radius: 12px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: rgba(248, 250, 252, 0.95);
            border: 1px solid rgba(226, 232, 240, 0.95);
            font-size: 19px;
            flex-shrink: 0;
        }

        .notification-panel--dark .notification-item__icon {
            background: rgba(30, 41, 59, 0.92);
            border-color: rgba(148, 163, 184, 0.18);
        }

        .notification-item__icon--assignment { color: #C2410C; }
        .notification-item__icon--feedback { color: #0F766E; }
        .notification-item__icon--reminder { color: #B45309; }
        .notification-item__icon--sync { color: #2563EB; }
        .notification-item__icon--sync-pending { color: #BE123C; }
        .notification-item__icon--insight { color: #7C3AED; }
        .notification-item__icon--student { color: #1D4ED8; }

        .notification-item__content {
            min-width: 0;
            flex: 1 1 auto;
        }

        .notification-item__category {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 8px;
            padding: 4px 10px;
            border-radius: 999px;
            background: rgba(248, 250, 252, 0.94);
            border: 1px solid rgba(226, 232, 240, 0.92);
            font-size: 11px;
            font-weight: 700;
            color: #475569;
        }

        .notification-panel--dark .notification-item__category {
            background: rgba(30, 41, 59, 0.94);
            border-color: rgba(148, 163, 184, 0.22);
            color: #CBD5E1;
        }

        .notification-item__message {
            margin: 0;
            font-size: 14px;
            line-height: 1.5;
            color: inherit;
            word-break: break-word;
        }

        .notification-item--unread .notification-item__message {
            font-weight: 700;
        }

        .notification-item__detail-row {
            margin-top: 8px;
            font-size: 12px;
            line-height: 1.45;
            color: #64748B;
        }

        .notification-panel--dark .notification-item__detail-row {
            color: #94A3B8;
        }

        .notification-item__label {
            font-weight: 700;
            color: #334155;
        }

        .notification-panel--dark .notification-item__label {
            color: #E2E8F0;
        }

        .notification-item__meta {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 8px;
            flex-shrink: 0;
        }

        .notification-status {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 74px;
            padding: 5px 10px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            border: 1px solid transparent;
        }

        .notification-status--unread {
            background: rgba(59, 130, 246, 0.12);
            color: #1D4ED8;
            border-color: rgba(59, 130, 246, 0.18);
        }

        .notification-status--read {
            background: rgba(148, 163, 184, 0.12);
            color: #64748B;
            border-color: rgba(148, 163, 184, 0.16);
        }

        .notification-item__time {
            font-size: 12px;
            font-weight: 600;
            color: #64748B;
            text-align: right;
        }

        .notification-panel--dark .notification-item__time {
            color: #94A3B8;
        }

        .notification-details {
            margin-top: 10px;
            padding: 12px;
            border-radius: 12px;
            background: rgba(248, 250, 252, 0.9);
            border: 1px solid rgba(226, 232, 240, 0.86);
            font-size: 13px;
            line-height: 1.55;
            color: #334155;
        }

        .notification-panel--dark .notification-details {
            background: rgba(30, 41, 59, 0.78);
            border-color: rgba(148, 163, 184, 0.2);
            color: #E2E8F0;
        }

        .notification-empty {
            margin: 16px 0 8px 0;
            padding: 24px 18px 20px 18px;
            border-radius: 18px;
            text-align: center;
            background: rgba(255, 255, 255, 0.88);
            border: 1px dashed rgba(226, 232, 240, 0.95);
            box-shadow: 0 14px 34px rgba(15, 23, 42, 0.05);
        }

        .notification-panel--dark .notification-empty {
            background: rgba(15, 23, 42, 0.88);
            border-color: rgba(148, 163, 184, 0.24);
        }

        .notification-empty__illustration {
            aspect-ratio: 1 / 1;
            width: min(148px, 100%);
            margin: 0 auto 14px auto;
            border-radius: 22px;
            border: 1px dashed rgba(148, 163, 184, 0.34);
            background:
                radial-gradient(circle at top, rgba(253, 186, 116, 0.4), transparent 62%),
                linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(248, 250, 252, 0.88));
            display: flex;
            align-items: center;
            justify-content: center;
            color: #94A3B8;
            font-size: 12px;
            line-height: 1.4;
            padding: 14px;
            box-sizing: border-box;
        }

        .notification-panel--dark .notification-empty__illustration {
            background:
                radial-gradient(circle at top, rgba(251, 191, 36, 0.18), transparent 60%),
                linear-gradient(180deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.9));
            border-color: rgba(148, 163, 184, 0.24);
            color: #94A3B8;
        }

        .notification-empty__title {
            margin: 0 0 6px 0;
            font-size: 18px;
            font-weight: 700;
            color: inherit;
        }

        .notification-empty__hint {
            margin: 0;
            font-size: 13px;
            line-height: 1.5;
            color: #64748B;
        }

        .notification-panel--dark .notification-empty__hint {
            color: #94A3B8;
        }

        @media (max-width: 768px) {
            .notification-item__top {
                flex-direction: column;
            }

            .notification-item__meta {
                align-items: flex-start;
            }

            .notification-item__time {
                text-align: left;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _ensure_notification_state(role: str) -> None:
    """Create placeholder notification state when no UI data has been supplied."""
    if role not in _ROLE_DEFAULTS:
        raise ValueError(f"Unsupported notification role: {role}")

    notifications_key = f"{role}_notifications"
    unread_key = f"{role}_notification_unread_count"

    st.session_state.setdefault(notifications_key, deepcopy(_ROLE_DEFAULTS[role]))
    st.session_state.setdefault(unread_key, _DEFAULT_UNREAD_COUNT)


def _safe_text(value: Any, fallback: str) -> str:
    raw = fallback if value in (None, "") else str(value)
    return escape(raw)


def _notification_html(item: dict[str, Any], role: str) -> str:
    """Build the main visual card for a notification item."""
    status = "read" if item.get("status") == "read" else "unread"
    priority = str(item.get("priority", "low")).lower()
    if priority not in {"low", "medium", "high"}:
        priority = "low"

    accent = str(item.get("accent", "assignment")).lower()
    category = _safe_text(item.get("category"), _DEFAULT_EVENT)
    icon = _safe_text(item.get("icon"), "🔔")
    timestamp = _safe_text(item.get("timestamp"), _DEFAULT_TIMESTAMP)
    status_label = "Read" if status == "read" else "Unread"

    if role == "teacher":
        student_name = _safe_text(item.get("student_name"), _DEFAULT_STUDENT_NAME)
        event = _safe_text(item.get("event"), _DEFAULT_EVENT)
        message_html = (
            f'<div class="notification-item__detail-row">'
            f'  <span class="notification-item__label">Student:</span> {student_name}'
            f"</div>"
            f'<p class="notification-item__message">'
            f'  <span class="notification-item__label">Event:</span> {event}'
            f"</p>"
        )
    else:
        message = _safe_text(item.get("message"), _DEFAULT_MESSAGE)
        event = _safe_text(item.get("event"), _DEFAULT_EVENT)
        message_html = (
            f'<p class="notification-item__message">{message}</p>'
            f'<div class="notification-item__detail-row">'
            f'  <span class="notification-item__label">Event:</span> {event}'
            f"</div>"
        )

    return f"""
    <div class="notification-item notification-item--{status} notification-item--priority-{priority}">
      <div class="notification-item__top">
        <div class="notification-item__main">
          <div class="notification-item__icon notification-item__icon--{accent}" aria-label="{category} icon">
            {icon}
          </div>
          <div class="notification-item__content">
            <div class="notification-item__category">{category}</div>
            {message_html}
          </div>
        </div>
        <div class="notification-item__meta">
          <span class="notification-status notification-status--{status}">{status_label}</span>
          <div class="notification-item__time">Time: {timestamp}</div>
        </div>
      </div>
    </div>
    """


def _set_notification_read(role: str, item_id: str) -> None:
    notifications_key = f"{role}_notifications"
    items = deepcopy(st.session_state.get(notifications_key, []))
    changed = False

    for item in items:
        if item.get("id") == item_id and item.get("status") != "read":
            item["status"] = "read"
            changed = True

    if changed:
        st.session_state[notifications_key] = items
        st.session_state[f"{role}_notification_unread_count"] = sum(
            1 for item in items if item.get("status") == "unread"
        )
        st.rerun()


def _clear_notifications(role: str) -> None:
    st.session_state[f"{role}_notifications"] = []
    st.session_state[f"{role}_notification_unread_count"] = 0
    st.rerun()


def _render_empty_state(theme: str) -> None:
    panel_class = "notification-panel notification-panel--dark" if theme == "dark" else "notification-panel"
    st.markdown(
        f"""
        <div class="{panel_class}">
          <div class="notification-empty" role="status" aria-live="polite">
            <div
              class="notification-empty__illustration"
              aria-label="Empty State Illustration Placeholder"
            >
              Empty State Illustration Placeholder
            </div>
            <p class="notification-empty__title">You're all caught up!</p>
            <p class="notification-empty__hint">
              New updates will appear here when notification data is available.
            </p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_notification_panel(role: str, theme: str, key_prefix: str) -> None:
    notifications_key = f"{role}_notifications"
    items = st.session_state.get(notifications_key, [])
    title = "Student Notifications" if role == "student" else "Teacher Notifications"
    subtitle = (
        "UI-only placeholders for local study alerts."
        if role == "student"
        else "UI-only placeholders for class and learner alerts."
    )
    panel_class = "notification-panel notification-panel--dark" if theme == "dark" else "notification-panel"

    st.markdown(
        f"""
        <div class="{panel_class}" role="region" aria-label="{title}">
          <p class="notification-panel__eyebrow">Notifications</p>
          <p class="notification-panel__title">{title}</p>
          <p class="notification-panel__subtitle">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    clear_col, _ = st.columns([1.2, 2.3])
    with clear_col:
        if st.button(
            "Clear all notifications",
            key=f"{key_prefix}_clear_all_notifications",
            use_container_width=True,
            help="Clear all notifications",
        ):
            _clear_notifications(role)

    if not items:
        _render_empty_state(theme)
        return

    st.markdown(
        f"""
        <div class="{panel_class}">
          <div class="notification-panel__hint">
            Placeholder notification data only. Replace values with real data later:
            {escape(_DEFAULT_EVENT)}, {escape(_DEFAULT_TIMESTAMP)}, {escape(_DEFAULT_UNREAD_COUNT)},
            {escape(_DEFAULT_MESSAGE)}.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for idx, item in enumerate(items):
        item_id = str(item.get("id", f"{role}-item-{idx}"))
        st.markdown(_notification_html(item, role), unsafe_allow_html=True)

        detail_text = _safe_text(item.get("details"), _DEFAULT_EVENT)
        st.markdown(
            f"""
            <div class="{panel_class}">
              <div class="notification-details">
                {detail_text}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if item.get("status") == "unread":
            if st.button(
                "Mark as read",
                key=f"{key_prefix}_mark_read_{item_id}",
                help="Mark notification as read",
            ):
                _set_notification_read(role, item_id)
        else:
            st.button(
                "Marked as read",
                key=f"{key_prefix}_mark_read_disabled_{item_id}",
                disabled=True,
                help="This notification is already marked as read",
            )


def render_notification_bell(role: str, theme: str, key_prefix: str) -> None:
    """
    Render the notification bell entry point in a header area.

    The control opens a non-intrusive expandable notification panel with
    placeholder-driven content. This function is UI-only.
    """
    _inject_notification_css()
    _ensure_notification_state(role)

    unread_count = st.session_state.get(f"{role}_notification_unread_count", _DEFAULT_UNREAD_COUNT)
    label = f"🔔 {unread_count}"

    popover = getattr(st, "popover", None)
    if popover is None:
        with st.expander(label, expanded=False):
            _render_notification_panel(role=role, theme=theme, key_prefix=key_prefix)
        return

    with popover(label, help="Notifications"):
        _render_notification_panel(role=role, theme=theme, key_prefix=key_prefix)
