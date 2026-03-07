# Studaxis

Offline-first, AI-powered tutoring for resource-constrained learners. React (Vite/TypeScript/Tailwind) frontend with a FastAPI backend; local AI via Ollama.

**Architecture:** [.kiro/DOCS_NEW/ARCHITECTURE_NEW.md](.kiro/DOCS_NEW/ARCHITECTURE_NEW.md)

---

## Quick start

### 1. Backend (API + optional SPA)

From repo root:

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run the server (serves API at /api and React build at / when frontend/dist exists)
python main.py
```

Or use the bootstrapper (optionally opens the browser):

```bash
python run.py
# Or without opening browser:
python run.py --no-browser
```

Server: **http://localhost:6782**

### 2. Frontend (development)

```bash
cd frontend
npm install
npm run build
```

After `npm run build`, the root server serves the built app at `/`. For live reload during development:

```bash
cd frontend && npm run dev
```

Then open **http://localhost:5173** (Vite dev server with proxy to `http://localhost:6782` for `/api`).

### 3. Local AI (Ollama)

For chat, grading, flashcards, and study recommendations:

- Install and start [Ollama](https://ollama.ai).
- The app uses the configured model (e.g. `llama3.2`). No network required after the first model pull.

---

## Hardware requirements

| Condition            | Action |
|----------------------|--------|
| **RAM &lt; 4 GB**      | Below minimum; app may not run reliably. |
| **RAM 4–6 GB**        | Meets minimum; Q2_K-style quantization recommended. |
| **RAM ≥ 6 GB**        | Recommended; better model options (e.g. Q4_K_M). |
| **Free disk**         | Minimum 2 GB for app and data. |

The app runs a hardware check on first launch (GET `/api/hardware`) and shows warnings or blocks if below minimums. See `.kiro/DOCS_NEW/ARCHITECTURE_NEW.md` for the 2 GB core installation limit and smart installer logic.

---

## Project layout

- **`backend/`** — FastAPI app and AI integration (`main.py`, `ai_integration_layer.py`, pages, utils, ai_chat, flashcards_system, grading).
- **`frontend/`** — React (Vite, TypeScript, Tailwind) SPA; build output in `frontend/dist`.
- **`main.py`** — Root entrypoint (in repo root): loads `backend.main` app and runs uvicorn.
- **`run.py`** — Bootstrapper (in repo root): same as `main.py` plus optional browser open. `backend/run.py` forwards to this so you can run from either directory.
- **`.kiro/DOCS_NEW/`** — Architecture and migration docs.

---

## API overview

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/health` | Liveness; Ollama availability |
| GET | `/api/hardware` | Hardware check (ok/warn/block + specs + tips) |
| POST | `/api/chat` | Turn-based chat |
| POST | `/api/grade` | Grade subjective/objective answers |
| GET | `/api/quiz/:id` | Get quiz content |
| POST | `/api/quiz/:id/submit` | Submit answers and get grades |
| GET/PUT | `/api/user/stats` | User progress and preferences |
| POST | `/api/flashcards/generate` | Generate flashcards from topic |
| GET | `/api/flashcards`, `/api/flashcards/due` | List / due cards |
| POST | `/api/sync` | Trigger sync (stub) |

---

## License

See repository license file.
