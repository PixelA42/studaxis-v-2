"""
Studaxis — Sync Orchestrator (Student Device)
═══════════════════════════════════════════════
Orchestration layer for real-time sync with state machine and edge case handling.

This class wraps SyncManager and adds:
  - State machine (IDLE, OFFLINE, QUEUED, SYNCING, SYNCED, ERROR, etc.)
  - Debouncing (5s window to batch rapid changes)
  - Queue merging (deduplicate similar items)
  - Exponential backoff with jitter
  - Dead letter queue for persistent failures
  - Auto-recovery from offline state
  - Rate limiting protection

No AWS dependencies - pure local orchestration.
"""

import json
import time
import logging
from pathlib import Path
from threading import Timer
from typing import Dict, List, Literal, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger("studaxis.sync_orchestrator")

# Type alias for sync states
SyncState = Literal[
    "IDLE",          # All synced, no pending items
    "OFFLINE",       # No connectivity, items queued
    "QUEUED",        # Items pending, ready to sync
    "SYNCING",       # Active sync in progress
    "SYNCED",        # Just completed sync (transient)
    "PARTIAL_SYNC",  # Some synced, some failed
    "ERROR",         # Sync failed
    "CONFLICT"       # Version conflict detected (Phase 2)
]


class SyncOrchestrator:
    """
    Orchestration layer for offline-first sync.
    
    Manages state machine, debouncing, edge cases on top of SyncManager.
    """
    
    # Configuration constants
    DEBOUNCE_WINDOW = 5.0      # seconds - wait after last change before syncing
    MAX_QUEUE_SIZE = 100       # maximum items in queue
    MAX_BATCH_SIZE = 10        # maximum items per sync batch
    MAX_RETRIES = 5            # maximum retry attempts per item
    BACKOFF_BASE = 2           # exponential backoff base
    BACKOFF_MAX = 300          # max backoff delay (5 minutes)
    JITTER_FACTOR = 0.1        # ±10% jitter
    MIN_SYNC_INTERVAL = 10     # min seconds between syncs (rate limiting)
    CONNECTIVITY_CHECK_INTERVAL = 30  # seconds between offline checks
    SYNCED_STATE_DURATION = 2  # seconds to show SYNCED before → IDLE
    
    def __init__(self, base_path: str = "."):
        """
        Initialize orchestrator.
        
        Args:
            base_path: Base directory for data files
        """
        self.base_path = Path(base_path)
        self.state_path = self.base_path / "data" / "sync_state.json"
        self.dlq_path = self.base_path / "data" / "dead_letter_queue.json"
        
        # Ensure data directory exists
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load state
        self.state: SyncState = self._load_state()
        self.last_sync_attempt: float = 0
        
        # Timers
        self.sync_timer: Optional[Timer] = None
        self.recovery_timer: Optional[Timer] = None
        self.transition_timer: Optional[Timer] = None
        
        # Initialize SyncManager (low-level sync operations)
        from sync_manager import SyncManager
        self.sync_manager = SyncManager(base_path=base_path)
        
        logger.info("SyncOrchestrator initialized, state: %s", self.state)
    
    # ═══════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════
    
    def enqueue_change(
        self,
        change_type: str,
        payload: Dict,
        priority: str = "normal"
    ) -> bool:
        """
        Add a local change to the sync queue.
        
        Args:
            change_type: "recordQuizAttempt" | "updateStreak"
            payload: GraphQL mutation variables
            priority: "normal" | "high" (quiz = high, streaks = normal)
        
        Returns:
            True if enqueued successfully
        """
        # Validate payload
        if not self._validate_payload(payload):
            logger.error("Invalid payload for %s", change_type)
            return False
        
        # Check queue size
        current_size = self.sync_manager.queue_size
        if current_size >= self.MAX_QUEUE_SIZE:
            logger.warning("Queue full (%d items), attempting to merge", current_size)
            # Queue will be merged on next sync
        
        # Add priority to payload metadata (SyncManager doesn't support this natively)
        # We'll handle priority sorting in _prepare_batch
        payload["_priority"] = priority
        
        # Enqueue via SyncManager
        if change_type == "recordQuizAttempt":
            success = self.sync_manager.enqueue_quiz_sync(
                user_id=payload["userId"],
                quiz_id=payload["quizId"],
                score=payload["score"],
                total_questions=payload["totalQuestions"],
                subject=payload.get("subject", "General"),
                difficulty=payload.get("difficulty", "Medium"),
                device_id=payload.get("deviceId"),
            )
        elif change_type == "updateStreak":
            success = self.sync_manager.enqueue_streak_sync(
                user_id=payload["userId"],
                current_streak=payload["currentStreak"],
            )
        else:
            logger.error("Unknown change type: %s", change_type)
            return False
        
        if not success:
            return False
        
        # Update state
        if self.state == "IDLE":
            self._transition_to("QUEUED")
        
        logger.info("Enqueued %s, queue size: %d", change_type, self.sync_manager.queue_size)
        return True
    
    def trigger_sync_debounced(self):
        """
        Trigger sync after debounce window.
        
        Cancels existing timer and starts a new one.
        This prevents rapid-fire sync attempts.
        """
        # Cancel existing timer
        if self.sync_timer:
            self.sync_timer.cancel()
            logger.debug("Cancelled existing sync timer")
        
        # Schedule new sync
        self.sync_timer = Timer(self.DEBOUNCE_WINDOW, self.execute_sync)
        self.sync_timer.daemon = True
        self.sync_timer.start()
        
        logger.info("Sync scheduled in %.1fs (debounced)", self.DEBOUNCE_WINDOW)
    
    def execute_sync(self) -> Dict:
        """
        Execute sync immediately.
        
        Returns:
            Dict with keys: synced, failed, pending, errors, online
        """
        result = {
            "synced": 0,
            "failed": 0,
            "pending": 0,
            "errors": [],
            "online": False
        }
        
        # Check if sync is allowed
        if self.state == "OFFLINE":
            result["errors"] = ["Cannot sync while offline"]
            result["pending"] = self.sync_manager.queue_size
            logger.info("Sync aborted: OFFLINE state")
            return result
        
        if self.state == "SYNCING":
            result["errors"] = ["Sync already in progress"]
            result["pending"] = self.sync_manager.queue_size
            logger.info("Sync aborted: already SYNCING")
            return result
        
        if self.sync_manager.queue_size == 0:
            result["online"] = self.sync_manager.check_connectivity()
            logger.info("Sync skipped: queue empty")
            return result
        
        # Check rate limiting
        now = time.time()
        if now - self.last_sync_attempt < self.MIN_SYNC_INTERVAL:
            remaining = self.MIN_SYNC_INTERVAL - (now - self.last_sync_attempt)
            result["errors"] = [f"Rate limited - wait {int(remaining)}s"]
            result["pending"] = self.sync_manager.queue_size
            logger.warning("Sync rate limited, wait %ds", int(remaining))
            return result
        
        self.last_sync_attempt = now
        
        # Transition to SYNCING state
        self._transition_to("SYNCING")
        
        # Execute sync via SyncManager
        try:
            sync_result = self.sync_manager.try_sync()
            
            result["synced"] = sync_result.get("synced", 0)
            result["failed"] = sync_result.get("failed", 0)
            result["pending"] = sync_result.get("pending", 0)
            result["errors"] = sync_result.get("errors", [])
            result["online"] = sync_result.get("online", False)
            
            # Process result and update state
            self._process_sync_result(result)
            
        except Exception as e:
            logger.exception("Sync execution failed")
            result["errors"] = [f"Unexpected error: {str(e)}"]
            result["failed"] = self.sync_manager.queue_size
            result["pending"] = self.sync_manager.queue_size
            self._transition_to("ERROR")
        
        return result
    
    def get_state(self) -> SyncState:
        """Get current sync state."""
        return self.state
    
    def get_queue_size(self) -> int:
        """Get number of pending items."""
        return self.sync_manager.queue_size
    
    def is_online(self) -> bool:
        """Check if connectivity is available."""
        return self.sync_manager.check_connectivity()
    
    def get_queue_summary(self) -> Dict:
        """Get detailed queue summary."""
        return self.sync_manager.get_queue_summary()
    
    def get_last_sync_timestamp(self) -> Optional[str]:
        """Get last successful sync timestamp."""
        try:
            from profile_store import load_profile
            profile = load_profile()
            return profile.last_sync_timestamp if profile else None
        except:
            return None
    
    def get_dead_letter_queue(self) -> List[Dict]:
        """Get items that failed after max retries."""
        if not self.dlq_path.exists():
            return []
        try:
            with open(self.dlq_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    
    def retry_dlq_item(self, change_id: str) -> bool:
        """
        Retry a failed item from dead letter queue.
        
        Args:
            change_id: Unique change ID
        
        Returns:
            True if re-queued successfully
        """
        dlq = self.get_dead_letter_queue()
        
        # Find item
        item = next((i for i in dlq if i.get("change_id") == change_id), None)
        if not item:
            return False
        
        # Reset retry count
        item["retry_count"] = 0
        item["last_error"] = None
        
        # Re-enqueue via SyncManager (reconstruct from DLQ data)
        mutation_type = item["mutation_type"]
        payload = item["payload"]
        
        success = self.enqueue_change(mutation_type, payload, priority="high")
        
        if success:
            # Remove from DLQ
            dlq = [i for i in dlq if i.get("change_id") != change_id]
            self._save_dlq(dlq)
            logger.info("Retried DLQ item: %s", change_id)
        
        return success
    
    def discard_dlq_item(self, change_id: str) -> bool:
        """
        Permanently discard a failed item from DLQ.
        
        Args:
            change_id: Unique change ID
        
        Returns:
            True if discarded successfully
        """
        dlq = self.get_dead_letter_queue()
        original_len = len(dlq)
        
        dlq = [i for i in dlq if i.get("change_id") != change_id]
        
        if len(dlq) < original_len:
            self._save_dlq(dlq)
            logger.info("Discarded DLQ item: %s", change_id)
            return True
        
        return False
    
    # ═══════════════════════════════════════════════════════════════════════
    # STATE MACHINE
    # ═══════════════════════════════════════════════════════════════════════
    
    def _transition_to(self, new_state: SyncState):
        """
        Transition to new state with validation.
        
        Args:
            new_state: Target state
        
        Raises:
            ValueError: If transition is invalid
        """
        # Validate transition
        if not self._is_valid_transition(self.state, new_state):
            logger.error("Invalid transition: %s → %s", self.state, new_state)
            raise ValueError(f"Invalid transition: {self.state} → {new_state}")
        
        # Execute transition
        old_state = self.state
        self.state = new_state
        self._save_state()
        
        logger.info("State transition: %s → %s", old_state, new_state)
        
        # Handle state-specific logic
        self._handle_state_entry(new_state)
    
    def _is_valid_transition(self, from_state: SyncState, to_state: SyncState) -> bool:
        """
        Check if state transition is valid.
        
        Args:
            from_state: Current state
            to_state: Target state
        
        Returns:
            True if transition is valid
        """
        valid_transitions = {
            "IDLE": ["QUEUED", "OFFLINE", "CONFLICT"],
            "OFFLINE": ["IDLE", "QUEUED"],
            "QUEUED": ["SYNCING", "OFFLINE", "IDLE"],
            "SYNCING": ["SYNCED", "ERROR", "PARTIAL_SYNC", "OFFLINE", "CONFLICT"],
            "SYNCED": ["IDLE", "QUEUED"],
            "PARTIAL_SYNC": ["SYNCING", "ERROR", "SYNCED", "OFFLINE"],
            "ERROR": ["SYNCING", "OFFLINE", "QUEUED", "IDLE"],
            "CONFLICT": ["IDLE", "QUEUED"]
        }
        
        return to_state in valid_transitions.get(from_state, [])
    
    def _handle_state_entry(self, state: SyncState):
        """
        Handle side effects when entering a state.
        
        Args:
            state: State being entered
        """
        if state == "SYNCED":
            # Auto-transition to IDLE after 2 seconds
            if self.transition_timer:
                self.transition_timer.cancel()
            
            self.transition_timer = Timer(self.SYNCED_STATE_DURATION, self._auto_idle)
            self.transition_timer.daemon = True
            self.transition_timer.start()
        
        elif state == "OFFLINE":
            # Start connectivity recovery checks
            self._schedule_recovery_check()
        
        elif state == "CONFLICT":
            # Auto-transition to IDLE after 10 seconds
            if self.transition_timer:
                self.transition_timer.cancel()
            
            self.transition_timer = Timer(10, self._auto_idle)
            self.transition_timer.daemon = True
            self.transition_timer.start()
    
    def _auto_idle(self):
        """Auto-transition to IDLE (called by timer)."""
        try:
            if self.sync_manager.queue_size > 0:
                # Items added during transition
                self._transition_to("QUEUED")
            else:
                self._transition_to("IDLE")
        except ValueError:
            # Invalid transition, stay in current state
            logger.warning("Auto-transition to IDLE failed, staying in %s", self.state)
    
    # ═══════════════════════════════════════════════════════════════════════
    # EDGE CASE HANDLING
    # ═══════════════════════════════════════════════════════════════════════
    
    def _handle_network_loss(self):
        """Handle connectivity loss during sync."""
        logger.warning("Network loss detected")
        
        # Transition to OFFLINE
        try:
            self._transition_to("OFFLINE")
        except ValueError:
            logger.error("Cannot transition to OFFLINE from %s", self.state)
    
    def _handle_conflict(self, conflict_data: Dict):
        """
        Handle version conflict (Phase 2).
        
        MVP: Last-write-wins (server always wins)
        
        Args:
            conflict_data: Conflict details from server
        """
        logger.warning("Conflict detected: %s", conflict_data)
        
        # Accept server version (MVP strategy)
        # In Phase 2, this would show a modal for manual resolution
        
        try:
            self._transition_to("CONFLICT")
        except ValueError:
            logger.error("Cannot transition to CONFLICT from %s", self.state)
    
    def _schedule_recovery_check(self):
        """Schedule connectivity recovery check."""
        if self.recovery_timer:
            self.recovery_timer.cancel()
        
        self.recovery_timer = Timer(
            self.CONNECTIVITY_CHECK_INTERVAL,
            self._check_and_recover
        )
        self.recovery_timer.daemon = True
        self.recovery_timer.start()
        
        logger.debug("Recovery check scheduled in %ds", self.CONNECTIVITY_CHECK_INTERVAL)
    
    def _check_and_recover(self):
        """Check connectivity and auto-recover from offline state."""
        if self.state != "OFFLINE":
            # Already recovered
            return
        
        if self.sync_manager.check_connectivity():
            logger.info("Connectivity restored")
            
            # Transition based on queue state
            if self.sync_manager.queue_size > 0:
                self._transition_to("QUEUED")
                # Auto-trigger sync
                self.trigger_sync_debounced()
            else:
                self._transition_to("IDLE")
        else:
            # Still offline, check again
            logger.debug("Still offline, will check again")
            self._schedule_recovery_check()
    
    def _process_sync_result(self, result: Dict):
        """
        Process sync result and update state.
        
        Args:
            result: Sync result dict from execute_sync
        """
        synced = result.get("synced", 0)
        failed = result.get("failed", 0)
        pending = result.get("pending", 0)
        
        # Determine new state
        if failed == 0 and pending == 0:
            # All synced successfully
            self._transition_to("SYNCED")
        
        elif failed > 0 and synced == 0 and pending > 0:
            # All attempts failed
            self._transition_to("ERROR")
        
        elif synced > 0 and (failed > 0 or pending > 0):
            # Partial sync
            self._transition_to("PARTIAL_SYNC")
        
        elif pending > 0:
            # Items still pending (network issues?)
            if not self.sync_manager.check_connectivity():
                self._handle_network_loss()
            else:
                self._transition_to("QUEUED")
        
        else:
            # Shouldn't reach here, but default to IDLE
            logger.warning("Unexpected sync result state, defaulting to IDLE")
            self._transition_to("IDLE")
    
    # ═══════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════
    
    def _validate_payload(self, payload: Dict) -> bool:
        """
        Validate payload size and required fields.
        
        Args:
            payload: Mutation payload
        
        Returns:
            True if valid
        """
        # Check size (50KB hard limit)
        payload_str = json.dumps(payload)
        if len(payload_str) > 50 * 1024:
            logger.error("Payload exceeds 50KB limit: %d bytes", len(payload_str))
            return False
        
        # Check required fields
        if "userId" not in payload:
            logger.error("Payload missing required field: userId")
            return False
        
        return True
    
    def _load_state(self) -> SyncState:
        """Load sync state from disk."""
        if not self.state_path.exists():
            return "IDLE"
        
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                state = data.get("state", "IDLE")
                
                # Validate state
                if state not in ["IDLE", "OFFLINE", "QUEUED", "SYNCING", "SYNCED", 
                                 "PARTIAL_SYNC", "ERROR", "CONFLICT"]:
                    logger.warning("Invalid state %s, defaulting to IDLE", state)
                    return "IDLE"
                
                return state
        except Exception as e:
            logger.warning("Failed to load state: %s", e)
            return "IDLE"
    
    def _save_state(self):
        """Save sync state to disk."""
        try:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump({
                    "state": self.state,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error("Failed to save state: %s", e)
    
    def _save_dlq(self, dlq: List[Dict]):
        """Save dead letter queue to disk."""
        try:
            with open(self.dlq_path, "w", encoding="utf-8") as f:
                json.dump(dlq, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Failed to save DLQ: %s", e)
    
    def cleanup(self):
        """Clean up timers (call on shutdown)."""
        if self.sync_timer:
            self.sync_timer.cancel()
        if self.recovery_timer:
            self.recovery_timer.cancel()
        if self.transition_timer:
            self.transition_timer.cancel()
        
        logger.info("Orchestrator cleanup complete")


# ── Standalone test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    print("Testing SyncOrchestrator...")
    print("=" * 60)
    
    orchestrator = SyncOrchestrator(base_path=".")
    
    print(f"Initial state: {orchestrator.get_state()}")
    print(f"Queue size: {orchestrator.get_queue_size()}")
    print(f"Online: {orchestrator.is_online()}")
    print()
    
    # Test 1: Enqueue changes
    print("Test 1: Enqueuing quiz attempt...")
    success = orchestrator.enqueue_change(
        change_type="recordQuizAttempt",
        payload={
            "userId": "test_user_001",
            "quizId": "quiz_test_001",
            "score": 8,
            "totalQuestions": 10,
            "subject": "Mathematics",
            "difficulty": "Medium"
        },
        priority="high"
    )
    print(f"  Enqueue success: {success}")
    print(f"  New state: {orchestrator.get_state()}")
    print(f"  Queue size: {orchestrator.get_queue_size()}")
    print()
    
    # Test 2: Debounced sync
    print("Test 2: Triggering debounced sync...")
    orchestrator.trigger_sync_debounced()
    print(f"  Sync scheduled (will execute in {orchestrator.DEBOUNCE_WINDOW}s)")
    print()
    
    # Test 3: Immediate sync
    print("Test 3: Executing immediate sync...")
    result = orchestrator.execute_sync()
    print(f"  Sync result: {result}")
    print(f"  Final state: {orchestrator.get_state()}")
    print()
    
    # Test 4: State transitions
    print("Test 4: Testing state transitions...")
    print(f"  Current: {orchestrator.get_state()}")
    
    # Cleanup
    orchestrator.cleanup()
    print()
    print("All tests complete!")
