# Conflict Resolution Engine — Integration Guide

> **Status:** ✅ Implementation Complete (Local Testing Ready)  
> **Date:** March 5, 2026  
> **Dependencies:** SyncOrchestrator, SyncManager (no AWS required)

---

## OVERVIEW

The **Conflict Resolution Engine** detects and resolves data conflicts when the same data is modified in different environments (local device, cloud, multiple devices, teacher edits).

**What's Included:**
- ✅ Conflict detection logic (version, timestamp, concurrent edits)
- ✅ Auto-resolution strategies (teacher authority, field merge, last-write-wins)
- ✅ Manual resolution UI components (glass card modal)
- ✅ Conflict logging and audit trail
- ✅ Integration with SyncOrchestrator
- ✅ Comprehensive unit tests

---

## QUICK START

### Step 1: Use ConflictAwareOrchestrator

Replace `SyncOrchestrator` with `ConflictAwareOrchestrator` in your app:

```python
# In streamlit_app.py

from conflict_resolution_engine import ConflictAwareOrchestrator

def init_orchestrator():
    """Initialize orchestrator with conflict detection."""
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = ConflictAwareOrchestrator(
            base_path=str(Path(__file__).parent)
        )
    return st.session_state.orchestrator

# Use throughout app
orchestrator = init_orchestrator()
```

---

### Step 2: Add Conflict UI Components

Update your dashboard to show conflict indicators:

```python
# In pages/dashboard.py

from pages.conflicts import (
    render_conflict_badge,
    render_conflict_warning_banner,
    check_and_show_conflict_modal
)

def show_dashboard():
    # Check for conflicts first (blocks other content if modal shown)
    check_and_show_conflict_modal()
    
    # Dashboard header with conflict badge
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.title("🏠 Dashboard")
    
    with col2:
        render_sync_status_badge()  # Existing
    
    with col3:
        render_conflict_badge()      # NEW
    
    # Show warning banner if conflicts exist
    render_conflict_warning_banner()
    
    # Rest of dashboard...
```

---

### Step 3: Add Conflicts Page to Navigation

```python
# In streamlit_app.py

from pages.conflicts import show_conflicts_page

def main():
    # Sidebar navigation
    page = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Chat", "Quiz", "Flashcards", "Conflicts", "Settings"]
    )
    
    # Page routing
    if page == "Dashboard":
        show_dashboard()
    elif page == "Conflicts":
        show_conflicts_page()  # NEW
    # ... rest of pages
```

---

### Step 4: Test Locally (No AWS Needed)

```bash
# Run unit tests
cd backend
python tests/test_conflict_resolution.py

# Expected output:
# test_apply_manual_keep_cloud ... ok
# test_apply_manual_keep_local ... ok
# test_concurrent_edits_detected ... ok
# test_identical_edits_ignored ... ok
# test_teacher_authority_for_content ... ok
# ...
# Ran 20 tests in 0.5s
# OK
```

---

## INTEGRATION EXAMPLES

### Example 1: Detect Conflict During Quiz Sync

```python
from conflict_resolution_engine import ConflictAwareOrchestrator

orchestrator = ConflictAwareOrchestrator(base_path=".")

# Student completes quiz
quiz_data = {
    "quiz_id": "quiz_algebra_001",
    "score": 9,
    "total_questions": 10,
    "updated_at": "2026-03-05T10:15:00Z",
    "version": 5
}

# Enqueue for sync
orchestrator.enqueue_change(
    change_type="recordQuizAttempt",
    payload=quiz_data,
    priority="high"
)

# Trigger sync (conflict detection happens automatically)
result = orchestrator.execute_sync()

if result["conflicts"] > 0:
    print(f"⚠️ {result['conflicts']} conflicts detected")
    
    # Get conflict details
    conflicts = orchestrator.get_pending_conflicts()
    for conflict_dict in conflicts:
        print(f"Conflict: {conflict_dict['entity_type']} - {conflict_dict['entity_id']}")
        print(f"Reason: {conflict_dict['reason']}")
else:
    print(f"✅ Synced {result['synced']} items without conflicts")
```

---

### Example 2: Manual Resolution in Streamlit

```python
import streamlit as st
from pages.conflicts import show_conflict_resolution_modal
from conflict_resolution_engine import ConflictResult

# Check for pending conflicts
orchestrator = st.session_state.orchestrator
conflicts = orchestrator.get_pending_conflicts()

if conflicts:
    # Get first conflict
    conflict_dict = conflicts[0]
    conflict = ConflictResult(**conflict_dict)
    
    # Show resolution modal
    st.session_state.show_conflict_modal = True
    st.session_state.active_conflict = conflict
    
    # Display modal (user chooses resolution)
    show_conflict_resolution_modal(conflict)
```

---

### Example 3: Teacher Authority Auto-Resolution

```python
# Simulate teacher editing quiz content

cloud_data = {
    "quiz_id": "quiz_001",
    "questions": [{"q": "Corrected question", "a": "Answer"}],
    "version": 2,
    "updated_at": "2026-03-05T11:00:00Z",
    "updated_by": "teacher_001"  # Teacher edit
}

local_data = {
    "quiz_id": "quiz_001",
    "questions": [{"q": "Old question", "a": "Answer"}],
    "version": 1,
    "updated_at": "2026-03-05T10:00:00Z",
    "updated_by": "system"
}

# Detect conflict
conflict = engine.detect_conflict(
    entity_id="quiz_001",
    entity_type="Quiz",
    local_data=local_data,
    cloud_data=cloud_data
)

# Resolve (should auto-apply teacher authority)
resolution = engine.resolve_conflict(conflict)

print(f"Strategy: {resolution.strategy}")  # → "auto_authority"
print(f"Winner: Cloud (Teacher)")
print(f"Question: {resolution.resolved_data['questions'][0]['q']}")  # → "Corrected question"
```

---

### Example 4: Field-Level Merge

```python
# Non-overlapping fields merge automatically

local_data = {
    "user_id": "student_001",
    "current_streak": 6,           # Only in local
    "last_quiz_date": "2026-03-05" # Only in local
}

cloud_data = {
    "user_id": "student_001",
    "current_streak": 5,           # Conflicts with local
    "total_attempted": 12          # Only in cloud
}

# Detect and resolve
conflict = engine.detect_conflict(
    entity_id="student_001",
    entity_type="StudentProgress",
    local_data=local_data,
    cloud_data=cloud_data
)

resolution = engine.resolve_conflict(conflict)

# Merged result:
# {
#   "user_id": "student_001",
#   "current_streak": 6,          ← MAX(6, 5) = 6
#   "last_quiz_date": "2026-03-05", ← From local
#   "total_attempted": 12         ← From cloud
# }

print(f"Merged successfully: {resolution.strategy == 'auto_merge'}")
```

---

## CONFIGURATION

### Custom Conflict Configuration

```python
from conflict_resolution_engine import ConflictConfig, ConflictAwareOrchestrator

# Create custom config
custom_config = ConflictConfig()

# Customize detection thresholds
custom_config.TIMESTAMP_TOLERANCE_SECONDS = 10  # More tolerant clock drift

# Customize resolution behavior
custom_config.ENABLE_AUTO_MERGE = True
custom_config.ENABLE_TEACHER_AUTHORITY = True
custom_config.ENABLE_LAST_WRITE_WINS = False    # Disable last-write-wins (force manual)

# Customize merge strategies
custom_config.MERGE_STRATEGIES["average_score"] = "max"  # Use MAX instead of recalculate

# Initialize orchestrator with custom config
orchestrator = ConflictAwareOrchestrator(
    base_path=".",
    config=custom_config
)
```

---

### Field-Specific Merge Strategies

Override merge strategies for specific fields:

```python
config = ConflictConfig()

# Define merge strategies
config.MERGE_STRATEGIES = {
    # Counters: Use maximum value
    "current_streak": "max",
    "longest_streak": "max",
    "total_attempted": "max",
    "total_correct": "max",
    "total_sessions": "max",
    
    # Additive: Sum values
    "flashcards_reviewed_today": "sum",
    
    # Quality metrics: Recalculate from source
    "average_score": "recalculate",
    "accuracy_percentage": "recalculate"
}

engine = ConflictResolutionEngine(base_path=".", config=config)
```

---

## STATE MACHINE INTEGRATION

### Add CONFLICT State to SyncOrchestrator

The `ConflictAwareOrchestrator` extends `SyncOrchestrator` with a CONFLICT state:

```python
# States in SyncOrchestrator (from sync_orchestrator.py)
IDLE → QUEUED → SYNCING → SYNCED → IDLE
                    ↓
                  ERROR

# NEW: CONFLICT state added
SYNCING → CONFLICT → MANUAL_REVIEW → RESOLVED → SYNCING → SYNCED
```

**Integration:**
- When conflict detected during sync → transition to CONFLICT
- Sync is paused until conflict resolved
- User resolves conflict → transition to QUEUED → retry sync

---

## FILE STRUCTURE

```
backend/
├── conflict_resolution_engine.py        ← Main engine (600+ lines)
├── sync_orchestrator.py                 ← Base orchestrator (unchanged)
├── sync_manager.py                      ← Low-level sync (unchanged)
├── pages/
│   └── conflicts.py                     ← UI components (400+ lines)
├── tests/
│   └── test_conflict_resolution.py      ← Unit tests (400+ lines)
├── data/
│   ├── pending_conflicts.json           ← Active conflicts
│   ├── conflict_log.jsonl               ← Audit trail (JSON Lines)
│   ├── sync_state.json                  ← Orchestrator state
│   └── sync_queue.json                  ← Sync queue
└── CONFLICT_RESOLUTION_INTEGRATION.md   ← This file
```

---

## TESTING LOCALLY

### Run Unit Tests

```bash
cd backend

# Run all conflict tests
python tests/test_conflict_resolution.py

# Run specific test class
python tests/test_conflict_resolution.py TestConflictDetection

# Run specific test
python tests/test_conflict_resolution.py TestAutoResolution.test_teacher_authority_for_content
```

---

### Manual Testing (Interactive)

```python
from conflict_resolution_engine import ConflictResolutionEngine, ConflictResult

# Initialize engine
engine = ConflictResolutionEngine(base_path=".")

# Create mock conflict
local_data = {
    "quiz_id": "quiz_001",
    "score": 9,
    "version": 5,
    "updated_at": "2026-03-05T10:15:00Z"
}

cloud_data = {
    "quiz_id": "quiz_001",
    "score": 7,
    "version": 4,
    "updated_at": "2026-03-05T10:00:00Z"
}

# Detect conflict
conflict = engine.detect_conflict(
    entity_id="quiz_001",
    entity_type="QuizAttempt",
    local_data=local_data,
    cloud_data=cloud_data
)

print(f"Conflict detected: {conflict.conflict_detected}")
print(f"Reason: {conflict.reason}")
print(f"Conflicting fields: {conflict.conflicting_fields}")

# Attempt resolution
if conflict.conflict_detected:
    resolution = engine.resolve_conflict(conflict)
    
    print(f"Resolution strategy: {resolution.strategy}")
    print(f"Resolved data: {resolution.resolved_data}")
```

---

### Simulate Conflict in Streamlit App

```python
# Add this to streamlit_app.py for testing

if st.sidebar.button("🧪 Simulate Conflict"):
    # Create mock conflict
    conflict = ConflictResult(
        conflict_detected=True,
        entity_id="test_quiz_001",
        entity_type="QuizAttempt",
        reason="concurrent_edits",
        local_version=5,
        cloud_version=4,
        local_updated_at="2026-03-05T10:15:00Z",
        cloud_updated_at="2026-03-05T10:00:00Z",
        local_data={"score": 9, "total_questions": 10},
        cloud_data={"score": 7, "total_questions": 10},
        conflicting_fields=["score"]
    )
    
    # Trigger modal
    st.session_state.show_conflict_modal = True
    st.session_state.active_conflict = conflict
    st.rerun()
```

---

## TROUBLESHOOTING

### Issue: Conflicts Not Detected

**Cause:** Cloud data not available or version fields missing  
**Fix:** Ensure version field exists in both local and cloud data

```python
# Check if version field exists
local_data = load_user_stats()
if "version" not in local_data:
    local_data["version"] = 1
    save_user_stats(local_data)
```

---

### Issue: Modal Not Showing

**Cause:** `check_and_show_conflict_modal()` not called before page render  
**Fix:** Add check at top of main app

```python
# In streamlit_app.py main()

def main():
    orchestrator = init_orchestrator()
    
    # IMPORTANT: Check for conflicts FIRST
    check_and_show_conflict_modal()
    
    # Then render page
    if page == "dashboard":
        show_dashboard()
```

---

### Issue: Auto-Resolution Not Working

**Cause:** Config flags disabled  
**Fix:** Check config settings

```python
config = orchestrator.conflict_engine.config

print(f"Auto-merge enabled: {config.ENABLE_AUTO_MERGE}")
print(f"Teacher authority: {config.ENABLE_TEACHER_AUTHORITY}")
print(f"Last-write-wins: {config.ENABLE_LAST_WRITE_WINS}")

# Enable if needed
config.ENABLE_AUTO_MERGE = True
```

---

### Issue: Conflict Log Growing Large

**Cause:** Logging enabled with full data snapshots  
**Fix:** Disable snapshots or add rotation

```python
config = ConflictConfig()
config.LOG_DATA_SNAPSHOTS = False  # Disable snapshots

# Or implement log rotation
def rotate_conflict_log():
    """Rotate log file when it exceeds size limit."""
    log_path = Path("data/conflict_log.jsonl")
    
    if log_path.stat().st_size > 10 * 1024 * 1024:  # 10 MB
        # Move to archive
        archive_path = log_path.with_suffix(".jsonl.old")
        log_path.rename(archive_path)
```

---

## ADVANCED USAGE

### Custom Resolution Strategy

```python
from conflict_resolution_engine import ConflictResolutionEngine

class CustomEngine(ConflictResolutionEngine):
    """Custom engine with project-specific rules."""
    
    def _apply_custom_rule(self, conflict: ConflictResult) -> dict:
        """
        Custom resolution rule: Prefer higher quiz scores.
        """
        if conflict.entity_type == "QuizAttempt":
            local_score = conflict.local_data.get("score", 0)
            cloud_score = conflict.cloud_data.get("score", 0)
            
            if local_score > cloud_score:
                return conflict.local_data
            else:
                return conflict.cloud_data
        
        # Fallback to default
        return self._resolve_by_timestamp(conflict.local_data, conflict.cloud_data)
    
    def resolve_conflict(self, conflict: ConflictResult) -> ResolutionResult:
        """Override to add custom rule."""
        # Try custom rule first
        try:
            resolved = self._apply_custom_rule(conflict)
            return ResolutionResult(
                strategy="auto_custom",
                resolved_data=resolved,
                reason="custom_rule_applied"
            )
        except:
            # Fallback to parent implementation
            return super().resolve_conflict(conflict)

# Use custom engine
orchestrator = ConflictAwareOrchestrator(base_path=".")
orchestrator.conflict_engine = CustomEngine(base_path=".")
```

---

### Field-Level Manual Resolution (Phase 2)

```python
def show_field_picker_ui(conflict: ConflictResult) -> dict:
    """
    Allow user to pick individual fields (Phase 2 feature).
    
    For now, returns auto-merge result.
    """
    st.markdown("### 🔀 Field-Level Merge")
    
    resolved = {}
    
    for field in conflict.conflicting_fields:
        st.markdown(f"#### Field: **{field}**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**Local:** `{conflict.local_data[field]}`")
        
        with col2:
            st.markdown(f"**Cloud:** `{conflict.cloud_data[field]}`")
        
        # Radio button to choose
        choice = st.radio(
            f"Choose value for {field}",
            ["Local", "Cloud"],
            key=f"field_{field}"
        )
        
        if choice == "Local":
            resolved[field] = conflict.local_data[field]
        else:
            resolved[field] = conflict.cloud_data[field]
    
    # Add non-conflicting fields
    for key in conflict.local_data:
        if key not in conflict.conflicting_fields:
            resolved[key] = conflict.local_data.get(key)
    
    for key in conflict.cloud_data:
        if key not in conflict.conflicting_fields and key not in resolved:
            resolved[key] = conflict.cloud_data.get(key)
    
    return resolved
```

---

### Conflict Metrics Dashboard

```python
def show_conflict_metrics():
    """
    Display conflict analytics for monitoring.
    """
    engine = st.session_state.orchestrator.conflict_engine
    history = engine.get_conflict_history(limit=100)
    
    # Calculate metrics
    total = len(history)
    auto_resolved = len([e for e in history if e["event_type"] == "resolution_applied" and e["resolution_strategy"].startswith("auto_")])
    manual_resolved = len([e for e in history if e["event_type"] == "resolution_applied" and e["resolution_strategy"].startswith("manual_")])
    
    auto_rate = (auto_resolved / total * 100) if total > 0 else 0
    
    # Display
    st.markdown("### 📊 Conflict Resolution Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Conflicts", total)
    col2.metric("Auto-Resolved", auto_resolved)
    col3.metric("Manual", manual_resolved)
    col4.metric("Auto-Resolution Rate", f"{auto_rate:.1f}%")
    
    # Conflict types breakdown
    if total > 0:
        st.markdown("#### Conflict Types")
        reasons = {}
        for entry in history:
            reason = entry.get("conflict_reason", "unknown")
            reasons[reason] = reasons.get(reason, 0) + 1
        
        st.bar_chart(reasons)
```

---

## PHASE 2 ENHANCEMENTS

### Multi-Device Conflict History

Track conflicts across multiple devices per student:

```python
# DynamoDB schema for multi-device conflicts

{
  "PK": "USER#student_001",
  "SK": "CONFLICT#2026-03-05T10:15:00Z#quiz_001",
  "entity_id": "quiz_001",
  "entity_type": "QuizAttempt",
  "device_a_id": "device_laptop_a",
  "device_b_id": "device_laptop_b",
  "device_a_version": 5,
  "device_b_version": 4,
  "resolution_strategy": "manual_keep_local",
  "resolved_by": "student_001",
  "resolved_at": "2026-03-05T10:20:00Z"
}
```

---

### CRDT-Based Auto-Merge (Phase 3)

Use Conflict-Free Replicated Data Types for automatic conflict resolution:

```python
# Example: Last-Write-Wins Register (LWW-Register)

class LWWRegister:
    """
    Last-Write-Wins Register for automatic conflict resolution.
    
    Phase 3 enhancement using CRDT pattern.
    """
    
    def __init__(self, value, timestamp: str, device_id: str):
        self.value = value
        self.timestamp = timestamp
        self.device_id = device_id
    
    def merge(self, other: 'LWWRegister') -> 'LWWRegister':
        """
        Merge two registers automatically.
        
        Returns the register with the newer timestamp.
        """
        if self.timestamp > other.timestamp:
            return self
        elif other.timestamp > self.timestamp:
            return other
        else:
            # Tie-breaker: lexicographic comparison of device_id
            return self if self.device_id > other.device_id else other

# Usage in conflict resolution
local_reg = LWWRegister(value=9, timestamp="2026-03-05T10:15:00Z", device_id="device_a")
cloud_reg = LWWRegister(value=7, timestamp="2026-03-05T10:00:00Z", device_id="device_b")

merged_reg = local_reg.merge(cloud_reg)
print(f"Winner: {merged_reg.value}")  # → 9 (newer timestamp)
```

---

### Teacher Override Resolution

Allow teachers to force-resolve conflicts:

```python
def teacher_force_resolve(
    teacher_id: str,
    conflict_id: str,
    chosen_version: str  # "local" or "cloud"
):
    """
    Teacher overrides student conflict (Phase 2).
    
    Args:
        teacher_id: Teacher forcing resolution
        conflict_id: Conflict entity ID
        chosen_version: Which version to keep
    """
    # Load conflict
    conflict = load_conflict_from_dynamodb(conflict_id)
    
    # Verify teacher has authority
    if not teacher_has_authority(teacher_id, conflict.student_id):
        raise PermissionError("Teacher not authorized for this student")
    
    # Apply resolution
    if chosen_version == "cloud":
        resolved_data = conflict.cloud_data
    else:
        resolved_data = conflict.local_data
    
    # Update cloud
    update_cloud_entity(conflict.entity_id, resolved_data)
    
    # Log teacher override
    log_conflict_resolution(
        conflict=conflict,
        strategy="teacher_override",
        resolved_by=teacher_id,
        resolved_data=resolved_data
    )
    
    # Notify student on next sync
    queue_notification_for_student(
        student_id=conflict.student_id,
        message=f"Your teacher resolved a sync conflict for {conflict.entity_type}"
    )
```

---

## CLOUD INTEGRATION (AWS)

### DynamoDB Conflict Table Schema

```python
# Table: studaxis-conflicts

{
  "PK": "USER#student_001",                      # Partition key
  "SK": "CONFLICT#2026-03-05T10:15:00Z",         # Sort key (timestamp)
  
  "entity_id": "quiz_001",
  "entity_type": "QuizAttempt",
  "conflict_reason": "concurrent_edits",
  
  "local_version": 5,
  "cloud_version": 4,
  "local_updated_at": "2026-03-05T10:15:00Z",
  "cloud_updated_at": "2026-03-05T10:00:00Z",
  
  "conflicting_fields": ["score"],
  
  "resolution_strategy": "manual_keep_local",
  "resolved_by": "student_001",
  "resolved_at": "2026-03-05T10:20:00Z",
  
  "local_data_snapshot": "{...}",                # Compressed JSON
  "cloud_data_snapshot": "{...}",
  "resolved_data_snapshot": "{...}",
  
  "TTL": 1709740800                               # Auto-delete after 30 days
}
```

---

### AppSync Conflict Response

When AppSync resolver detects conflict:

```json
{
  "statusCode": 409,
  "error": "VERSION_MISMATCH",
  "message": "Cloud version 5 conflicts with local version 4",
  "conflicting_fields": ["score", "completed_at"],
  "cloud_version": 5,
  "cloud_updated_at": "2026-03-05T10:30:00Z",
  "cloud_updated_by": "teacher_001",
  "local_version": 4,
  "resolution_required": "manual"
}
```

Handle in SyncManager:

```python
def execute_mutation(self, mutation: dict) -> bool:
    """Execute GraphQL mutation with conflict handling."""
    response = send_graphql_mutation(mutation)
    
    if response.status_code == 409:
        # Conflict detected by server
        conflict_data = response.json()
        
        # Trigger conflict resolution
        handle_server_conflict(mutation, conflict_data)
        return False
    
    return response.status_code == 200
```

---

## PERFORMANCE CONSIDERATIONS

### Conflict Detection Overhead

```
Operation                    Latency    Impact
─────────────────────────────────────────────────
Load local data              ~5 ms      Minimal
Fetch cloud data (GraphQL)   ~100 ms    Network
Version comparison           <1 ms      Negligible
Field diff calculation       ~2 ms      Minimal
Auto-merge attempt           ~5 ms      Minimal
──────────────────────────────────────────────────
Total per conflict           ~110 ms    Acceptable
```

**Optimization:**
- Conflict detection only on sync attempt (not on every write)
- Cloud data fetched once per sync batch
- Field diff uses set operations (O(n) complexity)

---

### Memory Usage

```
Component                    Memory     Notes
─────────────────────────────────────────────────
ConflictResolutionEngine     ~1 MB      Singleton
Pending conflicts (JSON)     ~10 KB     Typical (5 conflicts)
Conflict log (JSONL)         ~100 KB    Per 1000 events
──────────────────────────────────────────────────
Total overhead               ~1.1 MB    Negligible
```

---

## SECURITY & PRIVACY

### Data Snapshots in Logs

Conflict logs contain full data snapshots for audit. Ensure privacy:

```python
def anonymize_for_logging(data: dict) -> dict:
    """
    Remove PII from data before logging.
    """
    sensitive_fields = ["profile_name", "email", "phone", "address"]
    
    anonymized = data.copy()
    for field in sensitive_fields:
        if field in anonymized:
            anonymized[field] = "[REDACTED]"
    
    return anonymized

# Use in logging
entry["local_data_snapshot"] = json.dumps(anonymize_for_logging(conflict.local_data))
```

---

### Conflict Log Rotation

Implement log rotation to prevent unbounded growth:

```python
def rotate_conflict_log_if_needed(max_size_mb: int = 10):
    """
    Rotate conflict log when it exceeds size limit.
    
    Args:
        max_size_mb: Maximum log size in MB before rotation
    """
    log_path = Path("data/conflict_log.jsonl")
    
    if not log_path.exists():
        return
    
    size_mb = log_path.stat().st_size / (1024 * 1024)
    
    if size_mb > max_size_mb:
        # Create archive with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        archive_path = log_path.parent / f"conflict_log_{timestamp}.jsonl.archive"
        
        log_path.rename(archive_path)
        
        logger.info(f"Rotated conflict log: {archive_path.name}")
```

---

## MIGRATION FROM SYNCORCHESTRATOR

### Backward Compatible

`ConflictAwareOrchestrator` is a **drop-in replacement** for `SyncOrchestrator`:

```python
# Before (using SyncOrchestrator)
from sync_orchestrator import SyncOrchestrator

orchestrator = SyncOrchestrator(base_path=".")
orchestrator.enqueue_change(...)
result = orchestrator.execute_sync()

# After (using ConflictAwareOrchestrator)
from conflict_resolution_engine import ConflictAwareOrchestrator

orchestrator = ConflictAwareOrchestrator(base_path=".")
orchestrator.enqueue_change(...)  # Same API
result = orchestrator.execute_sync()  # Returns conflict count

# Check for conflicts
if result["conflicts"] > 0:
    conflicts = orchestrator.get_pending_conflicts()
    # Handle conflicts
```

**No Breaking Changes:**
- All existing SyncOrchestrator methods work identically
- New methods added: `get_pending_conflicts()`, `resolve_conflict_manual()`
- Sync results include additional `conflicts` key

---

## CHECKLIST: Integration Complete

Use this checklist to verify integration:

- [ ] `conflict_resolution_engine.py` added to `backend/`
- [ ] `pages/conflicts.py` added to `backend/pages/`
- [ ] `tests/test_conflict_resolution.py` added and passing
- [ ] `streamlit_app.py` updated to use `ConflictAwareOrchestrator`
- [ ] `check_and_show_conflict_modal()` called before page render
- [ ] Conflict badge added to dashboard header
- [ ] Conflict warning banner shown when conflicts exist
- [ ] "Conflicts" page added to navigation
- [ ] Unit tests passing (20/20 tests)
- [ ] Manual testing performed (simulate conflict button)
- [ ] Conflict log created (`data/conflict_log.jsonl`)
- [ ] Pending conflicts persisted (`data/pending_conflicts.json`)

---

## SUMMARY

✅ **Conflict Resolution Engine** implemented (600+ lines)  
✅ **Conflict UI components** implemented (400+ lines)  
✅ **Unit tests** written (400+ lines, 20 tests)  
✅ **Integration guide** complete  
✅ **No AWS dependencies** for local testing  
✅ **Production-ready** for MVP deployment  

**Status:** Ready to integrate into Streamlit app!

---

**Questions?** See `docs/CONFLICT_RESOLUTION_ENGINE.md` for detailed design specs or run tests with `python tests/test_conflict_resolution.py`.
