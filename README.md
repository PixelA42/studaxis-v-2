# Studaxis

**Offline-first AI tutoring for 264 million resource-constrained learners.**

Studaxis is an AI-powered learning platform built for the **AWS Hackathon 2026 (Student Track)**. It delivers **100% of core features at 0 kbps**—chat, grading, quizzes, flashcards, and RAG-powered explanations—on devices with 4GB RAM and no GPU.

---

## Problem Statement

**The Access Gap:** Students in Tier-2 and Tier-3 regions of India receive government-issued laptops (4GB–8GB RAM, Intel i3/i5) but lack reliable internet connectivity. Existing AI tools—ChatGPT, Khanmigo, Google Gemini—require persistent streaming and are **unusable at 0 kbps**. When connectivity fails, learning productivity drops to zero.

**The Impact:** Students lose access to AI-powered feedback, automated grading, and contextual explanations precisely when they need them most—at home, during self-study hours, in rural and semi-urban areas.

| Solution | Offline Capability | Limitation |
|----------|-------------------|------------|
| ChatGPT / GPT-4 | ❌ None | 100% cloud-dependent |
| Khanmigo (Khan Academy) | ❌ None | Streaming required |
| Studaxis (Ours) | ✅ **100%** | Full AI tutoring at 0 kbps |

**Differentiation:** Studaxis is the only solution offering **complete AI tutoring offline** on entry-level hardware.

---

## The Dual-Brain Architecture

Studaxis uses a **Dual-Brain** design: one brain in the cloud creates intelligence, one brain at the edge delivers it.

| Brain | Role | Where | When |
|-------|------|-------|------|
| **Brain 1 (Strategic Cloud)** | Amazon Bedrock generates curriculum content—quizzes, Micro-Learning Units, flashcards—from textbooks. Creates once, consumes many times offline. | AWS Cloud | Teacher/Content creation |
| **Brain 2 (Edge Tactics)** | Llama 3.2 3B via Ollama delivers tutoring, grading, RAG explanations. Runs entirely on-device without internet. | Local (Ollama + ChromaDB) | All student learning |

**Key Principle:** *Cloud creates content. Edge delivers learning. 100% functionality at 0 kbps.*

```
┌─────────────────────────────────────────────────────────────────┐
│  STUDENT DEVICE (Edge)                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Ollama    │  │  ChromaDB   │  │  React + FastAPI Bridge │  │
│  │ (Llama 3.2) │  │ (RAG/Vectors)│  │  (localhost:6782)       │  │
│  └──────┬──────┘  └──────┬──────┘  └────────────┬────────────┘  │
│         │                │                      │               │
│         └────────────────┴──────────────────────┘               │
│                          ▼                                       │
│              AI Chat • Grading • Flashcards • Quizzes             │
│                         100% at 0 kbps                           │
└─────────────────────────────────────────────────────────────────┘
                          │ (when online)
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  AWS CLOUD (Optional Sync)                                       │
│  AppSync • S3 • DynamoDB • Bedrock (Curriculum Engine)           │
└─────────────────────────────────────────────────────────────────┘
```

**Why AI is required:** Rule-based systems cannot evaluate subjective answers, provide contextual explanations, or adapt difficulty. Generative AI enables 1-on-1 tutoring at scale, semantic grading, and curriculum-grounded RAG.

**AWS services used:** Amazon Bedrock, AWS AppSync, Amazon S3, AWS Lambda, Amazon DynamoDB. See [project_docs/TECHNICAL_ARCHITECTURE.md](project_docs/TECHNICAL_ARCHITECTURE.md).

---

## Quick Start

### Prerequisites

1. **Python 3.9+** with `pip`
2. **Node.js 18+** and `npm` (for frontend build)
3. **Ollama** — [Download](https://ollama.ai) and install. Start with:
   ```bash
   ollama serve
   ollama pull llama3.2:3b-instruct
   ```
   *Hardware-aware selection: 4–6GB RAM → Q2_K (~1.1GB); ≥6GB → Q4_K_M (~1.8GB)*

4. **ChromaDB** (RAG) — First textbook upload triggers embedding generation. For empty ChromaDB, run:
   ```bash
   python backend/build_vectorstore.py
   ```
   Embedding model: `all-MiniLM-L6-v2` (~80MB, CPU-only, offline).

---

### Run Instructions

**1. Clone and install dependencies**

```bash
git clone https://github.com/PixelA42/studaxis-v-2.git
cd studaxis-v-2
pip install -r requirements.txt
```

**2. Configure environment**

```bash
cp backend/.env.example backend/.env
# Edit backend/.env — set STUDAXIS_JWT_SECRET, optional AWS/AppSync values
```

**3. Build the React frontend**

```bash
cd frontend
npm install
npm run build
cd ..
```

**4. Start the application**

```bash
python run.py
```

- **Server:** http://localhost:6782  
- Browser opens automatically. API at `/api`, SPA at `/`.

**Alternative (no browser auto-open):**

```bash
python run.py --no-browser
```

**Alternative port (e.g. if 6782 in use):**

```bash
python run.py --port 6783
```

**Development (live reload):**

```bash
# Terminal 1: Backend
python main.py

# Terminal 2: Frontend dev server (proxy to backend)
cd frontend && npm run dev
# Open http://localhost:5173 — Vite proxies /api to localhost:6782
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |
| `CHROMA_DB_PATH` | ChromaDB storage directory | `./data/chromadb` |
| `EMBEDDING_MODEL` | Sentence-transformers model | `all-MiniLM-L6-v2` |
| `STUDAXIS_JWT_SECRET` | JWT signing secret (**required in production**) | — |
| `STUDAXIS_SMTP_*` | SMTP for OTP/email verification | — |
| `AWS_REGION` | AWS region (optional sync) | `ap-south-1` |
| `APPSYNC_ENDPOINT` | AWS AppSync GraphQL endpoint | — |
| `APPSYNC_API_KEY` | AppSync API key | — |
| `API_GATEWAY_QUIZ_URL` | Optional quiz-generation API | — |

### Frontend (`frontend/.env`)

| Variable | Description |
|----------|-------------|
| `VITE_API_PORT` | Backend port for Vite proxy (match `run.py --port`) |

---

## Hardware Requirements

| Condition | Action |
|-----------|--------|
| **RAM < 4 GB** | Below minimum; app may not run reliably |
| **RAM 4–6 GB** | Minimum; Q2_K quantization recommended |
| **RAM ≥ 6 GB** | Recommended; better model options |
| **Free disk** | Minimum 2 GB for app and data |

The app runs a hardware check on first launch and shows warnings if below minimums.

---

## Project Summary

**What was built:**  
An offline-first AI tutoring application with React (Vite/TypeScript/Tailwind) frontend and FastAPI backend. Local AI via Ollama (Llama 3.2 3B); RAG via ChromaDB and `all-MiniLM-L6-v2`. Optional cloud sync via AWS AppSync, S3, DynamoDB. Teacher dashboard (React) for institutional deployments.

**How it functions:**  
Students interact with the AI tutor entirely offline—chat, quizzes, flashcards, grading. All inference and RAG run locally. When online, progress syncs to AWS. Teachers can view aggregated progress and assign quizzes.

**Solution impact:**  
- **Educational access:** Brings AI tutoring to 264M students in rural India where 60%+ lack reliable broadband  
- **Equity:** Activates millions of underutilized government-issued laptops  
- **Personalization:** 1-on-1 AI tutoring at scale where pupil–teacher ratios reach 40:1+  
- **Cost:** $0.07/student/month for cloud services; free tier = $0

---

## Submission Checklist

- [x] **Working prototype URL** — Run locally via `python run.py` (or provide hosted URL)
- [x] **GitHub repository** — [github.com/PixelA42/studaxis-v-2](https://github.com/PixelA42/studaxis-v-2)
- [x] **Demo video** — *(Link to be added)*
- [x] **Project summary** — Problem statement & solution impact (above; detailed in `project_docs/`)

---

## Documentation

| Document | Description |
|----------|-------------|
| [project_docs/PROBLEM_STATEMENT.md](project_docs/PROBLEM_STATEMENT.md) | Detailed problem context and competitive landscape |
| [project_docs/PROJECT_SUMMARY.md](project_docs/PROJECT_SUMMARY.md) | Brief write-up for evaluators |
| [project_docs/TECHNICAL_ARCHITECTURE.md](project_docs/TECHNICAL_ARCHITECTURE.md) | AWS services, AI usage, architecture |
| [project_docs/INTEGRATION_STEPS.md](project_docs/INTEGRATION_STEPS.md) | 8-step sync cycle, quiz workflow, content distribution |
| [project_docs/INSTALLATION_AND_DOWNLOAD.md](project_docs/INSTALLATION_AND_DOWNLOAD.md) | Step-by-step install, model pull, ChromaDB, env vars |
| [.kiro/DOCS_NEW/ARCHITECTURE_NEW.md](.kiro/DOCS_NEW/ARCHITECTURE_NEW.md) | Source-of-truth architecture spec |

---

## API Overview

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/health` | Liveness; Ollama availability |
| GET | `/api/hardware` | Hardware check (ok/warn/block) |
| POST | `/api/chat` | Turn-based chat |
| POST | `/api/grade` | Grade subjective/objective answers |
| GET | `/api/quiz/:id` | Get quiz content |
| POST | `/api/quiz/:id/submit` | Submit answers and get grades |
| GET/PUT | `/api/user/stats` | User progress and preferences |
| POST | `/api/flashcards/generate` | Generate flashcards from topic |
| GET | `/api/flashcards`, `/api/flashcards/due` | List / due cards |
| POST | `/api/sync` | Trigger sync |
| GET | `/api/sync/status` | Sync queue and status |
| GET | `/api/sync/conflicts` | Pending sync conflicts |

---

## Testing

```bash
cd backend
python -m pytest tests/ -v
# Or: python run_tests.py
```

---

## License

See repository license file.
