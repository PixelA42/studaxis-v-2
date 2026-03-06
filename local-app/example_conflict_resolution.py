"""
Example Usage — Conflict Resolution Engine
═══════════════════════════════════════════════════════════════
Demonstrates conflict detection, resolution, and UI workflows.

Run with: python example_conflict_resolution.py
"""

import json
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Import conflict resolution engine
from conflict_resolution_engine import (
    ConflictResolutionEngine,
    ConflictAwareOrchestrator,
    ConflictResult,
    ConflictReason,
    ResolutionStrategy,
    ConflictConfig,
    format_timestamp,
    calculate_time_ago,
    get_conflict_severity
)


def print_header(title: str):
    """Print section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def print_subheader(title: str):
    """Print subsection header."""
    print(f"\n--- {title} ---\n")


# ═══════════════════════════════════════════════════════════════════════
# EXAMPLE 1: DETECT CONCURRENT EDITS
# ═══════════════════════════════════════════════════════════════════════

def example_1_detect_concurrent_edits():
    """
    Example: Student edits quiz on two devices, syncs from Device A.
    """
    print_header("EXAMPLE 1: Detect Concurrent Edits (Multi-Device)")
    
    # Initialize engine
    engine = ConflictResolutionEngine(base_path=".")
    
    # Scenario: Student completed same quiz on two devices
    local_data = {
        "attempt_id": "attempt_001",
        "quiz_id": "quiz_algebra_001",
        "user_id": "student_001",
        "score": 9,
        "total_questions": 10,
        "completed_at": "2026-03-05T10:15:00Z",
        "device_id": "device_laptop_a",
        "version": 5,
        "updated_at": "2026-03-05T10:15:00Z",
        "last_sync_timestamp": "2026-03-05T09:00:00Z"
    }
    
    cloud_data = {
        "attempt_id": "attempt_001",
        "quiz_id": "quiz_algebra_001",
        "user_id": "student_001",
        "score": 7,
        "total_questions": 10,
        "completed_at": "2026-03-05T10:00:00Z",
        "device_id": "device_laptop_b",
        "version": 4,
        "updated_at": "2026-03-05T10:00:00Z"
    }
    
    print("📱 Device A (Local): Score 9/10 at 10:15 AM")
    print("💻 Device B (Cloud): Score 7/10 at 10:00 AM")
    print("🕐 Last sync: 09:00 AM")
    
    # Detect conflict
    conflict = engine.detect_conflict(
        entity_id="attempt_001",
        entity_type="QuizAttempt",
        local_data=local_data,
        cloud_data=cloud_data
    )
    
    print(f"\n✅ Conflict detected: {conflict.conflict_detected}")
    print(f"📋 Reason: {conflict.reason}")
    print(f"🔢 Versions: Local v{conflict.local_version} vs Cloud v{conflict.cloud_version}")
    print(f"📊 Conflicting fields: {', '.join(conflict.conflicting_fields)}")
    
    # Attempt resolution
    print("\n🔧 Attempting auto-resolution...")
    resolution = engine.resolve_conflict(conflict)
    
    print(f"✅ Strategy: {resolution.strategy}")
    print(f"📝 Reason: {resolution.reason}")
    
    if resolution.resolved_data:
        print(f"🎯 Winner: Score {resolution.resolved_data.get('score')}/10")
        print(f"   (Local had 9, Cloud had 7 → Last-write-wins: {resolution.resolved_data.get('score')})")


# ═══════════════════════════════════════════════════════════════════════
# EXAMPLE 2: TEACHER AUTHORITY RESOLUTION
# ═══════════════════════════════════════════════════════════════════════

def example_2_teacher_authority():
    """
    Example: Teacher edits quiz, student has cached old version.
    """
    print_header("EXAMPLE 2: Teacher Authority Resolution")
    
    engine = ConflictResolutionEngine(base_path=".")
    
    # Scenario: Teacher corrects quiz question
    local_data = {
        "quiz_id": "quiz_001",
        "title": "Algebra Basics",
        "questions": [
            {"id": "q1", "text": "What is 2+2?", "answer": "4"},
            {"id": "q2", "text": "Factorize x^2 + 5x + 6", "answer": "(x+2)(x+3)"},
            {"id": "q3", "text": "Solve for x: 2x = 8", "answer": "x=4"}  # Typo in original
        ],
        "version": 1,
        "updated_at": "2026-03-04T10:00:00Z",
        "updated_by": "system"
    }
    
    cloud_data = {
        "quiz_id": "quiz_001",
        "title": "Algebra Basics",
        "questions": [
            {"id": "q1", "text": "What is 2+2?", "answer": "4"},
            {"id": "q2", "text": "Factorize x^2 + 5x + 6", "answer": "(x+2)(x+3)"},
            {"id": "q3", "text": "Solve for x: 2x = 10", "answer": "x=5"}  # CORRECTED
        ],
        "version": 2,
        "updated_at": "2026-03-05T09:00:00Z",
        "updated_by": "teacher_001"  # Teacher edit
    }
    
    print("📚 Quiz cached locally (version 1)")
    print("👨‍🏫 Teacher corrected question 3 in cloud (version 2)")
    print("🔄 Student syncs and conflict is detected...")
    
    # Detect conflict
    conflict = engine.detect_conflict(
        entity_id="quiz_001",
        entity_type="Quiz",
        local_data=local_data,
        cloud_data=cloud_data
    )
    
    print(f"\n✅ Conflict detected: {conflict.conflict_detected}")
    print(f"📋 Reason: {conflict.reason}")
    
    # Resolve (should apply teacher authority)
    print("\n🔧 Attempting auto-resolution...")
    resolution = engine.resolve_conflict(conflict)
    
    print(f"✅ Strategy: {resolution.strategy}")
    print(f"📝 Reason: {resolution.reason}")
    
    if resolution.strategy == ResolutionStrategy.AUTO_AUTHORITY:
        print(f"👨‍🏫 Teacher authority applied → Cloud version wins")
        print(f"   Question 3: '{local_data['questions'][2]['text']}' → '{cloud_data['questions'][2]['text']}'")
        print(f"   Answer: '{local_data['questions'][2]['answer']}' → '{cloud_data['questions'][2]['answer']}'")


# ═══════════════════════════════════════════════════════════════════════
# EXAMPLE 3: FIELD-LEVEL AUTO-MERGE
# ═══════════════════════════════════════════════════════════════════════

def example_3_auto_merge():
    """
    Example: Non-overlapping fields merge automatically.
    """
    print_header("EXAMPLE 3: Auto-Merge Non-Overlapping Fields")
    
    engine = ConflictResolutionEngine(base_path=".")
    
    # Scenario: Different fields modified on different devices
    local_data = {
        "user_id": "student_001",
        "current_streak": 6,           # Modified locally
        "last_quiz_date": "2026-03-05", # Added locally
        "updated_at": "2026-03-05T10:00:00Z",
        "version": 3
    }
    
    cloud_data = {
        "user_id": "student_001",
        "current_streak": 5,           # Old value
        "total_attempted": 12,         # Added in cloud
        "average_score": 8.2,          # Added in cloud
        "updated_at": "2026-03-05T09:30:00Z",
        "version": 2
    }
    
    print("📱 Local added: last_quiz_date, updated streak")
    print("☁️ Cloud added: total_attempted, average_score")
    print("❓ Conflict: Both modified streak (6 vs 5)")
    
    # Detect
    conflict = engine.detect_conflict(
        entity_id="student_001",
        entity_type="StudentProgress",
        local_data=local_data,
        cloud_data=cloud_data
    )
    
    print(f"\n✅ Conflict detected: {conflict.conflict_detected}")
    
    # Resolve
    print("\n🔧 Attempting field-level merge...")
    resolution = engine.resolve_conflict(conflict)
    
    print(f"✅ Strategy: {resolution.strategy}")
    
    if resolution.resolved_data:
        print("\n📋 Merged data:")
        print(f"   current_streak: {resolution.resolved_data.get('current_streak')} (MAX strategy)")
        print(f"   last_quiz_date: {resolution.resolved_data.get('last_quiz_date')} (from local)")
        print(f"   total_attempted: {resolution.resolved_data.get('total_attempted')} (from cloud)")
        print(f"   average_score: {resolution.resolved_data.get('average_score')} (from cloud)")
        print("\n✨ All fields preserved!")


# ═══════════════════════════════════════════════════════════════════════
# EXAMPLE 4: MANUAL RESOLUTION WORKFLOW
# ═══════════════════════════════════════════════════════════════════════

def example_4_manual_resolution():
    """
    Example: Conflicting score values require user choice.
    """
    print_header("EXAMPLE 4: Manual Resolution Required")
    
    engine = ConflictResolutionEngine(base_path=".")
    
    # Disable last-write-wins to force manual resolution
    engine.config.ENABLE_LAST_WRITE_WINS = False
    
    # Scenario: Same quiz, different scores, same user
    local_data = {
        "attempt_id": "attempt_002",
        "quiz_id": "quiz_physics_001",
        "score": 8,
        "total_questions": 10,
        "version": 5,
        "updated_at": "2026-03-05T10:15:00Z",
        "updated_by": "student_001"
    }
    
    cloud_data = {
        "attempt_id": "attempt_002",
        "quiz_id": "quiz_physics_001",
        "score": 6,
        "total_questions": 10,
        "version": 4,
        "updated_at": "2026-03-05T10:00:00Z",
        "updated_by": "student_001"
    }
    
    print("📱 Local: Score 8/10")
    print("☁️ Cloud: Score 6/10")
    print("⚠️ Both by same student, different scores")
    
    # Detect
    conflict = engine.detect_conflict(
        entity_id="attempt_002",
        entity_type="QuizAttempt",
        local_data=local_data,
        cloud_data=cloud_data
    )
    
    print(f"\n✅ Conflict detected: {conflict.conflict_detected}")
    
    # Attempt resolution
    print("\n🔧 Attempting auto-resolution...")
    resolution = engine.resolve_conflict(conflict)
    
    print(f"⚠️ Strategy: {resolution.strategy}")
    print(f"📝 Reason: {resolution.reason}")
    
    if resolution.strategy == ResolutionStrategy.PENDING:
        print("\n🛑 Manual resolution required!")
        print("   User must choose: Keep Local (8/10) or Keep Cloud (6/10)")
        
        # Save as pending
        engine.save_pending_conflict(conflict)
        
        print("\n💾 Conflict saved to pending_conflicts.json")
        print("   UI will display resolution modal on next app load")
        
        # Simulate user choice
        print("\n👤 User chooses: Keep Local (better score)")
        
        resolved = engine.apply_manual_resolution(conflict, "keep_local")
        
        print(f"✅ Resolved! Final score: {resolved['score']}/10")
        print(f"🔢 Version bumped to: {resolved['version']}")


# ═══════════════════════════════════════════════════════════════════════
# EXAMPLE 5: IDENTICAL EDITS (FALSE CONFLICT)
# ═══════════════════════════════════════════════════════════════════════

def example_5_identical_edits():
    """
    Example: Same edit made on two devices (false conflict).
    """
    print_header("EXAMPLE 5: Identical Edits (False Conflict)")
    
    engine = ConflictResolutionEngine(base_path=".")
    
    # Scenario: Student updates streak to 5 on both devices
    local_data = {
        "user_id": "student_001",
        "current_streak": 5,
        "updated_at": "2026-03-05T10:00:00Z",
        "device_id": "device_laptop_a",
        "version": 3
    }
    
    cloud_data = {
        "user_id": "student_001",
        "current_streak": 5,  # Same value
        "updated_at": "2026-03-05T10:00:00Z",
        "device_id": "device_laptop_b",
        "version": 3
    }
    
    print("📱 Device A: streak = 5")
    print("💻 Device B: streak = 5")
    print("❓ Versions differ in device_id only")
    
    # Check if identical
    is_identical = engine._check_identical_edits(local_data, cloud_data)
    
    print(f"\n✅ Identical edits detected: {is_identical}")
    print("   Conflict is a false positive → No action needed")


# ═══════════════════════════════════════════════════════════════════════
# EXAMPLE 6: LOGGING AND AUDIT TRAIL
# ═══════════════════════════════════════════════════════════════════════

def example_6_logging():
    """
    Example: Logging conflict events for audit trail.
    """
    print_header("EXAMPLE 6: Conflict Logging & Audit Trail")
    
    engine = ConflictResolutionEngine(base_path=".")
    
    # Create conflict
    conflict = ConflictResult(
        conflict_detected=True,
        entity_id="quiz_003",
        entity_type="QuizAttempt",
        reason=ConflictReason.CONCURRENT_EDITS,
        local_version=5,
        cloud_version=4,
        local_updated_at="2026-03-05T10:15:00Z",
        cloud_updated_at="2026-03-05T10:00:00Z",
        local_data={"score": 9},
        cloud_data={"score": 7},
        conflicting_fields=["score"]
    )
    
    # Log detection
    print("📝 Logging conflict detection event...")
    engine.log_conflict_event(conflict)
    
    # Log resolution
    resolved_data = {"score": 9, "version": 6}
    print("📝 Logging conflict resolution event...")
    engine.log_conflict_resolution(
        conflict=conflict,
        strategy=ResolutionStrategy.MANUAL_KEEP_LOCAL,
        resolved_by="user",
        resolved_data=resolved_data
    )
    
    # Read history
    print("\n📜 Conflict history:")
    history = engine.get_conflict_history(limit=10)
    
    for entry in history:
        timestamp = entry.get("timestamp", "")
        event_type = entry.get("event_type", "")
        entity_id = entry.get("entity_id", "")
        
        print(f"   [{format_timestamp(timestamp)}] {event_type}: {entity_id}")
        
        if event_type == "resolution_applied":
            print(f"      → Strategy: {entry.get('resolution_strategy')}")
            print(f"      → Resolved by: {entry.get('resolved_by')}")
    
    print(f"\n✅ Total events logged: {len(history)}")
    print(f"📁 Log file: {engine.conflict_log_path}")


# ═══════════════════════════════════════════════════════════════════════
# EXAMPLE 7: CONFLICT-AWARE ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════

def example_7_orchestrator_integration():
    """
    Example: Using ConflictAwareOrchestrator in sync workflow.
    """
    print_header("EXAMPLE 7: Orchestrator Integration")
    
    # Initialize orchestrator
    orchestrator = ConflictAwareOrchestrator(base_path=".")
    
    print("✅ ConflictAwareOrchestrator initialized")
    print(f"   State: {orchestrator.get_state()}")
    print(f"   Queue: {orchestrator.get_queue_size()} items")
    
    # Enqueue change
    print("\n📝 Enqueuing quiz completion...")
    success = orchestrator.enqueue_change(
        change_type="recordQuizAttempt",
        payload={
            "userId": "student_001",
            "quizId": "quiz_history_001",
            "score": 8,
            "totalQuestions": 10,
            "completedAt": datetime.now(timezone.utc).isoformat()
        },
        priority="high"
    )
    
    print(f"✅ Enqueued: {success}")
    print(f"   State: {orchestrator.get_state()}")
    
    # Check for pending conflicts before syncing
    pending = orchestrator.get_pending_conflicts()
    print(f"\n🔍 Checking for pending conflicts...")
    print(f"   Pending conflicts: {len(pending)}")
    
    if len(pending) == 0:
        print("\n🔄 Executing sync (no conflicts blocking)...")
        result = orchestrator.execute_sync()
        
        print(f"✅ Sync result:")
        print(f"   Synced: {result.get('synced', 0)}")
        print(f"   Failed: {result.get('failed', 0)}")
        print(f"   Conflicts: {result.get('conflicts', 0)}")
    else:
        print("\n🛑 Sync blocked by pending conflicts")
        print("   User must resolve conflicts first")


# ═══════════════════════════════════════════════════════════════════════
# EXAMPLE 8: RECOMMENDATION GENERATION
# ═══════════════════════════════════════════════════════════════════════

def example_8_recommendations():
    """
    Example: Generate user-friendly recommendations.
    """
    print_header("EXAMPLE 8: Conflict Resolution Recommendations")
    
    engine = ConflictResolutionEngine(base_path=".")
    
    # Scenario 1: Better score on local
    print_subheader("Scenario 1: Better Score Locally")
    
    conflict1 = ConflictResult(
        conflict_detected=True,
        entity_id="quiz_001",
        entity_type="QuizAttempt",
        reason=ConflictReason.CONCURRENT_EDITS,
        local_data={"score": 9, "updated_at": "2026-03-05T10:15:00Z"},
        cloud_data={"score": 7, "updated_at": "2026-03-05T10:00:00Z"}
    )
    
    recommendation1 = engine.generate_recommendation(conflict1)
    print(f"💡 {recommendation1}")
    
    # Scenario 2: Teacher edited content
    print_subheader("Scenario 2: Teacher Edit")
    
    conflict2 = ConflictResult(
        conflict_detected=True,
        entity_id="quiz_002",
        entity_type="Quiz",
        reason=ConflictReason.VERSION_MISMATCH,
        local_data={"questions": [], "updated_by": "system"},
        cloud_data={"questions": [], "updated_by": "teacher_001", "updated_at": "2026-03-05T11:00:00Z"}
    )
    
    recommendation2 = engine.generate_recommendation(conflict2)
    print(f"💡 {recommendation2}")
    
    # Scenario 3: Newer timestamp
    print_subheader("Scenario 3: Timestamp-Based")
    
    conflict3 = ConflictResult(
        conflict_detected=True,
        entity_id="quiz_003",
        entity_type="QuizAttempt",
        reason=ConflictReason.TIMESTAMP_DIVERGENCE,
        local_updated_at="2026-03-05T10:15:00Z",
        cloud_updated_at="2026-03-05T10:00:00Z",
        local_data={"score": 8},
        cloud_data={"score": 8}
    )
    
    recommendation3 = engine.generate_recommendation(conflict3)
    print(f"💡 {recommendation3}")


# ═══════════════════════════════════════════════════════════════════════
# EXAMPLE 9: CONFLICT SEVERITY
# ═══════════════════════════════════════════════════════════════════════

def example_9_severity():
    """
    Example: Calculate conflict severity for UI prioritization.
    """
    print_header("EXAMPLE 9: Conflict Severity Levels")
    
    # High severity: Large score difference
    conflict_high = ConflictResult(
        conflict_detected=True,
        entity_id="quiz_001",
        entity_type="QuizAttempt",
        reason=ConflictReason.CONCURRENT_EDITS,
        local_data={"score": 10},
        cloud_data={"score": 5},  # 5-point difference
        conflicting_fields=["score"]
    )
    
    severity_high = get_conflict_severity(conflict_high)
    print(f"Quiz score conflict (10 vs 5): Severity = {severity_high.upper()}")
    
    # Medium severity: Multiple fields
    conflict_medium = ConflictResult(
        conflict_detected=True,
        entity_id="progress_001",
        entity_type="StudentProgress",
        reason=ConflictReason.CONCURRENT_EDITS,
        local_data={},
        cloud_data={},
        conflicting_fields=["streak", "total_attempted", "last_quiz_date"]
    )
    
    severity_medium = get_conflict_severity(conflict_medium)
    print(f"Multiple field conflicts (3 fields): Severity = {severity_medium.upper()}")
    
    # Low severity: Minor conflict
    conflict_low = ConflictResult(
        conflict_detected=True,
        entity_id="pref_001",
        entity_type="UserPreferences",
        reason=ConflictReason.TIMESTAMP_DIVERGENCE,
        local_data={"theme": "dark"},
        cloud_data={"theme": "light"},
        conflicting_fields=["theme"]
    )
    
    severity_low = get_conflict_severity(conflict_low)
    print(f"Preference conflict (theme): Severity = {severity_low.upper()}")


# ═══════════════════════════════════════════════════════════════════════
# EXAMPLE 10: FULL WORKFLOW SIMULATION
# ═══════════════════════════════════════════════════════════════════════

def example_10_full_workflow():
    """
    Example: Complete conflict resolution workflow.
    """
    print_header("EXAMPLE 10: Complete Workflow Simulation")
    
    engine = ConflictResolutionEngine(base_path=".")
    
    # Step 1: Conflict occurs
    print("📱 Step 1: Student completes quiz on Device A (score: 9/10)")
    local_data = {
        "attempt_id": "attempt_final",
        "score": 9,
        "version": 5,
        "updated_at": "2026-03-05T10:15:00Z",
        "last_sync_timestamp": "2026-03-05T09:00:00Z"
    }
    
    print("☁️ Step 2: Cloud has older attempt from Device B (score: 7/10)")
    cloud_data = {
        "attempt_id": "attempt_final",
        "score": 7,
        "version": 4,
        "updated_at": "2026-03-05T10:00:00Z"
    }
    
    # Step 2: Detect
    print("\n🔍 Step 3: Sync triggered, detecting conflicts...")
    conflict = engine.detect_conflict(
        entity_id="attempt_final",
        entity_type="QuizAttempt",
        local_data=local_data,
        cloud_data=cloud_data
    )
    
    if conflict.conflict_detected:
        print(f"⚠️ Conflict detected!")
        print(f"   Reason: {conflict.reason}")
        print(f"   Versions: {conflict.local_version} vs {conflict.cloud_version}")
        
        # Step 3: Log
        print("\n📝 Step 4: Logging conflict event...")
        engine.log_conflict_event(conflict)
        
        # Step 4: Attempt resolution
        print("\n🔧 Step 5: Attempting auto-resolution...")
        resolution = engine.resolve_conflict(conflict)
        
        print(f"✅ Resolution strategy: {resolution.strategy}")
        
        if resolution.strategy != ResolutionStrategy.PENDING:
            # Auto-resolved
            print(f"🎯 Auto-resolved! Winner: Score {resolution.resolved_data['score']}/10")
            
            # Log resolution
            print("\n📝 Step 6: Logging resolution...")
            engine.log_conflict_resolution(
                conflict=conflict,
                strategy=resolution.strategy,
                resolved_by="system",
                resolved_data=resolution.resolved_data
            )
            
            print("\n✅ Workflow complete!")
            print("   Conflict detected → Auto-resolved → Logged → Ready to sync")
        
        else:
            # Manual required
            print(f"🛑 Manual resolution required")
            print("\n📝 Step 6: Saving as pending conflict...")
            engine.save_pending_conflict(conflict)
            
            pending = engine.get_pending_conflicts()
            print(f"✅ Saved! Pending conflicts: {len(pending)}")
            
            # Generate recommendation
            print("\n💡 Step 7: Generating recommendation...")
            recommendation = engine.generate_recommendation(conflict)
            print(f"   {recommendation}")
            
            print("\n👤 Step 8: Waiting for user input...")
            print("   (User will see modal in Streamlit UI)")


# ═══════════════════════════════════════════════════════════════════════
# RUN ALL EXAMPLES
# ═══════════════════════════════════════════════════════════════════════

def main():
    """Run all examples."""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║       STUDAXIS CONFLICT RESOLUTION ENGINE — EXAMPLES                  ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    
    try:
        example_1_detect_concurrent_edits()
        time.sleep(1)
        
        example_2_teacher_authority()
        time.sleep(1)
        
        example_3_auto_merge()
        time.sleep(1)
        
        example_4_manual_resolution()
        time.sleep(1)
        
        example_5_identical_edits()
        time.sleep(1)
        
        example_6_logging()
        time.sleep(1)
        
        example_7_orchestrator_integration()
        time.sleep(1)
        
        example_8_recommendations()
        time.sleep(1)
        
        example_9_severity()
        time.sleep(1)
        
        example_10_full_workflow()
        
        print("\n" + "=" * 70)
        print("  ✅ ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 70 + "\n")
        
        print("📚 Next Steps:")
        print("   1. Run unit tests: python tests/test_conflict_resolution.py")
        print("   2. Integrate into Streamlit: see CONFLICT_RESOLUTION_INTEGRATION.md")
        print("   3. Test UI: Add simulate conflict button to app")
        print("\n")
    
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
