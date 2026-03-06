"""
Studaxis — Sync Status Panel (Student Local App)
═════════════════════════════════════════════════
UI Bridge layer for visualizing sync state.
No backend logic — reflects SyncManager state only.
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Optional


def _inject_sync_css():
    """Inject CSS for sync status components."""
    st.markdown("""
    <style>
    /* ══════════════════════════════════════════════════════════
       Sync Status Panel — Student Local App
       ══════════════════════════════════════════════════════════ */
    
    .sync-panel {
        --sync-bg: rgba(255, 255, 255, 0.7);
        --sync-border: #E2E8F0;
        --sync-text: #0F172A;
        --sync-muted: #64748B;
        --sync-success: #16A34A;
        --sync-syncing: #fb923c;
        --sync-error: #FA5C5C;
        --sync-offline: #94A3B8;
    }
    
    .theme-dark .sync-panel {
        --sync-bg: rgba(15, 23, 42, 0.9);
        --sync-border: rgba(148, 163, 184, 0.35);
        --sync-text: #E5E7EB;
        --sync-muted: #9CA3AF;
    }
    
    /* Sync status card */
    .sync-status-card {
        background: var(--sync-bg);
        border: 1px solid var(--sync-border);
        border-radius: 18px;
        padding: 20px 24px;
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        margin-bottom: 16px;
        color: var(--sync-text);
    }
    
    .sync-status-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;
        flex-wrap: wrap;
        gap: 12px;
    }
    
    .sync-status-title {
        font-size: 18px;
        font-weight: 600;
        color: var(--sync-text);
        margin: 0;
    }
    
    /* Status badge */
    .sync-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
        border: 1px solid;
    }
    
    .sync-badge__dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
    }
    
    .sync-badge--connected {
        background: rgba(22, 163, 74, 0.1);
        border-color: rgba(22, 163, 74, 0.3);
        color: #15803D;
    }
    
    .sync-badge--connected .sync-badge__dot {
        background: var(--sync-success);
    }
    
    .sync-badge--syncing {
        background: rgba(251, 146, 60, 0.1);
        border-color: rgba(251, 146, 60, 0.3);
        color: #9A3412;
    }
    
    .sync-badge--syncing .sync-badge__dot {
        background: var(--sync-syncing);
        animation: pulse-sync 1.5s infinite;
    }
    
    @keyframes pulse-sync {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
    
    .sync-badge--error {
        background: rgba(250, 92, 92, 0.1);
        border-color: rgba(250, 92, 92, 0.3);
        color: #7F1D1D;
    }
    
    .sync-badge--error .sync-badge__dot {
        background: var(--sync-error);
    }
    
    .sync-badge--offline {
        background: rgba(148, 163, 184, 0.1);
        border-color: rgba(148, 163, 184, 0.3);
        color: #475569;
    }
    
    .sync-badge--offline .sync-badge__dot {
        background: var(--sync-offline);
    }
    
    /* Sync info grid */
    .sync-info-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 16px;
        margin: 16px 0;
    }
    
    .sync-info-item {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    
    .sync-info-label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--sync-muted);
    }
    
    .sync-info-value {
        font-size: 16px;
        font-weight: 700;
        color: var(--sync-text);
    }
    
    /* Queue status */
    .sync-queue {
        padding: 12px 16px;
        background: rgba(148, 163, 184, 0.06);
        border-radius: 12px;
        margin-top: 12px;
    }
    
    .sync-queue-title {
        font-size: 13px;
        font-weight: 600;
        color: var(--sync-text);
        margin: 0 0 8px 0;
    }
    
    .sync-queue-item {
        display: flex;
        justify-content: space-between;
        padding: 6px 0;
        font-size: 12px;
        color: var(--sync-muted);
        border-bottom: 1px solid rgba(148, 163, 184, 0.1);
    }
    
    .sync-queue-item:last-child {
        border-bottom: none;
    }
    
    /* Error alert */
    .sync-error-alert {
        background: rgba(250, 92, 92, 0.08);
        border: 1px solid rgba(250, 92, 92, 0.25);
        border-left: 4px solid var(--sync-error);
        border-radius: 12px;
        padding: 12px 16px;
        margin-top: 12px;
    }
    
    .sync-error-title {
        font-size: 13px;
        font-weight: 600;
        color: #7F1D1D;
        margin: 0 0 6px 0;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    .sync-error-message {
        font-size: 12px;
        color: #991B1B;
        margin: 0;
        line-height: 1.5;
    }
    
    /* Offline banner */
    .offline-banner {
        background: linear-gradient(135deg, rgba(148, 163, 184, 0.12), rgba(148, 163, 184, 0.08));
        border: 1px solid rgba(148, 163, 184, 0.3);
        border-radius: 12px;
        padding: 12px 16px;
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
    }
    
    .offline-banner__icon {
        font-size: 20px;
    }
    
    .offline-banner__text {
        flex: 1;
        font-size: 13px;
        font-weight: 500;
        color: var(--sync-text);
    }
    
    /* Progress bar for partial sync */
    .sync-progress {
        margin-top: 12px;
    }
    
    .sync-progress__bar {
        height: 6px;
        background: rgba(148, 163, 184, 0.15);
        border-radius: 999px;
        overflow: hidden;
    }
    
    .sync-progress__fill {
        height: 100%;
        background: linear-gradient(90deg, #00A8E8, #0091C7);
        border-radius: 999px;
        transition: width 0.4s ease;
    }
    
    .sync-progress__label {
        font-size: 11px;
        color: var(--sync-muted);
        margin-top: 4px;
    }
    
    /* Conflict indicator (Phase 2) */
    .sync-conflict {
        background: rgba(251, 239, 118, 0.12);
        border: 1px solid rgba(251, 239, 118, 0.4);
        border-left: 4px solid #FBEF76;
        border-radius: 12px;
        padding: 12px 16px;
        margin-top: 12px;
    }
    
    .sync-conflict__title {
        font-size: 13px;
        font-weight: 600;
        color: #854D0E;
        margin: 0 0 6px 0;
    }
    </style>
    """, unsafe_allow_html=True)


def render_sync_status_badge(status: str) -> str:
    """
    Render sync status badge HTML.
    
    Args:
        status: 'connected' | 'syncing' | 'error' | 'offline' | 'idle'
    
    Returns:
        HTML string for badge
    """
    status_labels = {
        'connected': 'Connected',
        'syncing': 'Syncing',
        'error': 'Error',
        'offline': 'Offline',
        'idle': 'Synced',
    }
    
    label = status_labels.get(status, 'Unknown')
    status_class = status if status != 'idle' else 'connected'
    
    return f"""
    <div class="sync-badge sync-badge--{status_class}" role="status" aria-live="polite">
        <span class="sync-badge__dot" aria-hidden="true"></span>
        <span>{label}</span>
    </div>
    """


def render_sync_info_grid(
    last_sync: Optional[str],
    queue_size: int,
    connectivity: bool
) -> str:
    """Render sync information grid."""
    
    def format_timestamp(ts: Optional[str]) -> str:
        if not ts:
            return "Never"
        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
            diff = (now - dt).total_seconds()
            
            if diff < 60:
                return "Just now"
            elif diff < 3600:
                return f"{int(diff // 60)}m ago"
            elif diff < 86400:
                return f"{int(diff // 3600)}h ago"
            else:
                return dt.strftime("%b %d, %H:%M")
        except:
            return "Unknown"
    
    last_sync_formatted = format_timestamp(last_sync)
    connectivity_text = "Online" if connectivity else "Offline"
    connectivity_icon = "🟢" if connectivity else "⚪"
    
    return f"""
    <div class="sync-info-grid">
        <div class="sync-info-item">
            <span class="sync-info-label">Last Sync</span>
            <span class="sync-info-value">{last_sync_formatted}</span>
        </div>
        <div class="sync-info-item">
            <span class="sync-info-label">Pending Items</span>
            <span class="sync-info-value">{queue_size}</span>
        </div>
        <div class="sync-info-item">
            <span class="sync-info-label">Connectivity</span>
            <span class="sync-info-value">{connectivity_icon} {connectivity_text}</span>
        </div>
    </div>
    """


def render_queue_details(queue_summary: Dict) -> str:
    """Render detailed queue breakdown."""
    if queue_summary.get('total', 0) == 0:
        return ""
    
    quiz_count = queue_summary.get('quiz_attempts', 0)
    streak_count = queue_summary.get('streak_updates', 0)
    oldest = queue_summary.get('oldest_item', '')
    
    if oldest:
        try:
            dt = datetime.fromisoformat(oldest.replace('Z', '+00:00'))
            oldest_formatted = dt.strftime("%b %d, %H:%M")
        except:
            oldest_formatted = "Unknown"
    else:
        oldest_formatted = "Unknown"
    
    return f"""
    <div class="sync-queue">
        <h4 class="sync-queue-title">📦 Pending Sync Items</h4>
        <div class="sync-queue-item">
            <span>Quiz attempts</span>
            <strong>{quiz_count}</strong>
        </div>
        <div class="sync-queue-item">
            <span>Streak updates</span>
            <strong>{streak_count}</strong>
        </div>
        <div class="sync-queue-item">
            <span>Oldest item</span>
            <strong>{oldest_formatted}</strong>
        </div>
    </div>
    """


def render_sync_errors(errors: list) -> str:
    """Render sync error alerts."""
    if not errors:
        return ""
    
    error_html = []
    for error in errors[:3]:  # Show max 3 errors
        error_html.append(f"""
        <div class="sync-error-alert">
            <h4 class="sync-error-title">
                <span aria-hidden="true">⚠️</span>
                Sync Error
            </h4>
            <p class="sync-error-message">{error}</p>
        </div>
        """)
    
    return "".join(error_html)


def render_offline_banner() -> str:
    """Render offline mode banner."""
    return """
    <div class="offline-banner" role="alert">
        <span class="offline-banner__icon" aria-hidden="true">📡</span>
        <span class="offline-banner__text">
            <strong>Offline Mode</strong> — All features work without internet. 
            Your progress will sync when connectivity returns.
        </span>
    </div>
    """


def render_sync_progress(synced: int, total: int) -> str:
    """Render sync progress bar (for partial sync state)."""
    if total == 0:
        return ""
    
    percentage = int((synced / total) * 100)
    
    return f"""
    <div class="sync-progress">
        <div class="sync-progress__bar" role="progressbar" 
             aria-valuenow="{percentage}" aria-valuemin="0" aria-valuemax="100">
            <div class="sync-progress__fill" style="width: {percentage}%"></div>
        </div>
        <div class="sync-progress__label">
            Syncing {synced} of {total} items ({percentage}%)
        </div>
    </div>
    """


def show_sync_status_panel(orchestrator, preferences: Optional[Dict] = None):
    """
    Main sync status panel component for Student Local App.
    
    Args:
        orchestrator: SyncOrchestrator instance (wraps SyncManager)
        preferences: User preferences dict (for sync_enabled flag)
    """
    _inject_sync_css()
    
    # Check if sync is disabled in preferences
    sync_enabled = preferences.get('sync_enabled', True) if preferences else True
    
    # Get current sync state from orchestrator
    sync_state = orchestrator.get_state()
    connectivity = orchestrator.is_online()
    queue_size = orchestrator.get_queue_size()
    queue_summary = orchestrator.get_queue_summary()
    
    # Map orchestrator state to UI status
    if not sync_enabled:
        status = 'offline'
        status_text = 'Disabled in Settings'
    elif sync_state == "OFFLINE":
        status = 'offline'
        status_text = 'Offline Mode'
    elif sync_state == "SYNCING":
        status = 'syncing'
        status_text = 'Syncing...'
    elif sync_state == "ERROR":
        status = 'error'
        status_text = 'Sync Error'
    elif sync_state in ["IDLE", "SYNCED"]:
        status = 'idle'
        status_text = 'All synced'
    elif sync_state in ["QUEUED", "PARTIAL_SYNC"]:
        status = 'connected'
        status_text = f'{queue_size} items pending'
    elif sync_state == "CONFLICT":
        status = 'error'  # Use error styling for conflicts
        status_text = 'Conflict Resolved'
    else:
        status = 'connected'
        status_text = f'{queue_size} items pending'
    
    # Get last sync timestamp from orchestrator
    last_sync = orchestrator.get_last_sync_timestamp()
    
    # Render header with status badge
    header_html = f"""
    <div class="sync-status-card">
        <div class="sync-status-header">
            <h3 class="sync-status-title">Cloud Sync Status</h3>
            {render_sync_status_badge(status)}
        </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # Show offline banner if not connected
    if not connectivity and sync_enabled:
        st.markdown(render_offline_banner(), unsafe_allow_html=True)
    
    # Sync info grid
    st.markdown(
        render_sync_info_grid(last_sync, queue_size, connectivity),
        unsafe_allow_html=True
    )
    
    # Queue details
    if queue_size > 0:
        st.markdown(render_queue_details(queue_summary), unsafe_allow_html=True)
    
    # Manual sync button
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Disable button if sync disabled, offline, or already syncing
        button_disabled = (
            not sync_enabled or 
            sync_state == "OFFLINE" or 
            sync_state == "SYNCING"
        )
        
        if st.button(
            "🔄 Sync Now",
            key="manual_sync_btn",
            disabled=button_disabled,
            use_container_width=True,
            help="Manually trigger cloud sync"
        ):
            with st.spinner("Syncing..."):
                result = orchestrator.execute_sync()
                
                if result['synced'] > 0:
                    st.success(f"✅ Synced {result['synced']} items")
                
                if result['errors']:
                    for error in result['errors'][:2]:
                        st.error(error)
                
                if result['pending'] > 0:
                    st.warning(f"⚠️ {result['pending']} items still pending")
                
                st.rerun()
    
    with col2:
        if st.button(
            "⚙️ Sync Settings",
            key="sync_settings_btn",
            use_container_width=True,
            help="Configure sync preferences"
        ):
            st.session_state.page = "settings"
            st.rerun()
    
    # Close card
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Show sync errors if any (from last sync attempt)
    if 'last_sync_errors' in st.session_state:
        st.markdown(
            render_sync_errors(st.session_state.last_sync_errors),
            unsafe_allow_html=True
        )
