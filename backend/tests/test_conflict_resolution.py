"""
Unit Tests — Conflict Resolution Engine
═══════════════════════════════════════════════════════════════
Comprehensive test suite for conflict detection, resolution, and UI.

Test Coverage:
  - Conflict detection (all patterns)
  - Auto-resolution strategies
  - Manual resolution flow
  - State machine transitions
  - Field-level merging
  - Edge cases (clock drift, race conditions)

Run with: python tests/test_conflict_resolution.py
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

# Import module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from conflict_resolution_engine import (
    ConflictResolutionEngine,
    ConflictAwareOrchestrator,
    ConflictResult,
    ResolutionResult,
    ConflictReason,
    ResolutionStrategy,
    ConflictConfig
)


class TestConflictDetection(unittest.TestCase):
    """Test conflict detection logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.engine = ConflictResolutionEngine(base_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up test files."""
        shutil.rmtree(self.temp_dir)
    
    
    def test_no_conflict_when_no_cloud_data(self):
        """Test that no conflict detected when cloud data doesn't exist."""
        local_data = {"id": "quiz_001", "score": 9, "version": 1}
        
        conflict = self.engine.detect_conflict(
            entity_id="quiz_001",
            entity_type="QuizAttempt",
            local_data=local_data,
            cloud_data=None
        )
        
        self.assertFalse(conflict.conflict_detected)
        self.assertEqual(conflict.reason, ConflictReason.NO_CONFLICT)
    
    
    def test_concurrent_edits_detected(self):
        """Test detection of concurrent edits (both modified since last sync)."""
        last_sync = "2026-03-05T09:00:00Z"
        
        local_data = {
            "id": "quiz_001",
            "score": 9,
            "version": 5,
            "updated_at": "2026-03-05T10:15:00Z",
            "last_sync_timestamp": last_sync
        }
        
        cloud_data = {
            "id": "quiz_001",
            "score": 7,
            "version": 4,
            "updated_at": "2026-03-05T10:00:00Z"
        }
        
        conflict = self.engine.detect_conflict(
            entity_id="quiz_001",
            entity_type="QuizAttempt",
            local_data=local_data,
            cloud_data=cloud_data
        )
        
        self.assertTrue(conflict.conflict_detected)
        self.assertEqual(conflict.reason, ConflictReason.CONCURRENT_EDITS)
        self.assertEqual(conflict.local_version, 5)
        self.assertEqual(conflict.cloud_version, 4)
        self.assertIn("score", conflict.conflicting_fields)
    
    
    def test_timestamp_divergence_detected(self):
        """Test detection of large timestamp differences (clock skew)."""
        local_data = {
            "id": "quiz_001",
            "version": 5,
            "updated_at": "2026-03-05T10:00:00Z",
            "last_sync_timestamp": "2026-03-05T08:00:00Z"
        }
        
        cloud_data = {
            "id": "quiz_001",
            "version": 5,
            "updated_at": "2026-03-05T09:00:00Z"  # 1 hour behind
        }
        
        conflict = self.engine.detect_conflict(
            entity_id="quiz_001",
            entity_type="QuizAttempt",
            local_data=local_data,
            cloud_data=cloud_data
        )
        
        self.assertTrue(conflict.conflict_detected)
        self.assertEqual(conflict.reason, ConflictReason.TIMESTAMP_DIVERGENCE)
    
    
    def test_no_conflict_when_versions_match(self):
        """Test no conflict when versions and timestamps are compatible."""
        local_data = {
            "id": "quiz_001",
            "score": 9,
            "version": 5,
            "updated_at": "2026-03-05T10:00:00Z",
            "last_sync_timestamp": "2026-03-05T09:00:00Z"
        }
        
        cloud_data = {
            "id": "quiz_001",
            "score": 9,
            "version": 5,
            "updated_at": "2026-03-05T10:00:00Z"
        }
        
        conflict = self.engine.detect_conflict(
            entity_id="quiz_001",
            entity_type="QuizAttempt",
            local_data=local_data,
            cloud_data=cloud_data
        )
        
        self.assertFalse(conflict.conflict_detected)
    
    
    def test_clock_drift_tolerance(self):
        """Test that minor clock differences don't trigger conflicts."""
        local_data = {
            "id": "quiz_001",
            "version": 5,
            "updated_at": "2026-03-05T10:00:02Z",  # 2 seconds ahead
            "last_sync_timestamp": "2026-03-05T09:00:00Z"
        }
        
        cloud_data = {
            "id": "quiz_001",
            "version": 5,
            "updated_at": "2026-03-05T10:00:00Z"
        }
        
        conflict = self.engine.detect_conflict(
            entity_id="quiz_001",
            entity_type="QuizAttempt",
            local_data=local_data,
            cloud_data=cloud_data
        )
        
        # Should not conflict due to 5-second tolerance
        self.assertFalse(conflict.conflict_detected)


class TestAutoResolution(unittest.TestCase):
    """Test automatic conflict resolution strategies."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.engine = ConflictResolutionEngine(base_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up test files."""
        shutil.rmtree(self.temp_dir)
    
    
    def test_identical_edits_ignored(self):
        """Test that identical edits don't create conflicts."""
        local_data = {
            "id": "quiz_001",
            "score": 9,
            "version": 5,
            "updated_at": "2026-03-05T10:00:00Z",
            "device_id": "device_a"
        }
        
        cloud_data = {
            "id": "quiz_001",
            "score": 9,
            "version": 5,
            "updated_at": "2026-03-05T10:00:00Z",
            "device_id": "device_b"  # Different device but same data
        }
        
        # Should recognize as identical
        is_identical = self.engine._check_identical_edits(local_data, cloud_data)
        self.assertTrue(is_identical)
    
    
    def test_teacher_authority_for_content(self):
        """Test that teacher edits to content take priority."""
        local_data = {
            "quiz_id": "quiz_001",
            "questions": [{"q": "Old question"}],
            "updated_by": "student_001",
            "updated_at": "2026-03-05T11:00:00Z"
        }
        
        cloud_data = {
            "quiz_id": "quiz_001",
            "questions": [{"q": "Corrected question"}],
            "updated_by": "teacher_001",
            "updated_at": "2026-03-05T10:00:00Z"  # Earlier but teacher
        }
        
        conflict = ConflictResult(
            conflict_detected=True,
            entity_id="quiz_001",
            entity_type="Quiz",
            reason=ConflictReason.CONCURRENT_EDITS,
            local_data=local_data,
            cloud_data=cloud_data
        )
        
        # Should apply teacher authority
        resolved = self.engine._apply_authority_resolution(conflict)
        
        self.assertEqual(resolved, cloud_data)
        self.assertEqual(resolved["questions"][0]["q"], "Corrected question")
    
    
    def test_student_authority_for_progress(self):
        """Test that student edits to progress take priority."""
        local_data = {
            "attempt_id": "attempt_001",
            "score": 9,
            "updated_by": "student_001",
            "updated_at": "2026-03-05T10:00:00Z"
        }
        
        cloud_data = {
            "attempt_id": "attempt_001",
            "score": 7,
            "updated_by": "student_001",
            "updated_at": "2026-03-05T09:00:00Z"
        }
        
        conflict = ConflictResult(
            conflict_detected=True,
            entity_id="attempt_001",
            entity_type="QuizAttempt",
            reason=ConflictReason.CONCURRENT_EDITS,
            local_data=local_data,
            cloud_data=cloud_data
        )
        
        # Should apply student authority
        resolved = self.engine._apply_authority_resolution(conflict)
        
        self.assertEqual(resolved, local_data)
        self.assertEqual(resolved["score"], 9)
    
    
    def test_non_overlapping_field_merge(self):
        """Test merging of non-overlapping fields."""
        local_data = {
            "user_id": "student_001",
            "streak": 6,
            "last_quiz_date": "2026-03-05",
            "updated_at": "2026-03-05T10:00:00Z"
        }
        
        cloud_data = {
            "user_id": "student_001",
            "streak": 5,
            "total_attempted": 12,
            "updated_at": "2026-03-05T09:00:00Z"
        }
        
        merged = self.engine._auto_merge_non_overlapping(local_data, cloud_data)
        
        # Should have all unique fields
        self.assertIn("last_quiz_date", merged)  # From local
        self.assertIn("total_attempted", merged)  # From cloud
        self.assertIn("streak", merged)          # Resolved
    
    
    def test_last_write_wins_by_timestamp(self):
        """Test last-write-wins resolution strategy."""
        local_data = {
            "id": "quiz_001",
            "score": 9,
            "version": 5,
            "updated_at": "2026-03-05T10:15:00Z"  # Newer
        }
        
        cloud_data = {
            "id": "quiz_001",
            "score": 7,
            "version": 4,
            "updated_at": "2026-03-05T10:00:00Z"  # Older
        }
        
        resolved = self.engine._resolve_by_timestamp(local_data, cloud_data)
        
        # Local should win (newer timestamp)
        self.assertEqual(resolved, local_data)
        self.assertEqual(resolved["score"], 9)
    
    
    def test_max_merge_strategy_for_counters(self):
        """Test MAX merge strategy for numeric counters."""
        local_data = {"current_streak": 6}
        cloud_data = {"current_streak": 5}
        
        # Resolve field using MAX strategy
        resolved_val = self.engine._resolve_field_conflict(
            "current_streak",
            local_data["current_streak"],
            cloud_data["current_streak"],
            local_data,
            cloud_data
        )
        
        # Should use maximum value
        self.assertEqual(resolved_val, 6)


class TestManualResolution(unittest.TestCase):
    """Test manual conflict resolution flow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.engine = ConflictResolutionEngine(base_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up test files."""
        shutil.rmtree(self.temp_dir)
    
    
    def test_save_and_load_pending_conflict(self):
        """Test saving and retrieving pending conflicts."""
        conflict = ConflictResult(
            conflict_detected=True,
            entity_id="quiz_001",
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
        
        # Save
        self.engine.save_pending_conflict(conflict)
        
        # Load
        pending = self.engine.get_pending_conflicts()
        
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["entity_id"], "quiz_001")
        self.assertEqual(pending[0]["entity_type"], "QuizAttempt")
    
    
    def test_remove_pending_conflict(self):
        """Test removing conflict after resolution."""
        conflict = ConflictResult(
            conflict_detected=True,
            entity_id="quiz_001",
            entity_type="QuizAttempt",
            reason=ConflictReason.CONCURRENT_EDITS,
            local_data={"score": 9},
            cloud_data={"score": 7}
        )
        
        # Save
        self.engine.save_pending_conflict(conflict)
        self.assertEqual(len(self.engine.get_pending_conflicts()), 1)
        
        # Remove
        self.engine.remove_pending_conflict("quiz_001")
        self.assertEqual(len(self.engine.get_pending_conflicts()), 0)
    
    
    def test_apply_manual_keep_local(self):
        """Test applying user choice: keep local."""
        conflict = ConflictResult(
            conflict_detected=True,
            entity_id="quiz_001",
            entity_type="QuizAttempt",
            reason=ConflictReason.CONCURRENT_EDITS,
            local_version=5,
            cloud_version=4,
            local_data={"score": 9, "version": 5, "updated_at": "2026-03-05T10:15:00Z"},
            cloud_data={"score": 7, "version": 4, "updated_at": "2026-03-05T10:00:00Z"}
        )
        
        self.engine.save_pending_conflict(conflict)
        
        # User chooses "keep_local"
        resolved = self.engine.apply_manual_resolution(conflict, "keep_local")
        
        # Should use local data
        self.assertEqual(resolved["score"], 9)
        
        # Version should be incremented
        self.assertEqual(resolved["version"], 6)  # max(5,4) + 1
        
        # Conflict should be removed from pending
        self.assertEqual(len(self.engine.get_pending_conflicts()), 0)
    
    
    def test_apply_manual_keep_cloud(self):
        """Test applying user choice: keep cloud."""
        conflict = ConflictResult(
            conflict_detected=True,
            entity_id="quiz_001",
            entity_type="QuizAttempt",
            reason=ConflictReason.CONCURRENT_EDITS,
            local_version=5,
            cloud_version=4,
            local_data={"score": 9, "version": 5, "updated_at": "2026-03-05T10:15:00Z"},
            cloud_data={"score": 7, "version": 4, "updated_at": "2026-03-05T10:00:00Z"}
        )
        
        # User chooses "keep_cloud"
        resolved = self.engine.apply_manual_resolution(conflict, "keep_cloud")
        
        # Should use cloud data
        self.assertEqual(resolved["score"], 7)


class TestAutoMergeLogic(unittest.TestCase):
    """Test automatic merge strategies."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.engine = ConflictResolutionEngine(base_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up test files."""
        shutil.rmtree(self.temp_dir)
    
    
    def test_merge_non_overlapping_fields(self):
        """Test merging fields that don't overlap."""
        local_data = {
            "user_id": "student_001",
            "streak": 6,
            "last_quiz_date": "2026-03-05"
        }
        
        cloud_data = {
            "user_id": "student_001",
            "streak": 5,
            "total_attempted": 12
        }
        
        merged = self.engine._auto_merge_non_overlapping(local_data, cloud_data)
        
        # Should contain all unique fields
        self.assertEqual(merged["user_id"], "student_001")
        self.assertIn("last_quiz_date", merged)
        self.assertIn("total_attempted", merged)
        self.assertIn("streak", merged)
    
    
    def test_max_strategy_for_counters(self):
        """Test MAX merge strategy for numeric counters."""
        local_data = {"current_streak": 6, "updated_at": "2026-03-05T10:00:00Z"}
        cloud_data = {"current_streak": 5, "updated_at": "2026-03-05T09:00:00Z"}
        
        # Resolve using field-level conflict resolution
        merged = self.engine._auto_merge_non_overlapping(local_data, cloud_data)
        
        # current_streak should use MAX strategy (defined in config)
        self.assertEqual(merged["current_streak"], 6)
    
    
    def test_array_merge_deduplication(self):
        """Test array merging with deduplication."""
        local_array = [
            {"id": "msg1", "text": "Hello"},
            {"id": "msg2", "text": "World"}
        ]
        
        cloud_array = [
            {"id": "msg1", "text": "Hello"},
            {"id": "msg3", "text": "!"}
        ]
        
        merged = self.engine._merge_arrays(local_array, cloud_array, unique_key="id")
        
        # Should have 3 unique messages
        self.assertEqual(len(merged), 3)
        
        # Check IDs
        ids = [item["id"] for item in merged]
        self.assertIn("msg1", ids)
        self.assertIn("msg2", ids)
        self.assertIn("msg3", ids)
    
    
    def test_nested_object_merge(self):
        """Test merging nested objects recursively."""
        local_data = {
            "quiz_stats": {
                "total_attempted": 10,
                "by_topic": {"algebra": {"score": 8}}
            }
        }
        
        cloud_data = {
            "quiz_stats": {
                "total_attempted": 12,
                "by_topic": {"geometry": {"score": 7}}
            }
        }
        
        merged = self.engine._auto_merge_non_overlapping(local_data, cloud_data)
        
        # Should merge nested structures
        self.assertIn("quiz_stats", merged)
        self.assertIn("by_topic", merged["quiz_stats"])
        self.assertIn("algebra", merged["quiz_stats"]["by_topic"])
        self.assertIn("geometry", merged["quiz_stats"]["by_topic"])


class TestConflictResolutionWorkflow(unittest.TestCase):
    """Test full conflict resolution workflows."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        config = ConflictConfig()
        config.ENABLE_TEACHER_AUTHORITY = False  # Let auto-merge run for non-authority tests
        self.engine = ConflictResolutionEngine(base_path=self.temp_dir, config=config)
    
    def tearDown(self):
        """Clean up test files."""
        shutil.rmtree(self.temp_dir)
    
    
    def test_hybrid_resolution_auto_success(self):
        """Test hybrid resolution with successful auto-merge."""
        conflict = ConflictResult(
            conflict_detected=True,
            entity_id="quiz_001",
            entity_type="QuizAttempt",
            reason=ConflictReason.CONCURRENT_EDITS,
            local_data={
                "id": "quiz_001",
                "score": 9,
                "new_field": "local_only",
                "updated_at": "2026-03-05T10:15:00Z"
            },
            cloud_data={
                "id": "quiz_001",
                "score": 9,
                "cloud_field": "cloud_only",
                "updated_at": "2026-03-05T10:00:00Z"
            },
            conflicting_fields=["new_field", "cloud_field"],  # Both mergeable (one None each side)
        )
        
        # Resolve
        resolution = self.engine.resolve_conflict(conflict)
        
        # Should auto-resolve (non-overlapping fields)
        self.assertEqual(resolution.strategy, ResolutionStrategy.AUTO_MERGE)
        self.assertIsNotNone(resolution.resolved_data)
        self.assertIn("new_field", resolution.resolved_data)
        self.assertIn("cloud_field", resolution.resolved_data)
    
    
    def test_hybrid_resolution_manual_required(self):
        """Test hybrid resolution falling back to manual."""
        conflict = ConflictResult(
            conflict_detected=True,
            entity_id="quiz_001",
            entity_type="QuizAttempt",
            reason=ConflictReason.CONCURRENT_EDITS,
            local_version=5,
            cloud_version=4,
            local_data={
                "id": "quiz_001",
                "score": 9,
                "updated_at": "2026-03-05T10:15:00Z",
                "updated_by": "student_001"
            },
            cloud_data={
                "id": "quiz_001",
                "score": 7,
                "updated_at": "2026-03-05T10:00:00Z",
                "updated_by": "student_001"
            }
        )
        
        # Disable authority and last-write-wins to force manual resolution
        self.engine.config.ENABLE_TEACHER_AUTHORITY = False
        self.engine.config.ENABLE_LAST_WRITE_WINS = False
        
        # Resolve
        resolution = self.engine.resolve_conflict(conflict)
        
        # Should require manual resolution
        self.assertEqual(resolution.strategy, ResolutionStrategy.PENDING)
        self.assertIsNone(resolution.resolved_data)


class TestLoggingAndAudit(unittest.TestCase):
    """Test conflict logging and audit trail."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.engine = ConflictResolutionEngine(base_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up test files."""
        shutil.rmtree(self.temp_dir)
    
    
    def test_log_conflict_event(self):
        """Test logging conflict detection event."""
        conflict = ConflictResult(
            conflict_detected=True,
            entity_id="quiz_001",
            entity_type="QuizAttempt",
            reason=ConflictReason.CONCURRENT_EDITS,
            local_version=5,
            cloud_version=4,
            local_data={"score": 9},
            cloud_data={"score": 7}
        )
        
        # Log
        self.engine.log_conflict_event(conflict)
        
        # Verify log file exists
        self.assertTrue(self.engine.conflict_log_path.exists())
        
        # Read log
        history = self.engine.get_conflict_history()
        
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["event_type"], "conflict_detected")
        self.assertEqual(history[0]["entity_id"], "quiz_001")
    
    
    def test_log_conflict_resolution(self):
        """Test logging conflict resolution event."""
        conflict = ConflictResult(
            conflict_detected=True,
            entity_id="quiz_001",
            entity_type="QuizAttempt",
            reason=ConflictReason.CONCURRENT_EDITS,
            local_data={"score": 9},
            cloud_data={"score": 7}
        )
        
        resolved_data = {"score": 9, "version": 6}
        
        # Log resolution
        self.engine.log_conflict_resolution(
            conflict=conflict,
            strategy=ResolutionStrategy.MANUAL_KEEP_LOCAL,
            resolved_by="user",
            resolved_data=resolved_data
        )
        
        # Read log
        history = self.engine.get_conflict_history()
        
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["event_type"], "resolution_applied")
        self.assertEqual(history[0]["resolution_strategy"], "manual_keep_local")
        self.assertEqual(history[0]["resolved_by"], "user")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.engine = ConflictResolutionEngine(base_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up test files."""
        shutil.rmtree(self.temp_dir)
    
    
    def test_missing_timestamps_handled(self):
        """Test handling of missing timestamp fields."""
        local_data = {"id": "quiz_001", "score": 9, "version": 5}
        cloud_data = {"id": "quiz_001", "score": 7, "version": 4}
        
        # Should not crash, should use version comparison
        resolved = self.engine._resolve_by_timestamp(local_data, cloud_data)
        
        # Should use version number as fallback
        self.assertEqual(resolved["version"], 5)
    
    
    def test_malformed_timestamp_handled(self):
        """Test handling of malformed timestamp strings - engine does not crash."""
        local_data = {
            "id": "quiz_001",
            "version": 5,
            "updated_at": "invalid-timestamp"
        }
        
        cloud_data = {
            "id": "quiz_001",
            "version": 4,
            "updated_at": "2026-03-05T10:00:00Z"
        }
        
        # Should not crash - graceful degradation when timestamps can't be parsed
        conflict = self.engine.detect_conflict(
            entity_id="quiz_001",
            entity_type="QuizAttempt",
            local_data=local_data,
            cloud_data=cloud_data
        )
        
        # Returns valid ConflictResult; when timestamps are malformed, _is_concurrent_edit
        # returns False (can't reliably compare), so conflict may not be detected
        self.assertIsInstance(conflict.conflict_detected, bool)
        self.assertEqual(conflict.entity_id, "quiz_001")
    
    
    def test_empty_conflicting_fields_list(self):
        """Test handling when no specific fields conflict."""
        local_data = {"id": "quiz_001", "version": 5, "updated_at": "2026-03-05T10:15:00Z"}
        cloud_data = {"id": "quiz_001", "version": 4, "updated_at": "2026-03-05T10:00:00Z"}
        
        conflicting_fields = self.engine._find_conflicting_fields(local_data, cloud_data)
        
        # Should return empty list (only metadata differs)
        self.assertEqual(len(conflicting_fields), 0)


class TestConflictAwareOrchestrator(unittest.TestCase):
    """Test ConflictAwareOrchestrator integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create required data directory
        (Path(self.temp_dir) / "data").mkdir(exist_ok=True)
        
        # Create mock device_id.json
        device_id_data = {
            "device_id": "test_device_001",
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        with open(Path(self.temp_dir) / "data" / "device_id.json", "w") as f:
            json.dump(device_id_data, f)
    
    def tearDown(self):
        """Clean up test files."""
        shutil.rmtree(self.temp_dir)
    
    
    def test_orchestrator_blocks_sync_on_conflict(self):
        """Test that pending conflicts block sync when configured."""
        orchestrator = ConflictAwareOrchestrator(base_path=self.temp_dir)
        
        # Create pending conflict
        conflict = ConflictResult(
            conflict_detected=True,
            entity_id="quiz_001",
            entity_type="QuizAttempt",
            reason=ConflictReason.CONCURRENT_EDITS,
            local_data={"score": 9},
            cloud_data={"score": 7}
        )
        
        orchestrator.conflict_engine.save_pending_conflict(conflict)
        
        # Attempt sync
        result = orchestrator.execute_sync()
        
        # Should be blocked
        self.assertEqual(result["synced"], 0)
        self.assertEqual(result["conflicts"], 1)
        self.assertIn("Conflicts must be resolved", result["errors"][0])
    
    
    def test_get_pending_conflicts(self):
        """Test retrieving pending conflicts from orchestrator."""
        orchestrator = ConflictAwareOrchestrator(base_path=self.temp_dir)
        
        # Create conflict
        conflict = ConflictResult(
            conflict_detected=True,
            entity_id="quiz_001",
            entity_type="QuizAttempt",
            reason=ConflictReason.CONCURRENT_EDITS,
            local_data={"score": 9},
            cloud_data={"score": 7}
        )
        
        orchestrator.conflict_engine.save_pending_conflict(conflict)
        
        # Get conflicts
        pending = orchestrator.get_pending_conflicts()
        
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["entity_id"], "quiz_001")


class TestRecommendationGeneration(unittest.TestCase):
    """Test conflict resolution recommendations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.engine = ConflictResolutionEngine(base_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up test files."""
        shutil.rmtree(self.temp_dir)
    
    
    def test_recommend_better_score(self):
        """Test recommendation for better score."""
        conflict = ConflictResult(
            conflict_detected=True,
            entity_id="quiz_001",
            entity_type="QuizAttempt",
            reason=ConflictReason.CONCURRENT_EDITS,
            local_data={"score": 9},
            cloud_data={"score": 7}
        )
        
        recommendation = self.engine.generate_recommendation(conflict)
        
        self.assertIn("Keep Local", recommendation)
        self.assertIn("better score", recommendation)
    
    
    def test_recommend_teacher_authority(self):
        """Test recommendation for teacher edits."""
        conflict = ConflictResult(
            conflict_detected=True,
            entity_id="quiz_001",
            entity_type="Quiz",
            reason=ConflictReason.CONCURRENT_EDITS,
            local_data={"questions": []},
            cloud_data={"questions": [], "updated_by": "teacher_001"}
        )
        
        recommendation = self.engine.generate_recommendation(conflict)
        
        self.assertIn("Keep Cloud", recommendation)
        self.assertIn("teacher", recommendation)
    
    
    def test_recommend_newer_timestamp(self):
        """Test recommendation based on timestamp."""
        conflict = ConflictResult(
            conflict_detected=True,
            entity_id="quiz_001",
            entity_type="QuizAttempt",
            reason=ConflictReason.TIMESTAMP_DIVERGENCE,
            local_updated_at="2026-03-05T10:15:00Z",
            cloud_updated_at="2026-03-05T10:00:00Z",
            local_data={"score": 8},
            cloud_data={"score": 8}
        )
        
        recommendation = self.engine.generate_recommendation(conflict)
        
        self.assertIn("Keep Local", recommendation)
        self.assertIn("more recent", recommendation)


class TestConflictTypes(unittest.TestCase):
    """Test different conflict type scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.engine = ConflictResolutionEngine(base_path=self.temp_dir)
    
    def tearDown(self):
        """Clean up test files."""
        shutil.rmtree(self.temp_dir)
    
    
    def test_student_vs_student_multi_device(self):
        """Test conflict between same student's two devices."""
        local_data = {
            "attempt_id": "attempt_001",
            "score": 9,
            "device_id": "device_laptop_a",
            "updated_at": "2026-03-05T10:15:00Z",
            "version": 5
        }
        
        cloud_data = {
            "attempt_id": "attempt_001",
            "score": 7,
            "device_id": "device_laptop_b",
            "updated_at": "2026-03-05T10:00:00Z",
            "version": 4
        }
        
        conflict = self.engine.detect_conflict(
            entity_id="attempt_001",
            entity_type="QuizAttempt",
            local_data=local_data,
            cloud_data=cloud_data
        )
        
        # Should detect multi-device conflict
        self.assertTrue(conflict.conflict_detected)
        self.assertNotEqual(local_data["device_id"], cloud_data["device_id"])
    
    
    def test_student_vs_teacher_content_edit(self):
        """Test conflict when teacher edits content student has cached."""
        local_data = {
            "quiz_id": "quiz_001",
            "questions": [{"q": "Old"}],
            "version": 1,
            "updated_by": "system",
            "updated_at": "2026-03-05T09:00:00Z"
        }
        
        cloud_data = {
            "quiz_id": "quiz_001",
            "questions": [{"q": "Corrected"}],
            "version": 2,
            "updated_by": "teacher_001",
            "updated_at": "2026-03-05T10:00:00Z"
        }
        
        conflict = ConflictResult(
            conflict_detected=True,
            entity_id="quiz_001",
            entity_type="Quiz",
            reason=ConflictReason.VERSION_MISMATCH,
            local_data=local_data,
            cloud_data=cloud_data
        )
        
        # Should apply teacher authority
        resolved = self.engine._apply_authority_resolution(conflict)
        
        self.assertEqual(resolved["questions"][0]["q"], "Corrected")


# ═══════════════════════════════════════════════════════════════════════
# TEST RUNNER
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Run all tests
    unittest.main(verbosity=2)
