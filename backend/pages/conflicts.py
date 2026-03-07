"""
Studaxis — Conflict Resolution UI
═══════════════════════════════════════════════════════════════
UI components for displaying and resolving sync conflicts.

Components:
  - Conflict badge (dashboard header)
  - Conflict warning banner
  - Conflict resolution modal (full-screen)
  - Conflict history view
  - Version comparison UI

Design: Follows design_system.md (glass cards, accessibility)
"""

import streamlit as st
import json
from typing import Optional
from conflict_resolution_engine import (
    ConflictAwareOrchestrator,
    ConflictResult,
    format_timestamp,
    calculate_time_ago,
    get_conflict_severity
)


# ═══════════════════════════════════════════════════════════════════════
# CONFLICT BADGE (Dashboard Header)
# ═══════════════════════════════════════════════════════════════════════

def render_conflict_badge():
    """
    Show conflict indicator badge in dashboard header.
    
    Displays number of pending conflicts with warning icon.
    """
    orchestrator: ConflictAwareOrchestrator = st.session_state.get("orchestrator")
    if not orchestrator:
        return
    
    conflicts = orchestrator.get_pending_conflicts()
    
    if len(conflicts) > 0:
        # Inject CSS for conflict badge
        st.markdown("""
        <style>
            .conflict-badge {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 6px 12px;
                background: rgba(251, 92, 92, 0.1);
                border: 1px solid #FA5C5C;
                border-radius: 20px;
                color: #DC2626;
                font-size: 13px;
                font-weight: 500;
            }
            
            .conflict-badge .icon {
                font-size: 16px;
            }
        </style>
        """, unsafe_allow_html=True)
        
        # Render badge
        count_text = "1 Conflict" if len(conflicts) == 1 else f"{len(conflicts)} Conflicts"
        st.markdown(f"""
        <div class="conflict-badge">
            <span class="icon">⚠️</span>
            <span class="text">{count_text}</span>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# CONFLICT WARNING BANNER
# ═══════════════════════════════════════════════════════════════════════

def render_conflict_warning_banner():
    """
    Show persistent warning banner when conflicts exist.
    
    Full-width banner with link to conflicts page.
    """
    orchestrator: ConflictAwareOrchestrator = st.session_state.get("orchestrator")
    if not orchestrator:
        return
    
    conflicts = orchestrator.get_pending_conflicts()
    
    if len(conflicts) > 0:
        count_text = "1 sync conflict" if len(conflicts) == 1 else f"{len(conflicts)} sync conflicts"
        
        st.warning(
            f"⚠️ **{count_text} detected.** "
            f"Your data and cloud data differ. [Review and resolve →](#conflicts)",
            icon="⚠️"
        )


# ═══════════════════════════════════════════════════════════════════════
# CONFLICT RESOLUTION MODAL
# ═══════════════════════════════════════════════════════════════════════

def show_conflict_resolution_modal(conflict: ConflictResult):
    """
    Display full-screen conflict resolution modal.
    
    Args:
        conflict: ConflictResult to display
    """
    # Inject CSS for modal styling
    st.markdown("""
    <style>
        /* Glass card modal */
        .conflict-modal {
            background: rgba(255, 255, 255, 0.95);
            border: 1px solid var(--border-subtle-light, #E2E8F0);
            border-radius: 18px;
            padding: 32px;
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.12);
            backdrop-filter: blur(16px);
        }
        
        /* Two-column panel layout */
        .conflict-panels {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 24px 0;
        }
        
        .conflict-panel {
            background: rgba(255, 255, 255, 0.7);
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 20px;
        }
        
        .conflict-panel__header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 16px;
            font-size: 18px;
            font-weight: 600;
        }
        
        .conflict-panel__metadata {
            margin-bottom: 16px;
            padding: 12px;
            background: rgba(148, 163, 184, 0.08);
            border-radius: 8px;
            font-size: 13px;
        }
        
        .metadata-row {
            display: flex;
            justify-content: space-between;
            margin: 4px 0;
        }
        
        .metadata-row .label {
            color: #64748B;
            font-weight: 500;
        }
        
        .metadata-row .value {
            color: #0F172A;
            font-weight: 600;
        }
        
        /* Diff highlights */
        .diff-highlight {
            padding: 8px 12px;
            margin: 8px 0;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }
        
        .diff-highlight--added {
            background: rgba(22, 163, 74, 0.1);
            border-left: 3px solid #16A34A;
            color: #15803D;
        }
        
        .diff-highlight--removed {
            background: rgba(250, 92, 92, 0.1);
            border-left: 3px solid #FA5C5C;
            color: #DC2626;
            text-decoration: line-through;
        }
        
        .diff-highlight--changed {
            background: rgba(0, 168, 232, 0.1);
            border-left: 3px solid #00A8E8;
            color: #0284C7;
        }
        
        /* Badge styles */
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .badge--device {
            background: rgba(100, 116, 139, 0.1);
            color: #475569;
        }
        
        .badge--severity-high {
            background: rgba(250, 92, 92, 0.1);
            color: #DC2626;
        }
        
        .badge--severity-medium {
            background: rgba(251, 191, 36, 0.1);
            color: #D97706;
        }
        
        .badge--severity-low {
            background: rgba(59, 130, 246, 0.1);
            color: #2563EB;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Modal header
    st.markdown("# ⚠️ Sync Conflict Detected")
    
    severity = get_conflict_severity(conflict)
    severity_badge = f"<span class='badge badge--severity-{severity}'>{severity.upper()}</span>"
    
    st.markdown(
        f"The same data was modified in two places. {severity_badge}",
        unsafe_allow_html=True
    )
    
    st.markdown("---")
    
    # Two-column comparison
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📱 Your Device (Local)")
        
        # Metadata card
        st.markdown(f"""
        <div class="conflict-panel__metadata">
            <div class="metadata-row">
                <span class="label">Version</span>
                <span class="value">{conflict.local_version}</span>
            </div>
            <div class="metadata-row">
                <span class="label">Last Modified</span>
                <span class="value">{format_timestamp(conflict.local_updated_at)}</span>
            </div>
            <div class="metadata-row">
                <span class="label">Device</span>
                <span class="value">{conflict.local_data.get('device_id', 'Unknown')}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Data display
        st.markdown("**Data:**")
        st.json(conflict.local_data)
    
    with col2:
        st.markdown("### ☁️ Cloud / Other Device")
        
        # Metadata card
        st.markdown(f"""
        <div class="conflict-panel__metadata">
            <div class="metadata-row">
                <span class="label">Version</span>
                <span class="value">{conflict.cloud_version}</span>
            </div>
            <div class="metadata-row">
                <span class="label">Last Modified</span>
                <span class="value">{format_timestamp(conflict.cloud_updated_at)}</span>
            </div>
            <div class="metadata-row">
                <span class="label">Device</span>
                <span class="value">{conflict.cloud_data.get('device_id', 'Unknown')}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Data display
        st.markdown("**Data:**")
        st.json(conflict.cloud_data)
    
    # Show conflicting fields
    if conflict.conflicting_fields:
        st.markdown("### 🔍 Changes Detected")
        
        for field in conflict.conflicting_fields:
            local_val = conflict.local_data.get(field)
            cloud_val = conflict.cloud_data.get(field)
            
            st.markdown(f"**{field}:**")
            col_diff1, col_diff2 = st.columns(2)
            
            with col_diff1:
                st.markdown(
                    f"<div class='diff-highlight diff-highlight--added'>Local: {local_val}</div>",
                    unsafe_allow_html=True
                )
            
            with col_diff2:
                st.markdown(
                    f"<div class='diff-highlight diff-highlight--removed'>Cloud: {cloud_val}</div>",
                    unsafe_allow_html=True
                )
    
    st.markdown("---")
    
    # Resolution options
    st.markdown("### Resolution Options")
    
    # Action buttons
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button("📱 Keep Local", key="btn_keep_local", type="primary", use_container_width=True):
            _apply_resolution(conflict.entity_id, "keep_local")
            st.success("✅ Conflict resolved. Keeping local version.")
            st.session_state.show_conflict_modal = False
            st.rerun()
    
    with col_btn2:
        if st.button("☁️ Keep Cloud", key="btn_keep_cloud", use_container_width=True):
            _apply_resolution(conflict.entity_id, "keep_cloud")
            st.success("✅ Conflict resolved. Keeping cloud version.")
            st.session_state.show_conflict_modal = False
            st.rerun()
    
    with col_btn3:
        if st.button("🔀 Merge Both", key="btn_merge", use_container_width=True):
            st.info("📋 Field-level merge UI coming in Phase 2. Using auto-merge for now.")
            _apply_resolution(conflict.entity_id, "merge")
            st.session_state.show_conflict_modal = False
            st.rerun()
    
    # View history link
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📜 View Full History", key="btn_history", use_container_width=False):
        st.session_state.show_history = True
        st.rerun()
    
    # Show recommendation
    orchestrator = st.session_state.get("orchestrator")
    if orchestrator:
        recommendation = orchestrator.conflict_engine.generate_recommendation(conflict)
        st.info(recommendation)


def _apply_resolution(entity_id: str, user_choice: str):
    """
    Apply user's conflict resolution choice.
    
    Args:
        entity_id: Entity ID of conflict
        user_choice: "keep_local" | "keep_cloud" | "merge"
    """
    orchestrator: ConflictAwareOrchestrator = st.session_state.get("orchestrator")
    if not orchestrator:
        st.error("❌ Orchestrator not initialized")
        return
    
    try:
        resolved_data = orchestrator.resolve_conflict_manual(entity_id, user_choice)
        
        # Trigger sync with resolved data
        orchestrator.trigger_sync_debounced()
        
    except Exception as e:
        st.error(f"❌ Error resolving conflict: {e}")


# ═══════════════════════════════════════════════════════════════════════
# CONFLICTS PAGE (Full Page View)
# ═══════════════════════════════════════════════════════════════════════

def show_conflicts_page():
    """
    Dedicated conflicts page accessible from navigation.
    
    Shows all pending conflicts with resolution options.
    """
    st.title("⚠️ Sync Conflicts")
    
    orchestrator: ConflictAwareOrchestrator = st.session_state.get("orchestrator")
    if not orchestrator:
        st.error("❌ Orchestrator not initialized")
        return
    
    conflicts = orchestrator.get_pending_conflicts()
    
    # No conflicts
    if not conflicts:
        st.success("✅ No conflicts detected. All data is synchronized.")
        
        # Show history button
        if st.button("📜 View Resolution History"):
            st.session_state.show_history = True
            st.rerun()
        
        return
    
    # Show conflicts count
    st.warning(
        f"**{len(conflicts)} conflict{'s' if len(conflicts) != 1 else ''} "
        f"require your attention.**"
    )
    
    # Render each conflict
    for idx, conflict_dict in enumerate(conflicts):
        # Convert dict to ConflictResult
        conflict = ConflictResult(**conflict_dict)
        
        with st.expander(
            f"**{conflict.entity_type}** — {conflict.entity_id} "
            f"({calculate_time_ago(conflict.detected_at)})",
            expanded=(idx == 0)  # Expand first conflict
        ):
            show_conflict_card(conflict)


def show_conflict_card(conflict: ConflictResult):
    """
    Render individual conflict card with resolution options.
    
    Args:
        conflict: ConflictResult to display
    """
    # Conflict metadata
    st.markdown(f"**Detected:** {format_timestamp(conflict.detected_at)}")
    st.markdown(f"**Reason:** {conflict.reason}")
    st.markdown(f"**Severity:** {get_conflict_severity(conflict).upper()}")
    
    st.markdown("---")
    
    # Side-by-side comparison
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📱 Local Version")
        st.markdown(f"**Version:** {conflict.local_version}")
        st.markdown(f"**Modified:** {format_timestamp(conflict.local_updated_at)}")
        
        # Show conflicting fields only (for brevity)
        if conflict.conflicting_fields:
            st.markdown("**Changed Fields:**")
            local_subset = {
                k: conflict.local_data.get(k)
                for k in conflict.conflicting_fields
            }
            st.json(local_subset)
        else:
            st.json(conflict.local_data)
    
    with col2:
        st.markdown("#### ☁️ Cloud Version")
        st.markdown(f"**Version:** {conflict.cloud_version}")
        st.markdown(f"**Modified:** {format_timestamp(conflict.cloud_updated_at)}")
        
        # Show conflicting fields only
        if conflict.conflicting_fields:
            st.markdown("**Changed Fields:**")
            cloud_subset = {
                k: conflict.cloud_data.get(k)
                for k in conflict.conflicting_fields
            }
            st.json(cloud_subset)
        else:
            st.json(conflict.cloud_data)
    
    # Field differences
    if conflict.conflicting_fields:
        st.markdown("#### 📊 Field Comparison")
        
        for field in conflict.conflicting_fields:
            local_val = conflict.local_data.get(field)
            cloud_val = conflict.cloud_data.get(field)
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown(f"**{field}** (Local)")
                st.code(str(local_val), language="text")
            
            with col_b:
                st.markdown(f"**{field}** (Cloud)")
                st.code(str(cloud_val), language="text")
    
    st.markdown("---")
    
    # Resolution buttons
    st.markdown("#### Choose Resolution")
    
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        if st.button(
            "📱 Keep Local",
            key=f"keep_local_{conflict.entity_id}",
            type="primary",
            use_container_width=True
        ):
            _apply_resolution(conflict.entity_id, "keep_local")
            st.success("✅ Keeping local version. Syncing...")
            st.rerun()
    
    with col_btn2:
        if st.button(
            "☁️ Keep Cloud",
            key=f"keep_cloud_{conflict.entity_id}",
            use_container_width=True
        ):
            _apply_resolution(conflict.entity_id, "keep_cloud")
            st.success("✅ Keeping cloud version. Syncing...")
            st.rerun()
    
    with col_btn3:
        if st.button(
            "🔀 Merge Both",
            key=f"merge_{conflict.entity_id}",
            use_container_width=True
        ):
            _apply_resolution(conflict.entity_id, "merge")
            st.success("✅ Merged versions. Syncing...")
            st.rerun()
    
    # Show recommendation
    orchestrator = st.session_state.get("orchestrator")
    if orchestrator:
        recommendation = orchestrator.conflict_engine.generate_recommendation(conflict)
        st.info(recommendation)


# ═══════════════════════════════════════════════════════════════════════
# CONFLICT HISTORY VIEW
# ═══════════════════════════════════════════════════════════════════════

def show_conflict_history():
    """
    Display conflict resolution history.
    
    Shows past conflicts and how they were resolved.
    """
    st.title("📜 Conflict Resolution History")
    
    orchestrator: ConflictAwareOrchestrator = st.session_state.get("orchestrator")
    if not orchestrator:
        st.error("❌ Orchestrator not initialized")
        return
    
    history = orchestrator.conflict_engine.get_conflict_history(limit=50)
    
    if not history:
        st.info("No conflict history yet.")
        return
    
    # Summary stats
    st.markdown("### Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Events", len(history))
    
    with col2:
        detected = len([e for e in history if e["event_type"] == "conflict_detected"])
        st.metric("Conflicts Detected", detected)
    
    with col3:
        resolved = len([e for e in history if e["event_type"] == "resolution_applied"])
        st.metric("Resolved", resolved)
    
    with col4:
        auto_resolved = len([
            e for e in history
            if e["event_type"] == "resolution_applied"
            and e.get("resolution_strategy", "").startswith("auto_")
        ])
        st.metric("Auto-Resolved", auto_resolved)
    
    st.markdown("---")
    
    # History table
    st.markdown("### Recent Events")
    
    for entry in reversed(history[-20:]):  # Show last 20, most recent first
        event_type = entry.get("event_type", "unknown")
        timestamp = entry.get("timestamp", "")
        entity_type = entry.get("entity_type", "Unknown")
        entity_id = entry.get("entity_id", "Unknown")
        
        # Event icon
        if event_type == "conflict_detected":
            icon = "🔴"
        elif event_type == "resolution_applied":
            icon = "✅"
        else:
            icon = "ℹ️"
        
        with st.expander(
            f"{icon} {entity_type} — {format_timestamp(timestamp)}",
            expanded=False
        ):
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown("**Event Details**")
                st.markdown(f"- **Type:** {event_type}")
                st.markdown(f"- **Entity:** {entity_type}")
                st.markdown(f"- **Entity ID:** {entity_id}")
                
                if "conflict_reason" in entry:
                    st.markdown(f"- **Reason:** {entry['conflict_reason']}")
                
                if "conflicting_fields" in entry:
                    fields = entry["conflicting_fields"]
                    if fields:
                        st.markdown(f"- **Fields:** {', '.join(fields)}")
            
            with col_b:
                if event_type == "resolution_applied":
                    st.markdown("**Resolution**")
                    st.markdown(f"- **Strategy:** {entry.get('resolution_strategy', 'Unknown')}")
                    st.markdown(f"- **Resolved By:** {entry.get('resolved_by', 'Unknown')}")
                    st.markdown(f"- **Resolved At:** {format_timestamp(entry.get('resolved_at', ''))}")
                else:
                    st.markdown("**Versions**")
                    st.markdown(f"- **Local:** {entry.get('local_version', '?')}")
                    st.markdown(f"- **Cloud:** {entry.get('cloud_version', '?')}")
            
            # Show data snapshots if available
            if "local_data_snapshot" in entry or "cloud_data_snapshot" in entry:
                if st.button("View Data Snapshots", key=f"view_{entry.get('event_id', 'unknown')}"):
                    if "local_data_snapshot" in entry:
                        st.markdown("**Local Data:**")
                        st.json(json.loads(entry["local_data_snapshot"]))
                    
                    if "cloud_data_snapshot" in entry:
                        st.markdown("**Cloud Data:**")
                        st.json(json.loads(entry["cloud_data_snapshot"]))
                    
                    if "resolved_data_snapshot" in entry:
                        st.markdown("**Resolved Data:**")
                        st.json(json.loads(entry["resolved_data_snapshot"]))


# ═══════════════════════════════════════════════════════════════════════
# QUICK CONFLICT CHECK (Add to Main App)
# ═══════════════════════════════════════════════════════════════════════

def check_and_show_conflict_modal():
    """
    Check if conflict modal should be shown and display it.
    
    Add this to main streamlit_app.py before rendering page content:
    
        from pages.conflicts import check_and_show_conflict_modal
        
        # Check for conflicts first
        check_and_show_conflict_modal()
        
        # Then render normal page
        if page == "dashboard":
            show_dashboard()
    """
    if st.session_state.get("show_conflict_modal", False):
        conflict_data = st.session_state.get("active_conflict")
        
        if conflict_data:
            # Convert dict to ConflictResult if needed
            if isinstance(conflict_data, dict):
                conflict = ConflictResult(**conflict_data)
            else:
                conflict = conflict_data
            
            # Show modal (blocks other content)
            show_conflict_resolution_modal(conflict)
            
            # Stop rendering other content
            st.stop()


# ═══════════════════════════════════════════════════════════════════════
# TEACHER DASHBOARD COMPONENTS
# ═══════════════════════════════════════════════════════════════════════

def show_teacher_conflict_alerts(teacher_id: str, class_code: str):
    """
    Show conflict alerts for teacher dashboard.
    
    Args:
        teacher_id: Current teacher ID
        class_code: Class code to filter conflicts
    """
    # This would query DynamoDB for conflicts in teacher's class
    # For now, show placeholder
    
    st.markdown("### ⚠️ Student Sync Conflicts")
    
    # Placeholder: Would query cloud for actual conflicts
    st.info(
        "Teacher conflict dashboard requires cloud integration. "
        "See conflict_resolution_engine.py for implementation."
    )
    
    # Example UI structure:
    """
    conflicts = query_student_conflicts(class_code)
    
    for conflict in conflicts:
        with st.container():
            st.markdown(f"**{conflict['student_name']}** — {conflict['entity_type']}")
            st.markdown(f"Detected: {format_timestamp(conflict['detected_at'])}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("View Details", key=f"view_{conflict['id']}"):
                    show_conflict_detail_modal(conflict)
            
            with col2:
                if st.button("Auto-Resolve (Teacher Authority)", key=f"resolve_{conflict['id']}"):
                    apply_teacher_resolution(conflict)
    """


def show_conflict_analytics_for_teacher(teacher_id: str, class_code: str):
    """
    Show conflict metrics and analytics for teacher.
    
    Args:
        teacher_id: Current teacher ID
        class_code: Class code to analyze
    """
    st.markdown("### 📊 Conflict Analytics")
    
    # Placeholder metrics
    st.info("Conflict analytics require cloud data. See implementation guide.")
    
    # Example structure:
    """
    metrics = get_conflict_metrics_for_class(class_code)
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Conflicts", metrics["total_conflicts"])
    col2.metric("Auto-Resolved", metrics["auto_resolved_count"])
    col3.metric("Manual", metrics["manual_resolved_count"])
    col4.metric("Pending", metrics["pending_conflicts"])
    
    # Charts
    st.markdown("#### Conflict Trends")
    st.line_chart(metrics["conflicts_over_time"])
    
    st.markdown("#### Most Common Conflict Types")
    st.bar_chart(metrics["conflicts_by_type"])
    """


# ═══════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════

__all__ = [
    "render_conflict_badge",
    "render_conflict_warning_banner",
    "show_conflict_resolution_modal",
    "show_conflicts_page",
    "show_conflict_history",
    "check_and_show_conflict_modal",
    "show_teacher_conflict_alerts",
    "show_conflict_analytics_for_teacher"
]
