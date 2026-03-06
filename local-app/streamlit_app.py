"""
Studaxis - Main Streamlit Application
Offline-First AI Tutor for Low-Connectivity Learning

This module wires the initial hardware validation into the UI boot flow
and shows a blocking hardware warning modal on first launch or major update
when the device is at minimum specs.
"""

from pathlib import Path
import os

import streamlit as st

from deployment_ui import initialize_deployment_ui_state
from pages.auth import show_auth
from pages.chat import show_chat
from pages.dashboard import show_dashboard
from pages.error_demo import show_error_demo
from pages.flashcards import show_flashcards
from pages.panic_mode import show_panic_mode
from pages.quiz import show_quiz
from pages.settings import show_settings
from pages.teacher_insights_dashboard import show_teacher_insights_dashboard
from pages.hardware_modal import render_hardware_warning_modal
from pages.hardware_validator import HardwareValidator
from pages.landing import show_landing
from performance_ui import (
    apply_performance_mode_from_hardware,
    init_performance_ui_state,
    inject_performance_ui_css,
    render_model_initialization_screen,
)
from preferences import load_user_stats
from profile_store import UserProfile, load_profile, save_profile
from sync_manager import SyncManager


APP_VERSION = "0.1.0"


def _hydrate_profile_from_disk() -> None:
    """
    Load a previously saved local profile (if any) into session_state.

    This runs once on app start and keeps session_state in sync with
    any profile that was persisted to disk on a prior run.
    """
    if st.session_state.get("profile_loaded"):
        return

    profile = load_profile()
    if profile is None:
        st.session_state.profile_loaded = True
        return

    if profile.user_role in ("student", "teacher"):
        st.session_state.user_role = profile.user_role

    if profile.profile_name:
        st.session_state.profile_name = profile.profile_name
    if profile.profile_mode in ("solo", "teacher_linked", "teacher_linked_provisional"):
        st.session_state.profile_mode = profile.profile_mode
    if profile.class_code:
        st.session_state.class_code = profile.class_code

    st.session_state.profile_loaded = True


def _inject_global_css() -> None:
    """Inject global theme and component CSS once."""
    css_path = Path(__file__).parent / "styles" / "theme.css"
    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def _init_session_state() -> None:
    if "page" not in st.session_state:
        st.session_state.page = "landing"
    if "user_logged_in" not in st.session_state:
        st.session_state.user_logged_in = False

    # Theme + version flags (simplified for MVP)
    if "theme" not in st.session_state:
        st.session_state.theme = "light"
    if "theme_preference_hydrated" not in st.session_state:
        st.session_state.theme_preference_hydrated = False
    if "app_version" not in st.session_state:
        st.session_state.app_version = APP_VERSION
    if "last_seen_version" not in st.session_state:
        # Treat first run as first launch or major update
        st.session_state.last_seen_version = None

    # Hardware-related flags and cached values
    st.session_state.setdefault("hardware_status", None)  # "ok" | "warn" | "block"
    st.session_state.setdefault("hardware_block", False)
    st.session_state.setdefault("hardware_warning_required", False)
    st.session_state.setdefault("hardware_specs", None)
    st.session_state.setdefault("hardware_tips", [])
    st.session_state.setdefault("hardware_boot_checked", False)
    st.session_state.setdefault("hardware_warning_dismissed_version", None)

    # Boot flow state (UI-driven boot sequence before dashboard)
    st.session_state.setdefault("boot_phase", "splash")
    st.session_state.setdefault("boot_complete", False)
    st.session_state.setdefault("connectivity_status", "unknown")  # "unknown" | "online" | "offline"
    st.session_state.setdefault(
        "storage_state", "unknown"
    )  # "unknown" | "ready" | "degraded" | "critical_missing"
    st.session_state.setdefault(
        "profile_mode", None
    )  # None | "solo" | "teacher_linked" | "teacher_linked_provisional"
    st.session_state.setdefault("profile_name", None)
    st.session_state.setdefault("class_code", None)
    st.session_state.setdefault("boot_errors", [])
    st.session_state.setdefault("hardware_message", "")
    st.session_state.setdefault("hardware_quantization", None)

    # Role + profile persistence flags
    st.session_state.setdefault("user_role", None)  # None | "student" | "teacher"
    st.session_state.setdefault("profile_loaded", False)

    # Sync monitoring placeholders (UI-only; no backend logic)
    st.session_state.setdefault("sync_status", "[SYNC_STATUS]")
    st.session_state.setdefault("last_sync_time", "[LAST_SYNC_TIME]")
    st.session_state.setdefault("sync_retry_count", "[SYNC_RETRY_COUNT]")
    st.session_state.setdefault("partial_sync_status", None)

    # Deployment-readiness placeholders and diagnostics state
    initialize_deployment_ui_state()

    init_performance_ui_state()

    if not st.session_state.theme_preference_hydrated:
        try:
            theme_pref = load_user_stats().get("preferences", {}).get("theme", "light")
            if theme_pref in ("light", "dark"):
                st.session_state.theme = theme_pref
        except Exception:
            pass
        st.session_state.theme_preference_hydrated = True

    # Hydrate any existing profile from disk once at startup
    _hydrate_profile_from_disk()


def _run_hardware_check_if_needed() -> None:
    """Run hardware check only on first launch or major update."""
    if st.session_state.hardware_boot_checked:
        return

    first_launch_or_major = (
        st.session_state.last_seen_version is None
        or st.session_state.last_seen_version != st.session_state.app_version
    )

    if not first_launch_or_major:
        st.session_state.hardware_boot_checked = True
        return

    validator = HardwareValidator()
    is_valid, message, specs = validator.validate()
    tips = validator.get_optimization_tips()
    quantization = validator.get_quantization_recommendation()

    st.session_state.hardware_specs = specs
    st.session_state.hardware_tips = tips
    st.session_state.hardware_message = message
    st.session_state.hardware_quantization = quantization

    if not is_valid:
        # Below minimum thresholds → treated as BLOCK
        st.session_state.hardware_status = "block"
        st.session_state.hardware_block = True
        st.session_state.hardware_warning_required = False
    else:
        # Meets minimum; if we have any recommendations, surface a WARN modal once
        if "Recommendations" in message or tips:
            st.session_state.hardware_status = "warn"
            st.session_state.hardware_warning_required = True
        else:
            st.session_state.hardware_status = "ok"
            st.session_state.hardware_warning_required = False
        st.session_state.hardware_block = False

    apply_performance_mode_from_hardware()
    st.session_state.hardware_boot_checked = True


def _maybe_render_hardware_block_screen() -> None:
    if not st.session_state.hardware_block:
        return

    specs = st.session_state.hardware_specs or {}
    st.title("Studaxis cannot run reliably on this device")
    st.error(
        "Your laptop is below the minimum hardware requirements for Studaxis.\n\n"
        "Please try on a device with at least 4 GB RAM and 2 GB free disk space."
    )

    ram_gb = specs.get("ram_gb")
    disk_free_gb = specs.get("disk_free_gb")

    if ram_gb is not None or disk_free_gb is not None:
        with st.expander("View detected specs"):
            if ram_gb is not None:
                st.write(f"RAM: {ram_gb} GB (minimum {HardwareValidator.MIN_RAM_GB} GB)")
            if disk_free_gb is not None:
                st.write(
                    f"Disk free: {disk_free_gb} GB (minimum {HardwareValidator.MIN_DISK_GB} GB)"
                )

    st.stop()


def _maybe_render_hardware_warning_modal() -> None:
    """Show blocking hardware warning modal when hardware_status == 'warn'."""
    if st.session_state.hardware_status != "warn":
        return
    if not st.session_state.hardware_warning_required:
        return

    dismissed_version = st.session_state.hardware_warning_dismissed_version
    if dismissed_version == st.session_state.app_version:
        return

    specs = st.session_state.hardware_specs or {}
    tips = st.session_state.hardware_tips or []

    visible, action = render_hardware_warning_modal(
        specs=specs,
        tips=tips,
        theme=st.session_state.get("theme", "light"),
    )

    if not visible:
        return

    # When an action is taken, remember dismissal for this version and move on
    if action in ("continue", "optimize"):
        st.session_state.hardware_warning_required = False
        st.session_state.hardware_warning_dismissed_version = st.session_state.app_version
        st.session_state.last_seen_version = st.session_state.app_version

        if action == "optimize":
            # Route to settings when that screen exists; for now, keep current flow.
            st.session_state.page = "dashboard"

        st.rerun()

    # Block underlying UI while modal is visible
    st.stop()


def _run_connectivity_check() -> None:
    """Populate connectivity_status once using SyncManager."""
    if st.session_state.get("connectivity_status") != "unknown":
        return

    manager = SyncManager(base_path=str(Path(__file__).parent.parent))
    is_online = manager.check_connectivity()
    st.session_state.connectivity_status = "online" if is_online else "offline"


def _run_storage_validation() -> None:
    """
    Lightweight placeholder storage validation.

    For now, treat presence of the local data directory as READY and
    fall back to DEGRADED when it is missing. This can be expanded to
    inspect textbooks, embeddings, and backups.
    """
    if st.session_state.get("storage_state") != "unknown":
        return

    data_dir = Path(__file__).parent / "data"
    if data_dir.exists():
        st.session_state.storage_state = "ready"
    else:
        st.session_state.storage_state = "degraded"


def _render_boot_splash_shell(title: str, subtitle: str) -> None:
    """Shared splash shell with glass card layout."""
    with st.container():
        st.markdown(
            """
            <div class="boot-root">
              <div class="boot-main">
                <div class="boot-glass-card" role="status" aria-busy="true">
                  <div class="boot-card-header">
                    <h1 class="boot-title">{title}</h1>
                    <p class="boot-subtitle">{subtitle}</p>
                  </div>
                </div>
              </div>
            </div>
            """.format(
                title=title,
                subtitle=subtitle,
            ),
            unsafe_allow_html=True,
        )


def render_splash_screen() -> None:
    """Phase 1: Splash Screen."""
    _render_boot_splash_shell(
        title="Studaxis is getting ready",
        subtitle="We are checking your laptop, connectivity, and storage so your tutor feels smooth even offline.",
    )

    # Immediately move into hardware checks while keeping the same visual shell.
    st.session_state.boot_phase = "hardware_checks"
    st.rerun()


def render_hardware_check_screen() -> None:
    """Phase 2: Hardware Check Screen."""
    _render_boot_splash_shell(
        title="Checking your laptop hardware",
        subtitle="Making sure your RAM and disk space meet the minimum requirements.",
    )

    _run_hardware_check_if_needed()

    specs = st.session_state.get("hardware_specs") or {}
    message = st.session_state.get("hardware_message", "")
    quantization = st.session_state.get("hardware_quantization")

    # Show detected specs and quantization in a Streamlit card
    with st.container():
        st.markdown(
            '<div class="glass-card storage-card" role="status" aria-busy="false">',
            unsafe_allow_html=True,
        )
        if message:
            st.markdown(message.replace("\n", "  \n"))

        ram_gb = specs.get("ram_gb")
        disk_free_gb = specs.get("disk_free_gb")
        cpu_model = specs.get("cpu_model")
        cpu_count = specs.get("cpu_count")

        col1, col2 = st.columns(2)
        with col1:
            if ram_gb is not None:
                st.markdown(f"**RAM**: {ram_gb} GB (minimum {HardwareValidator.MIN_RAM_GB} GB)")
            if disk_free_gb is not None:
                st.markdown(
                    f"**Disk free**: {disk_free_gb} GB (minimum {HardwareValidator.MIN_DISK_GB} GB)"
                )
        with col2:
            if cpu_model:
                st.markdown(f"**CPU**: {cpu_model}")
            if cpu_count is not None:
                st.markdown(f"**CPU cores**: {cpu_count}")

        if quantization:
            st.markdown(f"**Recommended AI quantization**: `{quantization}`")

        st.markdown("</div>", unsafe_allow_html=True)

    # Handle hard block before any other UI
    if st.session_state.hardware_block:
        _maybe_render_hardware_block_screen()

    # Show hardware warning modal (first launch / major update)
    if (
        st.session_state.hardware_status == "warn"
        and st.session_state.hardware_warning_required
    ):
        _maybe_render_hardware_warning_modal()
        return

    # No blockers → advance to connectivity checks
    st.session_state.boot_phase = "connectivity"
    st.rerun()


def render_connectivity_check_screen() -> None:
    """Phase 3: Connectivity Check Indicator."""
    _render_boot_splash_shell(
        title="Checking connectivity to cloud",
        subtitle="Studaxis works fully offline, but we will sync with your teacher when a connection is available.",
    )

    _run_connectivity_check()

    status = st.session_state.get("connectivity_status", "unknown")
    with st.container():
        col_label, col_status = st.columns([2, 1])
        with col_label:
            st.markdown("**Connectivity to teacher dashboard**")
        with col_status:
            if status == "online":
                st.markdown(
                    '<div class="status-pill status-pill--online" role="status">Online</div>',
                    unsafe_allow_html=True,
                )
            elif status == "offline":
                st.markdown(
                    '<div class="status-pill status-pill--offline" role="status">Offline &mdash; Studaxis still works fully offline.</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="status-pill" role="status">Detecting...</div>',
                    unsafe_allow_html=True,
                )

    st.session_state.boot_phase = "storage_validation"
    st.rerun()


def render_storage_validation_screen() -> None:
    """Phase 4: Storage Validation Loading Screen."""
    _render_boot_splash_shell(
        title="Scanning local study data",
        subtitle="We are validating your local textbooks, notes, and quiz history so everything feels ready.",
    )

    _run_storage_validation()

    state = st.session_state.get("storage_state", "unknown")
    with st.container():
        st.markdown(
            '<div class="glass-card storage-card" role="status" aria-busy="false">',
            unsafe_allow_html=True,
        )
        if state == "ready":
            st.markdown(
                "✅ Local storage looks good. Your study data is ready.",
            )
        elif state == "degraded":
            st.markdown(
                "⚠️ Some storage information may be missing. We will show more details inside the dashboard.",
            )
        elif state == "critical_missing":
            st.markdown(
                "⚠️ Important resources are missing. A recovery helper will appear on the dashboard.",
            )
        else:
            st.markdown("Checking local storage...")
        st.markdown("</div>", unsafe_allow_html=True)

    # Decide next phase based on role and whether a profile already exists
    user_role = st.session_state.get("user_role")
    profile_mode = st.session_state.get("profile_mode")

    if user_role is None:
        st.session_state.boot_phase = "role_selection"
    elif user_role == "teacher":
        st.session_state.boot_phase = "teacher_redirect"
    else:
        # student role
        if profile_mode is None:
            st.session_state.boot_phase = "profile_selection"
        else:
            st.session_state.boot_phase = "model_initialization"
    st.rerun()


def render_profile_mode_selection_screen() -> None:
    """Phase 5: Profile Mode Selection Screen."""
    with st.container():
        st.markdown(
            """
            <div class="boot-root">
              <div class="boot-main">
                <div class="boot-glass-card boot-onboarding-card">
                  <div class="boot-onboarding-grid">
                    <div class="boot-onboarding-copy">
                      <h1 class="boot-title">Welcome to Studaxis</h1>
                      <p class="boot-subtitle">
                        Tell us how you are using Studaxis so we can tune your dashboard and streaks.
                      </p>
                    </div>
                    <div class="boot-onboarding-form">
                      <p class="sr-only" id="profile-onboarding-label">
                        Profile setup for Studaxis.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    name = st.text_input("What should we call you?", key="profile_name_input")
    mode_choice = st.radio(
        "How are you using Studaxis today?",
        ["Learn on my own", "Join a class"],
        key="profile_mode_choice",
    )

    if st.button("Continue", use_container_width=True):
        if not name.strip():
            st.error("Please enter a name so we know how to address you.")
            return

        st.session_state.profile_name = name.strip()

        if mode_choice == "Learn on my own":
            st.session_state.profile_mode = "solo"
            # Persist solo student profile locally
            profile = UserProfile(
                profile_name=st.session_state.profile_name,
                profile_mode=st.session_state.profile_mode,
                class_code=None,
                user_role=st.session_state.get("user_role") or "student",
            )
            save_profile(profile)
            st.session_state.boot_phase = "model_initialization"
        else:
            # Joining a class – persist partial profile (without class_code yet)
            profile = UserProfile(
                profile_name=st.session_state.profile_name,
                profile_mode=None,
                class_code=None,
                user_role=st.session_state.get("user_role") or "student",
            )
            save_profile(profile)
            st.session_state.boot_phase = "class_code"

        st.rerun()


def render_class_code_entry_screen() -> None:
    """Phase 6: Class Code Entry Screen."""
    with st.container():
        st.markdown(
            """
            <div class="boot-root">
              <div class="boot-main">
                <div class="boot-glass-card boot-class-card">
                  <h1 class="boot-title">Join your class</h1>
                  <p class="boot-subtitle">
                    Enter the class code shared by your teacher. If you are offline, we will link it as soon as we can verify.
                  </p>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    class_code = st.text_input("Enter your class code", key="class_code_input")
    col_primary, col_secondary = st.columns([2, 1])
    error_message = None

    with col_primary:
        if st.button("Link class", use_container_width=True):
            if not class_code.strip():
                error_message = "Please enter a class code or continue in Solo mode."
            else:
                # Placeholder: treat any non-empty code as provisionally accepted.
                st.session_state.class_code = class_code.strip()
                st.session_state.profile_mode = "teacher_linked_provisional"

                profile = UserProfile(
                    profile_name=st.session_state.get("profile_name"),
                    profile_mode=st.session_state.profile_mode,
                    class_code=st.session_state.class_code,
                    user_role=st.session_state.get("user_role") or "student",
                )
                save_profile(profile)

                st.session_state.boot_phase = "model_initialization"
                st.rerun()

    with col_secondary:
        if st.button("Skip for now (Solo mode)", use_container_width=True):
            st.session_state.profile_mode = "solo"
            st.session_state.class_code = None

            profile = UserProfile(
                profile_name=st.session_state.get("profile_name"),
                profile_mode=st.session_state.profile_mode,
                class_code=None,
                user_role=st.session_state.get("user_role") or "student",
            )
            save_profile(profile)

            st.session_state.boot_phase = "model_initialization"
            st.rerun()

    if error_message:
        st.error(error_message)

    status = st.session_state.get("connectivity_status", "unknown")
    if status == "online":
        st.markdown(
            "When you are online, we will confirm this code with your teacher's dashboard.",
        )
    elif status == "offline":
        st.markdown(
            "You appear to be offline. We will remember this code and attempt to verify it later.",
        )


def render_dashboard_reveal_transition() -> None:
    """Phase 7: Dashboard Reveal Transition."""
    with st.container():
        st.markdown(
            """
            <div class="boot-root">
              <div class="boot-main">
                <div class="boot-glass-card boot-reveal-card">
                  <h1 class="boot-title">You are all set</h1>
                  <p class="boot-subtitle">
                    Your profile, hardware, and local storage are ready. Loading your dashboard now.
                  </p>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Mark boot as complete so subsequent runs skip boot screens.
    st.session_state.boot_complete = True
    # Default starting page after boot
    st.session_state.page = "dashboard"
    st.rerun()


def render_model_initialization_phase() -> None:
    """Phase: model initialization screen for student AI features."""
    render_model_initialization_screen()

    if st.session_state.get("low_power_mode_active", False):
        st.caption(
            "Low Power Mode Active — Reduced animations and background tasks "
            f"below {st.session_state.get('low_power_mode_reason')}."
        )

    if st.button("Continue to dashboard", type="primary", use_container_width=True):
        st.session_state.model_init_complete = True
        st.session_state.boot_phase = "dashboard_reveal"
        st.rerun()


def render_role_selection_screen() -> None:
    """Phase 5: Role Selection (Student vs Teacher)."""
    with st.container():
        st.markdown(
            """
            <div class="boot-root">
              <div class="boot-main">
                <div class="boot-glass-card boot-onboarding-card">
                  <div class="boot-onboarding-grid">
                    <div class="boot-onboarding-copy">
                      <h1 class="boot-title">Who is using Studaxis on this laptop?</h1>
                      <p class="boot-subtitle">
                        Choose your role so we can route you to the right experience.
                      </p>
                    </div>
                    <div class="boot-onboarding-form">
                      <p class="sr-only" id="role-onboarding-label">
                        Role selection for Studaxis.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    choice = st.radio(
        "Select your role",
        ["I am a student using Studaxis on this device", "I am a teacher checking progress"],
        key="role_selection_choice",
    )

    if st.button("Continue", use_container_width=True):
        if not choice:
            st.error("Please select a role to continue.")
            return

        if choice.startswith("I am a student"):
            st.session_state.user_role = "student"
            # If a student profile already exists, skip straight to dashboard reveal
            if st.session_state.get("profile_mode") is None:
                st.session_state.boot_phase = "profile_selection"
            else:
                st.session_state.boot_phase = "model_initialization"
        else:
            st.session_state.user_role = "teacher"
            st.session_state.boot_phase = "teacher_redirect"

        st.rerun()


def render_teacher_redirect_screen() -> None:
    """Phase: Teacher redirect – no teacher UI in local app."""
    with st.container():
        st.markdown(
            """
            <div class="boot-root">
              <div class="boot-main">
                <div class="boot-glass-card boot-onboarding-card">
                  <div class="boot-onboarding-copy">
                    <h1 class="boot-title">Teacher dashboard is available via web portal</h1>
                    <p class="boot-subtitle">
                      This local Studaxis app is designed for student laptops. As a teacher,
                      you can access the full dashboard from your browser.
                    </p>
                  </div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    teacher_dashboard_url = os.getenv("TEACHER_DASHBOARD_URL", "").strip()

    if not teacher_dashboard_url:
        st.error(
            "The Teacher Dashboard URL is not configured on this device. "
            "Please contact your administrator to set TEACHER_DASHBOARD_URL."
        )
    else:
        # Prefer Streamlit's native link button when available.
        try:
            st.link_button("Open Teacher Dashboard", teacher_dashboard_url, use_container_width=True)
        except AttributeError:
            st.markdown(
                f"[Open Teacher Dashboard]({teacher_dashboard_url})",
                unsafe_allow_html=False,
            )

    if st.button("Open Local Teacher Insights Preview", use_container_width=True):
        st.session_state.page = "teacher_insights"
        st.session_state.boot_complete = True
        st.rerun()

    st.info(
        "You can close this window after opening the Teacher Dashboard in your browser. "
        "Student features are not rendered for teacher accounts in this app."
    )

    # Mark boot as complete so this screen does not block normal routing logic.
    st.session_state.boot_complete = True


def render_boot_flow() -> None:
    """Entry point for the visual boot sequence."""
    phase = st.session_state.get("boot_phase", "splash")

    if phase == "splash":
        render_splash_screen()
    elif phase == "hardware_checks":
        render_hardware_check_screen()
    elif phase == "connectivity":
        render_connectivity_check_screen()
    elif phase == "storage_validation":
        render_storage_validation_screen()
    elif phase == "role_selection":
        render_role_selection_screen()
    elif phase == "teacher_redirect":
        render_teacher_redirect_screen()
    elif phase == "profile_selection":
        render_profile_mode_selection_screen()
    elif phase == "class_code":
        render_class_code_entry_screen()
    elif phase == "model_initialization":
        render_model_initialization_phase()
    elif phase == "dashboard_reveal":
        render_dashboard_reveal_transition()
    else:
        # Fallback to splash if phase is unknown
        st.session_state.boot_phase = "splash"
        render_splash_screen()


def _show_feature_placeholder(title: str, icon: str, description: str) -> None:
    """
    Thin coming-soon stub for feature sub-pages (chat, quiz, flashcards, panic_mode).
    Renders a centred glass card with a Back button returning to the dashboard.
    """
    st.markdown(
        f"""
        <div class="boot-root">
          <div class="boot-main">
            <div class="boot-glass-card boot-reveal-card" role="main">
              <div style="font-size:40px;margin-bottom:12px;text-align:center">{icon}</div>
              <h1 class="boot-title" style="text-align:center">{title}</h1>
              <p class="boot-subtitle" style="text-align:center">{description}</p>
              <p class="boot-subtitle" style="text-align:center;margin-top:8px;font-style:italic">
                This feature is coming soon — it will be fully implemented in the next sprint.
              </p>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_back, _ = st.columns([1, 3])
    with col_back:
        if st.button("← Back to Dashboard", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()


def main() -> None:
    _inject_global_css()
    _init_session_state()
    inject_performance_ui_css()
    # Visual boot flow runs before any dashboard or landing content.
    if not st.session_state.get("boot_complete", False):
        render_boot_flow()
        return

    # Normal page routing after boot is complete
    page = st.session_state.page

    if page == "landing":
        show_landing()
    elif page == "auth":
        show_auth()
    elif page == "dashboard":
        show_dashboard()
    elif page == "chat":
        show_chat()
    elif page == "quiz":
        show_quiz()
    elif page == "flashcards":
        show_flashcards()
    elif page == "settings":
        show_settings()
    elif page == "panic_mode":
        show_panic_mode()
    elif page == "teacher_insights":
        show_teacher_insights_dashboard()
    elif page == "error_demo":
        show_error_demo()


if __name__ == "__main__":
    main()

