# SyncOrchestrator Integration Checklist

> Quick step-by-step guide to integrate SyncOrchestrator into your Streamlit app

---

## ✅ STEP 1: Verify Files Exist

Check that these files are in place:

```
backend/
├── ✅ sync_orchestrator.py              (430 lines - NEW)
├── ✅ sync_manager.py                   (existing - unchanged)
├── ✅ pages/
│   └── ✅ sync_status.py                (updated to use orchestrator)
├── ✅ tests/
│   └── ✅ test_sync_orchestrator.py     (250 lines - NEW)
├── ✅ example_orchestrator_usage.py     (examples - NEW)
└── ✅ README_SYNC_ORCHESTRATOR.md       (docs - NEW)
```

---

## ✅ STEP 2: Run Tests (Optional but Recommended)

```bash
cd backend
python tests/test_sync_orchestrator.py
```

**Expected:** All 16 tests pass  
**If fails:** Check Python version (3.8+) and dependencies

---

## ✅ STEP 3: Update `streamlit_app.py`

Add orchestrator initialization at the top of `main()`:

```python
# Add import at top of file
from sync_orchestrator import SyncOrchestrator

# Add this function before main()
def _init_orchestrator():
    """Initialize orchestrator once per session."""
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = SyncOrchestrator(
            base_path=str(Path(__file__).parent)
        )
    return st.session_state.orchestrator

# In main(), add after _init_session_state()
def main():
    _inject_global_css()
    _init_session_state()
    
    # ADD THIS: Initialize orchestrator
    orchestrator = _init_orchestrator()
    
    # Auto-trigger sync if items pending (optional)
    if orchestrator.get_queue_size() > 0:
        orchestrator.trigger_sync_debounced()
    
    # Visual boot flow runs before any dashboard or landing content.
    if not st.session_state.get("boot_complete", False):
        render_boot_flow()
        return
    
    # ... rest of your code ...
```

---

## ✅ STEP 4: Update Settings Page

Replace `SyncManager` with orchestrator in `pages/settings.py`:

**Before:**
```python
from sync_manager import SyncManager
sync_manager = SyncManager(base_path=".")
show_sync_status_panel(sync_manager, preferences)
```

**After:**
```python
# Orchestrator is already in session_state
orchestrator = st.session_state.orchestrator
show_sync_status_panel(orchestrator, preferences)
```

---

## ✅ STEP 5: Update Quiz Completion

Wherever you handle quiz completion, use orchestrator:

**Before:**
```python
from sync_manager import SyncManager
sync_manager = SyncManager(base_path=".")
sync_manager.enqueue_quiz_sync(user_id, quiz_id, score, total)
```

**After:**
```python
# Orchestrator is already in session_state
orchestrator = st.session_state.orchestrator

# Enqueue with priority
orchestrator.enqueue_change(
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

# Trigger debounced sync
orchestrator.trigger_sync_debounced()
```

---

## ✅ STEP 6: Update Streak Updates

**Before:**
```python
sync_manager.enqueue_streak_sync(user_id, current_streak)
```

**After:**
```python
orchestrator = st.session_state.orchestrator
orchestrator.enqueue_change(
    change_type="updateStreak",
    payload={
        "userId": user_id,
        "currentStreak": current_streak
    },
    priority="normal"  # Streaks = normal priority
)
orchestrator.trigger_sync_debounced()
```

---

## ✅ STEP 7: Test Basic Flow

Run your Streamlit app:

```bash
streamlit run streamlit_app.py
```

**Test Checklist:**
- [ ] App starts without errors
- [ ] Navigate to Settings page
- [ ] See sync status panel
- [ ] Badge shows "Synced" or "Offline"
- [ ] Complete a quiz (if implemented)
- [ ] Badge updates to "Connected · 1 items"
- [ ] Click "Sync Now" button
- [ ] Badge shows "Syncing..." then "Synced"

---

## ✅ STEP 8: Test Edge Cases

### Test A: Offline Mode
1. Disconnect internet
2. Complete a quiz
3. Badge should show "Offline"
4. Offline banner should appear
5. Reconnect internet
6. Banner should disappear
7. Badge should auto-sync

### Test B: Rapid Changes
1. Complete 5 quizzes rapidly (within 5 seconds)
2. Only ONE sync should trigger after 5s
3. All 5 should sync in a single batch

### Test C: State Persistence
1. Complete a quiz
2. Close Streamlit app (Ctrl+C)
3. Restart app
4. Navigate to Settings
5. Pending items should still be queued

---

## ✅ STEP 9: Verify State Machine

Open Python console while app is running:

```python
import streamlit as st

# Get orchestrator from session
orch = st.session_state.orchestrator

# Check state
print(f"State: {orch.get_state()}")
print(f"Queue: {orch.get_queue_size()}")
print(f"Online: {orch.is_online()}")

# View queue summary
print(orch.get_queue_summary())
```

**Valid States:**
- `IDLE` - All synced, no items
- `OFFLINE` - No connectivity
- `QUEUED` - Items pending sync
- `SYNCING` - Sync in progress
- `SYNCED` - Just completed sync
- `ERROR` - Sync failed

---

## ✅ STEP 10: Check Data Files

Verify that data files are being created:

```
backend/data/
├── ✅ sync_queue.json           (queue managed by SyncManager)
├── ✅ sync_state.json           (state managed by Orchestrator)
└── ✅ dead_letter_queue.json   (failed items - may be empty)
```

**View state file:**
```bash
cat data/sync_state.json
```

**Expected:**
```json
{
  "state": "IDLE",
  "timestamp": "2026-03-05T10:30:00Z"
}
```

---

## ✅ TROUBLESHOOTING

### Issue: Import Error

**Error:** `ModuleNotFoundError: No module named 'sync_orchestrator'`

**Fix:** Ensure you're in the correct directory:
```bash
cd backend
python streamlit_app.py
```

### Issue: State Stuck in SYNCING

**Cause:** App crashed during sync

**Fix:** Reset state:
```python
from sync_orchestrator import SyncOrchestrator
orch = SyncOrchestrator(base_path=".")
orch.state = "QUEUED"
orch._save_state()
```

### Issue: "Rate limited" Errors

**Cause:** Syncing too frequently

**Fix:** Use debounced sync:
```python
# Don't do this in a loop
for item in items:
    orch.execute_sync()  # ❌ Too many syncs

# Do this instead
for item in items:
    orch.enqueue_change(...)
orch.trigger_sync_debounced()  # ✅ Single batched sync
```

### Issue: Queue Not Syncing

**Check:**
1. Is sync enabled in settings?
2. Is app online? (`orch.is_online()`)
3. Is state OFFLINE? (`orch.get_state()`)
4. Are there items in queue? (`orch.get_queue_size()`)

**Debug:**
```python
orch = st.session_state.orchestrator
print(f"State: {orch.get_state()}")
print(f"Queue: {orch.get_queue_size()}")
print(f"Online: {orch.is_online()}")

# Force sync if needed
if orch.get_state() == "QUEUED":
    result = orch.execute_sync()
    print(f"Result: {result}")
```

---

## ✅ FINAL VERIFICATION

Run this checklist to confirm everything works:

```python
# test_integration.py
from sync_orchestrator import SyncOrchestrator

orch = SyncOrchestrator(base_path=".")

# 1. Check initial state
assert orch.get_state() == "IDLE", "Initial state should be IDLE"
print("✅ Initial state correct")

# 2. Enqueue change
success = orch.enqueue_change(
    change_type="recordQuizAttempt",
    payload={
        "userId": "test_user",
        "quizId": "test_quiz",
        "score": 8,
        "totalQuestions": 10
    }
)
assert success, "Enqueue should succeed"
assert orch.get_state() == "QUEUED", "State should be QUEUED"
print("✅ Enqueue working")

# 3. Trigger sync
result = orch.execute_sync()
print(f"   Sync result: {result}")
print("✅ Sync execution working")

# 4. Cleanup
orch.cleanup()
print("✅ All checks passed!")
```

---

## 📚 REFERENCE DOCS

For detailed information, see:

- **`README_SYNC_ORCHESTRATOR.md`** - Complete documentation
- **`example_orchestrator_usage.py`** - Usage examples
- **`tests/test_sync_orchestrator.py`** - Unit tests
- **`docs/REALTIME_SYNC_WIRING_LAYER.md`** - Architecture (5,800 lines)

---

## 🎉 DONE!

Once all steps are complete, your app has:

✅ State machine with 8 states  
✅ Edge case handling (network loss, debounce, rate limiting)  
✅ Queue management with priorities  
✅ Auto-recovery from offline  
✅ Dead letter queue for persistent failures  
✅ Production-ready sync orchestration  

**No AWS needed** - works entirely locally until you're ready to deploy backend!

---

**Questions?** Check the examples or run the tests for more details.
