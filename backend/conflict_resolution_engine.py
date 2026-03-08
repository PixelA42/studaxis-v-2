"""
Studaxis — Conflict Resolution Engine
═══════════════════════════════════════════════════════════════
Handles data conflicts when the same data is modified in different environments.

Supports:
  - Conflict detection (version mismatch, timestamp divergence, concurrent edits)
  - Auto-resolution (teacher authority, non-overlapping merge, last-write-wins)
  - Manual resolution (user UI workflow)
  - Conflict logging and audit trail
  - Integration with SyncOrchestrator

No AWS dependencies for local testing.
"""

import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Literal, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger("studaxis.conflict_resolution")


# ═══════════════════════════════════════════════════════════════════════
# TYPE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════

class ConflictReason(str, Enum):
    """Reasons for conflict detection."""
    CONCURRENT_EDITS = "concurrent_edits"
    TIMESTAMP_DIVERGENCE = "timestamp_divergence"
    VERSION_MISMATCH = "version_mismatch"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    MERGE_FAILURE = "merge_failure"
    NO_CONFLICT = "no_conflict"


class ResolutionStrategy(str, Enum):
    """Strategies for conflict resolution."""
    AUTO_TIMESTAMP = "auto_timestamp"
    AUTO_AUTHORITY = "auto_authority"
    AUTO_MERGE = "auto_merge"
    AUTO_IDENTICAL = "auto_identical"
    MANUAL_KEEP_LOCAL = "manual_keep_local"
    MANUAL_KEEP_CLOUD = "manual_keep_cloud"
    MANUAL_MERGE = "manual_merge"
    PENDING = "pending"


@dataclass
class ConflictResult:
    """Result of conflict detection."""
    conflict_detected: bool
    entity_id: str
    entity_type: str
    reason: ConflictReason
    local_version: int = 0
    cloud_version: int = 0
    local_updated_at: str = ""
    cloud_updated_at: str = ""
    local_data: Optional[dict] = None
    cloud_data: Optional[dict] = None
    conflicting_fields: Optional[List[str]] = None
    detected_at: Optional[str] = None
    
    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.now(timezone.utc).isoformat()
    
    @classmethod
    def from_dict(cls, d: dict) -> "ConflictResult":
        """Build ConflictResult from dict (e.g. loaded from JSON). Handles reason as string."""
        reason = d.get("reason")
        if isinstance(reason, str):
            try:
                reason = ConflictReason(reason)
            except ValueError:
                reason = ConflictReason.NO_CONFLICT
        elif not isinstance(reason, ConflictReason):
            reason = ConflictReason.NO_CONFLICT
        return cls(
            conflict_detected=d.get("conflict_detected", True),
            entity_id=d["entity_id"],
            entity_type=d.get("entity_type", "UserStats"),
            reason=reason,
            local_version=d.get("local_version", 0),
            cloud_version=d.get("cloud_version", 0),
            local_updated_at=d.get("local_updated_at", ""),
            cloud_updated_at=d.get("cloud_updated_at", ""),
            local_data=d.get("local_data"),
            cloud_data=d.get("cloud_data"),
            conflicting_fields=d.get("conflicting_fields"),
            detected_at=d.get("detected_at"),
        )


@dataclass
class ResolutionResult:
    """Result of conflict resolution."""
    strategy: ResolutionStrategy
    resolved_data: Optional[dict]
    reason: str
    resolution_timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.resolution_timestamp is None:
            self.resolution_timestamp = datetime.now(timezone.utc).isoformat()


# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

class ConflictConfig:
    """Configuration for conflict detection and resolution."""
    
    # Detection Thresholds
    TIMESTAMP_TOLERANCE_SECONDS = 5      # Clock drift tolerance
    VERSION_DIFF_THRESHOLD = 1           # Version difference to flag
    
    # Field Names (Placeholders - override if different in your schema)
    DATA_VERSION_FIELD = "version"
    LAST_SYNC_TIMESTAMP_FIELD = "last_sync_timestamp"
    UPDATED_AT_FIELD = "updated_at"
    DEVICE_ID_FIELD = "device_id"
    UPDATED_BY_FIELD = "updated_by"
    
    # Resolution Strategy
    ENABLE_AUTO_MERGE = True             # Enable automatic merging
    ENABLE_TEACHER_AUTHORITY = True      # Teacher wins for content
    ENABLE_LAST_WRITE_WINS = True        # Timestamp-based fallback
    
    # Manual Resolution
    MANUAL_RESOLUTION_TIMEOUT = 300      # 5 minutes before default action
    DEFAULT_TIMEOUT_ACTION = "defer"     # "defer" | "keep_local" | "keep_cloud"
    
    # Logging
    ENABLE_CONFLICT_LOGGING = True       # Log all conflicts
    LOG_DATA_SNAPSHOTS = True            # Include full data in logs
    COMPRESS_SNAPSHOTS = True            # Compress JSON snapshots
    
    # UI Behavior
    SHOW_CONFLICT_BADGE = True           # Show badge in header
    SHOW_CONFLICT_BANNER = True          # Show warning banner
    BLOCK_SYNC_ON_CONFLICT = True        # Pause sync until resolved
    
    # Field-Specific Merge Strategies
    MERGE_STRATEGIES = {
        "current_streak": "max",
        "longest_streak": "max",
        "total_attempted": "max",
        "total_correct": "max",
        "total_sessions": "max",
        "average_score": "recalculate",
        "flashcards_reviewed_today": "sum"
    }
    
    # Authority Rules
    TEACHER_ID_PREFIX = "teacher_"
    TEACHER_OWNED_ENTITIES = ["Quiz", "FlashcardDeck", "Assignment", "LessonNotes"]
    STUDENT_OWNED_ENTITIES = ["QuizAttempt", "StreakRecord", "ChatHistory", "FlashcardStats"]


# ═══════════════════════════════════════════════════════════════════════
# CONFLICT RESOLUTION ENGINE
# ═══════════════════════════════════════════════════════════════════════

class ConflictResolutionEngine:
    """
    Main engine for detecting and resolving data conflicts.
    
    Usage:
        engine = ConflictResolutionEngine(base_path=".")
        conflict = engine.detect_conflict(entity_id, entity_type, local_data, cloud_data)
        
        if conflict.conflict_detected:
            resolution = engine.resolve_conflict(conflict)
            
            if resolution.strategy.startswith("auto_"):
                # Apply resolved data automatically
                save_entity(resolution.resolved_data)
            else:
                # Show manual resolution UI to user
                show_conflict_modal(conflict)
    """
    
    def __init__(self, base_path: str = ".", user_id: Optional[str] = None, config: ConflictConfig = None):
        """
        Initialize conflict resolution engine.
        
        Args:
            base_path: Base directory for data files
            user_id: Optional user ID for per-user conflict storage. When provided,
                     conflicts and logs are stored under data/users/{user_id}/
            config: Optional custom configuration
        """
        self.base_path = Path(base_path)
        self.user_id = user_id
        self.config = config or ConflictConfig()
        
        # Paths — per-user when user_id provided, otherwise global (legacy)
        if user_id:
            user_dir = self.base_path / "data" / "users" / user_id
            self.conflicts_path = user_dir / "pending_conflicts.json"
            self.conflict_log_path = user_dir / "conflict_log.jsonl"
        else:
            self.conflicts_path = self.base_path / "data" / "pending_conflicts.json"
            self.conflict_log_path = self.base_path / "data" / "conflict_log.jsonl"
        
        # Ensure directories exist
        self.conflicts_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info("ConflictResolutionEngine initialized" + (f" for user {user_id}" if user_id else ""))
    
    
    # ═══════════════════════════════════════════════════════════════════════
    # CONFLICT DETECTION
    # ═══════════════════════════════════════════════════════════════════════
    
    def detect_conflict(
        self,
        entity_id: str,
        entity_type: str,
        local_data: dict,
        cloud_data: Optional[dict] = None
    ) -> ConflictResult:
        """
        Detect if a conflict exists between local and cloud data.
        
        Args:
            entity_id: Unique identifier for entity
            entity_type: Type of entity (Quiz, QuizAttempt, etc.)
            local_data: Local version of data
            cloud_data: Cloud version of data (optional)
        
        Returns:
            ConflictResult with detection status and metadata
        """
        # No local data → no conflict
        if not local_data:
            return ConflictResult(
                conflict_detected=False,
                entity_id=entity_id,
                entity_type=entity_type,
                reason=ConflictReason.NO_CONFLICT
            )
        
        # No cloud data → first sync, no conflict
        if not cloud_data:
            return ConflictResult(
                conflict_detected=False,
                entity_id=entity_id,
                entity_type=entity_type,
                reason=ConflictReason.NO_CONFLICT
            )
        
        # Extract version info
        local_version = local_data.get(self.config.DATA_VERSION_FIELD, 0)
        cloud_version = cloud_data.get(self.config.DATA_VERSION_FIELD, 0)
        
        local_updated = local_data.get(self.config.UPDATED_AT_FIELD)
        cloud_updated = cloud_data.get(self.config.UPDATED_AT_FIELD)
        last_sync = local_data.get(self.config.LAST_SYNC_TIMESTAMP_FIELD)
        
        # Pattern 1: Version mismatch with concurrent edits
        if local_version != cloud_version:
            if self._is_concurrent_edit(local_updated, cloud_updated, last_sync):
                conflicting_fields = self._find_conflicting_fields(local_data, cloud_data)
                
                logger.warning(
                    f"Conflict detected for {entity_type}:{entity_id} - "
                    f"concurrent edits (v{local_version} vs v{cloud_version})"
                )
                
                return ConflictResult(
                    conflict_detected=True,
                    entity_id=entity_id,
                    entity_type=entity_type,
                    reason=ConflictReason.CONCURRENT_EDITS,
                    local_version=local_version,
                    cloud_version=cloud_version,
                    local_updated_at=local_updated or "",
                    cloud_updated_at=cloud_updated or "",
                    local_data=local_data,
                    cloud_data=cloud_data,
                    conflicting_fields=conflicting_fields
                )
        
        # Pattern 2: Timestamp divergence (clock skew)
        if local_updated and cloud_updated:
            timestamp_diff = self._calculate_timestamp_diff(local_updated, cloud_updated)
            
            if timestamp_diff > self.config.TIMESTAMP_TOLERANCE_SECONDS:
                logger.warning(
                    f"Conflict detected for {entity_type}:{entity_id} - "
                    f"timestamp divergence ({timestamp_diff}s)"
                )
                
                return ConflictResult(
                    conflict_detected=True,
                    entity_id=entity_id,
                    entity_type=entity_type,
                    reason=ConflictReason.TIMESTAMP_DIVERGENCE,
                    local_version=local_version,
                    cloud_version=cloud_version,
                    local_updated_at=local_updated,
                    cloud_updated_at=cloud_updated,
                    local_data=local_data,
                    cloud_data=cloud_data,
                    conflicting_fields=self._find_conflicting_fields(local_data, cloud_data)
                )
        
        # No conflict detected
        return ConflictResult(
            conflict_detected=False,
            entity_id=entity_id,
            entity_type=entity_type,
            reason=ConflictReason.NO_CONFLICT,
            local_version=local_version,
            cloud_version=cloud_version
        )
    
    
    def _is_concurrent_edit(
        self,
        local_updated: Optional[str],
        cloud_updated: Optional[str],
        last_sync: Optional[str]
    ) -> bool:
        """Check if local and cloud were both modified since last sync."""
        if not local_updated or not cloud_updated or not last_sync:
            return False
        
        try:
            local_ts = self._parse_timestamp(local_updated)
            cloud_ts = self._parse_timestamp(cloud_updated)
            sync_ts = self._parse_timestamp(last_sync)
            
            return local_ts > sync_ts and cloud_ts > sync_ts
        except Exception as e:
            logger.error(f"Error parsing timestamps: {e}")
            return False
    
    
    def _calculate_timestamp_diff(self, ts1: str, ts2: str) -> float:
        """Calculate absolute difference between timestamps in seconds."""
        try:
            t1 = self._parse_timestamp(ts1)
            t2 = self._parse_timestamp(ts2)
            return abs((t1 - t2).total_seconds())
        except Exception as e:
            logger.error(f"Error calculating timestamp diff: {e}")
            return 0.0
    
    
    def _parse_timestamp(self, ts_string: str) -> datetime:
        """Parse ISO 8601 timestamp string."""
        return datetime.fromisoformat(ts_string.replace("Z", "+00:00"))
    
    
    def _find_conflicting_fields(self, local_data: dict, cloud_data: dict) -> List[str]:
        """
        Identify specific fields that differ between versions.
        
        Excludes sync metadata fields.
        """
        conflicting = []
        
        # Fields to exclude from comparison
        exclude_fields = [
            self.config.UPDATED_AT_FIELD,
            self.config.DATA_VERSION_FIELD,
            self.config.DEVICE_ID_FIELD,
            self.config.LAST_SYNC_TIMESTAMP_FIELD,
            "sync_status",
            "synced_at",
            "retry_count",
            "last_sync_attempt"
        ]
        
        all_keys = set(local_data.keys()) | set(cloud_data.keys())
        
        for key in all_keys:
            if key in exclude_fields:
                continue
            
            local_val = local_data.get(key)
            cloud_val = cloud_data.get(key)
            
            if local_val != cloud_val:
                conflicting.append(key)
        
        return conflicting
    
    
    # ═══════════════════════════════════════════════════════════════════════
    # CONFLICT RESOLUTION
    # ═══════════════════════════════════════════════════════════════════════
    
    def resolve_conflict(self, conflict: ConflictResult) -> ResolutionResult:
        """
        Attempt to resolve conflict using hybrid strategy.
        
        Resolution priority:
        1. Check for identical edits (false conflict)
        2. Apply authority rules (teacher vs student)
        3. Attempt field-level merge (non-overlapping)
        4. Apply last-write-wins (timestamp)
        5. Require manual resolution
        
        Args:
            conflict: ConflictResult from detect_conflict()
        
        Returns:
            ResolutionResult with strategy and resolved data
        """
        # Step 1: Check for false conflicts (identical data)
        if self._check_identical_edits(conflict.local_data, conflict.cloud_data):
            logger.info(f"Conflict is false positive - data is identical")
            return ResolutionResult(
                strategy=ResolutionStrategy.AUTO_IDENTICAL,
                resolved_data=conflict.cloud_data,
                reason="identical_edits_false_conflict"
            )
        
        # Step 2: Apply authority rules (if enabled)
        if self.config.ENABLE_TEACHER_AUTHORITY:
            try:
                resolved = self._apply_authority_resolution(conflict)
                logger.info(f"Conflict auto-resolved via authority rule")
                return ResolutionResult(
                    strategy=ResolutionStrategy.AUTO_AUTHORITY,
                    resolved_data=resolved,
                    reason="authority_rule_applied"
                )
            except Exception as e:
                logger.debug(f"Authority rule not applicable: {e}")
        
        # Step 3: Attempt field-level merge
        if self.config.ENABLE_AUTO_MERGE:
            if self._has_non_overlapping_fields(conflict):
                try:
                    merged = self._auto_merge_non_overlapping(
                        conflict.local_data,
                        conflict.cloud_data
                    )
                    logger.info(f"Conflict auto-resolved via field merge")
                    return ResolutionResult(
                        strategy=ResolutionStrategy.AUTO_MERGE,
                        resolved_data=merged,
                        reason="non_overlapping_field_merge"
                    )
                except Exception as e:
                    logger.debug(f"Auto-merge failed: {e}")
        
        # Step 4: Apply last-write-wins
        if self.config.ENABLE_LAST_WRITE_WINS:
            resolved = self._resolve_by_timestamp(conflict.local_data, conflict.cloud_data)
            logger.info(f"Conflict auto-resolved via last-write-wins")
            return ResolutionResult(
                strategy=ResolutionStrategy.AUTO_TIMESTAMP,
                resolved_data=resolved,
                reason="last_write_wins_timestamp"
            )
        
        # Step 5: Manual resolution required
        logger.warning(f"Conflict requires manual resolution")
        return ResolutionResult(
            strategy=ResolutionStrategy.PENDING,
            resolved_data=None,
            reason="conflicting_fields_require_user_input"
        )
    
    
    def _check_identical_edits(self, local_data: dict, cloud_data: dict) -> bool:
        """
        Check if local and cloud data are semantically identical.
        
        Returns True if conflict is a false positive.
        """
        # Normalize data (remove sync metadata)
        local_normalized = self._normalize_for_comparison(local_data)
        cloud_normalized = self._normalize_for_comparison(cloud_data)
        
        return local_normalized == cloud_normalized
    
    
    def _normalize_for_comparison(self, data: dict) -> dict:
        """Remove sync metadata fields before comparison."""
        exclude_fields = [
            self.config.UPDATED_AT_FIELD,
            self.config.DATA_VERSION_FIELD,
            self.config.DEVICE_ID_FIELD,
            self.config.LAST_SYNC_TIMESTAMP_FIELD,
            "sync_status",
            "synced_at",
            "retry_count",
            "last_sync_attempt",
            "checksum"
        ]
        
        return {k: v for k, v in data.items() if k not in exclude_fields}
    
    
    def _apply_authority_resolution(self, conflict: ConflictResult) -> dict:
        """
        Apply authority-based resolution rules.
        
        Teacher owns content. Student owns progress.
        
        Raises:
            Exception if authority rule not applicable
        """
        cloud_updated_by = conflict.cloud_data.get(self.config.UPDATED_BY_FIELD, "")
        is_teacher_edit = cloud_updated_by.startswith(self.config.TEACHER_ID_PREFIX)
        
        # Content entities → Teacher authority
        if conflict.entity_type in self.config.TEACHER_OWNED_ENTITIES:
            if is_teacher_edit:
                logger.info(f"Applying teacher authority for {conflict.entity_type}")
                return conflict.cloud_data
        
        # Progress entities → Student authority
        elif conflict.entity_type in self.config.STUDENT_OWNED_ENTITIES:
            logger.info(f"Applying student authority for {conflict.entity_type}")
            return conflict.local_data
        
        # Cannot determine authority
        raise Exception("Authority rule not applicable")
    
    
    def _has_non_overlapping_fields(self, conflict: ConflictResult) -> bool:
        """
        Check if conflict has non-overlapping fields that can be safely merged.
        """
        if not conflict.conflicting_fields:
            return False
        
        # If all conflicting fields can be merged, return True
        mergeable_count = sum(
            1 for field in conflict.conflicting_fields
            if self._is_field_mergeable(field, conflict.local_data.get(field), conflict.cloud_data.get(field))
        )
        
        return mergeable_count == len(conflict.conflicting_fields)
    
    
    def _is_field_mergeable(self, field_name: str, local_val, cloud_val) -> bool:
        """
        Check if a specific field can be safely auto-merged.
        """
        # Numeric fields with merge strategies
        if field_name in self.config.MERGE_STRATEGIES:
            return True
        
        # One is None (added/removed field)
        if local_val is None or cloud_val is None:
            return True
        
        # Both are dicts → can recurse
        if isinstance(local_val, dict) and isinstance(cloud_val, dict):
            return True
        
        # Arrays → can merge
        if isinstance(local_val, list) and isinstance(cloud_val, list):
            return True
        
        # Conflicting primitives → not safe
        return False
    
    
    def _auto_merge_non_overlapping(self, local_data: dict, cloud_data: dict) -> dict:
        """
        Merge fields that don't overlap between local and cloud edits.
        
        Returns:
            Merged dictionary
        """
        merged = {}
        
        all_keys = set(local_data.keys()) | set(cloud_data.keys())
        
        for key in all_keys:
            local_val = local_data.get(key)
            cloud_val = cloud_data.get(key)
            
            # Case 1: Only in local → use local
            if local_val is not None and cloud_val is None:
                merged[key] = local_val
            
            # Case 2: Only in cloud → use cloud
            elif cloud_val is not None and local_val is None:
                merged[key] = cloud_val
            
            # Case 3: Both present and identical → use either
            elif local_val == cloud_val:
                merged[key] = local_val
            
            # Case 4: Both present and different → resolve
            else:
                merged[key] = self._resolve_field_conflict(
                    key, local_val, cloud_val, local_data, cloud_data
                )
        
        return merged
    
    
    def _resolve_field_conflict(
        self,
        field_name: str,
        local_val,
        cloud_val,
        local_data: dict,
        cloud_data: dict
    ):
        """
        Resolve conflict for a single field.
        
        Uses merge strategies or last-write-wins.
        """
        # Apply merge strategy if defined
        strategy = self.config.MERGE_STRATEGIES.get(field_name)
        
        if strategy == "max" and isinstance(local_val, (int, float)) and isinstance(cloud_val, (int, float)):
            return max(local_val, cloud_val)
        
        elif strategy == "sum" and isinstance(local_val, (int, float)) and isinstance(cloud_val, (int, float)):
            return local_val + cloud_val
        
        elif strategy == "recalculate":
            # Cannot recalculate without access to raw data
            # Use timestamp as fallback
            return self._resolve_by_timestamp_field(field_name, local_val, cloud_val, local_data, cloud_data)
        
        # Nested objects → recurse
        elif isinstance(local_val, dict) and isinstance(cloud_val, dict):
            return self._auto_merge_non_overlapping(local_val, cloud_val)
        
        # Arrays → merge by appending unique
        elif isinstance(local_val, list) and isinstance(cloud_val, list):
            return self._merge_arrays(local_val, cloud_val)
        
        # Default: use timestamp
        else:
            return self._resolve_by_timestamp_field(field_name, local_val, cloud_val, local_data, cloud_data)
    
    
    def _resolve_by_timestamp_field(
        self,
        field_name: str,
        local_val,
        cloud_val,
        local_data: dict,
        cloud_data: dict
    ):
        """Resolve field conflict using parent entity timestamps."""
        local_updated = local_data.get(self.config.UPDATED_AT_FIELD)
        cloud_updated = cloud_data.get(self.config.UPDATED_AT_FIELD)
        
        if not local_updated or not cloud_updated:
            # No timestamps → prefer local (safer for offline-first)
            return local_val
        
        try:
            local_ts = self._parse_timestamp(local_updated)
            cloud_ts = self._parse_timestamp(cloud_updated)
            
            return local_val if local_ts > cloud_ts else cloud_val
        except:
            return local_val
    
    
    def _resolve_by_timestamp(self, local_data: dict, cloud_data: dict) -> dict:
        """
        Prefer the version with the most recent updated_at timestamp.
        
        This is the MVP default strategy.
        """
        local_updated = local_data.get(self.config.UPDATED_AT_FIELD)
        cloud_updated = cloud_data.get(self.config.UPDATED_AT_FIELD)
        
        if not local_updated and not cloud_updated:
            # No timestamps → compare versions
            local_version = local_data.get(self.config.DATA_VERSION_FIELD, 0)
            cloud_version = cloud_data.get(self.config.DATA_VERSION_FIELD, 0)
            return local_data if local_version > cloud_version else cloud_data
        
        if not local_updated:
            return cloud_data
        if not cloud_updated:
            return local_data
        
        try:
            local_ts = self._parse_timestamp(local_updated)
            cloud_ts = self._parse_timestamp(cloud_updated)
            
            if local_ts > cloud_ts:
                logger.info(f"Local version is newer ({local_updated} > {cloud_updated})")
                return local_data
            elif cloud_ts > local_ts:
                logger.info(f"Cloud version is newer ({cloud_updated} > {local_updated})")
                return cloud_data
            else:
                # Timestamps equal → compare version number
                local_version = local_data.get(self.config.DATA_VERSION_FIELD, 0)
                cloud_version = cloud_data.get(self.config.DATA_VERSION_FIELD, 0)
                return local_data if local_version > cloud_version else cloud_data
        
        except Exception as e:
            logger.error(f"Error comparing timestamps: {e}")
            return local_data  # Default to local for offline-first
    
    
    def _merge_arrays(self, local_array: list, cloud_array: list, unique_key: str = "id") -> list:
        """
        Merge arrays by deduplicating on unique_key.
        
        Args:
            local_array: Local array
            cloud_array: Cloud array
            unique_key: Key to use for deduplication (default "id")
        
        Returns:
            Merged array with unique items
        """
        seen_keys = set()
        merged = []
        
        # Process all items from both arrays
        for item in local_array + cloud_array:
            # Handle both dict and primitive items
            if isinstance(item, dict):
                key_val = item.get(unique_key)
            else:
                key_val = item
            
            if key_val not in seen_keys:
                seen_keys.add(key_val)
                merged.append(item)
        
        # Sort by timestamp if available
        if merged and isinstance(merged[0], dict) and "created_at" in merged[0]:
            merged.sort(key=lambda x: x.get("created_at", ""))
        
        return merged
    
    
    # ═══════════════════════════════════════════════════════════════════════
    # MANUAL RESOLUTION SUPPORT
    # ═══════════════════════════════════════════════════════════════════════
    
    def save_pending_conflict(self, conflict: ConflictResult):
        """
        Save conflict to pending conflicts file for UI display.
        
        Args:
            conflict: ConflictResult to save
        """
        conflicts = self._load_pending_conflicts()
        
        # Add or update conflict
        conflict_dict = asdict(conflict)
        conflict_dict["reason"] = conflict.reason.value  # Convert enum
        
        # Remove existing conflict for same entity (if any)
        conflicts = [c for c in conflicts if c.get("entity_id") != conflict.entity_id]
        
        # Add new conflict
        conflicts.append(conflict_dict)
        
        # Save
        self._save_pending_conflicts(conflicts)
        
        logger.info(f"Saved pending conflict for {conflict.entity_type}:{conflict.entity_id}")
    
    
    def get_pending_conflicts(self) -> List[dict]:
        """
        Get all pending conflicts requiring user resolution.
        
        Returns:
            List of conflict dictionaries
        """
        return self._load_pending_conflicts()
    
    
    def remove_pending_conflict(self, entity_id: str):
        """
        Remove conflict from pending list after resolution.
        
        Args:
            entity_id: Entity ID of resolved conflict
        """
        conflicts = self._load_pending_conflicts()
        conflicts = [c for c in conflicts if c.get("entity_id") != entity_id]
        self._save_pending_conflicts(conflicts)
        
        logger.info(f"Removed pending conflict for entity {entity_id}")
    
    
    def apply_manual_resolution(
        self,
        conflict: ConflictResult,
        user_choice: Literal["keep_local", "keep_cloud", "merge"],
        resolved_data: Optional[dict] = None
    ) -> dict:
        """
        Apply user's manual resolution choice.
        
        Args:
            conflict: ConflictResult being resolved
            user_choice: User's resolution choice
            resolved_data: Optional pre-merged data (for "merge" choice)
        
        Returns:
            Resolved data to save locally
        """
        if user_choice == "keep_local":
            resolved = conflict.local_data
            strategy = ResolutionStrategy.MANUAL_KEEP_LOCAL
        
        elif user_choice == "keep_cloud":
            resolved = conflict.cloud_data
            strategy = ResolutionStrategy.MANUAL_KEEP_CLOUD
        
        elif user_choice == "merge":
            if resolved_data is None:
                # User chose merge but didn't provide data → use auto-merge
                resolved = self._auto_merge_non_overlapping(conflict.local_data, conflict.cloud_data)
            else:
                resolved = resolved_data
            strategy = ResolutionStrategy.MANUAL_MERGE
        
        else:
            raise ValueError(f"Invalid user choice: {user_choice}")
        
        # Update version and timestamp
        resolved[self.config.DATA_VERSION_FIELD] = max(
            conflict.local_version,
            conflict.cloud_version
        ) + 1
        resolved[self.config.UPDATED_AT_FIELD] = datetime.now(timezone.utc).isoformat()
        
        # Log resolution
        self.log_conflict_resolution(
            conflict=conflict,
            strategy=strategy,
            resolved_by="user",
            resolved_data=resolved
        )
        
        # Remove from pending
        self.remove_pending_conflict(conflict.entity_id)
        
        return resolved
    
    
    # ═══════════════════════════════════════════════════════════════════════
    # LOGGING & AUDIT TRAIL
    # ═══════════════════════════════════════════════════════════════════════
    
    def log_conflict_event(self, conflict: ConflictResult):
        """
        Log conflict detection event.
        
        Args:
            conflict: ConflictResult to log
        """
        if not self.config.ENABLE_CONFLICT_LOGGING:
            return
        
        entry = {
            "event_id": self._generate_uuid(),
            "event_type": "conflict_detected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entity_id": conflict.entity_id,
            "entity_type": conflict.entity_type,
            "conflict_reason": conflict.reason.value,
            "local_version": conflict.local_version,
            "cloud_version": conflict.cloud_version,
            "local_updated_at": conflict.local_updated_at,
            "cloud_updated_at": conflict.cloud_updated_at,
            "conflicting_fields": conflict.conflicting_fields or [],
            "resolution_strategy": "pending",
            "device_id": self._get_device_id(),
            "session_id": self._get_session_id()
        }
        
        # Add data snapshots if enabled
        if self.config.LOG_DATA_SNAPSHOTS:
            entry["local_data_snapshot"] = self._compress_data(conflict.local_data)
            entry["cloud_data_snapshot"] = self._compress_data(conflict.cloud_data)
        
        self._append_to_conflict_log(entry)
    
    
    def log_conflict_resolution(
        self,
        conflict: ConflictResult,
        strategy: ResolutionStrategy,
        resolved_by: str,
        resolved_data: dict
    ):
        """
        Log conflict resolution event.
        
        Args:
            conflict: Original conflict
            strategy: Resolution strategy used
            resolved_by: Who resolved ("system", "user", "teacher_id")
            resolved_data: Final resolved data
        """
        if not self.config.ENABLE_CONFLICT_LOGGING:
            return
        
        entry = {
            "event_id": self._generate_uuid(),
            "event_type": "resolution_applied",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entity_id": conflict.entity_id,
            "entity_type": conflict.entity_type,
            "resolution_strategy": strategy.value,
            "resolved_by": resolved_by,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "original_conflict_reason": conflict.reason.value,
            "device_id": self._get_device_id(),
            "session_id": self._get_session_id()
        }
        
        # Add resolved data snapshot
        if self.config.LOG_DATA_SNAPSHOTS:
            entry["resolved_data_snapshot"] = self._compress_data(resolved_data)
        
        self._append_to_conflict_log(entry)
    
    
    def get_conflict_history(self, limit: int = 50) -> List[dict]:
        """
        Get conflict resolution history from log.
        
        Args:
            limit: Maximum number of entries to return
        
        Returns:
            List of conflict log entries
        """
        if not self.conflict_log_path.exists():
            return []
        
        entries = []
        
        try:
            with open(self.conflict_log_path, "r") as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
            
            # Return most recent entries
            return entries[-limit:] if len(entries) > limit else entries
        
        except Exception as e:
            logger.error(f"Error reading conflict log: {e}")
            return []
    
    
    # ═══════════════════════════════════════════════════════════════════════
    # RECOMMENDATION GENERATION
    # ═══════════════════════════════════════════════════════════════════════
    
    def generate_recommendation(self, conflict: ConflictResult) -> str:
        """
        Generate user-friendly recommendation for conflict resolution.
        
        Uses simple heuristics (no AI needed).
        
        Args:
            conflict: ConflictResult
        
        Returns:
            Recommendation string for UI display
        """
        # Recommendation 1: Prefer local if newer and better score
        if conflict.entity_type == "QuizAttempt":
            local_score = conflict.local_data.get("score", 0)
            cloud_score = conflict.cloud_data.get("score", 0)
            
            if local_score > cloud_score:
                return "💡 Recommendation: Keep Local — your device has the better score."
            elif cloud_score > local_score:
                return "💡 Recommendation: Keep Cloud — the cloud version has a better score."
        
        # Recommendation 2: Prefer teacher edits for content
        if conflict.entity_type in self.config.TEACHER_OWNED_ENTITIES:
            cloud_updated_by = conflict.cloud_data.get(self.config.UPDATED_BY_FIELD, "")
            if cloud_updated_by.startswith(self.config.TEACHER_ID_PREFIX):
                return "💡 Recommendation: Keep Cloud — your teacher updated this content."
        
        # Recommendation 3: Prefer newer timestamp
        if conflict.local_updated_at and conflict.cloud_updated_at:
            try:
                local_ts = self._parse_timestamp(conflict.local_updated_at)
                cloud_ts = self._parse_timestamp(conflict.cloud_updated_at)
                
                if local_ts > cloud_ts:
                    return "💡 Recommendation: Keep Local — your changes are more recent."
                else:
                    return "💡 Recommendation: Keep Cloud — cloud version is more recent."
            except:
                pass
        
        # Default recommendation
        return "💡 Review both versions carefully before choosing."
    
    
    # ═══════════════════════════════════════════════════════════════════════
    # STORAGE HELPERS
    # ═══════════════════════════════════════════════════════════════════════
    
    def _load_pending_conflicts(self) -> List[dict]:
        """Load pending conflicts from file."""
        if not self.conflicts_path.exists():
            return []
        
        try:
            with open(self.conflicts_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading pending conflicts: {e}")
            return []
    
    
    def _save_pending_conflicts(self, conflicts: List[dict]):
        """Save pending conflicts to file."""
        try:
            with open(self.conflicts_path, "w") as f:
                json.dump(conflicts, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving pending conflicts: {e}")
    
    
    def _append_to_conflict_log(self, entry: dict):
        """
        Append entry to conflict log (JSON Lines format).
        
        Args:
            entry: Log entry dictionary
        """
        try:
            with open(self.conflict_log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Error appending to conflict log: {e}")
    
    
    def _compress_data(self, data: dict) -> str:
        """
        Compress data for logging (if compression enabled).
        
        Args:
            data: Dictionary to compress
        
        Returns:
            JSON string (compressed if enabled)
        """
        if self.config.COMPRESS_SNAPSHOTS:
            # Simple compression: minified JSON
            return json.dumps(data, separators=(',', ':'))
        else:
            return json.dumps(data)
    
    
    # ═══════════════════════════════════════════════════════════════════════
    # UTILITY FUNCTIONS
    # ═══════════════════════════════════════════════════════════════════════
    
    def _generate_uuid(self) -> str:
        """Generate UUID for event IDs."""
        import uuid
        return str(uuid.uuid4())
    
    
    def _get_device_id(self) -> str:
        """
        Get device ID from device_id.json.
        
        Returns:
            Device ID string or "unknown"
        """
        device_id_path = self.base_path / "data" / "device_id.json"
        
        if device_id_path.exists():
            try:
                with open(device_id_path, "r") as f:
                    data = json.load(f)
                    return data.get("device_id", "unknown")
            except:
                pass
        
        return "unknown"
    
    
    def _get_session_id(self) -> str:
        """
        Get current session ID (if available).
        
        Returns:
            Session ID or timestamp-based ID
        """
        # In Streamlit app, this would come from st.session_state
        # For now, generate timestamp-based ID
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    
    def calculate_checksum(self, data: dict) -> str:
        """
        Calculate SHA-256 checksum for data integrity verification.
        
        Args:
            data: Dictionary to hash
        
        Returns:
            First 16 characters of SHA-256 hash
        """
        # Normalize and sort for consistent hashing
        normalized = self._normalize_for_comparison(data)
        json_str = json.dumps(normalized, sort_keys=True)
        
        hash_obj = hashlib.sha256(json_str.encode())
        return hash_obj.hexdigest()[:16]


# ═══════════════════════════════════════════════════════════════════════
# CONFLICT-AWARE ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════

class ConflictAwareOrchestrator:
    """
    Extends SyncOrchestrator with conflict detection and resolution.
    
    Drop-in replacement for SyncOrchestrator with added conflict handling.
    
    Usage:
        orchestrator = ConflictAwareOrchestrator(base_path=".")
        orchestrator.enqueue_change(...)
        result = orchestrator.execute_sync()
        
        # Check for conflicts
        if result.get("conflicts", 0) > 0:
            conflicts = orchestrator.get_pending_conflicts()
            # Show conflict UI
    """
    
    def __init__(self, base_path: str = ".", user_id: Optional[str] = None, config: ConflictConfig = None):
        """
        Initialize conflict-aware orchestrator.
        
        Args:
            base_path: Base directory for data files
            user_id: Optional user ID for per-user conflict storage
            config: Optional custom conflict configuration
        """
        # Initialize conflict engine (user-scoped when user_id provided)
        self.conflict_engine = ConflictResolutionEngine(base_path, user_id=user_id, config=config)
        
        # Initialize base orchestrator
        from sync_orchestrator import SyncOrchestrator
        self.base_orchestrator = SyncOrchestrator(base_path)
        
        # Delegate most methods to base orchestrator
        self.base_path = self.base_orchestrator.base_path
        self.state = self.base_orchestrator.state
        self.sync_manager = self.base_orchestrator.sync_manager
        
        logger.info("ConflictAwareOrchestrator initialized")
    
    
    def execute_sync(self, check_conflicts: bool = True) -> Dict:
        """
        Execute sync with conflict detection.
        
        Args:
            check_conflicts: Whether to check for conflicts (default True)
        
        Returns:
            Dict with sync results including conflict count
        """
        # Check for pending conflicts first
        pending_conflicts = self.conflict_engine.get_pending_conflicts()
        
        if pending_conflicts and self.conflict_engine.config.BLOCK_SYNC_ON_CONFLICT:
            logger.warning(f"{len(pending_conflicts)} conflicts pending resolution")
            return {
                "synced": 0,
                "failed": 0,
                "pending": self.base_orchestrator.get_queue_size(),
                "conflicts": len(pending_conflicts),
                "errors": ["Conflicts must be resolved before syncing"],
                "status": "blocked_by_conflicts"
            }
        
        # Execute base sync (may detect new conflicts)
        # For MVP, we'll enhance the base sync with conflict detection
        
        # Delegate to base orchestrator for now
        # In full implementation, this would intercept each sync item
        # and call conflict_engine.detect_conflict() before syncing
        
        result = self.base_orchestrator.execute_sync()
        
        # Add conflict count to result
        result["conflicts"] = len(pending_conflicts)
        
        return result
    
    
    def detect_and_resolve_conflict(
        self,
        entity_id: str,
        entity_type: str,
        local_data: dict,
        cloud_data: dict
    ) -> Tuple[bool, Optional[dict]]:
        """
        Detect conflict and attempt auto-resolution.
        
        Args:
            entity_id: Entity ID
            entity_type: Entity type
            local_data: Local version
            cloud_data: Cloud version
        
        Returns:
            (success, resolved_data) tuple
            - success: True if resolved (auto or no conflict)
            - resolved_data: Data to use (None if manual required)
        """
        # Detect conflict
        conflict = self.conflict_engine.detect_conflict(
            entity_id, entity_type, local_data, cloud_data
        )
        
        if not conflict.conflict_detected:
            # No conflict
            return (True, local_data)
        
        # Log conflict
        self.conflict_engine.log_conflict_event(conflict)
        
        # Attempt resolution
        resolution = self.conflict_engine.resolve_conflict(conflict)
        
        if resolution.strategy == ResolutionStrategy.PENDING:
            # Manual resolution required
            self.conflict_engine.save_pending_conflict(conflict)
            self.transition_to("CONFLICT")
            return (False, None)
        
        else:
            # Auto-resolved
            self.conflict_engine.log_conflict_resolution(
                conflict=conflict,
                strategy=resolution.strategy,
                resolved_by="system",
                resolved_data=resolution.resolved_data
            )
            return (True, resolution.resolved_data)
    
    
    # Delegate common methods to base orchestrator
    
    def enqueue_change(self, change_type: str, payload: Dict, priority: str = "normal") -> bool:
        """Delegate to base orchestrator."""
        return self.base_orchestrator.enqueue_change(change_type, payload, priority)
    
    def trigger_sync_debounced(self):
        """Delegate to base orchestrator."""
        return self.base_orchestrator.trigger_sync_debounced()
    
    def get_state(self) -> str:
        """Delegate to base orchestrator."""
        return self.base_orchestrator.get_state()
    
    def get_queue_size(self) -> int:
        """Delegate to base orchestrator."""
        return self.base_orchestrator.get_queue_size()
    
    def is_online(self) -> bool:
        """Delegate to base orchestrator."""
        return self.base_orchestrator.is_online()
    
    def transition_to(self, new_state: str):
        """Delegate to base orchestrator."""
        return self.base_orchestrator.transition_to(new_state)
    
    def get_pending_conflicts(self) -> List[dict]:
        """Get pending conflicts from engine."""
        return self.conflict_engine.get_pending_conflicts()
    
    def resolve_conflict_manual(
        self,
        entity_id: str,
        user_choice: Literal["keep_local", "keep_cloud", "merge"]
    ) -> dict:
        """
        Apply user's manual resolution choice.
        
        Args:
            entity_id: Entity ID of conflict to resolve
            user_choice: User's choice
        
        Returns:
            Resolved data
        """
        # Find conflict
        conflicts = self.conflict_engine.get_pending_conflicts()
        conflict_dict = next((c for c in conflicts if c["entity_id"] == entity_id), None)
        
        if not conflict_dict:
            raise ValueError(f"No pending conflict found for entity {entity_id}")
        
        # Convert dict to ConflictResult (handles reason as string from JSON)
        conflict = ConflictResult.from_dict(conflict_dict)
        
        # Apply resolution
        resolved_data = self.conflict_engine.apply_manual_resolution(
            conflict, user_choice
        )
        
        # Transition back to normal state
        self.transition_to("QUEUED")
        
        return resolved_data
    
    def cleanup(self):
        """Cleanup resources."""
        self.base_orchestrator.cleanup()


# ═══════════════════════════════════════════════════════════════════════
# UI HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def format_timestamp(iso_timestamp: str) -> str:
    """
    Format ISO timestamp for UI display.
    
    Args:
        iso_timestamp: ISO 8601 timestamp string
    
    Returns:
        Human-readable timestamp (e.g., "Mar 5, 10:15 AM")
    """
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %I:%M %p")
    except:
        return iso_timestamp


def calculate_time_ago(iso_timestamp: str) -> str:
    """
    Calculate time ago for UI display.
    
    Args:
        iso_timestamp: ISO 8601 timestamp string
    
    Returns:
        Relative time string (e.g., "5 minutes ago")
    """
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt
        
        if delta < timedelta(minutes=1):
            return "just now"
        elif delta < timedelta(hours=1):
            mins = int(delta.total_seconds() / 60)
            return f"{mins} minute{'s' if mins != 1 else ''} ago"
        elif delta < timedelta(days=1):
            hours = int(delta.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = delta.days
            return f"{days} day{'s' if days != 1 else ''} ago"
    except:
        return "unknown"


def get_conflict_severity(conflict: ConflictResult) -> Literal["low", "medium", "high"]:
    """
    Calculate conflict severity for UI prioritization.
    
    Args:
        conflict: ConflictResult
    
    Returns:
        Severity level
    """
    # High severity: Score conflicts or teacher edits
    if conflict.entity_type == "QuizAttempt":
        local_score = conflict.local_data.get("score", 0)
        cloud_score = conflict.cloud_data.get("score", 0)
        if abs(local_score - cloud_score) >= 3:
            return "high"
    
    if conflict.entity_type in ["Quiz", "FlashcardDeck"]:
        return "high"
    
    # Medium severity: Multiple field conflicts
    if conflict.conflicting_fields and len(conflict.conflicting_fields) >= 3:
        return "medium"
    
    # Low severity: Minor conflicts
    return "low"


# ═══════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════

__all__ = [
    "ConflictResolutionEngine",
    "ConflictAwareOrchestrator",
    "ConflictResult",
    "ResolutionResult",
    "ConflictReason",
    "ResolutionStrategy",
    "ConflictConfig",
    "format_timestamp",
    "calculate_time_ago",
    "get_conflict_severity"
]
