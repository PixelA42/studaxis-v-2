# Studaxis — Full-Stack Integration Checklist

> **Purpose:** Verify all integration points from frontend → backend → Ollama/ChromaDB → AWS.  
> **Reference:** `.kiro/DOCS_NEW/ARCHITECTURE_NEW.md`, `backend/INTEGRATION_CHECKLIST.md`, `aws-infra/`

---

## 1. Runtime & Servers

| # | Check | Notes |
|---|-------|-------|
| □ | FastAPI running on `localhost:6782` (or `8000` if configured) | Default: `python run.py` or `uvicorn backend.main:app --port 6782` |
| □ | React dev server on `localhost:5173` (Vite) | `cd frontend && npm run dev` — proxies `/api` to backend |
| □ | Ollama running on `localhost:11434` | Required for chat, grading, flashcards, panic mode |
| □ | ChromaDB initialized (RAG) | `data/chromadb/` or `CHROMA_DB_PATH` — needed for `/api/rag/search`, chat RAG |
| □ | Port alignment: `VITE_API_PORT` matches `run.py --port` | Dev: set `VITE_API_PORT=6782` if backend ≠ 6782 |

---

## 2. Frontend → Backend (React → FastAPI)

### 2.1 API Base & Proxy

| # | Check | Endpoint | Notes |
|---|-------|----------|-------|
| □ | React calls real endpoints (not mocks) | `API_BASE = ""` in `api.ts` | Relative `/api` — works with proxy (dev) or same-origin (prod) |
| □ | Vite proxy forwards `/api` to backend | `vite.config.ts` | Target: `http://localhost:${VITE_API_PORT \|\| 6782}` |
| □ | CORS allows frontend origin | `main.py` | Origins: 5173, 3000, 6782, 6783 |

### 2.2 Auth Flow

| # | Check | Endpoint | Notes |
|---|-------|----------|-------|
| □ | Signup → OTP printed to console | `POST /api/auth/signup` | `_send_otp_email` prints `[OTP] email → code` |
| □ | OTP verification returns JWT | `POST /api/auth/verify-otp` | Returns `access_token`, `onboarding_complete` |
| □ | Login returns JWT | `POST /api/auth/login` | Username or email + password |
| □ | JWT sent in `Authorization: Bearer` | `api.ts` | `localStorage.getItem(STORAGE_TOKEN)` |
| □ | 401 triggers logout + redirect | `setUnauthorizedHandler` | Redirects to `/auth/login` |
| □ | Complete onboarding persists profile | `POST /api/auth/complete-onboarding` | Writes to `profile.json` |

### 2.3 User & Profile

| # | Check | Endpoint | Notes |
|---|-------|----------|-------|
| □ | Profile saved to `profile.json` | `POST /api/user/profile`, `load_profile()` | `backend/data/profile.json` |
| □ | User stats loaded | `GET /api/user/stats` | `user_stats.json` |
| □ | User stats updated | `PUT /api/user/stats` | Preferences, theme, streak, etc. |
| □ | Current user (JWT decode) | `GET /api/user/me` | Auth-protected |

### 2.4 Dashboard

| # | Check | Endpoint | Notes |
|---|-------|----------|-------|
| □ | Dashboard loads real user data | `GET /api/user/stats` | Streak, quiz stats, flashcard stats |
| □ | Dashboard flashcards | `GET /api/dashboard/flashcards` | Due/review cards |
| □ | Hardware status | `GET /api/hardware` | CPU, RAM, Ollama status |
| □ | Health check | `GET /api/health` | Liveness |
| □ | Ollama ping (boot gate) | `GET /api/ollama/ping` | Blocks app until Ollama ready |

---

## 3. AI & RAG (Ollama + ChromaDB)

| # | Check | Endpoint / Component | Notes |
|---|-------|----------------------|-------|
| □ | AI chat calling Ollama locally | `POST /api/chat` | `ai_integration_layer.py` → `OLLAMA_API_URL` |
| □ | Chat uses RAG context (when available) | `/api/chat` + ChromaDB | RAG chunks injected into prompt |
| □ | RAG search (semantic) | `GET /api/rag/search?q=&k=5` | ChromaDB vector search |
| □ | Flashcard generation (Ollama) | `POST /api/flashcards/generate/*` | textbook, weblink, files |
| □ | Flashcard explain | `POST /api/flashcards/explain` | Ollama |
| □ | Study recommendation | `POST /api/study/recommendation` | Ollama |
| □ | Quiz grading | `POST /api/grade` | Ollama (subjective/objective) |

---

## 4. Exam / Panic Mode

| # | Check | Endpoint | Notes |
|---|-------|----------|-------|
| □ | Exam mode generates questions from local PDF | `POST /api/quiz/panic/generate/textbook` | Textbook ID → RAG + Ollama |
| □ | Exam mode from weblink | `POST /api/quiz/panic/generate/weblink` | URL → fetch + RAG |
| □ | Exam mode from uploaded files | `POST /api/quiz/panic/generate/files` | FormData upload |
| □ | Per-question grading | `POST /api/quiz/panic/grade-one` | Ollama grading |
| □ | Finalize panic quiz | `POST /api/quiz/panic/finalize` | Persist scores, sync |
| □ | Regular quiz submit | `POST /api/quiz/{id}/submit` | Grade + update stats |

---

## 5. Flashcards

| # | Check | Endpoint | Notes |
|---|-------|----------|-------|
| □ | List flashcards | `GET /api/flashcards` | From `flashcards.json` |
| □ | Due flashcards | `GET /api/flashcards/due` | SRS logic |
| □ | Append flashcards | `POST /api/flashcards` | Merge with storage |
| □ | Update flashcards | `PUT /api/flashcards` | Replace storage |
| □ | Generate from textbook | `POST /api/flashcards/generate/textbook` | RAG + Ollama |
| □ | Generate from weblink | `POST /api/flashcards/generate/weblink` | Fetch + RAG |
| □ | Generate from files | `POST /api/flashcards/generate/files` | FormData |

---

## 6. Textbooks & Storage

| # | Check | Endpoint | Notes |
|---|-------|----------|-------|
| □ | List textbooks | `GET /api/textbooks` | `data/sample_textbooks/` |
| □ | Upload textbook | `POST /api/textbooks/upload` | Saves to `sample_textbooks/` |
| □ | Storage files list | `GET /api/storage/files` | Settings panel |
| □ | RAG uses uploaded PDFs | ChromaDB | Embeddings from `sample_textbooks/` |

---

## 7. Sync & Conflicts

| # | Check | Endpoint | Notes |
|---|-------|----------|-------|
| □ | Sync status | `GET /api/sync/status` | Queue, state, last sync |
| □ | Trigger sync | `POST /api/sync` | Push to AWS (when online) |
| □ | List conflicts | `GET /api/sync/conflicts` | ConflictAwareOrchestrator |
| □ | Resolve conflict | `POST /api/sync/conflicts/{id}/resolve` | Merge/resolve |
| □ | Sync manager enqueues quiz/streak | `SyncManager` | After quiz, panic mode |

---

## 8. Settings & Data

| # | Check | Endpoint | Notes |
|---|-------|----------|-------|
| □ | Export data | `GET /api/data/export` | JSON backup |
| □ | Clear data | `POST /api/data/clear` | Reset stats, flashcards, profile |
| □ | Diagnostics | `GET /api/diagnostics` | Debug info |
| □ | Theme persisted via user stats | `PUT /api/user/stats` | `preferences.theme` |

---

## 9. Teacher Dashboard (AWS)

| # | Check | Component | Notes |
|---|-------|-----------|-------|
| □ | Teacher dashboard URL configurable | `VITE_TEACHER_DASHBOARD_URL` | Default: `https://teacher.studaxis.com` |
| □ | Onboarding links to teacher dashboard | `OnboardingFlow.tsx` | For teacher role |
| □ | Teacher dashboard runs locally | `aws-infra/teacher-dashboard-web` | `npm run dev` |
| □ | Teacher dashboard builds for Amplify | `npm run build` | Static hosting |
| □ | Teacher dashboard connects to cloud data | AppSync / API | UI only per README — backend TBD |
| □ | Cloud sync status in teacher UI | `CloudSyncStatus`, `SyncStatusBadge` | Placeholder / mock until wired |

---

## 10. AWS Infrastructure (when online)

| # | Check | Service | Notes |
|---|-------|---------|-------|
| □ | S3 buckets exist | studaxis-student-stats, studaxis-content, studaxis-payloads | Per `.kiro/steering/tech.md` |
| □ | DynamoDB table | studaxis-student-sync | Sync metadata |
| □ | AppSync GraphQL | Delta sync | Conflict resolution |
| □ | Lambda functions | Quiz gen, sync resolvers | Bedrock, S3, DynamoDB |
| □ | API Gateway | REST for quiz generation | IAM auth |

---

## 11. Local Data Files

| # | Check | Path | Notes |
|---|-------|------|-------|
| □ | `profile.json` | `backend/data/profile.json` | Profile, onboarding_complete |
| □ | `user_stats.json` | `backend/data/user_stats.json` | Streak, quiz stats, preferences |
| □ | `flashcards.json` | `backend/data/flashcards.json` | Flashcard storage |
| □ | `users.db` | `backend/data/users.db` | SQLite auth |
| □ | `chromadb/` | `data/chromadb/` or `CHROMA_DB_PATH` | Vector store |
| □ | `sample_textbooks/` | `backend/data/sample_textbooks/` | Uploaded PDFs |
| □ | `sync_queue.json` | `backend/data/` | SyncManager queue |
| □ | `sync_state.json` | `backend/data/` | SyncOrchestrator state |

---

## 12. Environment & Config

| # | Check | Variable | Notes |
|---|-------|----------|-------|
| □ | `OLLAMA_BASE_URL` | Default `http://localhost:11434` | Backend Ollama ping |
| □ | `OLLAMA_HOST` | `.env.example` | For Ollama client |
| □ | `CHROMA_DB_PATH` | Default `./data/chromadb` | RAG vector store |
| □ | `STUDAXIS_BASE_PATH` | Backend data root | When run from repo root |
| □ | `STUDAXIS_JWT_SECRET` | Auth | Change in production |
| □ | `STUDAXIS_SMTP_HOST` | Email verification | Local dev: OTP print only |
| □ | `VITE_API_PORT` | Frontend proxy target | Match `run.py --port` |
| □ | `VITE_TEACHER_DASHBOARD_URL` | Teacher link | Default teacher.studaxis.com |

---

## 13. Core User Flow (E2E)

| # | Check | Flow | Notes |
|---|-------|------|-------|
| □ | New user signup → OTP in console | Auth / OnboardingFlow | Backend prints OTP |
| □ | OTP verify → JWT | `postVerifyOtp` | Token stored in localStorage |
| □ | After OTP → onboarding steps | role → profile → setup | Route: `/onboarding` or `/login` |
| □ | Onboarding complete → dashboard | `navigate("/dashboard")` | |
| □ | Refresh on dashboard → stay logged in | Token + profile in localStorage | AuthProvider restores state |
| □ | Dashboard shows real streak/stats | `getUserStats()` | From `user_stats.json` |
| □ | Profile name present after onboarding | `profile.profile_name` | Dashboard redirects if missing |

---

## 14. Related Docs

- **Architecture:** `.kiro/DOCS_NEW/ARCHITECTURE_NEW.md`
- **Tech stack:** `.kiro/steering/tech.md`
- **Structure:** `.kiro/steering/structure.md`
- **Sync orchestrator:** `backend/README_SYNC_ORCHESTRATOR.md`
- **Conflict resolution:** `backend/CONFLICT_RESOLUTION_INTEGRATION.md`
- **Teacher dashboard:** `aws-infra/teacher-dashboard-web/README.md`
- **AWS specs:** `.kiro/specs/aws-infrastructure-elevation/`

---

## Quick Run Commands

```bash
# Backend (from repo root)
python run.py
# or: uvicorn backend.main:app --reload --host 0.0.0.0 --port 6782

# Frontend dev
cd frontend && npm run dev

# Frontend build (for SPA serving by FastAPI)
cd frontend && npm run build

# Teacher dashboard
cd aws-infra/teacher-dashboard-web && npm run dev
```

---

*Last updated: 2026-03*
