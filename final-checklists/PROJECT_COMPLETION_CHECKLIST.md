# Studaxis — Project Completion Checklist

> **Purpose:** Everything left to make the project complete (local + AWS).  
> **Reference:** `docs/INTEGRATION_CHECKLIST.md`, `docs/AWS_INTEGRATION_CHECKLIST.md`, `.kiro/`, `backend/`, `frontend/`

---

## 1. Core User Flow Fixes (Priority)

| # | Check | Current Issue | Fix |
|---|-------|---------------|-----|
| □ | Auth flow: OTP → /onboarding | Auth signup navigates to /onboarding with `startFrom="role"` (ignores state); user skips OTP | Pass `startFrom` from `location.state` in OnboardingFlow route; or add OTP step to Auth |
| □ | Auth flow: /login vs /onboarding | After OTP on /login, user stays on /login (role step); never goes to /onboarding URL | Either navigate to /onboarding after OTP, or document that /login = full flow |
| □ | Profile/user scoping | `profile.json`, `user_stats.json` are global (single-user); `/api/user/profile`, `/api/user/stats` not auth-protected | Scope by JWT `user_id`; require `get_current_user`; use per-user files or DynamoDB |
| □ | Dashboard redirect | Redirects to `/auth/login` if `!profile.profile_name`; may flash on slow load | Consider loading state; ensure profile saved before navigate |

---

## 2. Backend — Data & API Gaps

### 2.1 Multi-User / Scoping

| # | Check | Current | Target |
|---|-------|---------|--------|
| □ | Profile per user | `profile_store.py` single file | `load_profile(user_id)`, `save_profile(user_id, profile)`; or DynamoDB |
| □ | User stats per user | `_load_user_stats()` single file | `_load_user_stats(user_id)`; path `data/{user_id}/user_stats.json` or DynamoDB |
| □ | Flashcards per user | `flashcards.json` single file | `data/{user_id}/flashcards.json` or S3 key |
| □ | Auth-protect profile API | `GET/POST /api/user/profile` no auth | Add `Depends(get_current_user)`; scope by `current_user.id` |
| □ | Auth-protect user stats API | `GET/PUT /api/user/stats` no auth | Add `Depends(get_current_user)`; scope by `current_user.id` |

### 2.2 Stubs & Placeholders

| # | Check | Location | Fix |
|---|-------|----------|-----|
| □ | Quiz stub content | `main.py` `_QUIZ_ITEMS` — returns stub for known ids | Wire to real quiz storage or Bedrock-generated content |
| □ | Grading rubric placeholder | `main.py` `"[GRADING_RUBRIC_PLACEHOLDER]"` | Replace with real rubric from config or prompt |
| □ | AI prompt placeholders | `ai_integration_layer.py` | Finalize model/template config; remove unresolved placeholders |
| □ | Sync stub (README) | README says "stub" | Sync is wired to SyncManager; update README or verify behavior |

### 2.3 Export & Settings

| # | Check | Location | Fix |
|---|-------|----------|-----|
| □ | Settings import bug | `backend/pages/settings.py` imports `load_user_stats, save_user_stats` from `profile_store` | `profile_store` has `load_profile`/`save_profile`; use `preferences` for user_stats |
| □ | Export data (Settings) | `backend/pages/settings.py` "Feature coming soon" | Implement export in React Settings; `GET /api/data/export` exists — wire UI |
| □ | Export includes user-scoped data | `main.py` `data_export` | Scope by `user_id` when multi-user |
| □ | Clear data preserves auth | `POST /api/data/clear` | Does not delete users.db; document; consider user-scoped clear |

### 2.4 Data Path Consistency

| # | Check | Current | Fix |
|---|-------|---------|-----|
| □ | `user_stats.json` path | `backend/data/` when run from backend; `data/` at repo root? | `BASE_PATH` / `STUDAXIS_BASE_PATH`; ensure single source |
| □ | `profile.json` path | `profile_store.PROFILE_FILE` = `backend/data/profile.json` | Align with `BASE_PATH` when backend runs from root |
| □ | ChromaDB path | `CHROMA_DB_PATH` vs `data/chromadb` | Document; ensure RAG uses correct path |
| □ | Multiple `load_user_stats` impls | `preferences.py`, `local_storage.py`, `main.py`, `pages/dashboard.py` | Consolidate; use single source (e.g. `main._load_user_stats` or shared util) |
| □ | Streamlit settings import bug | `pages/settings.py` imports `load_user_stats, save_user_stats` from `profile_store` | `profile_store` has `load_profile` only; change to `from preferences import load_user_stats, save_user_stats` |

---

## 3. Frontend — Gaps & Placeholders

### 3.1 Pages & Components

| # | Check | Location | Fix |
|---|-------|----------|-----|
| □ | ErrorDemo page | `ErrorDemo.tsx` — "Error UI demo placeholder" | Implement real error states (timeout, sync fail, corrupt file) or remove |
| □ | BootFlow vs OnboardingFlow | BootFlow has name/class inputs; OnboardingFlow has full flow | Clarify when each is used; avoid duplication |
| □ | Settings Export button | Settings page | Wire to `GET /api/data/export`; trigger download |
| □ | Settings Clear data | Settings page | Wire to `POST /api/data/clear`; confirm dialog |

### 3.2 Teacher Dashboard (React)

| # | Check | Location | Fix |
|---|-------|----------|-----|
| □ | Students page | `PLACEHOLDER_STUDENTS` mock data | Connect to DynamoDB/AppSync or backend API |
| □ | Dashboard overview | `DashboardOverview.tsx` mock data | Real metrics from `studaxis-student-sync` |
| □ | CloudSyncStatus | Placeholder badge | Wire to sync status API |
| □ | Manual sync button | UI only | Call `POST /api/sync` or teacher backend |
| □ | Analytics/GraphPlaceholder | Placeholder charts | Real data from student progress |

### 3.3 Config & Build

| # | Check | Fix |
|---|-------|-----|
| □ | `VITE_API_URL` for production | Add to build; use when `API_BASE` empty and prod |
| □ | `main.py` vs `run.py` | `run.py` is canonical bootstrapper; `main.py` at root loads backend — align docs |

---

## 4. Sync & Conflict Resolution

| # | Check | Current | Fix |
|---|-------|---------|-----|
| □ | SyncManager AppSync env | `APPSYNC_ENDPOINT`, `APPSYNC_API_KEY` empty locally | Document; set when deploying to AWS |
| □ | Sync status in UI | Settings/Sync page | Show real queue, last sync, errors from `GET /api/sync/status` |
| □ | Conflict UI | Conflicts page | Wire to `GET /api/sync/conflicts`; resolve flow |
| □ | Conflict orchestrator | `ConflictAwareOrchestrator` | Ensure integrated in sync flow; test conflict detection |

---

## 5. Streamlit Legacy (Optional Cleanup)

| # | Check | Location | Fix |
|---|-------|----------|-----|
| □ | Streamlit app | `backend/streamlit_app.py` | Deprecated for React; remove or keep for teacher dashboard? |
| □ | Streamlit pages | `backend/pages/` | Chat, quiz, flashcards, panic_mode — "coming soon" stubs; React has real impl |
| □ | Deployment UI placeholders | `deployment_ui.py` | Wire real env/build values or remove |
| □ | Notifications UI | `notifications_ui.py` | Placeholder-driven; wire real data or remove |
| □ | Error demo (Streamlit) | `pages/error_demo.py` | Placeholder vars; align with React ErrorDemo or remove |

---

## 6. Testing & Quality

| # | Check | Fix |
|---|-------|-----|
| □ | Backend unit tests | `backend/tests/` | Run `pytest`; add tests for auth, profile, sync |
| □ | Lambda tests | `aws-infra/lambda/lambda_test_runner.py` | Run with mocks; add real AWS integration tests |
| □ | E2E user flow test | None | Add Playwright/Cypress: signup → OTP → onboarding → dashboard |
| □ | Linting / type check | Frontend `tsc`, backend | Add to CI; fix any errors |

---

## 7. Documentation & Config

| # | Check | Fix |
|---|-------|-----|
| □ | README run instructions | Port 6782 vs 8000 | Align with `run.py` (6782); update ARCHITECTURE_NEW if needed |
| □ | `.env.example` | Incomplete? | Add all required vars: OLLAMA, CHROMA, JWT, SMTP, AWS |
| □ | `run.py` vs `main.py` | Two entrypoints | Document: `run.py` for dev (opens browser); `main.py` for uvicorn direct |
| □ | Data directory layout | `backend/data/` vs `data/` | Document; ensure `BASE_PATH` resolves correctly |

---

## 8. AWS Integration (Deployment)

See `docs/AWS_INTEGRATION_CHECKLIST.md` for full list. Summary:

| # | Check |
|---|-------|
| □ | Swap profile.json → DynamoDB |
| □ | Swap console OTP → SES |
| □ | Add S3 sync for progress data |
| □ | Deploy FastAPI → EC2/ECS |
| □ | Deploy React → S3 + CloudFront |
| □ | Teacher dashboard → Amplify + real DynamoDB/S3 |
| □ | AppSync + Lambda wired and deployed |

---

## 9. Suggested Completion Order

### Phase A — Local Completeness (No AWS)
1. Fix auth flow (OTP → onboarding routing)
2. Scope profile + user_stats + flashcards by user_id
3. Auth-protect `/api/user/profile` and `/api/user/stats`
4. Wire Settings Export/Clear in frontend
5. Replace quiz/grading placeholders
6. ErrorDemo: implement or remove

### Phase B — Sync & Conflicts
7. Document AppSync env; verify SyncManager when online
8. Wire sync status + conflict UI in frontend
9. Test conflict resolution flow

### Phase C — Teacher Dashboard
10. Replace mock data with real API/DynamoDB
11. Deploy to Amplify

### Phase D — AWS Migration
12. Follow `docs/AWS_INTEGRATION_CHECKLIST.md` phases 1–5

---

## 10. Quick Reference

| Doc | Purpose |
|-----|---------|
| `docs/INTEGRATION_CHECKLIST.md` | Verify frontend ↔ backend ↔ Ollama integration |
| `docs/AWS_INTEGRATION_CHECKLIST.md` | AWS migration steps |
| `docs/PROJECT_COMPLETION_CHECKLIST.md` | This file — remaining work |
| `backend/INTEGRATION_CHECKLIST.md` | SyncOrchestrator integration |
| `backend/CONFLICT_RESOLUTION_INTEGRATION.md` | Conflict engine integration |

---

*Last updated: 2026-03*
