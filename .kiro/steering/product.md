# Product Overview

Studaxis is an offline-first AI tutor designed for low-connectivity learning environments in Tier-2/3 India. Built for AWS Hackathon 2026.

## Problem Statement

264 million Indian students have government-issued laptops (4GB RAM, i3 CPUs) but lack reliable internet. Existing AI tools (ChatGPT, Khanmigo) require constant streaming and are unusable at 0 kbps. When connectivity fails, learning productivity drops to zero.

## Solution: Dual-Brain Architecture

**Brain 1 (Strategic Cloud)**: Amazon Bedrock generates curriculum content (quizzes, Micro-Learning Units, flashcards) from textbooks. Creates intelligence once, consumed many times offline.

**Brain 2 (Edge Tactics)**: Llama 3.2 3B via Ollama delivers 100% offline tutoring, grading, and RAG-powered explanations. Runs entirely on-device without internet.

**Key Principle**: Cloud creates content. Edge delivers learning. 100% functionality at 0 kbps.

## Core Features

- 100% offline AI tutoring with semantic grading (0-10 scores, 0.5 granularity)
- Red Pen feedback (text-based error identification and corrections)
- RAG-powered curriculum grounding (ChromaDB + all-MiniLM-L6-v2, top-K=3)
- Adaptive difficulty (Beginner/Intermediate/Expert with tailored system prompts)
- Hinglish language support (functional, not fine-tuned)
- Panic Mode exam simulator (maximized layout, timer, AI assistance hidden)
- Delta sync via AWS AppSync GraphQL (<5KB payloads for 2G/3G networks)
- Flashcard system with spaced repetition (Easy: 7 days, Medium: 3 days, Hard: 1 day)
- Streak system with milestone badges (7/30/100 days)
- Bento grid dashboard with modern UI (light/dark themes, default: light)
- Teacher Dashboard (Streamlit for MVP; Amazon Q Copilot planned Phase 2)

## Target Users

**Primary Users**:
- K-12 students (Class 8-12) in rural/semi-urban areas
- Tier-2/3 engineering/science undergraduates
- Competitive exam prep (SSC, Banking, Government jobs)
- Voluntary offline-first learners seeking distraction-free study

**Secondary Users**:
- Teachers/Admins monitoring progress via cloud dashboard (optional)

**Solo Mode**: Independent learners can use all features without teacher linkage.

## Technical Constraints

- **Hardware**: 4GB RAM minimum, i3 CPU, no GPU required
- **Memory**: ≤3GB peak RAM, ≤2GB core installation, ≤2.5GB with 10 textbooks
- **Performance**: <10s inference on minimum hardware, <100ms DynamoDB queries
- **Sync**: <5KB delta payloads (target), <50KB upper bound
- **Storage**: Q2_K quantization (~1.1GB model), lazy-loading embeddings

## Business Model

Freemium + institutional licensing. Free tier (full offline AI) costs zero to operate. Revenue from institutional licensing (₹30-500/student/year) covering Teacher Dashboard, Bedrock content generation, and Phase 2 features (Amazon Q analytics).

Cost: $0.07/student/month for cloud services.

## Success Metrics

**Primary**:
- Offline Functionality: 100% core features work at 0 kbps
- Sync Efficiency: <5KB delta payloads (<50KB upper bound)
- Hardware Compatibility: Runs on 4GB RAM devices (80%+ target)
- Latency: <10s local inference on minimum hardware (95% queries)

**Secondary**:
- Engagement: ≥20min daily usage
- Retention: 40%+ maintain 7-day streaks (first month)
- Learning: 15%+ quiz score improvement (30 days)
- Teacher Adoption: 60%+ use dashboard actively

## Why AI is Required

Rule-based systems cannot:
- Evaluate subjective, free-form student answers
- Provide contextual explanations tailored to individual learning gaps
- Assess deeper understanding beyond multiple-choice questions
- Adapt difficulty based on performance patterns

Generative AI enables:
- Personalized 1-on-1 pedagogical feedback at scale
- Semantic grading of open-ended responses
- Adaptive difficulty adjustment
- Curriculum-grounded RAG preventing hallucination

## Out of Scope (MVP)

- Mobile apps (Android/iOS) - Phase 3
- Voice input/output (Transcribe/Polly) - Phase 2
- Handwriting OCR (Textract) - Phase 2
- Multi-language UI (Hindi/Tamil/Telugu translations) - Phase 2
- Video playback with caching - Phase 2
- Peer-to-peer sync (Bluetooth mesh) - Phase 3
- Leaderboards/gamification (DynamoDB GSI) - Phase 2
- Parent dashboard - Phase 2+
- Payment/subscription system - Post-MVP
- Advanced conflict resolution (versioning, custom merge) - Phase 2
- Real-time WebSocket alerts - Phase 2

## Impact

**Educational Access**: Brings AI tutoring to 264M students in rural India where 60%+ lack reliable broadband.

**Equity**: Activates millions of underutilized government-issued laptops for self-study.

**Personalization**: Enables 1-on-1 AI tutoring at scale where pupil-teacher ratios reach 40:1+ in rural schools.

**Economic Mobility**: Better AI-assisted preparation improves exam scores and placement rates for 1.5M annual engineering graduates.

**Language Inclusion**: Hinglish support reduces English proficiency barriers for 57% of students in Hindi-medium schools.
