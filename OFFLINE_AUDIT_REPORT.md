# Offline-First Architecture Audit — Studaxis

**Date:** 2025-03-08  
**Scope:** 0 kbps operation for FastAPI + React local stack

---

## Summary

External dependencies were identified and removed or replaced. The app is now configured for 100% offline-capable core AI features and UI.

---

## Task 1: AI Endpoints Audit

### External Dependencies Found

| Location | Issue | Status |
|---------|-------|--------|
| `ai_integration_layer.py` | Hardcoded `OLLAMA_API_URL`; ConnectionError returned generic message | Fixed |
| `main.py` `ollama_ping` | Could return 500 if Ollama not ready; no friendly message | Fixed |
| `main.py` `_generate_single_flashcard_via_ollama` | Hardcoded `http://localhost:11434/api/generate` | Fixed |
| `rag/topic_extractor.py` | Hardcoded Ollama URL | Fixed |
| `ai_chat/main.py` | `OllamaLLM` used default base_url; chain.invoke error message not "AI warming up" | Fixed |

### Changes Made

1. **ai_integration_layer.py**
   - `OLLAMA_API_URL` now derived from `OLLAMA_BASE_URL` env (default `http://localhost:11434`)
   - Fallback message: `"AI is warming up. Please wait a moment and try again, or ensure Ollama is running (ollama serve)."`
   - Timeout error: `"AI is warming up. Inference took too long — try again shortly."`

2. **main.py**
   - `ollama_ping`: Returns `{"ok": false, "message": "AI is warming up..."}` instead of raising; never 500
   - `_generate_single_flashcard_via_ollama`: Uses `OLLAMA_BASE_URL` env

3. **rag/topic_extractor.py**
   - `OLLAMA_API_URL` from `OLLAMA_BASE_URL` env

4. **ai_chat/main.py**
   - `OllamaLLM` created with `base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")`
   - `chain.invoke` catch: connection/refused/timeout → "AI is warming up..." message

### ChromaDB

- **Status:** Fully local — `CHROMA_DIR = DATA_DIR / "chromadb"` (local disk)
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` — local model, no network after download

---

## Task 2: Frontend Assets Audit

### External Dependencies Found

| Location | Issue | Status |
|---------|-------|--------|
| `index.html` | Google Fonts preconnect + Plus Jakarta Sans CSS | Removed |
| `HeroSection.tsx` | `@import url('https://fonts.googleapis.com/...')` | Removed |

### Local Assets (Already Offline)

- **Icons:** `react-icons` (HiFire, HiSparkles, etc.) — bundled in node_modules, no CDN
- **Fonts:** `public/assets/fonts/` — Inter & JetBrains Mono woff2 files; `index.css` @font-face
- **Tailwind:** Local build, no external CDN

### Changes Made

1. **index.html** — Removed:
   - `<link rel="preconnect" href="https://fonts.googleapis.com" />`
   - `<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />`
   - `<link href="https://fonts.googleapis.com/..." />`

2. **HeroSection.tsx** — Removed `@import url`; uses `'Inter', system-ui, sans-serif` (local)

---

## Task 3: Local File Fallbacks Audit

### Flow Verified

- **Flashcard reviews:** `_save_user_stats` / `_save_flashcard_decks` called first, then `_enqueue_sync` (fire-and-forget)
- **Quiz results:** `_save_quiz_result` / `_save_user_stats` first, then `_enqueue_sync`
- **Chat:** `LocalStorage.add_chat_message` writes to `user_stats.json` immediately
- **Sync:** `SyncManager` queues to `sync_queue.json`; `try_sync()` only when user triggers or status checked; no blocking on cloud

### Bug Fixed

- **utils/local_storage.py** — Typo: `"flashcard_stats": or self._user_id {"total_...` → `"flashcard_stats": {"total_...`

### Storage Paths (All Local)

- `data/users/{user_id}/user_stats.json`
- `data/users/{user_id}/flashcards.json`
- `data/sync_queue.json` (offline queue)
- `data/chromadb/` (vector store)

---

## Environment Variables for Offline

| Variable | Default | Purpose |
|----------|---------|---------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | All Ollama API calls |
| `OLLAMA_HOST` | (optional) | Used by some Ollama clients |
| `OLLAMA_MODEL` | `llama3:3b` | Model name |

---

## Optional Cloud (Non-Blocking)

- **SyncManager:** `APPSYNC_ENDPOINT`, `APPSYNC_API_KEY` — only used when user triggers sync; `check_connectivity` returns `False` if not configured
- **Auth:** `users.db` local SQLite; JWT validation local

---

## Testing Checklist (Offline)

1. Turn off network / airplane mode
2. Start backend: `python run.py` (or `uvicorn main:app`)
3. Start Ollama: `ollama serve`
4. Load React app — no FOUT (flash of unstyled text) from missing fonts
5. Navigate pages — icons render (react-icons bundled)
6. Use Chat — "AI is warming up" if Ollama not ready; normal response when ready
7. Save flashcard Easy/Hard — `user_stats.json` updated immediately
8. Complete quiz — stats saved locally before any sync attempt
