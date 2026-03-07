"""
Example: Using SyncOrchestrator in Streamlit App
═══════════════════════════════════════════════════

This example shows how to integrate SyncOrchestrator
into your Streamlit pages for offline-first sync.

No AWS dependencies - works entirely locally.
"""

import streamlit as st
from pathlib import Path

# Import orchestrator
from sync_orchestrator import SyncOrchestrator
from pages.sync_status import show_sync_status_panel


def init_orchestrator():
    """
    Initialize orchestrator once per session.
    
    Use st.cache_resource to ensure single instance.
    """
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = SyncOrchestrator(
            base_path=str(Path(__file__).parent)
        )
        print("✅ SyncOrchestrator initialized")
    
    return st.session_state.orchestrator


def example_quiz_completion(user_id: str, quiz_id: str, score: int, total: int):
    """
    Example: Handle quiz completion with orchestrator.
    
    Args:
        user_id: Student user ID
        quiz_id: Quiz identifier
        score: Score achieved
        total: Total questions
    """
    # Get orchestrator instance
    orchestrator = init_orchestrator()
    
    # 1. Save quiz locally (primary authority)
    # This would normally use your local storage functions
    print(f"📝 Saving quiz {quiz_id} locally...")
    # save_to_local_storage(quiz_id, score, total)
    
    # 2. Enqueue for sync
    success = orchestrator.enqueue_change(
        change_type="recordQuizAttempt",
        payload={
            "userId": user_id,
            "quizId": quiz_id,
            "score": score,
            "totalQuestions": total,
            "subject": "Mathematics",
            "difficulty": "Medium"
        },
        priority="high"  # Quiz = high priority
    )
    
    if success:
        print(f"✅ Quiz {quiz_id} queued for sync")
        print(f"   Queue size: {orchestrator.get_queue_size()}")
        print(f"   State: {orchestrator.get_state()}")
        
        # 3. Trigger debounced sync (waits 5s)
        orchestrator.trigger_sync_debounced()
        print(f"   Sync scheduled in {orchestrator.DEBOUNCE_WINDOW}s")
    else:
        print(f"❌ Failed to queue quiz {quiz_id}")
    
    return success


def example_streak_update(user_id: str, current_streak: int):
    """
    Example: Handle streak update with orchestrator.
    
    Args:
        user_id: Student user ID
        current_streak: Current streak count
    """
    orchestrator = init_orchestrator()
    
    # Enqueue streak update (normal priority)
    success = orchestrator.enqueue_change(
        change_type="updateStreak",
        payload={
            "userId": user_id,
            "currentStreak": current_streak
        },
        priority="normal"  # Streaks = normal priority
    )
    
    if success:
        print(f"🔥 Streak {current_streak} queued for sync")
    
    return success


def example_manual_sync():
    """Example: Manual sync trigger."""
    orchestrator = init_orchestrator()
    
    print("🔄 Triggering manual sync...")
    
    # Execute sync immediately
    result = orchestrator.execute_sync()
    
    print(f"   Synced: {result['synced']}")
    print(f"   Failed: {result['failed']}")
    print(f"   Pending: {result['pending']}")
    print(f"   Online: {result['online']}")
    
    if result['errors']:
        print(f"   Errors: {result['errors']}")
    
    return result


def example_settings_page():
    """Example: Settings page with sync status panel."""
    orchestrator = init_orchestrator()
    
    st.title("⚙️ Settings")
    
    # Load preferences
    try:
        from preferences import load_user_stats
        prefs = load_user_stats().get("preferences", {})
    except:
        prefs = {"sync_enabled": True}
    
    # Show sync status panel
    st.subheader("Cloud Sync")
    show_sync_status_panel(orchestrator, prefs)
    
    # Sync preferences toggle
    st.markdown("---")
    st.subheader("Privacy Controls")
    
    sync_enabled = st.checkbox(
        "Enable cloud sync",
        value=prefs.get("sync_enabled", True),
        help="When enabled, your progress syncs to teacher dashboard"
    )
    
    if sync_enabled != prefs.get("sync_enabled", True):
        prefs["sync_enabled"] = sync_enabled
        # Save preferences
        # save_user_preferences(prefs)
        st.success("Preferences saved!")
    
    # Show current state info
    st.markdown("---")
    st.subheader("Debug Info")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("State", orchestrator.get_state())
    
    with col2:
        st.metric("Queue Size", orchestrator.get_queue_size())
    
    with col3:
        online = orchestrator.is_online()
        st.metric("Status", "🟢 Online" if online else "⚪ Offline")
    
    # Dead letter queue (failed items)
    dlq = orchestrator.get_dead_letter_queue()
    if dlq:
        st.markdown("---")
        st.subheader("⚠️ Failed Items")
        st.warning(f"{len(dlq)} items failed after multiple retries")
        
        for item in dlq:
            with st.expander(f"{item['mutation_type']} - {item['change_id'][:8]}"):
                st.write(f"**Error:** {item['last_error']}")
                st.write(f"**Retries:** {item['retry_count']}")
                st.write(f"**Failed at:** {item.get('dlq_timestamp', 'Unknown')}")
                
                col_retry, col_discard = st.columns(2)
                
                with col_retry:
                    if st.button("Retry", key=f"retry_{item['change_id']}"):
                        success = orchestrator.retry_dlq_item(item['change_id'])
                        if success:
                            st.success("Re-queued for sync!")
                            st.rerun()
                
                with col_discard:
                    if st.button("Discard", key=f"discard_{item['change_id']}"):
                        success = orchestrator.discard_dlq_item(item['change_id'])
                        if success:
                            st.success("Discarded!")
                            st.rerun()


def example_dashboard_page():
    """Example: Dashboard with auto-sync on load."""
    orchestrator = init_orchestrator()
    
    st.title("📊 Dashboard")
    
    # Auto-trigger sync on page load (debounced)
    if "dashboard_loaded" not in st.session_state:
        st.session_state.dashboard_loaded = True
        
        # Trigger sync if items are queued
        if orchestrator.get_queue_size() > 0:
            orchestrator.trigger_sync_debounced()
            st.info("🔄 Sync scheduled for pending items")
    
    # Show sync status badge
    state = orchestrator.get_state()
    queue_size = orchestrator.get_queue_size()
    
    if state == "OFFLINE":
        st.warning("📡 Offline Mode — Your progress will sync when online")
    elif state == "SYNCING":
        st.info("🔄 Syncing...")
    elif queue_size > 0:
        st.info(f"📦 {queue_size} items pending sync")
    
    # Rest of dashboard UI...
    st.write("Your dashboard content here...")


# ═══════════════════════════════════════════════════════════════════════
# STANDALONE TEST
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Testing SyncOrchestrator Integration")
    print("=" * 60)
    
    # Initialize orchestrator
    orch = SyncOrchestrator(base_path=".")
    print(f"Initial state: {orch.get_state()}")
    print()
    
    # Test 1: Quiz completion
    print("Test 1: Quiz Completion")
    print("-" * 60)
    example_quiz_completion(
        user_id="student_001",
        quiz_id="quiz_algebra_001",
        score=8,
        total=10
    )
    print()
    
    # Test 2: Streak update
    print("Test 2: Streak Update")
    print("-" * 60)
    example_streak_update(
        user_id="student_001",
        current_streak=5
    )
    print()
    
    # Test 3: Manual sync
    print("Test 3: Manual Sync")
    print("-" * 60)
    result = example_manual_sync()
    print()
    
    # Test 4: State check
    print("Test 4: Final State")
    print("-" * 60)
    print(f"State: {orch.get_state()}")
    print(f"Queue: {orch.get_queue_size()} items")
    print(f"Online: {orch.is_online()}")
    print()
    
    # Cleanup
    orch.cleanup()
    print("✅ All tests complete!")
