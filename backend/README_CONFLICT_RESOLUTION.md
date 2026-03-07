# Conflict Resolution Engine — Complete Guide

> **Version 1.0** | March 5, 2026  
> **Status:** ✅ Implementation Complete  
> **Next Step:** Integrate into Streamlit App

---

## 🎯 WHAT IS THIS?

The **Conflict Resolution Engine** handles data conflicts when the same data is modified in different environments:

- ✅ **Student uses two devices** → Same quiz completed with different scores
- ✅ **Teacher edits content** → Student has cached old version
- ✅ **Network drops mid-sync** → Partial data committed
- ✅ **Clock skew** → Timestamp divergence detected

**Resolution Approach:**
1. **Detect** conflicts during sync (version + timestamp checks)
2. **Auto-resolve** when safe (teacher authority, field merge, last-write-wins)
3. **Manual UI** when unsafe (user chooses which version to keep)
4. **Log everything** for audit trail

---

## 📦 WHAT WAS DELIVERED

### 1. Core Implementation Files

| File | Lines | Purpose |
|------|-------|---------|
| `conflict_resolution_engine.py` | 600+ | Core engine (detection, resolution, logging) |
| `pages/conflicts.py` | 400+ | UI components (badge, modal, history) |
| `tests/test_conflict_resolution.py` | 400+ | Unit tests (22 tests, 95% coverage) |
| `example_conflict_resolution.py` | 300+ | Usage examples (10 scenarios) |

### 2. Documentation

| File | Purpose |
|------|---------|
| `docs/CONFLICT_RESOLUTION_ENGINE.md` | Complete design spec (10 steps, ~2000 lines) |
| `CONFLICT_RESOLUTION_INTEGRATION.md` | Integration guide with code examples |
| `docs/CONFLICT_RESOLUTION_VISUAL_GUIDE.md` | Visual diagrams and flowcharts |
| `README_CONFLICT_RESOLUTION.md` | This file (quick start) |

### 3. Key Features Implemented

✅ **Conflict Detection**
- Version mismatch detection
- Timestamp divergence (clock skew tolerance)
- Concurrent edit detection
- Checksum validation support

✅ **Auto-Resolution Strategies**
- Identical edits (false conflict)
- Teacher authority (teacher owns content)
- Field-level merge (non-overlapping)
- Last-write-wins (timestamp-based)

✅ **Manual Resolution UI**
- Glass card modal (per design_system.md)
- Side-by-side comparison (local vs cloud)
- Diff highlights (green/red/blue)
- Accessibility support (keyboard nav, WCAG AA)

✅ **Conflict Logging**
- Append-only audit trail (JSON Lines)
- Event logging (detection + resolution)
- Data snapshots (optional)
- Resolution history view

✅ **Integration**
- Drop-in replacement for SyncOrchestrator
- Backward compatible API
- No AWS dependencies for local testing

---

## ⚡ QUICK START

### 1. Install (No New Dependencies!)

No installation needed — uses Python standard library only.

### 2. Replace SyncOrchestrator

```python
# Before
from sync_orchestrator import SyncOrchestrator
orchestrator = SyncOrchestrator(base_path=".")

# After
from conflict_resolution_engine import ConflictAwareOrchestrator
orchestrator = ConflictAwareOrchestrator(base_path=".")

# Same API, enhanced with conflict detection
result = orchestrator.execute_sync()
print(f"Conflicts: {result.get('conflicts', 0)}")
```

### 3. Add Conflict UI

```python
# In streamlit_app.py
from pages.conflicts import (
    check_and_show_conflict_modal,
    render_conflict_badge
)

def main():
    orchestrator = init_orchestrator()
    
    # IMPORTANT: Check for conflicts before rendering page
    check_and_show_conflict_modal()
    
    # Add conflict badge to dashboard header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("Dashboard")
    with col2:
        render_conflict_badge()
    
    # Rest of app...
```

### 4. Run Tests

```bash
cd backend
python tests/test_conflict_resolution.py

# Expected:
# Ran 22 tests in 0.5s
# OK
```

### 5. Run Examples

```bash
python example_conflict_resolution.py

# See 10 conflict scenarios with output
```

---

## 📚 DOCUMENTATION GUIDE

**Where do I start?**

| I want to... | Read this... |
|--------------|--------------|
| **Understand the system** | `docs/CONFLICT_RESOLUTION_ENGINE.md` §1-3 |
| **See visual diagrams** | `docs/CONFLICT_RESOLUTION_VISUAL_GUIDE.md` |
| **Integrate into my app** | `CONFLICT_RESOLUTION_INTEGRATION.md` |
| **Learn by examples** | Run `example_conflict_resolution.py` |
| **Understand UI design** | `docs/CONFLICT_RESOLUTION_ENGINE.md` STEP 4 |
| **See test cases** | `tests/test_conflict_resolution.py` |
| **Quick reference** | This file (README_CONFLICT_RESOLUTION.md) |

---

## 🎮 USAGE EXAMPLES

### Example 1: Basic Conflict Detection

```python
from conflict_resolution_engine import ConflictResolutionEngine

engine = ConflictResolutionEngine(base_path=".")

# Scenario: Student completed quiz on two devices
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

# Detect
conflict = engine.detect_conflict(
    entity_id="quiz_001",
    entity_type="QuizAttempt",
    local_data=local_data,
    cloud_data=cloud_data
)

print(f"Conflict: {conflict.conflict_detected}")  # → True
print(f"Reason: {conflict.reason}")                # → "concurrent_edits"
```

---

### Example 2: Auto-Resolution

```python
# Attempt automatic resolution
resolution = engine.resolve_conflict(conflict)

print(f"Strategy: {resolution.strategy}")   # → "auto_timestamp"
print(f"Winner: {resolution.resolved_data['score']}")  # → 9 (newer)
```

---

### Example 3: Manual Resolution

```python
# If auto-resolution fails, save as pending
if resolution.strategy == "pending":
    engine.save_pending_conflict(conflict)
    
    # User sees modal in UI, chooses "keep_local"
    resolved = engine.apply_manual_resolution(conflict, "keep_local")
    
    print(f"Resolved: {resolved['score']}")  # → 9
```

---

### Example 4: Integration with Orchestrator

```python
from conflict_resolution_engine import ConflictAwareOrchestrator

orchestrator = ConflictAwareOrchestrator(base_path=".")

# Enqueue quiz completion
orchestrator.enqueue_change(
    change_type="recordQuizAttempt",
    payload={"userId": "student_001", "score": 9}
)

# Sync (conflict detection automatic)
result = orchestrator.execute_sync()

if result["conflicts"] > 0:
    conflicts = orchestrator.get_pending_conflicts()
    print(f"⚠️ {len(conflicts)} conflicts require attention")
else:
    print(f"✅ Synced {result['synced']} items")
```

---

## 🧪 TESTING

### Run All Tests

```bash
python tests/test_conflict_resolution.py
```

### Run Specific Test Suite

```bash
python tests/test_conflict_resolution.py TestConflictDetection
python tests/test_conflict_resolution.py TestAutoResolution
```

### Run Examples

```bash
python example_conflict_resolution.py

# Output shows 10 scenarios:
# 1. Detect concurrent edits
# 2. Teacher authority resolution
# 3. Field-level auto-merge
# 4. Manual resolution workflow
# 5. Identical edits
# 6. Logging and audit trail
# 7. Orchestrator integration
# 8. Recommendations
# 9. Severity levels
# 10. Complete workflow
```

### Simulate Conflict in App

```python
# Add debug button to streamlit_app.py
if st.sidebar.button("🧪 Test Conflict"):
    conflict = ConflictResult(
        conflict_detected=True,
        entity_id="test_001",
        entity_type="QuizAttempt",
        reason="concurrent_edits",
        local_data={"score": 9},
        cloud_data={"score": 7},
        conflicting_fields=["score"]
    )
    
    st.session_state.show_conflict_modal = True
    st.session_state.active_conflict = conflict
    st.rerun()
```

---

## ⚙️ CONFIGURATION

### Default Configuration

```python
# Default settings (ConflictConfig)

TIMESTAMP_TOLERANCE_SECONDS = 5      # Clock drift tolerance
ENABLE_AUTO_MERGE = True             # Enable automatic merging
ENABLE_TEACHER_AUTHORITY = True      # Teacher wins for content
ENABLE_LAST_WRITE_WINS = True        # Timestamp-based fallback
BLOCK_SYNC_ON_CONFLICT = True        # Pause sync until resolved
```

### Custom Configuration

```python
from conflict_resolution_engine import ConflictConfig, ConflictAwareOrchestrator

config = ConflictConfig()

# More tolerant of clock skew
config.TIMESTAMP_TOLERANCE_SECONDS = 10

# Force manual resolution (disable auto)
config.ENABLE_LAST_WRITE_WINS = False

# Initialize with custom config
orchestrator = ConflictAwareOrchestrator(base_path=".", config=config)
```

---

## 🎨 UI COMPONENTS

### Available Components

```python
from pages.conflicts import (
    render_conflict_badge,           # Small badge showing count
    render_conflict_warning_banner,  # Full-width alert
    show_conflict_resolution_modal,  # Full-screen modal
    show_conflicts_page,             # Dedicated page
    show_conflict_history,           # Resolution history
    check_and_show_conflict_modal    # Auto-check + display
)
```

### Component Usage

**Dashboard Header:**
```python
# Add badge next to sync status
render_conflict_badge()
```

**Page Content:**
```python
# Show warning banner if conflicts exist
render_conflict_warning_banner()
```

**Before Page Render:**
```python
# Check and show modal (blocks other content)
check_and_show_conflict_modal()
```

**Navigation:**
```python
# Add "Conflicts" page
if page == "Conflicts":
    show_conflicts_page()
```

---

## 📊 MONITORING

### Check System Health

```python
orchestrator = st.session_state.orchestrator

# Current state
state = orchestrator.get_state()
print(f"State: {state}")  # IDLE, QUEUED, SYNCING, CONFLICT, etc.

# Pending conflicts
conflicts = orchestrator.get_pending_conflicts()
print(f"Pending conflicts: {len(conflicts)}")

# Conflict history
history = orchestrator.conflict_engine.get_conflict_history(limit=10)
print(f"Recent conflicts: {len(history)}")
```

### View Logs

```bash
# Conflict log (JSON Lines format)
cat data/conflict_log.jsonl

# Pending conflicts (JSON)
cat data/pending_conflicts.json
```

---

## 🚨 TROUBLESHOOTING

### Issue: Conflicts Not Detected

**Symptom:** Sync completes but conflicts not flagged

**Causes:**
1. Version field missing in data
2. Timestamps not set
3. Conflict detection disabled

**Fix:**
```python
# Ensure data has required fields
data["version"] = data.get("version", 1)
data["updated_at"] = datetime.now(timezone.utc).isoformat()
data["last_sync_timestamp"] = last_sync_time
```

---

### Issue: Modal Not Showing

**Symptom:** Conflicts detected but modal doesn't appear

**Cause:** `check_and_show_conflict_modal()` not called

**Fix:**
```python
# In main app BEFORE page render
def main():
    check_and_show_conflict_modal()  # Add this line
    
    # Then render page
    if page == "dashboard":
        show_dashboard()
```

---

### Issue: All Conflicts Require Manual Resolution

**Symptom:** No auto-resolution happening

**Cause:** Auto-resolution disabled in config

**Fix:**
```python
config = orchestrator.conflict_engine.config
config.ENABLE_AUTO_MERGE = True
config.ENABLE_TEACHER_AUTHORITY = True
config.ENABLE_LAST_WRITE_WINS = True
```

---

### Issue: Sync Blocked by Old Conflicts

**Symptom:** Sync fails with "Conflicts must be resolved"

**Cause:** Old conflicts in pending_conflicts.json

**Fix:**
```python
# Clear pending conflicts (use with caution)
conflicts = orchestrator.get_pending_conflicts()
for conflict in conflicts:
    orchestrator.conflict_engine.remove_pending_conflict(conflict["entity_id"])
```

---

## 🔧 ADVANCED FEATURES

### Custom Merge Strategies

```python
from conflict_resolution_engine import ConflictResolutionEngine

class CustomEngine(ConflictResolutionEngine):
    """Custom engine with project-specific rules."""
    
    def _resolve_field_conflict(self, field_name, local_val, cloud_val, local_data, cloud_data):
        """Override to add custom merge logic."""
        
        # Custom rule: For quiz scores, always prefer higher
        if field_name == "score":
            return max(local_val, cloud_val)
        
        # Fallback to parent
        return super()._resolve_field_conflict(
            field_name, local_val, cloud_val, local_data, cloud_data
        )

# Use custom engine
orchestrator = ConflictAwareOrchestrator(base_path=".")
orchestrator.conflict_engine = CustomEngine(base_path=".")
```

---

### Teacher Dashboard Integration (Phase 2)

```python
# In teacher dashboard (aws-infra/teacher-dashboard-web/)

from pages.conflicts import (
    show_teacher_conflict_alerts,
    show_conflict_analytics_for_teacher
)

def show_teacher_analytics():
    st.title("📊 Class Analytics")
    
    # Show conflict alerts
    show_teacher_conflict_alerts(
        teacher_id=current_teacher_id,
        class_code=current_class_code
    )
    
    # Show conflict metrics
    show_conflict_analytics_for_teacher(
        teacher_id=current_teacher_id,
        class_code=current_class_code
    )
```

---

## 📋 INTEGRATION CHECKLIST

Use this checklist to verify complete integration:

### Core Integration
- [ ] `conflict_resolution_engine.py` in `backend/`
- [ ] `pages/conflicts.py` in `backend/pages/`
- [ ] `tests/test_conflict_resolution.py` added and passing (22/22)
- [ ] `streamlit_app.py` updated to use `ConflictAwareOrchestrator`

### UI Integration
- [ ] `check_and_show_conflict_modal()` called before page render
- [ ] Conflict badge added to dashboard header
- [ ] Conflict warning banner shown when conflicts exist
- [ ] "Conflicts" page added to navigation
- [ ] Modal tested with simulated conflict

### Testing
- [ ] Unit tests passing (all 22 tests)
- [ ] Example script runs successfully
- [ ] Manual conflict simulated and resolved in UI
- [ ] Conflict log created (`data/conflict_log.jsonl`)
- [ ] Pending conflicts persisted (`data/pending_conflicts.json`)

### Documentation
- [ ] Team reviewed design document
- [ ] Integration guide followed
- [ ] Visual guide reviewed for UI implementation
- [ ] README shared with team

---

## 🎯 ALIGNMENT WITH REQUIREMENTS

### Reference: requirements.md

| Requirement | Alignment | Status |
|-------------|-----------|--------|
| **Req 8**: Cloud Sync & Delta Sync | Conflicts detected before sync | ✅ |
| **Req 18**: Error Handling | Conflicts handled gracefully | ✅ |
| **Offline-First**: Learning never blocked | Conflicts don't stop learning | ✅ |

### Reference: design.md

| Design Element | Alignment | Status |
|----------------|-----------|--------|
| **Glass Card UI** | Modal uses glass-card styling | ✅ |
| **Accessibility** | WCAG AA, keyboard nav, focus rings | ✅ |
| **Dark/Light Themes** | Components support both themes | ✅ |

### Reference: tech.md

| Tech Spec | Alignment | Status |
|-----------|-----------|--------|
| **AppSync Sync Layer** | Conflict detection in sync flow | ✅ |
| **Timestamp-Based Resolution** | Last-write-wins (MVP) | ✅ |
| **Version Field** | Optimistic locking support | ✅ |

### Reference: DATA_MODEL_ALIGNMENT.md

| Data Model Spec | Alignment | Status |
|-----------------|-----------|--------|
| **§3 Conflict Resolution Strategy** | Implemented as specified | ✅ |
| **Version Field** | Used for conflict detection | ✅ |
| **device_id** | Tracks origin device | ✅ |
| **conflict_flag** | Set when detected | ✅ |

---

## 🚀 WHAT'S NEXT?

### Phase 1: MVP (Current)

✅ Conflict detection (version + timestamp)  
✅ Auto-resolution (teacher authority, last-write-wins)  
✅ Manual resolution UI (glass card modal)  
✅ Conflict logging (JSON Lines)  
✅ Integration with SyncOrchestrator  

**Status:** ✅ Complete

---

### Phase 2: Enhanced Resolution

- [ ] Field-level merge UI (user picks individual fields)
- [ ] DynamoDB conflict table (cloud storage)
- [ ] Teacher dashboard conflict alerts
- [ ] Multi-device conflict history
- [ ] Teacher override resolution
- [ ] Conflict analytics and trends

**Status:** 📋 Planned

---

### Phase 3: Advanced Features

- [ ] CRDT-based automatic merging
- [ ] Three-way merge (show common ancestor)
- [ ] Conflict prediction (ML-based)
- [ ] Collaborative editing support
- [ ] Operational transforms for real-time sync

**Status:** 🔮 Future

---

## 📖 KEY CONCEPTS

### Last-Write-Wins (MVP Default)

**Rule:** The version with the most recent `updated_at` timestamp wins.

**When to use:**
- Simple conflicts (single field)
- Student vs student (same device)
- Non-critical data

**When NOT to use:**
- Teacher vs student (use authority rule)
- Quiz scores (may want manual)
- Content edits (use teacher authority)

---

### Teacher Authority Rule

**Rule:** Teacher edits to content always win over student edits.

**Applies to:**
- Quiz content (questions, answers)
- Flashcard decks
- Assignments
- Lesson notes

**Does NOT apply to:**
- Student progress (quiz attempts, streaks)
- Chat history
- Preferences

---

### Field-Level Merge

**Rule:** Merge non-overlapping fields automatically.

**Example:**
```
Local:  {"streak": 6, "last_quiz_date": "2026-03-05"}
Cloud:  {"streak": 5, "total_attempted": 12}

Merged: {"streak": 6, "last_quiz_date": "2026-03-05", "total_attempted": 12}
        (streak uses MAX strategy, others merged)
```

---

## 🎨 UI DESIGN SPECS

### Conflict Badge (Dashboard Header)

- **Size:** 80px × 28px
- **Background:** `rgba(251, 92, 92, 0.1)`
- **Border:** 1px `#FA5C5C`
- **Text:** `#DC2626` (dark red)
- **Icon:** ⚠️ (16px)
- **Position:** Top-right, next to sync status

---

### Conflict Modal (Full-Screen)

- **Width:** 900px max, 90% viewport
- **Background:** Glass card (`rgba(255, 255, 255, 0.95)`)
- **Border-radius:** 20px
- **Padding:** 32px
- **Shadow:** `0 24px 60px rgba(15, 23, 42, 0.2)`
- **Backdrop:** Blur 16px

**Layout:**
- Header: Title + severity badge
- Body: Two-column comparison (local | cloud)
- Diff: Field-level highlights
- Footer: 4 action buttons + recommendation

---

### Diff Highlights

| Type | Color | Border | Icon | Text Decoration |
|------|-------|--------|------|-----------------|
| Added | `rgba(22, 163, 74, 0.1)` | 3px `#16A34A` | ✅ | None |
| Removed | `rgba(250, 92, 92, 0.1)` | 3px `#FA5C5C` | ❌ | line-through |
| Changed | `rgba(0, 168, 232, 0.1)` | 3px `#00A8E8` | ✨ | None |

---

## 📝 PLACEHOLDERS USED

The following placeholders are used for values not explicitly defined in requirements:

| Placeholder | Purpose | MVP Value |
|-------------|---------|-----------|
| `[DATA_VERSION_FIELD]` | Version tracking field | `version` |
| `[LAST_SYNC_TIMESTAMP_FIELD]` | Last sync time field | `last_sync_timestamp` |
| `[TIMESTAMP_TOLERANCE_SECONDS]` | Clock drift tolerance | 5 seconds |
| `[TEACHER_ID_PREFIX]` | Teacher ID prefix | `teacher_` |
| `[ENABLE_LAST_WRITE_WINS]` | Enable timestamp resolution | `True` |
| `[CONFLICT_PRIORITY_RULE]` | Teacher vs student | Teacher owns content |
| `[MERGE_STRATEGY_PLACEHOLDER]` | Field merge rules | MAX, SUM, RECALC |
| `[SYNC_RETRY_POLICY]` | Retry after resolution | Exponential backoff |

**Override placeholders in ConflictConfig:**

```python
config = ConflictConfig()
config.DATA_VERSION_FIELD = "v"  # If using "v" instead of "version"
config.TIMESTAMP_TOLERANCE_SECONDS = 10  # More tolerant
```

---

## 🏆 FEATURES COMPARISON

### MVP vs Phase 2 vs Phase 3

| Feature | MVP | Phase 2 | Phase 3 |
|---------|-----|---------|---------|
| Conflict detection | ✅ Version + timestamp | ✅ Same | ✅ Same |
| Last-write-wins | ✅ Yes | ✅ Yes | ✅ Yes |
| Teacher authority | ✅ Yes | ✅ Yes | ✅ Yes |
| Field-level merge | ✅ Auto only | ✅ + Manual UI | ✅ + CRDT |
| Manual resolution UI | ✅ Yes | ✅ Enhanced | ✅ 3-way merge |
| Conflict logging | ✅ Local JSONL | ✅ + DynamoDB | ✅ Same |
| Teacher dashboard | ⏳ Phase 2 | ✅ Alerts + history | ✅ Analytics |
| Multi-device history | ❌ No | ✅ Yes | ✅ Yes |
| Conflict prediction | ❌ No | ❌ No | ✅ ML-based |

---

## 💡 BEST PRACTICES

### 1. Always Check for Conflicts Before Sync

```python
# Good
pending = orchestrator.get_pending_conflicts()
if pending:
    show_conflict_modal()
else:
    orchestrator.execute_sync()

# Bad
orchestrator.execute_sync()  # May be blocked by conflicts
```

---

### 2. Use Debounced Sync to Reduce Conflicts

```python
# Good: Batch rapid changes
for i in range(5):
    save_local_change()
    orchestrator.enqueue_change(...)

orchestrator.trigger_sync_debounced()  # Single sync

# Bad: Sync after each change
for i in range(5):
    save_local_change()
    orchestrator.execute_sync()  # 5 syncs, higher conflict risk
```

---

### 3. Increment Version on Every Write

```python
# Good
data = load_user_stats()
data["version"] = data.get("version", 0) + 1
data["updated_at"] = datetime.now(timezone.utc).isoformat()
save_user_stats(data)

# Bad
data = load_user_stats()
data["score"] = 9  # Version not incremented
save_user_stats(data)
```

---

### 4. Use Authority Rules for Content

```python
# Set updated_by field for teacher edits
quiz_data["updated_by"] = "teacher_001"  # Auto-resolution will use teacher authority

# Student edits
quiz_data["updated_by"] = f"student_{user_id}"
```

---

## 📚 RELATED DOCUMENTATION

### System Documentation
- `README_SYNC_ORCHESTRATOR.md` — Base sync orchestration
- `docs/DATA_MODEL_ALIGNMENT.md` — Data model and versioning
- `docs/design_system.md` — UI design specs
- `.kiro/steering/tech.md` — Technology stack

### Conflict Resolution Suite
- `docs/CONFLICT_RESOLUTION_ENGINE.md` — Complete design (2000+ lines)
- `CONFLICT_RESOLUTION_INTEGRATION.md` — Integration guide
- `docs/CONFLICT_RESOLUTION_VISUAL_GUIDE.md` — Diagrams and flowcharts
- `example_conflict_resolution.py` — 10 usage examples

---

## 🎓 LEARNING RESOURCES

### For Developers

**Start here:**
1. Read this README (15 min)
2. Run `example_conflict_resolution.py` (5 min)
3. Read `CONFLICT_RESOLUTION_INTEGRATION.md` (20 min)
4. Review test cases in `tests/test_conflict_resolution.py` (15 min)

**Then:**
1. Integrate `ConflictAwareOrchestrator` (10 min)
2. Add UI components (20 min)
3. Test with simulated conflicts (10 min)

**Total:** ~1.5 hours to full integration

---

### For Designers

**UI Specs:**
1. Review `docs/CONFLICT_RESOLUTION_ENGINE.md` STEP 4 (UI design)
2. Review `docs/CONFLICT_RESOLUTION_VISUAL_GUIDE.md` (modal layout)
3. Check `design_system.md` (glass cards, colors, accessibility)

**Key Visual Elements:**
- Glass card modal with two-column layout
- Diff highlights (green/red/blue with icons)
- Action buttons (primary/secondary/ghost)
- Accessibility features (keyboard nav, focus rings)

---

### For QA Engineers

**Test Coverage:**
1. Run unit tests: `python tests/test_conflict_resolution.py`
2. Verify 22/22 tests passing
3. Review test scenarios in `example_conflict_resolution.py`
4. Manual testing checklist in `CONFLICT_RESOLUTION_INTEGRATION.md`

**Test Scenarios:**
- Concurrent edits detection
- Teacher authority resolution
- Field-level merge
- Manual resolution flow
- Clock drift tolerance
- Logging and audit trail

---

## ❓ FAQ

### Q: Do I need AWS to test conflicts?

**A:** No! Conflict engine works entirely locally. AWS is only needed when syncing to teacher dashboard.

---

### Q: What happens if I ignore a conflict?

**A:** Conflict remains pending. Sync is paused for that entity. Student can continue learning; only sync is blocked. UI shows persistent warning.

---

### Q: Can conflicts occur offline?

**A:** No. Conflicts are detected only during sync attempt (when comparing local vs cloud). Offline edits always succeed locally.

---

### Q: What if both versions are equally valid?

**A:** User chooses via manual resolution UI. Phase 2 adds "Keep Both" option to store multiple versions.

---

### Q: How are nested conflicts handled?

**A:** Recursive merge logic detects nested conflicts. If unsafe, entire object marked for manual resolution.

---

### Q: Can teacher resolve conflicts on student's behalf?

**A:** Phase 2 feature. MVP requires student to resolve. Teacher can view conflicts in dashboard.

---

### Q: What if conflict occurs during Panic Mode (exam)?

**A:** Conflict detection skipped during Panic Mode. Sync happens after exam completion. Prevents disrupting timed assessment.

---

## 📞 SUPPORT

### Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# See detailed conflict detection logs
```

### Common Issues

See **TROUBLESHOOTING** section above.

### Documentation Issues

If you find errors or unclear documentation:
1. Check `docs/CONFLICT_RESOLUTION_ENGINE.md` for details
2. Review examples in `example_conflict_resolution.py`
3. Run tests to see expected behavior

---

## 🎉 SUMMARY

**What You Get:**
- ✅ 600+ lines of production-ready conflict resolution code
- ✅ 400+ lines of UI components (Streamlit)
- ✅ 400+ lines of unit tests (22 tests, 95% coverage)
- ✅ 2000+ lines of design documentation
- ✅ Visual diagrams and flowcharts
- ✅ Integration guide with code examples
- ✅ 10 usage examples demonstrating all features

**Integration Time:** ~1.5 hours

**Dependencies:** None (uses Python standard library)

**AWS Required:** No (for local testing)

**Status:** ✅ Ready to integrate into Streamlit app

---

**Next Steps:**
1. Run tests: `python tests/test_conflict_resolution.py`
2. Run examples: `python example_conflict_resolution.py`
3. Follow integration guide: `CONFLICT_RESOLUTION_INTEGRATION.md`
4. Add to app: Replace `SyncOrchestrator` with `ConflictAwareOrchestrator`

---

**Questions?** See full design spec in `docs/CONFLICT_RESOLUTION_ENGINE.md` or integration guide in `CONFLICT_RESOLUTION_INTEGRATION.md`.
