"""
Deployment preparation UI helpers for Studaxis.

This module is intentionally UI-focused. It prepares placeholder-safe
deployment metadata, lightweight system diagnostics, and environment-aware
labels without introducing infrastructure, CI/CD, or AWS runtime logic.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st
import streamlit.components.v1 as components

try:
    import psutil
except ImportError:  # pragma: no cover - optional dependency fallback
    psutil = None


APP_VERSION_PLACEHOLDER = "[APP_VERSION]"
BUILD_NUMBER_PLACEHOLDER = "[BUILD_NUMBER]"
DEPLOYMENT_ENVIRONMENT_PLACEHOLDER = "[DEPLOYMENT_ENVIRONMENT]"
LAST_UPDATE_TIMESTAMP_PLACEHOLDER = "[LAST_UPDATE_TIMESTAMP]"
LAST_SYNC_TIMESTAMP_PLACEHOLDER = "[LAST_SYNC_TIMESTAMP]"
BACKEND_ENDPOINT_PLACEHOLDER = "[BACKEND_ENDPOINT]"
SYSTEM_DIAGNOSTICS_PLACEHOLDER = "[SYSTEM_DIAGNOSTICS_PLACEHOLDER]"
PENDING_CHANGES_COUNT_PLACEHOLDER = "[PENDING_CHANGES_COUNT]"
ERROR_LOG_PLACEHOLDER = "[ERROR_LOG_PLACEHOLDER]"
SYNC_STATE_PLACEHOLDER = "[SYNC_STATE]"


def _env_or_placeholder(name: str, placeholder: str) -> str:
    value = os.getenv(name, "").strip()
    return value or placeholder


def _display_or_placeholder(value: Any, placeholder: str) -> str:
    if value is None:
        return placeholder
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or placeholder
    return str(value)


def _format_bytes(num_bytes: float) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit in {"GB", "TB"}:
                return f"{size:.1f} {unit}"
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _detect_ram() -> str:
    if psutil is None:
        return "[DETECTED_RAM]"
    try:
        return _format_bytes(psutil.virtual_memory().total)
    except Exception:
        return "[DETECTED_RAM]"


def _detect_disk() -> str:
    try:
        anchor = Path(__file__).resolve().anchor or str(Path.cwd())
        return _format_bytes(shutil.disk_usage(anchor).free)
    except Exception:
        return "[DETECTED_DISK]"


def initialize_deployment_ui_state() -> None:
    """Seed placeholder-safe deployment/session values."""
    st.session_state.setdefault("app_version", APP_VERSION_PLACEHOLDER)
    st.session_state.setdefault("build_number", _env_or_placeholder("BUILD_NUMBER", BUILD_NUMBER_PLACEHOLDER))
    st.session_state.setdefault(
        "deployment_environment",
        _env_or_placeholder("DEPLOYMENT_ENVIRONMENT", DEPLOYMENT_ENVIRONMENT_PLACEHOLDER),
    )
    st.session_state.setdefault(
        "last_update_timestamp",
        _env_or_placeholder("LAST_UPDATE_TIMESTAMP", LAST_UPDATE_TIMESTAMP_PLACEHOLDER),
    )
    st.session_state.setdefault(
        "backend_endpoint",
        _env_or_placeholder("BACKEND_ENDPOINT", BACKEND_ENDPOINT_PLACEHOLDER),
    )
    st.session_state.setdefault(
        "system_diagnostics_output",
        _env_or_placeholder("SYSTEM_DIAGNOSTICS_OUTPUT", SYSTEM_DIAGNOSTICS_PLACEHOLDER),
    )
    st.session_state.setdefault(
        "pending_changes_count",
        _env_or_placeholder("PENDING_CHANGES_COUNT", PENDING_CHANGES_COUNT_PLACEHOLDER),
    )
    st.session_state.setdefault("last_sync_timestamp", LAST_SYNC_TIMESTAMP_PLACEHOLDER)
    st.session_state.setdefault("deployment_sync_state", SYNC_STATE_PLACEHOLDER)
    st.session_state.setdefault("recent_errors", [ERROR_LOG_PLACEHOLDER])
    st.session_state.setdefault("safe_mode_requested", False)


def get_environment_state(sync_enabled: Optional[bool] = None) -> str:
    """Derive the current environment label for header badges."""
    deployment_environment = str(st.session_state.get("deployment_environment", "")).strip().lower()
    connectivity_status = str(st.session_state.get("connectivity_status", "unknown")).strip().lower()

    if deployment_environment in {"development", "dev", "development mode"}:
        return "Development Mode"
    if connectivity_status == "offline":
        return "Offline Mode"
    if connectivity_status == "online" and (sync_enabled is None or sync_enabled):
        return "Cloud Connected"
    return "Local Mode"


def build_environment_badge_html(sync_enabled: Optional[bool] = None) -> str:
    label = get_environment_state(sync_enabled=sync_enabled)
    return (
        '<span class="environment-pill" role="status" '
        f'aria-label="Environment: {label}">Environment: {label}</span>'
    )


def _connectivity_label() -> str:
    status = str(st.session_state.get("connectivity_status", "unknown")).strip().lower()
    if status == "online":
        return "Online"
    if status == "offline":
        return "Offline"
    return "Unknown"


def _map_sync_state() -> str:
    raw_state = str(st.session_state.get("deployment_sync_state", "")).strip()
    if raw_state and raw_state != SYNC_STATE_PLACEHOLDER:
        return raw_state

    sync_status = str(st.session_state.get("sync_status", "")).strip().lower()
    connectivity = str(st.session_state.get("connectivity_status", "unknown")).strip().lower()
    mapping = {
        "synced": "Idle",
        "connected": "Idle",
        "idle": "Idle",
        "syncing": "Syncing",
        "pending": "Pending",
        "error": "Failed",
        "failed": "Failed",
    }

    if sync_status in mapping:
        return mapping[sync_status]
    if connectivity == "offline" and sync_status == "offline":
        return "Pending"
    return SYNC_STATE_PLACEHOLDER


def _latest_recent_errors() -> List[str]:
    candidates: List[str] = []

    boot_errors = st.session_state.get("boot_errors", [])
    if isinstance(boot_errors, list):
        candidates.extend([str(item) for item in boot_errors if str(item).strip()])

    recent_errors = st.session_state.get("recent_errors", [])
    if isinstance(recent_errors, list):
        candidates.extend([str(item) for item in recent_errors if str(item).strip()])

    if not candidates:
        return [ERROR_LOG_PLACEHOLDER]

    return candidates[-5:]


def get_deployment_context(
    user_stats: Optional[Dict[str, Any]] = None,
    preferences: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Gather placeholder-safe deployment metadata for settings panels."""
    sync_enabled = True
    if isinstance(preferences, dict):
        sync_enabled = preferences.get("sync_enabled", True)

    user_stats = user_stats or {}
    last_sync = (
        st.session_state.get("last_sync_time")
        or st.session_state.get("last_sync_timestamp")
        or user_stats.get("last_sync_timestamp")
    )
    last_sync_value = _display_or_placeholder(last_sync, LAST_SYNC_TIMESTAMP_PLACEHOLDER)

    diagnostics_output = _display_or_placeholder(
        st.session_state.get("system_diagnostics_output"),
        SYSTEM_DIAGNOSTICS_PLACEHOLDER,
    )

    context = {
        "app_version": _display_or_placeholder(st.session_state.get("app_version"), APP_VERSION_PLACEHOLDER),
        "build_number": _display_or_placeholder(st.session_state.get("build_number"), BUILD_NUMBER_PLACEHOLDER),
        "deployment_environment": _display_or_placeholder(
            st.session_state.get("deployment_environment"),
            DEPLOYMENT_ENVIRONMENT_PLACEHOLDER,
        ),
        "environment_state": get_environment_state(sync_enabled=sync_enabled),
        "last_update_timestamp": _display_or_placeholder(
            st.session_state.get("last_update_timestamp"),
            LAST_UPDATE_TIMESTAMP_PLACEHOLDER,
        ),
        "backend_endpoint": _display_or_placeholder(
            st.session_state.get("backend_endpoint"),
            BACKEND_ENDPOINT_PLACEHOLDER,
        ),
        "detected_ram": _detect_ram(),
        "detected_disk": _detect_disk(),
        "connectivity": _connectivity_label(),
        "last_sync_timestamp": last_sync_value,
        "pending_changes_count": _display_or_placeholder(
            st.session_state.get("pending_changes_count"),
            PENDING_CHANGES_COUNT_PLACEHOLDER,
        ),
        "sync_state": _map_sync_state(),
        "diagnostics_output": diagnostics_output,
        "diagnostics_output_available": diagnostics_output != SYSTEM_DIAGNOSTICS_PLACEHOLDER,
        "recent_errors": _latest_recent_errors(),
        "sync_enabled": sync_enabled,
    }
    return context


def build_copy_diagnostics_payload(context: Dict[str, Any]) -> str:
    """Return a support-friendly diagnostics payload."""
    recent_errors = context.get("recent_errors") or [ERROR_LOG_PLACEHOLDER]
    if isinstance(recent_errors, list):
        recent_errors_block = "\n".join(f"- {item}" for item in recent_errors)
    else:
        recent_errors_block = f"- {recent_errors}"

    diagnostics_output = context.get("diagnostics_output", SYSTEM_DIAGNOSTICS_PLACEHOLDER)

    return "\n".join(
        [
            "Studaxis Support Diagnostics",
            "===========================",
            f"Environment State: {context.get('environment_state', 'Local Mode')}",
            f"App Version: {context.get('app_version', APP_VERSION_PLACEHOLDER)}",
            f"Build Number: {context.get('build_number', BUILD_NUMBER_PLACEHOLDER)}",
            f"Environment: {context.get('deployment_environment', DEPLOYMENT_ENVIRONMENT_PLACEHOLDER)}",
            f"Last Updated: {context.get('last_update_timestamp', LAST_UPDATE_TIMESTAMP_PLACEHOLDER)}",
            f"Backend Endpoint: {context.get('backend_endpoint', BACKEND_ENDPOINT_PLACEHOLDER)}",
            "",
            "System Specs",
            "------------",
            f"Device RAM: {context.get('detected_ram', '[DETECTED_RAM]')}",
            f"Disk Space: {context.get('detected_disk', '[DETECTED_DISK]')}",
            f"Connectivity: {context.get('connectivity', 'Unknown')}",
            "",
            "Sync State",
            "----------",
            f"Local Changes Pending: {context.get('pending_changes_count', PENDING_CHANGES_COUNT_PLACEHOLDER)}",
            f"Last Sync Attempt: {context.get('last_sync_timestamp', LAST_SYNC_TIMESTAMP_PLACEHOLDER)}",
            f"Sync State: {context.get('sync_state', SYNC_STATE_PLACEHOLDER)}",
            "",
            "Recent Errors",
            "-------------",
            recent_errors_block,
            "",
            "System Diagnostics Output",
            "-------------------------",
            str(diagnostics_output),
        ]
    )


def render_copy_to_clipboard_button(payload: str, key: str = "copy_diagnostics") -> None:
    """Render a keyboard-accessible HTML button that copies text to clipboard."""
    button_id = f"{key}_button"
    status_id = f"{key}_status"
    payload_json = json.dumps(payload)

    components.html(
        f"""
        <div style="display:flex;align-items:center;gap:10px;font-family:Inter,system-ui,sans-serif;">
          <button
            id="{button_id}"
            type="button"
            aria-describedby="{status_id}"
            style="
              border:none;
              border-radius:10px;
              padding:10px 18px;
              background:#00A8E8;
              color:#ffffff;
              font-size:14px;
              font-weight:600;
              cursor:pointer;
            "
          >
            Copy Diagnostics
          </button>
          <span id="{status_id}" aria-live="polite" style="font-size:12px;color:#64748B;"></span>
        </div>
        <script>
          const button = document.getElementById("{button_id}");
          const status = document.getElementById("{status_id}");
          const payload = {payload_json};

          button.addEventListener("click", async () => {{
            try {{
              await navigator.clipboard.writeText(payload);
              status.textContent = "Copied to clipboard.";
            }} catch (error) {{
              status.textContent = "Copy failed. Select and copy manually.";
            }}
          }});
        </script>
        """,
        height=56,
    )
