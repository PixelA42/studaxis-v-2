Studaxis Migration: Streamlit → React (Vite/TS/Tailwind) + FastAPI
Stage 1 — Analysis & Execution Plan
1. Architecture Summary (Source of Truth)
Reference: .kiro/DOCS_NEW/ARCHITECTURE_NEW.md

Runtime: Offline-first, browser-based. Python bootstrapper starts FastAPI (uvicorn), serves React dist at /, exposes REST at /api/*, and can open http://localhost:8000.
Design system: “Thermal Vitreous” — glassmorphic, high-contrast. Tokens: Deep Background #05070a, Surface Light rgba(255,255,255,0.03), Border Glass rgba(255,255,255,0.08), Accent #00A8E8, Text Primary #ffffff, Fonts Inter + JetBrains Mono.
Backend: FastAPI as API bridge: React → FastAPI → Ollama / ChromaDB (and AWS when online). Contract is the documented API endpoints (health, flashcards, explain, chat, grade, quiz, user/stats, sync, rag/search).
Hardware: 2 GB core install limit; psutil-based RAM check to choose model (e.g. <6 GB → Q2_K, ≥6 GB → Q4_K_M).
2. Current Streamlit Analysis
2.1 Entry & Routing
Entry: backend/streamlit_app.py → main().
Boot gate: Single-run “app_booted” flow: hardware check, ChromaDB init, Ollama model load, then st.rerun() into main shell.
Routing: st.session_state.page + URL ?page=.... Sidebar reads get_current_page() (from ui/components/sidebar.py). Valid pages: landing, auth, dashboard, chat, quiz, flashcards, settings, panic_mode, insights, conflicts, profile, sync_status, teacher_insights, error_demo.
2.2 State
Session: st.session_state holds: page, user_logged_in, theme, app_version, last_seen_version, boot_phase, boot_complete, profile_*, user_role, connectivity_status, storage_state, hardware_*, ollama_*, sync_*, chat_messages, chat_is_loading, chat_difficulty, ai_engine, current_deck, flashcard_*, orchestrator, dashboard_stats_ready, etc.
Persistence:
profile_store.py → data/profile.json (UserProfile).
preferences.py / user_stats.json → theme, difficulty, sync_enabled, streak, quiz/flashcard stats, chat_history.
utils/local_storage.py → data/user_stats.json, data/flashcards.json (LocalStorage used by flashcards page and flashcards_system).
2.3 Boot Flow (Pre-Dashboard)
Phases in order: splash → hardware_checks → connectivity → storage_validation → role_selection → then either teacher_redirect or profile_selection → optional class_code → dashboard_reveal → set boot_complete=True, page=dashboard. Hardware can block (below min) or warn (modal); HardwareValidator uses psutil and lives in pages/hardware_validator.py.

2.4 Pages and Responsibilities
Page / Area	File	Main behavior
Landing	pages/landing.py	Hero glass card, “Get Started” → auth or dashboard.
Auth	pages/auth.py	Username/password form; on submit sets user_logged_in, page=dashboard.
Dashboard	pages/dashboard.py	Header (avatar, streak, mode, connectivity, theme), stats row (streak, quiz avg, cards mastered), feature grid (Chat, Quiz, Flashcards, Panic Mode), sync bar, footer (Settings, Logout). Data from user_stats.json.
Chat	pages/chat.py	Messages from user_stats.chat_history, difficulty select, AI via AIEngine (CHAT/CLARIFY), clarify expanders, typing skeleton.
Quiz	pages/quiz.py	Static _QUIZ_ITEMS, select question, text area, “Submit for AI Grading” → GRADING + STUDY_RECOMMENDATION, update quiz stats in user_stats.
Flashcards	pages/flashcards.py	Generator UI (topic/chapter, count) → FLASHCARD_GENERATION; review UI (front/back, Explain, Easy/Hard, recommendation); LocalStorage + optional flashcards_system (SRS).
Settings	pages/settings.py	Theme, sync toggle, difficulty, deployment panels (version, diagnostics, sync readiness, errors, safe mode), storage placeholder, account, Sign Out.
Panic Mode	pages/panic_mode.py	Distraction-free exam simulator (to be reviewed for full behavior).
Insights	pages/insights.py	Student insights from stats.
Conflicts	pages/conflicts.py	Conflict resolution UI (orchestrator).
Profile	pages/profile.py	Profile display/edit.
Sync Status	pages/sync_status.py	Sync panel (SyncManager/orchestrator).
Teacher Insights	pages/teacher_insights_dashboard.py	Teacher preview.
Error Demo	pages/error_demo.py	Error UI demo.
2.5 UI Building Blocks (to be mirrored in React)
Layouts: dashboard_layout.py, boot_layout.py (boot screens).
Components: glass_card, sidebar, page_chrome (blobs, root open/close, back button), stat_card, feature_card, status_indicator, empty_state, loading_skeleton, modal, illustration_placeholder; hardware_modal, status_indicator.
Styles: ui/styles + inject_all_css; theme.css and inline CSS for dashboard/settings/chat.
2.6 Backend (AI & API)
ai_integration_layer.py: AIEngine.request(task_type, user_input, context_data, …) → AIResponse; task types CHAT, CLARIFY, GRADING, FLASHCARD_EXPLANATION, FLASHCARD_GENERATION, WEAK_TOPIC_DETECTION, STUDY_RECOMMENDATION, TEACHER_ANALYTICS_INSIGHT. Uses PromptTemplateLibrary, _call_ollama() (non-streaming), timeout/connection fallbacks, optional logging.
backend/main.py (FastAPI): Already has CORS, GET /api/health, POST /api/flashcards/generate, POST /api/flashcards/explain, POST /api/study/recommendation. Uses AIEngine and shared helpers (_extract_json_array, _normalize_cards).
Gaps vs ARCHITECTURE: /api/chat, /api/grade, /api/quiz/:id, /api/quiz/:id/submit, /api/user/stats (GET/PUT), /api/sync, /api/rag/search; static serving of frontend/dist at / when present.

3. Existing Frontend (Vite/React)
Stack: Vite, React, TypeScript, Tailwind; frontend/src/App.tsx uses React Router, Layout, GlassCard, LoadingSpinner, HardwareStatus, FlashcardDeckProvider, FlashcardsPage.
Design: Thermal Vitreous tokens in index.css and tailwind.config.js (deep, surface-light, glass-border, accent-blue, Inter/JetBrains Mono).
API: services/api.ts — getHealth, generateFlashcards, explainFlashcard, getStudyRecommendation (relative /api for same-origin or Vite proxy).
4. Phase-by-Phase Execution Plan
Phase 1 — Backend: FastAPI completion and static SPA serve
Goal: Align backend with ARCHITECTURE and make the app run as “single origin” (SPA + API on same port).

Static SPA serving

In backend/main.py (or repo-root main.py if that’s the entry): mount static files from frontend/dist at /, with fallback to index.html for client-side routes. Ensure no conflict with /api.
New API endpoints (contract from ARCHITECTURE)

POST /api/chat — body: message + optional context; call AIEngine.request(AITaskType.CHAT, ...); return { text, confidence_score?, metadata? }.
POST /api/grade — body: question, answer, rubric/context; call AITaskType.GRADING; return feedback + score.
GET /api/quiz/:id — return quiz content (local or stub); structure compatible with current _QUIZ_ITEMS.
POST /api/quiz/:id/submit — accept answers; call grading; return grades; persist quiz stats (reuse existing stats schema).
GET /api/user/stats — read from same backing store as Streamlit (user_stats.json + profile); return JSON (streak, quiz_stats, flashcard_stats, preferences, etc.).
PUT /api/user/stats — update preferences/streak/stats; write to same paths.
POST /api/sync — trigger sync (stub or wire to SyncManager when online).
GET /api/rag/search — optional; semantic search over ChromaDB (stub or real when RAG is wired).
Health and AI readiness

Extend GET /api/health optionally with Ollama/ChromaDB status so the frontend can show “AI ready” or “AI unavailable”.
Data paths

Keep BASE_PATH / STUDAXIS_BASE_PATH; ensure all reads/writes use backend/data/ (profile.json, user_stats.json, flashcards.json) so React and Streamlit (if run in parallel) share the same data.
Deliverables: FastAPI serves SPA at /, all listed API routes implemented or stubbed, health endpoint extended; no frontend changes required yet.

Phase 2 — Frontend: Design system and shell
Goal: One-to-one design system and app shell so every subsequent page can be dropped in.

Design tokens and Tailwind

Confirm index.css and tailwind.config.js use the exact Thermal Vitreous tokens (including #05070a, rgba(255,255,255,0.03), 0.08 border, #00A8E8, Inter, JetBrains Mono). Add any missing tokens (e.g. secondary text, success/error) as CSS variables and Tailwind extensions.
Global layout and routing

Layout: persistent sidebar (collapsible, localStorage) + main content area; same nav items as Streamlit (Dashboard, AI Chat, Flashcards, Quiz, Insights, Panic Mode, Conflicts, Sync Status, Settings, Profile).
React Router: / (landing or redirect), /auth, /dashboard, /chat, /flashcards, /quiz, /quiz/:id, /settings, /panic-mode, /insights, /conflicts, /profile, /sync, /teacher-insights, /error-demo.
Routes that need no sidebar: landing, auth, teacher_insights, error_demo (match Streamlit pages_without_sidebar).
Core components (design system)

GlassCard (already present): refine to use surface-light, glass border, 24px blur.
Sidebar: nav links, active state, optional conflict badge, sync status pill, collapse toggle (localStorage).
PageChrome: background blobs (or gradient), optional back button.
StatCard, FeatureCard, StatusIndicator (sync/online pill).
EmptyState, LoadingSkeleton, Modal (for hardware warning, confirmations).
HardwareStatus / low-power indicator if needed.
Boot flow (first-time experience)

Dedicated route or guarded flow: splash → hardware check (call backend or static check) → connectivity → storage → role selection → profile/class code → dashboard reveal.
Store “boot complete” and “last seen version” in localStorage (and optionally sync to backend) so returning users skip to dashboard.
Auth and global state

Minimal auth state: “user_logged_in” + profile (name, role, mode, class_code).
Use React context (e.g. AuthContext + AppStateContext) or a small store; persist profile to backend (GET/PUT /api/user/stats or a dedicated profile endpoint if added).
Landing “Get Started” → /auth if not logged in, else /dashboard.
Deliverables: Design system documented (or clearly reflected in code), Layout + Sidebar + routes, boot flow and auth state; no feature logic yet except “landing → auth → dashboard”.

Phase 3 — Dashboard and user stats
Goal: Dashboard page and user stats API fully usable from React.

User stats API

Consume GET /api/user/stats for dashboard and any header stats.
Use PUT /api/user/stats for theme, difficulty, sync_enabled (and later any in-page edits).
Dashboard page

Hero header: avatar (initials), “Welcome back, {name}”, streak pill, mode badge, connectivity pill, theme toggle.
Stats row: three StatCards — streak (with progress), quiz average, flashcards mastered (with “due” subtitle).
Feature grid: AI Chat, Quiz, Flashcards, Panic Mode (same layout as Streamlit).
Sync bar and footer: last sync time, Settings, Logout.
Logout: clear local auth state and call backend if needed; redirect to landing.
Connectivity and theme

Connectivity: from backend health or a small /api/connectivity if needed; show Online/Offline in header and footer.
Theme: persist via PUT /api/user/stats (preferences.theme) and apply CSS class or data-theme for Thermal Vitreous dark variant.
Deliverables: Dashboard page with stats and feature grid; user stats read/write via API; theme and connectivity reflected in UI.

Phase 4 — Chat
Goal: Chat page with history, difficulty, and AI responses via API.

Chat API

Use POST /api/chat with message + optional context (e.g. difficulty, recent history).
Optionally support “clarify” as same endpoint with a flag or a dedicated POST /api/chat/clarify that uses CLARIFY task type.
Chat UI

Header: title, “Powered by Llama 3.2”, connectivity pill, difficulty selector, Clear button.
Message list: user bubbles (right), assistant bubbles (left); timestamps; markdown for assistant messages.
“Clarify” per message: expander or inline input + button → send clarify request, append reply as clarification.
Input at bottom: send on submit; show loading skeleton or spinner while waiting for POST /api/chat.
Persistence

Load/save chat history via GET /api/user/stats and PUT /api/user/stats (chat_history array), or dedicated chat endpoint if introduced.
Deliverables: Chat page with history, difficulty, clarify, and AI responses using backend.

Phase 5 — Flashcards (full flow)
Goal: Flashcards generation and review in React, reusing existing backend and storage.

APIs

Already present: POST /api/flashcards/generate, POST /api/flashcards/explain, POST /api/study/recommendation.
Add if missing: GET /api/flashcards (or rely on user/stats + local list) and PUT /api/flashcards or PATCH for updating cards (e.g. SRS fields) so the same LocalStorage schema can be backed by API.
Generator UI

Topic/chapter input, type (Topic Name / Textbook Chapter), count slider; “Generate Flashcards” → call generate API; on success, store deck and switch to review mode.
Review UI

Front → Show answer → Back; “Explain with AI” (explain API), “Mark easy” / “Mark hard” (update intervals via backend or local state + PUT); “Get study recommendation” (study recommendation API).
Persist updated intervals and stats via backend so they match Streamlit’s LocalStorage + optional flashcards_system.
Due cards

If backend exposes “due” (e.g. from user_stats or /api/flashcards/due), show “Review due cards” and load that deck.
Deliverables: Full flashcard generate + review flow in React using existing API and consistent storage.

Phase 6 — Quiz and grading
Goal: Quiz selection, attempt, and grading in React.

Quiz API

GET /api/quiz/:id: return quiz metadata and questions (from static list or DB).
POST /api/quiz/:id/submit: body: answers; call grading for each; return scores and feedback; update quiz stats via same user_stats mechanism.
Quiz UI

List or select quiz → start attempt; one question at a time or single page (match Streamlit).
Submit → call submit API; show scores and AI feedback (reuse grading response shape).
Update dashboard stats (quiz average, etc.) via existing user/stats.
Deliverables: Quiz flow in React with grading and stats.

Phase 7 — Settings, Profile, Panic Mode, Insights, Conflicts, Sync
Goal: All remaining pages and system features.

Settings

Sections: Cloud Sync (toggle), Deployment Readiness (version, diagnostics, sync readiness, errors, safe mode), Appearance (theme), Learning Preferences (difficulty), Privacy, Storage placeholder, Account (name, mode, Sign out).
All toggles and preferences persist via PUT /api/user/stats or dedicated endpoints.
Profile

Display and edit profile (name, mode, class code); persist via backend (profile or user/stats).
Panic Mode

Full-screen, minimal UI, timer, submit quiz; grading via /api/grade or quiz submit; no AI hints during attempt.
Insights

Consume user/stats and optional weak-topic/study insights from backend; render bento or cards.
Conflicts & Sync

Conflicts page: list and resolve conflicts (orchestrator); Sync Status page: last sync, retry, status.
Backend: POST /api/sync and optional GET /api/sync/status if needed.
Deliverables: Settings, Profile, Panic Mode, Insights, Conflicts, Sync Status implemented and wired to API where applicable.

Phase 8 — Bootstrapper, hardware, and polish
Goal: Match ARCHITECTURE runtime and hardware behavior.

Python bootstrapper

Script (e.g. backend/init.py or run.py at repo root): start Ollama if needed, ChromaDB if needed, then uvicorn serving FastAPI (SPA at /, API at /api). Optionally open browser to http://localhost:8000.
Hardware check

Backend: GET /api/hardware or include in health: run HardwareValidator, return ok/warn/block + specs + tips.
Frontend: on first launch (or version change), show hardware modal (warn) or block screen; use same thresholds (e.g. 4 GB RAM, 2 GB disk).
Offline-first

Ensure all critical flows work with backend only (no external CDN for app logic); fonts can be self-hosted to avoid network dependency.
Optional: service worker for caching index.html and assets.
Docs and README

README: how to run backend, build frontend, run bootstrapper; 2 GB limit and hardware table from ARCHITECTURE.
Deliverables: Single-command run (bootstrapper), hardware check via API + UI, offline-first verified, README updated.

5. Dependency and Order Summary
Phase 1 must be done first (API + SPA serve).
Phase 2 (design system + shell + boot + auth) is the base for all pages.
Phases 3–7 can be parallelized by page after Phase 2, but recommended order: 3 (dashboard) → 4 (chat) → 5 (flashcards) → 6 (quiz) → 7 (settings, profile, panic, insights, conflicts, sync).
Phase 8 (bootstrapper, hardware, polish) after core pages are in place.
6. Risks and Mitigations
Duplicate state: Keep a single source of truth for user/stats and profile on the backend; frontend only reads/writes via API.
Flashcards SRS: If flashcards_system stays Python-only, FastAPI must expose “due” and “update card” so React stays in sync.
Streamlit coexistence: Same data/ and same API allow running Streamlit and React in parallel during migration; remove Streamlit when React is fully accepted.