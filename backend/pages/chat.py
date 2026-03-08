"""
Studaxis – AI Tutor Chat Interface
Conversational interface with glass message bubbles, session-state history,
Clarify support, and a placeholder streaming simulation (no backend wiring).
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any

import streamlit as st
from ai_integration_layer import AIEngine, AITaskType
from performance_ui import render_low_power_indicator
from ui.components.page_chrome import render_page_root_open, render_page_root_close, render_back_button
from ui.components.loading_skeleton import render_chat_typing_skeleton

# ── Constants ────────────────────────────────────────────────────────────────

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "user_stats.json")
MAX_HISTORY = 50


# ── Data helpers ─────────────────────────────────────────────────────────────

def _load_stats() -> dict[str, Any]:
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_stats(stats: dict[str, Any]) -> None:
    try:
        with open(_DATA_PATH, "w", encoding="utf-8") as fh:
            json.dump(stats, fh, indent=2, ensure_ascii=False)
    except OSError:
        pass  # Silently ignore write errors in degraded storage state


def _load_history() -> list[dict[str, Any]]:
    stats = _load_stats()
    raw: list[dict[str, Any]] = stats.get("chat_history", [])
    return raw[-MAX_HISTORY:] if len(raw) > MAX_HISTORY else raw


def _save_history(messages: list[dict[str, Any]]) -> None:
    stats = _load_stats()
    stats["chat_history"] = messages[-MAX_HISTORY:]
    _save_stats(stats)


def _save_difficulty(level: str) -> None:
    stats = _load_stats()
    stats.setdefault("preferences", {})["difficulty_level"] = level
    _save_stats(stats)


def _ts() -> str:
    return datetime.now().strftime("%H:%M")


def _full_ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ── Session state ─────────────────────────────────────────────────────────────

def _init_chat_state() -> None:
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = _load_history()
    if "chat_is_loading" not in st.session_state:
        st.session_state.chat_is_loading = False
    if "chat_difficulty" not in st.session_state:
        stats = _load_stats()
        st.session_state.chat_difficulty = (
            stats.get("preferences", {}).get("difficulty_level", "Beginner")
        )
    if "ai_engine" not in st.session_state:
        # Base path resolves to backend directory for logs/data.
        st.session_state.ai_engine = AIEngine(base_path=os.path.join(os.path.dirname(__file__), ".."))


# ── Message helpers ───────────────────────────────────────────────────────────

def _make_message(
    role: str,
    content: str,
    is_clarification: bool = False,
    parent_idx: int | None = None,
) -> dict[str, Any]:
    return {
        "role": role,
        "content": content,
        "timestamp": _full_ts(),
        "is_clarification": is_clarification,
        "parent_idx": parent_idx,
    }


def _add_user_message(content: str) -> None:
    st.session_state.chat_messages.append(_make_message("user", content))
    _save_history(st.session_state.chat_messages)


def _add_ai_message(content: str, is_clarification: bool = False, parent_idx: int | None = None) -> None:
    st.session_state.chat_messages.append(
        _make_message("assistant", content, is_clarification=is_clarification, parent_idx=parent_idx)
    )
    _save_history(st.session_state.chat_messages)


# ── Render helpers ────────────────────────────────────────────────────────────

def _render_header() -> None:
    connectivity = st.session_state.get("connectivity_status", "offline")
    if connectivity == "online":
        pill_class = "chat-status-pill chat-status-pill--online"
        pill_dot = "●"
        pill_label = "Online"
    else:
        pill_class = "chat-status-pill chat-status-pill--offline"
        pill_dot = "●"
        pill_label = "Offline · AI works fully offline"

    st.markdown(
        f"""
        <div class="chat-header-card">
          <div class="db-icon-chip db-icon-chip--blue" aria-hidden="true">🤖</div>
          <div style="flex:1">
            <div class="chat-header-title">AI Tutor Chat</div>
            <div class="chat-header-meta">Powered by Llama 3.2 · RAG-grounded</div>
          </div>
          <span class="{pill_class}" role="status" aria-label="Connectivity: {pill_label}">
            {pill_dot} {pill_label}
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.session_state.get("low_power_mode_active", False):
        render_low_power_indicator()

    col_diff, col_clear = st.columns([3, 1])
    with col_diff:
        new_diff = st.selectbox(
            "Difficulty level",
            options=["Beginner", "Intermediate", "Expert"],
            index=["Beginner", "Intermediate", "Expert"].index(
                st.session_state.chat_difficulty
            ),
            key="chat_diff_select",
            label_visibility="collapsed",
            help="Adjusts how the AI tutor explains concepts",
        )
        if new_diff and new_diff != st.session_state.chat_difficulty:
            st.session_state.chat_difficulty = new_diff
            _save_difficulty(str(new_diff))
    with col_clear:
        if st.button("🗑 Clear", key="chat_clear_btn", use_container_width=True, help="Clear chat history"):
            st.session_state.chat_messages = []
            _save_history([])
            st.session_state.chat_is_loading = False
            st.rerun()


def _render_skeleton() -> None:
    render_chat_typing_skeleton()


def _render_message(msg: dict[str, Any], idx: int) -> None:
    role = msg["role"]
    content = msg["content"]
    ts = msg.get("timestamp", "")
    if ts and "T" in ts:
        ts = ts.split("T")[1][:5]
    is_clarify = msg.get("is_clarification", False)

    if role == "user":
        safe_content = content.replace("<", "&lt;").replace(">", "&gt;")
        st.markdown(
            f"""
            <div class="chat-msg-user">
              <div>
                <div class="chat-bubble-user">{safe_content}</div>
                <div class="chat-bubble-meta chat-bubble-meta--right">You · {ts}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        bubble_class = "chat-bubble-clarify" if is_clarify else "chat-bubble-ai"
        indent_style = "margin-left:20px;" if is_clarify else ""
        label = "Clarification" if is_clarify else "AI Tutor"
        # Render markdown content safely via st.chat_message context trick:
        # Use a container so markdown renders properly inside the styled bubble.
        st.markdown(
            f'<div class="chat-msg-ai" style="{indent_style}">',
            unsafe_allow_html=True,
        )
        with st.container():
            st.markdown(
                f'<div class="{bubble_class}">', unsafe_allow_html=True
            )
            st.markdown(content)
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(
            f'<div class="chat-bubble-meta">{label} · {ts}</div>',
            unsafe_allow_html=True,
        )

        # Clarify expander — only on primary AI responses, not nested clarifications
        if not is_clarify:
            with st.expander("🤔 Clarify this", expanded=False):
                clarify_val = st.text_input(
                    "What part needs more explanation?",
                    key=f"clarify_input_{idx}",
                    placeholder="e.g. I didn't understand the second point…",
                    label_visibility="collapsed",
                )
                if st.button("Get Clarification", key=f"clarify_btn_{idx}", type="primary"):
                    if clarify_val.strip():
                        _add_user_message(f"[Clarification] {clarify_val.strip()}")
                        st.session_state.chat_is_loading = True
                        st.session_state._clarify_parent_idx = idx
                        st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


def _render_empty_state() -> None:
    st.markdown(
        """
        <div class="chat-empty-state">
          <div class="chat-empty-icon">🤖</div>
          <div class="chat-empty-text">
            Ask me anything from your textbooks.<br>
            I'm fully offline — no internet needed.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_messages() -> None:
    messages = st.session_state.chat_messages
    if not messages and not st.session_state.chat_is_loading:
        _render_empty_state()
        return

    st.markdown('<div class="chat-messages-area">', unsafe_allow_html=True)
    for i, msg in enumerate(messages):
        _render_message(msg, i)
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.chat_is_loading:
        _render_skeleton()


# ── Streaming simulation ──────────────────────────────────────────────────────

def _process_ai_response() -> None:
    """
    Simulate offline inference latency, then append a placeholder AI response.
    Called synchronously while the skeleton is visible on the prior render pass.
    """
    with st.spinner("AI Tutor is preparing a response..."):
        time.sleep(0.3)

    parent_idx = st.session_state.pop("_clarify_parent_idx", None)
    is_clarification = parent_idx is not None

    last_user_text = ""
    for msg in reversed(st.session_state.chat_messages):
        if msg.get("role") == "user":
            last_user_text = msg.get("content", "")
            break

    request_task = AITaskType.CLARIFY if is_clarification else AITaskType.CHAT
    connectivity = st.session_state.get("connectivity_status", "offline")
    offline_mode = connectivity != "online"

    ai_response = st.session_state.ai_engine.request(
        task_type=request_task,
        user_input=last_user_text,
        context_data={
            "difficulty": st.session_state.get("chat_difficulty", "Beginner"),
            "chat_history": st.session_state.chat_messages[-8:],
            "subject": st.session_state.get("active_subject") or "",
            "active_textbook": st.session_state.get("active_textbook") or "",
        },
        offline_mode=offline_mode,
        privacy_sensitive=True,
        user_id=st.session_state.get("profile_name"),
    )

    _add_ai_message(ai_response.text, is_clarification=is_clarification, parent_idx=parent_idx)
    st.session_state.chat_is_loading = False


# ── Main entry ────────────────────────────────────────────────────────────────

def show_chat() -> None:
    theme = st.session_state.get("theme", "light")
    theme_class = "theme-dark" if theme == "dark" else ""

    _init_chat_state()

    # ── If loading, generate response first (skeleton was rendered last pass) ──
    if st.session_state.chat_is_loading:
        _process_ai_response()
        st.rerun()

    # ── Page root div ──────────────────────────────────────────────────────────
    render_page_root_open("chat", theme)

    # Back navigation
    render_back_button("dashboard", "← Back to Dashboard")

    _render_header()
    _render_messages()

    render_page_root_close()

    # ── Chat input (Streamlit native — pins to bottom automatically) ───────────
    user_input = st.chat_input(
        f"Ask a question… ({st.session_state.chat_difficulty})",
        key="chat_main_input",
    )
    if user_input and user_input.strip():
        _add_user_message(user_input.strip())
        st.session_state.chat_is_loading = True
        st.rerun()
