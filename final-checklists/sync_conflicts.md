# Sync Conflicts — Detection and Resolution

> Offline/online sync conflicts when local and cloud data diverge.

---

## Overview

Conflicts arise when:
- **Local** changes (e.g. quiz attempts, streak) exist on the device
- **Cloud** has a different version of the same entity (e.g. from another device or teacher update)
- Both were modified after the last sync

The system detects these during sync and presents them on the Conflicts page for user resolution.

---

## Resolution Strategy (Order of Application)

1. **Identical edits** (`auto_identical`)
   - Local and cloud content are semantically identical (false conflict)
   - Use cloud version

2. **Authority rules** (`auto_authority`)
   - **Teacher-owned** (Quiz, FlashcardDeck, Assignment, LessonNotes): Teacher version wins
   - **Student-owned** (QuizAttempt, StreakRecord, ChatHistory, FlashcardStats): Local (student) wins

3. **Field-level merge** (`auto_merge`)
   - Non-overlapping fields → merge both
   - Numeric stats use merge strategies (`max`, `sum`, `recalculate`)

4. **Last-write-wins** (`auto_timestamp`)
   - Compare `updated_at`; newer version wins
   - Fallback when authority/merge don't apply

5. **Manual resolution** (`manual_*`)
   - When auto-resolution fails, conflict is saved to pending and shown in UI
   - User chooses: **Keep Local**, **Keep Cloud**, or **Merge Both**

---

## Manual Resolution Options

| Choice        | Meaning                                                   |
|---------------|-----------------------------------------------------------|
| `keep_local`  | Use this device's version; overwrite cloud on next sync  |
| `keep_cloud`  | Use cloud version; overwrite local                        |
| `merge`       | Merge non-overlapping fields; numeric fields use `max`   |

---

## API

| Endpoint                                           | Auth | Scope   | Description                         |
|----------------------------------------------------|------|---------|-------------------------------------|
| `GET /api/sync/conflicts`                          | JWT  | `user_id` | List pending conflicts              |
| `POST /api/sync/conflicts/{entity_id}/resolve`     | JWT  | `user_id` | Resolve with `{ "choice": "…" }`   |

Conflicts are stored at `data/users/{user_id}/pending_conflicts.json` (per-user).

---

## Frontend

- **Conflicts page** (`/conflicts`): Lists conflicts, shows local vs cloud, offers Keep Local / Keep Cloud / Merge
- **Route guard**: Under `ProtectedRoute` (requires authentication + profile)
- **API**: `getSyncConflicts()`, `resolveConflict(entityId, choice)`

---

## When Conflicts Are Created

Conflicts are written to `pending_conflicts.json` when:
- Sync detects version/timestamp divergence between local and cloud
- Auto-resolution returns `PENDING` → engine saves to pending and sync is blocked until resolved

The sync flow (e.g. `ConflictAwareOrchestrator` or `SyncManager` + conflict check) should call `ConflictResolutionEngine.detect_conflict()` before applying cloud data; if resolution is manual, call `engine.save_pending_conflict(conflict)` with a **user-scoped** engine (`ConflictResolutionEngine(base_path, user_id=user_id)`).
