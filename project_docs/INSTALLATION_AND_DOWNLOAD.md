# Installation and Download Steps — Studaxis

**Step-by-step setup for evaluators and developers**

---

## 1. Prerequisites

### System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| RAM | 4 GB | 6 GB+ |
| CPU | Intel i3 / equivalent | i5 or better |
| Disk (free) | 2 GB | 4 GB+ |
| OS | Windows 10/11, Linux, macOS | — |
| GPU | Not required | — |

### Software Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.9+ | Backend (FastAPI, ChromaDB, Ollama client) |
| Node.js | 18+ | Frontend build (Vite, React) |
| Ollama | Latest | Local LLM runtime |
| pip | Latest | Python package manager |
| npm | Latest | Node package manager |

---

## 2. Download and Install Ollama

### Windows / macOS / Linux

1. **Download Ollama**  
   - Visit [https://ollama.ai](https://ollama.ai)  
   - Download installer for your OS  
   - Run installer

2. **Start Ollama**
   ```bash
   ollama serve
   ```
   *(Ollama may auto-start as a service on some systems.)*

3. **Verify**
   ```bash
   ollama list
   ```
   Should show installed models (or empty list if none yet).

---

## 3. Download LLM Model

### Hardware-Aware Selection

| RAM | Model to Use | Size | Command |
|-----|--------------|------|---------|
| 4–6 GB | `llama3.2:3b-instruct-q2_K` | ~1.1 GB | `ollama pull llama3.2:3b-instruct` (Ollama may choose variant) |
| ≥ 6 GB | `llama3.2:3b-instruct-q4_K_M` | ~1.8 GB | `ollama pull llama3.2:3b-instruct` |

**Recommended (works on 4 GB):**
```bash
ollama pull llama3.2:3b-instruct
```

**Alternative (smaller, lower quality):**
```bash
ollama pull llama3:3b
```

The app uses `psutil` at runtime to suggest the best model; pulling `llama3.2:3b-instruct` covers the default path.

---

## 4. Clone Repository and Install Dependencies

### Step 1: Clone

```bash
git clone https://github.com/PixelA42/studaxis-v-2.git
cd studaxis-v-2
```
*(Replace with your actual repo URL if different.)*

### Step 2: Python Dependencies

```bash
pip install -r requirements.txt
```

Key packages: `fastapi`, `uvicorn`, `chromadb`, `sentence-transformers`, `ollama`, `langchain-ollama`, `langchain-chroma`, `psutil`, `python-dotenv`, `pydantic`, `bcrypt`, `PyJWT`, `boto3`.

### Step 3: Frontend Dependencies

```bash
cd frontend
npm install
npm run build
cd ..
```

---

## 5. ChromaDB and Embeddings Setup

### Embedding Model

- **Model:** `all-MiniLM-L6-v2` (~80 MB)
- **First use:** Automatically downloaded when ChromaDB is first used (e.g. textbook upload or `build_vectorstore.py`).
- **Storage:** `backend/data/chromadb/` (default)

### Option A: Empty ChromaDB (No Textbooks)

If you want RAG to work but have no textbooks yet:

```bash
python backend/build_vectorstore.py
```

This initializes ChromaDB. You can add textbooks later via the UI (Textbooks page → Upload PDF).

### Option B: With Sample Textbooks

1. Place PDF files in `backend/data/sample_textbooks/`
2. Run build script or use the Textbooks page to upload
3. Embeddings are generated locally (CPU-only, offline)

---

## 6. Environment Variables

### Backend (`backend/.env`)

```bash
cp backend/.env.example backend/.env
# Edit backend/.env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `OLLAMA_HOST` | No | Default `http://localhost:11434` |
| `CHROMA_DB_PATH` | No | Default `./data/chromadb` |
| `STUDAXIS_JWT_SECRET` | **Yes** (prod) | Change from `change-in-production` |
| `APPSYNC_ENDPOINT` | No (sync) | AWS AppSync GraphQL URL |
| `APPSYNC_API_KEY` | No (sync) | AppSync API key |
| `AWS_REGION` | No | e.g. `ap-south-1` |
| `API_GATEWAY_QUIZ_URL` | No | Quiz generation API |
| `STUDAXIS_SMTP_*` | No | Email/OTP (optional) |

### Frontend (`frontend/.env`)

| Variable | Description |
|----------|-------------|
| `VITE_API_PORT` | Backend port for Vite proxy (match `run.py --port`, default 6782) |

---

## 7. Run the Application

### Single Command (Recommended)

```bash
python run.py
```

- Starts FastAPI on port 6782  
- Serves React SPA from `frontend/dist`  
- Opens browser to `http://localhost:6782`  
- Preflight checks: Ollama, ChromaDB

### Without Browser Auto-Open

```bash
python run.py --no-browser
```

### Custom Port

```bash
python run.py --port 6783
```

### Development (Live Reload)

**Terminal 1 (backend):**
```bash
python main.py
```

**Terminal 2 (frontend):**
```bash
cd frontend && npm run dev
```

Open `http://localhost:5173` — Vite proxies `/api` to `localhost:6782`.

---

## 8. Textbook Download / Content Library (MVP)

| Scenario | Flow |
|----------|------|
| **Local upload** | Textbooks page → drag & drop PDF → saved to `backend/data/sample_textbooks/` → embeddings generated |
| **Teacher-assigned** | When online, Sync_Manager downloads assigned quizzes from S3 (pre-signed URL) |
| **Content Library** | UI shows textbooks with download status and sizes; "Select for download" triggers fetch on next sync |

**Solo Mode:** Independent learners can drag-and-drop their own PDFs into the library; embeddings generated locally.

---

## 9. Verification Checklist

| Check | Command / Action |
|-------|------------------|
| Ollama running | `ollama list` or visit `http://localhost:11434/api/tags` |
| Model pulled | `ollama list` shows `llama3.2:3b-instruct` (or variant) |
| ChromaDB ready | `backend/data/chromadb/` exists and has content after build |
| Backend health | `curl http://localhost:6782/api/health` |
| Hardware check | `curl http://localhost:6782/api/hardware` |
| Frontend built | `frontend/dist/` exists with `index.html` |
| App loads | Open `http://localhost:6782` in browser |

---

## 10. Troubleshooting

| Issue | Solution |
|-------|----------|
| **Ollama not running** | Start: `ollama serve`; check firewall |
| **Model not found** | `ollama pull llama3.2:3b-instruct` |
| **ChromaDB empty** | Run `python backend/build_vectorstore.py` or upload textbook via UI |
| **frontend/dist not found** | `cd frontend && npm run build` |
| **Port 6782 in use** | `python run.py --port 6783` |
| **AI timeout** | Check RAM; use Q2_K on 4 GB devices |
| **Import errors** | `pip install -r requirements.txt` |
