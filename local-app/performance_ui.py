from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from ui.components.loading_skeleton import (
    render_stats_skeleton as _new_render_stats_skeleton,
    render_chart_skeleton as _new_render_chart_skeleton,
    render_list_skeleton as _new_render_list_skeleton,
    render_lazy_card as _new_render_lazy_card,
)
from ui.components.illustration_placeholder import render_illustration


MEMORY_LIMIT = "[MEMORY_LIMIT]"
MODEL_LOAD_TIME = "[MODEL_LOAD_TIME]"
LOW_POWER_MODE_THRESHOLD = "[LOW_POWER_MODE_THRESHOLD]"
MAX_BACKGROUND_TASKS = "[MAX_BACKGROUND_TASKS]"


def init_performance_ui_state() -> None:
    """Seed placeholder-driven UI state for performance-aware rendering."""
    st.session_state.setdefault("performance_css_ready", False)
    st.session_state.setdefault("low_power_mode_active", False)
    st.session_state.setdefault("low_power_mode_reason", LOW_POWER_MODE_THRESHOLD)
    st.session_state.setdefault("network_speed_state", "normal")  # normal | low
    st.session_state.setdefault("model_init_complete", False)
    st.session_state.setdefault("dashboard_stats_ready", False)
    st.session_state.setdefault("teacher_analytics_visible", False)
    st.session_state.setdefault("flashcard_set_visible", False)
    st.session_state.setdefault("storage_manager_visible", False)


def inject_performance_ui_css() -> None:
    """Inject shared CSS for loading, low-power, and low-bandwidth states."""
    low_power_mode = st.session_state.get("low_power_mode_active", False)
    low_power_overrides = """
    .dashboard-stat-card,
    .dashboard-feature-card,
    .insight-card,
    .chat-bubble-ai,
    .chat-skeleton-line,
    .performance-loading-spinner,
    .performance-shimmer,
    .sync-monitor__pill--syncing .sync-monitor__dot {
        animation: none !important;
        transition: none !important;
        transform: none !important;
    }
    """ if low_power_mode else ""

    st.markdown(
        f"""
        <style>
        .performance-pill {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 12px;
            border-radius: 999px;
            border: 1px solid rgba(148, 163, 184, 0.35);
            background: rgba(148, 163, 184, 0.14);
            color: #475569;
            font-size: 11px;
            font-weight: 600;
            line-height: 1.3;
            white-space: nowrap;
        }}

        .performance-pill__dot {{
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #94A3B8;
            display: inline-block;
            flex-shrink: 0;
        }}

        .performance-note {{
            margin-top: 8px;
            padding: 10px 12px;
            border-radius: 12px;
            background: rgba(148, 163, 184, 0.08);
            border: 1px solid rgba(148, 163, 184, 0.22);
            color: #64748B;
            font-size: 12px;
            line-height: 1.5;
        }}

        .performance-note--network {{
            background: rgba(148, 163, 184, 0.08);
            border-color: rgba(148, 163, 184, 0.22);
            color: #475569;
        }}

        .performance-loading-card {{
            border-radius: 18px;
            padding: 20px 22px;
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid #E2E8F0;
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            color: #0F172A;
            margin-bottom: 14px;
        }}

        .performance-loading-card__head {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            margin-bottom: 14px;
            flex-wrap: wrap;
        }}

        .performance-loading-card__title {{
            margin: 0;
            font-size: 16px;
            font-weight: 700;
            color: #0F172A;
        }}

        .performance-loading-card__desc {{
            margin: 4px 0 0 0;
            font-size: 13px;
            line-height: 1.5;
            color: #64748B;
        }}

        .performance-loading-spinner {{
            width: 16px;
            height: 16px;
            border-radius: 50%;
            border: 2px solid rgba(148, 163, 184, 0.35);
            border-top-color: #94A3B8;
            animation: performance-spin 1s linear infinite;
            flex-shrink: 0;
        }}

        @keyframes performance-spin {{
            from {{ transform: rotate(0deg); }}
            to {{ transform: rotate(360deg); }}
        }}

        .performance-illustration {{
            width: 100%;
            border-radius: 16px;
            border: 1px dashed rgba(148, 163, 184, 0.35);
            background:
                radial-gradient(circle at top, rgba(254, 194, 136, 0.18), transparent 55%),
                linear-gradient(180deg, rgba(255, 255, 255, 0.7), rgba(248, 250, 252, 0.92));
            position: relative;
            overflow: hidden;
        }}

        .performance-illustration--four-three {{
            aspect-ratio: 4 / 3;
        }}

        .performance-illustration--sixteen-nine {{
            aspect-ratio: 16 / 9;
        }}

        .performance-illustration::after {{
            content: "";
            position: absolute;
            inset: 16px;
            border-radius: 12px;
            border: 1px dashed rgba(148, 163, 184, 0.28);
        }}

        .performance-skeleton-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
            margin-bottom: 14px;
        }}

        .performance-skeleton-card,
        .performance-skeleton-chart,
        .performance-skeleton-list {{
            border-radius: 18px;
            padding: 18px;
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid #E2E8F0;
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.06);
        }}

        .performance-skeleton-row {{
            height: 12px;
            border-radius: 999px;
            background: linear-gradient(90deg, #E5E7EB 25%, #F3F4F6 50%, #E5E7EB 75%);
            background-size: 200% 100%;
            animation: performance-shimmer 1.6s ease-in-out infinite;
            margin-bottom: 10px;
        }}

        .performance-skeleton-row:last-child {{
            margin-bottom: 0;
        }}

        .performance-skeleton-row--lg {{
            height: 22px;
            width: 48%;
        }}

        .performance-skeleton-row--md {{
            width: 72%;
        }}

        .performance-skeleton-row--sm {{
            width: 42%;
        }}

        .performance-skeleton-chart {{
            min-height: 220px;
        }}

        .performance-skeleton-chart__plot {{
            height: 140px;
            border-radius: 16px;
            background: linear-gradient(180deg, rgba(229, 231, 235, 0.9), rgba(243, 244, 246, 0.7));
            margin-top: 18px;
            position: relative;
            overflow: hidden;
        }}

        .performance-skeleton-chart__plot::after {{
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(90deg, rgba(243, 244, 246, 0), rgba(255, 255, 255, 0.65), rgba(243, 244, 246, 0));
            animation: performance-shimmer 1.6s ease-in-out infinite;
        }}

        .performance-skeleton-list__item {{
            display: grid;
            grid-template-columns: 44px 1fr;
            gap: 12px;
            align-items: center;
            margin-bottom: 12px;
        }}

        .performance-skeleton-list__item:last-child {{
            margin-bottom: 0;
        }}

        .performance-skeleton-avatar {{
            width: 44px;
            height: 44px;
            border-radius: 12px;
            background: #E5E7EB;
            animation: performance-shimmer 1.6s ease-in-out infinite;
            background-image: linear-gradient(90deg, #E5E7EB 25%, #F3F4F6 50%, #E5E7EB 75%);
            background-size: 200% 100%;
        }}

        @keyframes performance-shimmer {{
            0% {{ background-position: 200% 0; }}
            100% {{ background-position: -200% 0; }}
        }}

        .model-init-shell {{
            min-height: 100vh;
            padding: 40px 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #F8FAFC;
        }}

        .model-init-card {{
            width: min(860px, 100%);
            border-radius: 24px;
            padding: 28px;
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid #E2E8F0;
            box-shadow: 0 24px 64px rgba(15, 23, 42, 0.08);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
        }}

        .model-init-title {{
            margin: 0 0 8px 0;
            font-size: 28px;
            line-height: 1.2;
            color: #0F172A;
        }}

        .model-init-subtitle {{
            margin: 0 0 18px 0;
            font-size: 14px;
            line-height: 1.55;
            color: #64748B;
        }}

        .model-init-progress {{
            margin-top: 18px;
            padding: 12px 14px;
            border-radius: 14px;
            background: rgba(148, 163, 184, 0.08);
            border: 1px solid rgba(148, 163, 184, 0.22);
        }}

        .model-init-progress__label {{
            font-size: 12px;
            font-weight: 600;
            color: #475569;
            margin-bottom: 8px;
        }}

        .model-init-progress__track {{
            height: 8px;
            border-radius: 999px;
            overflow: hidden;
            background: rgba(148, 163, 184, 0.18);
        }}

        .model-init-progress__fill {{
            height: 100%;
            width: 42%;
            border-radius: 999px;
            background: linear-gradient(90deg, #E5E7EB, #CBD5E1, #E5E7EB);
            background-size: 200% 100%;
            animation: performance-shimmer 1.6s ease-in-out infinite;
        }}

        .theme-dark .performance-loading-card,
        .dashboard-root.theme-dark .performance-loading-card,
        .chat-root.theme-dark .performance-loading-card,
        .settings-root.theme-dark .performance-loading-card,
        .theme-dark .performance-skeleton-card,
        .theme-dark .performance-skeleton-chart,
        .theme-dark .performance-skeleton-list,
        .dashboard-root.theme-dark .performance-skeleton-card,
        .dashboard-root.theme-dark .performance-skeleton-chart,
        .dashboard-root.theme-dark .performance-skeleton-list,
        .chat-root.theme-dark .performance-skeleton-card,
        .chat-root.theme-dark .performance-skeleton-chart,
        .chat-root.theme-dark .performance-skeleton-list,
        .settings-root.theme-dark .performance-skeleton-card,
        .settings-root.theme-dark .performance-skeleton-chart,
        .settings-root.theme-dark .performance-skeleton-list,
        .theme-dark .model-init-card {{
            background: rgba(15, 23, 42, 0.9);
            border-color: rgba(148, 163, 184, 0.25);
            color: #E5E7EB;
        }}

        .theme-dark .performance-loading-card__title,
        .theme-dark .model-init-title,
        .dashboard-root.theme-dark .performance-loading-card__title,
        .settings-root.theme-dark .performance-loading-card__title {{
            color: #E5E7EB;
        }}

        .theme-dark .performance-loading-card__desc,
        .theme-dark .performance-note,
        .theme-dark .model-init-subtitle,
        .theme-dark .model-init-progress__label,
        .dashboard-root.theme-dark .performance-loading-card__desc,
        .settings-root.theme-dark .performance-loading-card__desc {{
            color: #94A3B8;
        }}

        .theme-dark .performance-skeleton-row,
        .theme-dark .performance-skeleton-avatar,
        .dashboard-root.theme-dark .performance-skeleton-row,
        .dashboard-root.theme-dark .performance-skeleton-avatar,
        .settings-root.theme-dark .performance-skeleton-row,
        .settings-root.theme-dark .performance-skeleton-avatar {{
            background: linear-gradient(90deg, #1E293B 25%, #334155 50%, #1E293B 75%);
            background-size: 200% 100%;
        }}

        .theme-dark .performance-skeleton-chart__plot,
        .dashboard-root.theme-dark .performance-skeleton-chart__plot,
        .settings-root.theme-dark .performance-skeleton-chart__plot {{
            background: linear-gradient(180deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.78));
        }}

        .theme-dark .performance-pill,
        .dashboard-root.theme-dark .performance-pill,
        .chat-root.theme-dark .performance-pill {{
            background: rgba(148, 163, 184, 0.14);
            border-color: rgba(148, 163, 184, 0.24);
            color: #CBD5E1;
        }}

        .theme-dark .performance-note--network,
        .dashboard-root.theme-dark .performance-note--network,
        .settings-root.theme-dark .performance-note--network {{
            color: #CBD5E1;
        }}

        @media (prefers-reduced-motion: reduce) {{
            .performance-loading-spinner,
            .performance-skeleton-row,
            .performance-skeleton-avatar,
            .performance-skeleton-chart__plot::after,
            .model-init-progress__fill,
            .chat-skeleton-line,
            .sync-monitor__pill--syncing .sync-monitor__dot {{
                animation: none !important;
            }}

            .dashboard-stat-card,
            .dashboard-feature-card,
            .insight-card,
            div.stButton > button {{
                transition: none !important;
                transform: none !important;
            }}
        }}

        {low_power_overrides}
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_performance_mode_from_hardware() -> None:
    """Map existing hardware warnings onto a UI-only low power mode."""
    hardware_status = st.session_state.get("hardware_status")
    if hardware_status == "warn":
        st.session_state.low_power_mode_active = True
        st.session_state.low_power_mode_reason = LOW_POWER_MODE_THRESHOLD


def render_low_power_indicator() -> None:
    if not st.session_state.get("low_power_mode_active", False):
        return

    st.markdown(
        """
        <span class="performance-pill" role="status" aria-label="Low Power Mode Active">
          <span class="performance-pill__dot" aria-hidden="true"></span>
          Low Power Mode Active — Reduced animations and background tasks.
        </span>
        """,
        unsafe_allow_html=True,
    )


def render_low_bandwidth_note() -> None:
    if st.session_state.get("network_speed_state", "normal") != "low":
        return

    st.markdown(
        """
        <div class="performance-note performance-note--network" role="status" aria-live="polite">
          Low network speed detected. Sync may take longer.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard_stats_skeleton() -> None:
    _new_render_stats_skeleton()


def render_teacher_analytics_skeleton() -> None:
    _new_render_chart_skeleton()


def render_storage_list_skeleton() -> None:
    _new_render_list_skeleton()


def render_lazy_loading_card(
    title: str,
    description: str = "Loading data...",
    illustration_ratio: str = "4:3",
) -> None:
    _new_render_lazy_card(title, description, illustration_ratio)


def render_model_initialization_screen(
    progress: int = 0,
    status_text: str = "Preparing AI engine...",
) -> None:
    """Render the AI engine loading screen with milestone-based progress (no JS timer)."""
    # 🚨 THE FAILSAFE: If already booted, completely abort rendering!
    if st.session_state.get("app_booted", False):
        return

    progress = max(0, min(100, progress))
    pct_str = f"{progress:02d}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        html, body {{
            height: 100%;
            width: 100%;
            margin: 0;
            padding: 0;
            overflow: hidden;
        }}
        body {{
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'Inter', 'Poppins', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }}
        .model-init-shell {{
            height: 100vh;
            width: 100vw;
            min-height: 100%;
            min-width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-sizing: border-box;
            --init-bg-page: #F8FAFC;
            --init-bg-surface: rgba(255, 255, 255, 0.7);
            --init-text-main: #0F172A;
            --init-text-muted: #64748B;
            --init-border: #E2E8F0;
            --init-accent: #00A8E8;
            --init-track: rgba(0, 0, 0, 0.05);
            background: var(--init-bg-page);
        }}

        .model-init-shell .ambient-glow {{
            position: absolute;
            width: 600px;
            height: 600px;
            background: radial-gradient(circle, rgba(0, 168, 232, 0.07) 0%, transparent 70%);
            filter: blur(80px);
            z-index: 0;
            animation: model-init-pulse-glow 8s infinite alternate ease-in-out;
        }}

        .model-init-shell .loading-container {{
            position: relative;
            z-index: 10;
            width: 100%;
            max-width: 600px;
            padding: 40px;
            display: flex;
            flex-direction: column;
            gap: 24px;
            margin: 0 auto;
        }}

        .model-init-shell .glass-layer {{
            position: relative;
            background: var(--init-bg-surface);
            backdrop-filter: blur(24px) saturate(150%);
            -webkit-backdrop-filter: blur(24px) saturate(150%);
            border: 1px solid var(--init-border);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 50px rgba(15, 23, 42, 0.08);
            overflow: hidden;
        }}

        .model-init-shell .brand-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-bottom: 8px;
        }}

        .model-init-shell .title {{
            font-size: 0.85rem;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            font-weight: 600;
            color: var(--init-text-main);
            font-family: 'Inter', sans-serif;
        }}

        .model-init-shell .percentage-wrap {{
            position: relative;
            height: 120px;
            display: flex;
            align-items: center;
        }}

        .model-init-shell .percentage {{
            font-size: 8rem;
            font-weight: 800;
            line-height: 0.8;
            letter-spacing: -0.04em;
            z-index: 2;
            color: var(--init-text-main);
            font-family: 'JetBrains Mono', monospace;
        }}

        .model-init-shell .percentage-wrap .pct-suffix {{
            font-size: 1.5rem;
            font-weight: 300;
            margin-top: 30px;
            margin-left: 10px;
            color: var(--init-text-muted);
            font-family: 'Inter', sans-serif;
        }}

        .model-init-shell .status-meta {{
            margin-top: 20px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            border-top: 1px solid var(--init-border);
            padding-top: 20px;
        }}

        .model-init-shell .meta-item {{
            font-size: 0.75rem;
            display: flex;
            flex-direction: column;
            gap: 4px;
            font-family: 'Inter', sans-serif;
        }}

        .model-init-shell .meta-item .meta-label {{
            opacity: 0.7;
            font-size: 0.65rem;
            color: var(--init-text-muted);
        }}

        .model-init-shell .meta-item .meta-value {{
            font-weight: 600;
            color: var(--init-text-main);
            font-family: 'JetBrains Mono', monospace;
        }}

        .model-init-shell .progress-track {{
            position: relative;
            width: 100%;
            height: 4px;
            background: var(--init-track);
            margin-top: 10px;
            border-radius: 4px;
        }}

        .model-init-shell .progress-fill {{
            position: absolute;
            height: 100%;
            width: {progress}%;
            background: var(--init-accent);
            box-shadow: 0 0 15px rgba(0, 168, 232, 0.5);
            border-radius: 4px;
            transition: width 0.4s cubic-bezier(0.1, 0.5, 0.5, 1);
        }}

        .model-init-shell .status-line {{
            font-size: 0.75rem;
            color: var(--init-text-muted);
            margin-top: 8px;
            font-weight: 500;
            font-family: 'Inter', sans-serif;
        }}

        .model-init-shell .footer-note {{
            font-size: 0.75rem;
            opacity: 0.6;
            text-align: center;
            margin-top: 10px;
            color: var(--init-text-muted);
            font-family: 'Inter', sans-serif;
        }}

        @keyframes model-init-pulse-glow {{
            0% {{ transform: scale(1) translate(0, 0); }}
            100% {{ transform: scale(1.2) translate(5%, 5%); }}
        }}

        @media (prefers-reduced-motion: reduce) {{
            .model-init-shell .ambient-glow {{
                animation: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="model-init-shell" role="status" aria-busy="true" aria-live="polite">
        <div class="ambient-glow" aria-hidden="true"></div>
        <main class="loading-container">
            <div class="brand-header">
                <span class="title">Preparing AI engine...</span>
            </div>

            <section class="glass-layer">
                <div class="percentage-wrap">
                    <span class="percentage" id="model-init-load-val">{pct_str}</span>
                    <span class="pct-suffix">%</span>
                </div>

                <div class="progress-track">
                    <div class="progress-fill" id="model-init-bar-val"></div>
                </div>

                <p class="status-line" id="model-init-status-text">{status_text}</p>

                <div class="status-meta">
                    <div class="meta-item">
                        <span class="meta-label">ESTIMATED TIME</span>
                        <span class="meta-value">{MODEL_LOAD_TIME}</span>
                    </div>
                    <div class="meta-item">
                        <span class="meta-label">TASK CAP</span>
                        <span class="meta-value">{MAX_BACKGROUND_TASKS}</span>
                    </div>
                </div>
            </section>
            <div class="footer-note">
                This may take a moment on first launch.
            </div>
        </main>
    </div>
</body>
</html>"""
    components.html(html, height=800, scrolling=False)


def render_performance_thresholds_caption() -> None:
    st.caption(
        "Performance placeholders: "
        f"memory {MEMORY_LIMIT} · model load {MODEL_LOAD_TIME} · "
        f"low power {LOW_POWER_MODE_THRESHOLD} · background tasks {MAX_BACKGROUND_TASKS}"
    )
