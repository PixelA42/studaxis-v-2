# Project Summary — Studaxis

**AWS Hackathon 2026 | Student Track 1**

---

## What Was Built

Studaxis is an **offline-first AI tutoring application** for resource-constrained learners (Tier-2/3 India). Built with:

- **Frontend:** React (Vite, TypeScript, Tailwind CSS)
- **Backend:** FastAPI serving the SPA and API
- **Local AI:** Llama 3.2 3B via Ollama — chat, grading, explanations
- **RAG:** ChromaDB + `all-MiniLM-L6-v2` for curriculum-grounded answers
- **Cloud (optional):** AWS AppSync, S3, DynamoDB, Bedrock for sync and curriculum generation

---

## How It Functions

1. **Student experience (0 kbps):**
   - Chat with AI tutor
   - Take quizzes (MCQ + open-ended)
   - Receive semantic grading with Red Pen feedback
   - Use flashcards with spaced repetition
   - Ask questions grounded in uploaded textbook content (RAG)

2. **Teacher experience (when online):**
   - View synced student progress
   - Use teacher dashboard for institutional deployments
   - Assign quizzes generated via Amazon Bedrock (cloud)

3. **Architecture:**
   - **Dual-Brain:** Cloud creates content (Bedrock); Edge delivers it (Ollama + ChromaDB)
   - All student learning works offline; cloud is enhancement, not dependency

---

## Solution Impact

| Impact Area | Description |
|-------------|-------------|
| **Educational Access** | Brings AI tutoring to 264M students where 60%+ lack reliable broadband |
| **Equity** | Activates millions of underutilized government-issued laptops |
| **Personalization** | 1-on-1 AI tutoring at scale where pupil–teacher ratios reach 40:1+ |
| **Economic Mobility** | Improves exam scores and placement for engineering and competitive exam aspirants |
| **Cost** | $0.07/student/month for cloud services; free tier = $0 |

---

## Key Differentiators

- **100% offline core features** — chat, grading, quizzes, flashcards, RAG
- **4GB RAM compatible** — runs on lowest-spec government laptops
- **0 kbps operation** — no internet required after initial setup
- **Dual-Brain design** — Cloud for strategy; Edge for tactics
