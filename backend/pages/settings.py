"""
Studaxis — Settings Page (Student Local App)
═════════════════════════════════════════════
User preferences, deployment readiness UI, sync controls, and account settings.
"""

from __future__ import annotations

from html import escape
import os
from pathlib import Path

import streamlit as st

from deployment_ui import (
    build_copy_diagnostics_payload,
    get_deployment_context,
    render_copy_to_clipboard_button,
)
from performance_ui import (
    render_lazy_loading_card,
    render_performance_thresholds_caption,
    render_storage_list_skeleton,
)
from ui.components.page_chrome import render_page_root_close, render_page_root_open


def _inject_settings_css() -> None:
    """Inject CSS for settings page and deployment-readiness panels."""
    st.markdown(
        """
        <style>
        .settings-root {
            --db-bg-page: #F8FAFC;
            --db-bg-card: rgba(255, 255, 255, 0.78);
            --db-text-main: #0F172A;
            --db-text-muted: #64748B;
            --db-border: #E2E8F0;
            --db-radius: 18px;
            --db-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
            min-height: 100vh;
            padding: 24px 8px 40px 8px;
            font-family: "Inter", "Poppins", system-ui, sans-serif;
        }

        .settings-root.theme-dark {
            --db-bg-page: #020617;
            --db-bg-card: rgba(15, 23, 42, 0.85);
            --db-text-main: #E5E7EB;
            --db-text-muted: #9CA3AF;
            --db-border: rgba(148, 163, 184, 0.35);
            --db-shadow: 0 18px 45px rgba(0, 0, 0, 0.35);
        }

        .settings-page-title {
            font-size: 26px;
            font-weight: 700;
            color: var(--db-text-main);
            margin: 0 0 8px 0;
        }

        .settings-page-subtitle {
            font-size: 13px;
            color: var(--db-text-muted);
            margin: 0 0 24px 0;
            line-height: 1.6;
        }

        .settings-section-card,
        .deployment-card {
            border-radius: var(--db-radius);
            padding: 20px 24px;
            margin-bottom: 20px;
            background: var(--db-bg-card);
            border: 1px solid var(--db-border);
            box-shadow: var(--db-shadow);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            color: var(--db-text-main);
        }

        .settings-section-title,
        .deployment-card__title {
            font-size: 18px;
            font-weight: 600;
            color: var(--db-text-main);
            margin: 0 0 4px 0;
        }

        .settings-section-desc,
        .deployment-card__desc {
            font-size: 12px;
            color: var(--db-text-muted);
            margin: 0 0 16px 0;
            line-height: 1.55;
        }

        .settings-section-note {
            font-size: 12px;
            color: var(--db-text-muted);
            margin: -6px 0 18px 0;
            line-height: 1.55;
        }

        .settings-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 12px 0;
            border-bottom: 1px solid var(--db-border);
        }

        .settings-row:last-child {
            border-bottom: none;
        }

        .settings-row__label {
            flex: 1;
        }

        .settings-row__label-title {
            font-size: 14px;
            font-weight: 500;
            color: var(--db-text-main);
            display: block;
        }

        .settings-row__label-desc {
            font-size: 11px;
            color: var(--db-text-muted);
            margin-top: 2px;
        }

        .deployment-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
            margin-top: 12px;
        }

        .deployment-kv {
            display: flex;
            flex-direction: column;
            gap: 4px;
            padding: 14px 16px;
            border-radius: 14px;
            background: rgba(248, 250, 252, 0.72);
            border: 1px solid rgba(226, 232, 240, 0.9);
        }

        .settings-root.theme-dark .deployment-kv {
            background: rgba(15, 23, 42, 0.72);
            border-color: rgba(148, 163, 184, 0.18);
        }

        .deployment-kv__label {
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            color: var(--db-text-muted);
        }

        .deployment-kv__value {
            font-size: 15px;
            font-weight: 600;
            color: var(--db-text-main);
            word-break: break-word;
        }

        .deployment-inline-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 12px;
            border-radius: 999px;
            background: rgba(148, 163, 184, 0.12);
            border: 1px solid rgba(148, 163, 184, 0.24);
            font-size: 12px;
            font-weight: 600;
            color: #475569;
            margin-top: 4px;
        }

        .settings-root.theme-dark .deployment-inline-badge {
            color: #CBD5E1;
        }

        .deployment-log {
            max-height: 220px;
            overflow-y: auto;
            border-radius: 14px;
            background: rgba(15, 23, 42, 0.96);
            color: #E2E8F0;
            padding: 16px;
            margin-top: 16px;
            border: 1px solid rgba(148, 163, 184, 0.2);
        }

        .deployment-log pre {
            margin: 0;
            white-space: pre-wrap;
            word-break: break-word;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
            font-size: 12px;
            line-height: 1.6;
        }

        .deployment-empty-state {
            margin-top: 16px;
            padding: 20px;
            border-radius: 16px;
            border: 1px dashed rgba(148, 163, 184, 0.45);
            background: rgba(248, 250, 252, 0.75);
            display: flex;
            align-items: center;
            gap: 18px;
        }

        .settings-root.theme-dark .deployment-empty-state {
            background: rgba(15, 23, 42, 0.72);
            border-color: rgba(148, 163, 184, 0.3);
        }

        .deployment-empty-state__illustration {
            width: 92px;
            aspect-ratio: 1 / 1;
            border-radius: 18px;
            border: 1px dashed rgba(148, 163, 184, 0.55);
            background:
                radial-gradient(circle at top, rgba(254, 194, 136, 0.2), transparent 60%),
                linear-gradient(180deg, rgba(255, 255, 255, 0.7), rgba(248, 250, 252, 0.95));
            flex-shrink: 0;
        }

        .settings-root.theme-dark .deployment-empty-state__illustration {
            background:
                radial-gradient(circle at top, rgba(254, 194, 136, 0.12), transparent 60%),
                linear-gradient(180deg, rgba(15, 23, 42, 0.92), rgba(15, 23, 42, 0.78));
        }

        .deployment-empty-state__title {
            font-size: 15px;
            font-weight: 600;
            color: var(--db-text-main);
            margin: 0 0 4px 0;
        }

        .deployment-empty-state__text {
            font-size: 12px;
            color: var(--db-text-muted);
            margin: 0;
            line-height: 1.55;
        }

        .deployment-error-list {
            margin: 16px 0 0 0;
            padding: 0;
            list-style: none;
        }

        .deployment-error-item {
            border-radius: 12px;
            padding: 12px 14px;
            margin-bottom: 10px;
            background: rgba(250, 92, 92, 0.06);
            border: 1px solid rgba(250, 92, 92, 0.2);
            color: var(--db-text-main);
            font-size: 13px;
            line-height: 1.55;
        }

        .deployment-error-item:last-child {
            margin-bottom: 0;
        }

        .deployment-safe-mode {
            padding: 14px 16px;
            border-radius: 14px;
            background: rgba(251, 239, 118, 0.1);
            border: 1px solid rgba(251, 239, 118, 0.35);
            color: var(--db-text-main);
            font-size: 13px;
            line-height: 1.55;
            margin-top: 14px;
        }

        @media (max-width: 640px) {
            .deployment-empty-state {
                flex-direction: column;
                align-items: flex-start;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_section_header(title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="settings-section-card">
            <h2 class="settings-section-title">{escape(title)}</h2>
            <p class="settings-section-desc">{escape(description)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_key_value_items(items: list[tuple[str, str]]) -> str:
    return "".join(
        f"""
        <div class="deployment-kv">
            <span class="deployment-kv__label">{escape(label)}</span>
            <span class="deployment-kv__value">{escape(value)}</span>
        </div>
        """
        for label, value in items
    )


def _render_version_information_panel(context: dict[str, str]) -> None:
    items = [
        ("App Version", context["app_version"]),
        ("Build Number", context["build_number"]),
        ("Environment", context["deployment_environment"]),
        ("Last Updated", context["last_update_timestamp"]),
    ]
    st.markdown(
        f"""
        <div class="deployment-card" role="region" aria-label="Version information">
            <h3 class="deployment-card__title">Version Information</h3>
            <p class="deployment-card__desc">
                Build metadata stays visible here so local, cloud-connected, and teacher deployments
                can be verified without opening any infrastructure tools.
            </p>
            <div class="deployment-inline-badge" aria-live="polite">
                Environment State: {escape(context["environment_state"])}
            </div>
            <div class="deployment-grid">
                {_render_key_value_items(items)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_system_diagnostics_panel(context: dict[str, object]) -> None:
    summary_items = [
        ("Device RAM", str(context["detected_ram"])),
        ("Disk Space", str(context["detected_disk"])),
        ("Connectivity", str(context["connectivity"])),
        ("Last Sync", str(context["last_sync_timestamp"])),
    ]

    if context["diagnostics_output_available"]:
        diagnostics_markup = (
            '<div class="deployment-log" role="log" aria-label="System diagnostics output">'
            f"<pre>{escape(str(context['diagnostics_output']))}</pre>"
            "</div>"
        )
    else:
        diagnostics_markup = """
        <div class="deployment-empty-state" role="status" aria-live="polite">
            <div class="deployment-empty-state__illustration" aria-hidden="true"></div>
            <div>
                <p class="deployment-empty-state__title">No diagnostic data available.</p>
                <p class="deployment-empty-state__text">
                    Empty State Illustration Placeholder shown until runtime diagnostics are wired.
                </p>
            </div>
        </div>
        """

    st.markdown(
        f"""
        <div class="deployment-card" role="region" aria-label="System diagnostics">
            <h3 class="deployment-card__title">Diagnostics</h3>
            <p class="deployment-card__desc">
                Review device health, connectivity state, and diagnostic output before support or deployment checks.
            </p>
            <div class="deployment-grid">
                {_render_key_value_items(summary_items)}
            </div>
            {diagnostics_markup}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_sync_readiness_panel(context: dict[str, object]) -> None:
    sync_items = [
        ("Local Changes Pending", str(context["pending_changes_count"])),
        ("Last Sync Attempt", str(context["last_sync_timestamp"])),
        ("Sync State", str(context["sync_state"])),
    ]

    st.markdown(
        f"""
        <div class="deployment-card" role="region" aria-label="Sync readiness">
            <h3 class="deployment-card__title">Sync Readiness</h3>
            <p class="deployment-card__desc">
                This panel summarizes whether the device is ready to push local progress when connectivity is available.
            </p>
            <div class="deployment-grid">
                {_render_key_value_items(sync_items)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    is_offline = str(context["connectivity"]).lower() == "offline"
    if st.button(
        "Force Sync",
        key="deployment_force_sync",
        use_container_width=True,
        disabled=is_offline,
        help="Sync unavailable while offline." if is_offline else "Trigger a manual sync attempt.",
    ):
        st.info("Force Sync is a UI placeholder in this deployment-preparation layer.")


def _render_error_reporting_panel(context: dict[str, object]) -> None:
    recent_errors = context["recent_errors"]
    error_list_html = "".join(
        f'<li class="deployment-error-item">{escape(str(entry))}</li>'
        for entry in recent_errors[:5]
    )
    st.markdown(
        f"""
        <div class="deployment-card" role="region" aria-label="Error reporting">
            <h3 class="deployment-card__title">Error Reporting</h3>
            <p class="deployment-card__desc">
                Recent error context is collected here so support reports can include the app version,
                diagnostics, sync state, and the latest failures.
            </p>
            <ul class="deployment-error-list" aria-label="Recent errors">
                {error_list_html}
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_copy_to_clipboard_button(
        build_copy_diagnostics_payload(context),
        key="settings_copy_diagnostics",
    )


def _render_safe_mode_panel() -> None:
    st.markdown(
        """
        <div class="deployment-card" role="region" aria-label="Safe mode">
            <h3 class="deployment-card__title">Safe Mode</h3>
            <p class="deployment-card__desc">
                Use Safe Mode as a troubleshooting entry point when the app behaves unexpectedly.
            </p>
            <div class="deployment-safe-mode">
                Safe Mode disables AI modules and background sync for troubleshooting.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Restart in Safe Mode", key="restart_safe_mode", use_container_width=True):
        st.session_state.safe_mode_requested = True
        st.info("Safe Mode restart is a placeholder in this UI-only implementation.")


def show_settings_page() -> None:
    """Render Settings page."""
    _inject_settings_css()

    try:
        from profile_store import load_user_stats, save_user_stats

        user_stats = load_user_stats()
        preferences = user_stats.get("preferences", {})
    except ImportError:
        st.error("Profile store not available")
        return

    render_page_root_open("settings", st.session_state.get("theme", "light"))
    st.markdown('<h1 class="settings-page-title">Settings</h1>', unsafe_allow_html=True)
    st.markdown(
        """
        <p class="settings-page-subtitle">
            Deployment readiness, diagnostics, sync awareness, and personal preferences
            are collected here without introducing infrastructure-side logic.
        </p>
        """,
        unsafe_allow_html=True,
    )

    _render_section_header(
        "Cloud Sync",
        "Control how your progress syncs with the cloud. Disabling sync keeps all data local.",
    )

    sync_enabled = st.toggle(
        "Enable Cloud Sync",
        value=preferences.get("sync_enabled", True),
        key="sync_enabled_toggle",
        help="When enabled, progress syncs to cloud when connectivity is available.",
    )

    if sync_enabled != preferences.get("sync_enabled", True):
        preferences["sync_enabled"] = sync_enabled
        user_stats["preferences"] = preferences
        save_user_stats(user_stats)
        st.success(f"Cloud sync {'enabled' if sync_enabled else 'disabled'}")

    if sync_enabled:
        try:
            import sys

            parent_dir = Path(__file__).parent.parent
            if str(parent_dir) not in sys.path:
                sys.path.insert(0, str(parent_dir))

            from sync_manager import SyncManager
            from pages.sync_status import show_sync_status_panel

            sync_manager = SyncManager(
                appsync_endpoint=os.getenv("APPSYNC_ENDPOINT"),
                appsync_api_key=os.getenv("APPSYNC_API_KEY"),
                base_path=str(parent_dir),
            )
            show_sync_status_panel(sync_manager, preferences)
        except ImportError as exc:
            st.warning(f"⚠️ Sync manager not available: {exc}")
        except Exception as exc:
            st.error(f"❌ Error loading sync panel: {exc}")
    else:
        st.info("ℹ️ Cloud sync is disabled. All learning progress stays on this device.")

    deployment_context = get_deployment_context(user_stats=user_stats, preferences=preferences)

    _render_section_header(
        "Deployment Readiness",
        "UI-only deployment awareness for local student apps, cloud-connected sessions, and teacher dashboard previews.",
    )
    st.markdown(
        """
        <p class="settings-section-note">
            Placeholder fields remain visible until runtime deployment values are wired.
        </p>
        """,
        unsafe_allow_html=True,
    )
    _render_version_information_panel(deployment_context)
    _render_system_diagnostics_panel(deployment_context)
    _render_sync_readiness_panel(deployment_context)
    _render_error_reporting_panel(deployment_context)
    _render_safe_mode_panel()

    _render_section_header("Appearance", "Customize your visual experience.")

    theme = st.radio(
        "Theme",
        options=["light", "dark"],
        index=0 if preferences.get("theme", "light") == "light" else 1,
        key="theme_radio",
        horizontal=True,
        help="Switch between light and dark themes",
    )

    if theme != preferences.get("theme", "light"):
        preferences["theme"] = theme
        user_stats["preferences"] = preferences
        save_user_stats(user_stats)
        st.session_state.theme = theme
        st.rerun()

    _render_section_header(
        "Learning Preferences",
        "Adjust AI behavior and content difficulty.",
    )

    difficulty = st.select_slider(
        "Default Difficulty",
        options=["Beginner", "Intermediate", "Expert"],
        value=preferences.get("default_difficulty", "Intermediate"),
        key="difficulty_slider",
        help="AI will adjust explanation complexity",
    )

    if difficulty != preferences.get("default_difficulty", "Intermediate"):
        preferences["default_difficulty"] = difficulty
        user_stats["preferences"] = preferences
        save_user_stats(user_stats)

    _render_section_header(
        "Privacy & Data",
        "Control what data is stored and synced.",
    )
    st.info(
        "🔐 All learning data is stored locally. Cloud sync uploads only progress summaries "
        "(scores, streaks) — never chat transcripts or quiz answers."
    )

    _render_section_header(
        "Storage Manager",
        "File-heavy views stay lightweight on low-spec devices and load only when needed.",
    )

    if not st.session_state.get("storage_manager_visible", False):
        render_lazy_loading_card(
            title="Storage manager file list",
            description="Loading data...",
            illustration_ratio="4:3",
        )
        render_storage_list_skeleton()
        if st.button("Load storage manager", key="load_storage_manager", use_container_width=True):
            st.session_state.storage_manager_visible = True
            st.rerun()
    else:
        st.info(
            "Storage manager preview loaded. In the full implementation this area will "
            "list local textbooks, embeddings, and removable study assets."
        )

    render_performance_thresholds_caption()

    col_export, col_clear = st.columns(2)
    with col_export:
        if st.button("📥 Export Data", use_container_width=True, help="Download your data"):
            st.info("Feature coming soon — exports user_stats.json")

    with col_clear:
        if st.button(
            "🗑️ Clear Local Data",
            use_container_width=True,
            help="Reset all local data",
            type="secondary",
        ):
            st.warning("⚠️ This will delete all local progress. Use with caution.")

    _render_section_header(
        "Account",
        "Profile and authentication settings.",
    )

    profile = user_stats.get("profile", {})
    # Do not auto-populate when profile is empty — use None to avoid fake session
    profile_name = profile.get("name") if profile else None
    profile_mode = profile.get("mode") if profile else None

    st.markdown(
        f"""
        <div class="settings-row">
            <div class="settings-row__label">
                <span class="settings-row__label-title">Name</span>
                <span class="settings-row__label-desc">{escape(profile_name or "Not set")}</span>
            </div>
        </div>
        <div class="settings-row">
            <div class="settings-row__label">
                <span class="settings-row__label-title">Mode</span>
                <span class="settings-row__label-desc">{escape((profile_mode or "Not set").capitalize())}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🚪 Sign Out", use_container_width=True):
        st.session_state.clear()
        st.session_state.page = "landing"
        st.rerun()

    render_page_root_close()


if __name__ == "__main__":
    show_settings_page()


def show_settings() -> None:
    """Routing alias used by the main Streamlit app."""
    show_settings_page()
