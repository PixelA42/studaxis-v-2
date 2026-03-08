# Technical Architecture — Studaxis

**AWS Hackathon 2026 | Student Track 1**

---

## 1. AWS Generative AI Value Proposition

*(Addresses Technical Evaluation Criteria: Why AI is required, How AWS is used, What value the AI layer adds.)*

### Why Is AI Required?

Rule-based systems cannot:

- Evaluate subjective, free-form student answers
- Provide contextual explanations tailored to individual learning gaps
- Assess deeper understanding beyond multiple-choice questions
- Adapt difficulty based on performance patterns

Generative AI enables:

- Personalized 1-on-1 pedagogical feedback at scale
- Semantic grading of open-ended responses (0–10 scores, 0.5 granularity)
- Adaptive difficulty adjustment (Beginner / Intermediate / Expert)
- Curriculum-grounded RAG to prevent hallucination

**Conclusion:** Without AI, the system would be limited to static content delivery with no ability to understand or respond to student needs.

---

### How Are AWS Services Used?

| AWS Service | Role in Architecture |
|-------------|----------------------|
| **Amazon Bedrock** | Strategic Cloud Brain — generates quizzes, Micro-Learning Units, flashcards from textbooks. Content creation (not real-time tutoring). |
| **AWS AppSync** | GraphQL API for delta sync — student progress, streaks, preferences. <5KB payloads for 2G/3G networks. |
| **Amazon S3** | Storage for synced user stats, textbook assets, quiz content. |
| **Amazon DynamoDB** | Sync metadata, user records, quiz assignments (when cloud sync is enabled). |
| **AWS Lambda** | Quiz generation workflows, optional serverless processing. |
| **AWS Amplify** | Teacher dashboard hosting (optional deployment). |

**Architecture principle:** Cloud services are *enhancements* for institutional oversight; they are never *dependencies* for student learning. All core features work at 0 kbps.

---

### What Value Does the AI Layer Add?

| Value | Description |
|-------|-------------|
| **Connectivity independence** | Eliminates the connectivity dependency that plagues ChatGPT, Khanmigo, and similar tools. Works at 0 kbps. |
| **Scalable content** | A single educator can generate tailored curriculum for thousands of students via Bedrock — impossible with manual authoring. |
| **Edge delivery** | Edge AI (Ollama + ChromaDB) delivers that curriculum at 0 kbps, turning $200 government laptops into autonomous smart-tutors. |
| **Personalization at scale** | Socratic dialogue, instant feedback, adaptive learning paths — all without per-student API calls during learning. |

---

## 2. Dual-Brain Architecture

### Brain 1: Strategic Cloud (AWS)

- **Technology:** Amazon Bedrock
- **Role:** Generate curriculum content — quizzes, MLUs, flashcards
- **When:** Teacher content creation; batch processing
- **Where:** AWS Cloud
- **Policy:** NOT used for student chat, tutoring, grading, or learning-time interactions

### Brain 2: Edge Tactics (Local)

- **Technology:** Llama 3.2 3B via Ollama + ChromaDB
- **Role:** Deliver tutoring, grade answers, provide RAG explanations
- **When:** All student learning (online or offline)
- **Where:** Student device (localhost)
- **Bandwidth:** 100% functionality at 0 kbps

**Key Principle:** *Cloud creates content. Edge delivers learning.*

```
┌──────────────────────────────────────────────────────────┐
│  STUDENT DEVICE (Edge)                                    │
│  Ollama (Llama 3.2) + ChromaDB (RAG) + FastAPI (Bridge)  │
│  → Chat • Grading • Quizzes • Flashcards • RAG            │
│  → 100% at 0 kbps                                         │
└────────────────────────────┬─────────────────────────────┘
                             │ (when online)
                             ▼
┌──────────────────────────────────────────────────────────┐
│  AWS CLOUD                                                │
│  Bedrock (Content) • AppSync (Sync) • S3 • DynamoDB       │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Local AI Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **LLM** | Llama 3.2 3B (Ollama) | Chat, grading, explanations |
| **Quantization** | Q2_K (~1.1GB) / Q4_K_M (~1.8GB) | Hardware-aware; 4–6GB RAM → Q2_K |
| **RAG** | ChromaDB + sentence-transformers | Curriculum-grounded retrieval |
| **Embedding model** | `all-MiniLM-L6-v2` (~80MB) | CPU-only, offline, ChromaDB-compatible |
| **API bridge** | FastAPI | React ↔ Ollama / ChromaDB / AWS |

---

## 4. API Contract (Core Endpoints)

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

## 5. Hardware Requirements

| Condition | Action |
|-----------|--------|
| RAM < 4 GB | Below minimum; app may not run reliably |
| RAM 4–6 GB | Q2_K quantization recommended |
| RAM ≥ 6 GB | Q4_K_M for better quality |
| Free disk | Minimum 2 GB for app and data |
| GPU | Not required (CPU-only inference) |

---

## 6. AWS-Native Patterns

- **Serverless:** Lambda for quiz generation; no long-running EC2 for MVP
- **Managed services:** Bedrock, AppSync, DynamoDB, S3 — minimal ops overhead
- **Scalable architecture:** Content generated once (cloud), consumed many times (edge)
- **Delta sync:** GraphQL selection minimizes payload size (<5KB target)
