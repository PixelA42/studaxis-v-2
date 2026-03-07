# Studaxis — Architecture & Technical Specification (New)

> **Document type:** Source of Truth for AI code generation  
> **Audience:** Engineers, AI codegen agents, future maintainers  
> **Scope:** Decoupled React + FastAPI architecture (post-Streamlit pivot)  
> **Location:** `.kiro/DOCS_NEW/ARCHITECTURE_NEW.md`

---

## 1. Executive Summary & Workflow

### 1.1 Product Context

**Studaxis** is an offline-first, AI-powered tutoring application for resource-constrained learners (e.g. Tier-2/3 India). The system has **pivoted from a monolithic Streamlit architecture to a decoupled React + FastAPI architecture** to achieve a high-performance, glassmorphic UI while respecting strict local hardware constraints.

### 1.2 Offline-First, Browser-Based Workflow

The runtime workflow is **offline-first** and **browser-based**, avoiding Electron or heavy desktop runtimes:

1. **Python bootstrapper** (e.g. `init.py` or a dedicated launcher script) runs on the user machine.
2. The bootstrapper **starts a FastAPI server** (e.g. `uvicorn`), which:
   - Serves the **compiled React application** from the React `dist` folder (static files).
   - Exposes **REST/API routes** for AI, RAG, sync, and app state.
3. The bootstrapper **boots local AI infrastructure** (Ollama with the selected model, ChromaDB if needed) so the app can run at **0 kbps** after first launch.
4. The bootstrapper **opens `http://localhost:8000`** (or the configured port) in the user’s **default system browser**.

**Design principle:** No Electron bloat. The UI is a standard web app served by FastAPI; the “app” is the browser tab. All learning features work without internet after the initial setup and model download.

### 1.3 High-Level Flow

```
User runs bootstrapper
       → FastAPI server starts
       → React dist served at /
       → Ollama + ChromaDB ready (local)
       → Browser opens localhost:8000
       → 100% learning at 0 kbps (after first launch)
```

---

## 2. Hardware & Smart Installation Strategy

### 2.1 Core Installation Limit

- **Strict 2.0 GB core installation limit** for the Studaxis application + bundled runtime dependencies (excluding user data and optional textbooks).
- This keeps the product viable on government-issued and low-spec devices (e.g. 4GB RAM, i3 CPU).

### 2.2 Smart Installer Logic (psutil)

Installation and model selection use **`psutil`** to adapt to available RAM:

| Condition            | Action |
|----------------------|--------|
| **User RAM &lt; 6 GB** | Download / use **`llama3.2:3b-instruct-q2_K`** (~1.1 GB). |
| **User RAM ≥ 6 GB**  | Download / use **`llama3.2:3b-instruct-q4_K_M`** (~1.8 GB). |

- The installer or first-run logic **checks `psutil.virtual_memory().total`** (and optionally `.available`) to choose the model.
- Models are **stored locally** (e.g. in the user’s **AppData** or an equivalent platform-specific data directory), not inside the 2 GB “core” app bundle if that would exceed the limit.
- After the first launch and model pull, the app runs at **0 kbps** for all core tutoring, grading, RAG, and flashcard features.

### 2.3 Storage and Offline Guarantee

- **Models:** Local path (e.g. AppData) — managed by Ollama or the same path Ollama uses.
- **Embeddings / RAG:** ChromaDB and embedding model (e.g. `all-MiniLM-L6-v2`) are local; no network required for inference or retrieval.
- **User data:** Local JSON (or equivalent) for progress, streaks, preferences; sync is optional and runs only when connectivity is detected.

---

## 3. Frontend Architecture (React + Vite + Tailwind)

### 3.1 Stack

- **React** — UI components and state.
- **Vite** — build tooling and dev server; production build output in **`dist`**.
- **Tailwind CSS** — utility-first styling and design tokens.

### 3.2 Design System: “Thermal Vitreous”

The UI design system is named **Thermal Vitreous**: a glassmorphic, high-contrast theme suitable for long study sessions and low-ambient light.

### 3.3 Design Tokens

Use these **exact** values across the React app and any design docs:

| Token               | Value                      | Usage |
|---------------------|----------------------------|--------|
| **Deep Background** | `#05070a`                  | Page and main app background |
| **Surface Light**   | `rgba(255, 255, 255, 0.03)`| Cards, panels, elevated surfaces |
| **Border Glass**    | `rgba(255, 255, 255, 0.08)`| Borders for glassmorphic elements |
| **Accent Primary (Electric Blue)** | `#00A8E8` | CTAs, links, focus, key actions |
| **Text Primary**   | `#ffffff`                  | Primary body and heading text |
| **Font (sans-serif)** | `'Inter'`               | UI and body copy |
| **Font (monospace)**  | `'JetBrains Mono'`      | Code, formulas, technical content |

These tokens define the core look and feel; Tailwind config and CSS variables should reference them so the whole UI stays consistent and AI-generated UI code can rely on this spec.

---

## 4. Backend Architecture (FastAPI + AI Engine)

### 4.1 API Bridge Concept

- **React** (browser) talks only to **FastAPI** (same origin: `localhost:8000`).
- **FastAPI** is the **API bridge**: it talks to **Ollama** (local LLM), **ChromaDB** (local RAG), and when online to **AWS** (sync, content, etc.).

```
React (dist)  ←→  FastAPI  ←→  Ollama / ChromaDB
                    ↓
                    ←→  AWS (when online): S3, RDS/DynamoDB, etc.
```

### 4.2 Core API Endpoints to Be Built

These endpoints represent the **contract** between the React UI and the FastAPI backend. Implement and extend as needed:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET`  | `/api/health` | Liveness/readiness; Ollama/ChromaDB availability if needed |
| `POST` | `/api/generate-flashcards` | Generate flashcards from chapter/topic (local AI + optional RAG) |
| `POST` | `/api/explain` | RAG-powered explanation for a question or concept |
| `POST` | `/api/chat` | Turn-based chat with local LLM (and RAG context when applicable) |
| `POST` | `/api/grade` | Grade subjective/objective answers (local LLM, Red Pen–style feedback) |
| `GET`  | `/api/quiz/:id` | Get quiz content (local or synced from cloud) |
| `POST` | `/api/quiz/:id/submit` | Submit quiz answers and receive grades |
| `GET`  | `/api/user/stats` | User progress, streaks, preferences |
| `PUT`  | `/api/user/stats` | Update user progress/preferences |
| `POST` | `/api/sync` | Trigger sync with AWS when online (payload to S3/DynamoDB) |
| `GET`  | `/api/rag/search` | Semantic search over local ChromaDB (for debug or UI-driven search) |

Additional endpoints (e.g. panic mode, settings, content library) should follow the same pattern: React → FastAPI → Ollama/ChromaDB or AWS.

---

## 5. Hybrid Cloud Deployment (AWS)

### 5.1 Offline-First, Cloud-Enhanced

- The app is **offline-first**: all core learning features work with **0 kbps** after first launch.
- **FastAPI acts as the bridge to AWS.** When an internet connection is detected, the same FastAPI server (or a dedicated sync path) can:
  - **Sync** user progress and metadata to **S3**, **RDS**, or **DynamoDB** (as per existing Studaxis cloud design).
  - **Pull** teacher-assigned content (quizzes, flashcards) from S3 or from APIs backed by DynamoDB/RDS.

### 5.2 Sync and Services

- **Detection:** Connectivity detection (e.g. polling or failed request) triggers sync when **online**.
- **Storage:** Use **S3** for blobs (e.g. payloads, content); use **DynamoDB** or **RDS** for metadata and queryable state (e.g. student sync metadata, assignments).
- **Flow:** React calls FastAPI → FastAPI uploads/updates to S3 and/or DynamoDB/RDS; on next launch or when online, FastAPI can pull down new content and merge with local state.

This keeps a **single, clear contract**: the React app only talks to FastAPI; FastAPI owns all communication with Ollama, ChromaDB, and AWS.

---

## Document Metadata

- **Version:** 1.0  
- **Last updated:** 2026-03  
- **Supersedes:** Legacy Streamlit-focused architecture docs for the new React + FastAPI stack.  
- **Reference:** `.kiro/steering/` and `.kiro/specs/` for product, tech, and AWS requirements; this file is the **architecture and tech spec source of truth** for the new UI and backend.

---

## How to Run the Full Stack

1. **Backend (from repo root)**  
   - Install Python deps: `pip install -r requirements.txt` (or at least `fastapi`, `uvicorn[standard]`, `psutil`, `pydantic`).  
   - Start API + SPA server: `python main.py`  
   - Or: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`  
   - Serves API at `http://localhost:8000` and the compiled React app from `frontend/dist` at `/` when that folder exists.

2. **Frontend build**  
   - `cd frontend && npm install && npm run build`  
   - Produces `frontend/dist`. The root `main.py` serves this at `/` when present.

3. **Frontend dev (optional)**  
   - `cd frontend && npm run dev` — Vite on port 5173 with proxy to `http://localhost:8000` for `/api`.  
   - Use `http://localhost:5173` for development; use `http://localhost:8000` after building for production-style testing.
