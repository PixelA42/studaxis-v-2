# Requirements: Studaxis

> **Submission Document — AWS Hackathon 2026**  
> **Version 1.0** | February 2026  
> This document presents the complete requirements specification for Studaxis, including architecture decisions, technology rationale, and a phased scalability roadmap. Section 8 provides the Future Scope & Scalability Roadmap, Section 9 covers Risks & Mitigations, Section 10 provides AWS Cost Estimates, and Section 11 contains the Glossary.

---

## Executive Summary

**Studaxis** is an offline-first AI tutoring application designed for Tier-2/3 India students with entry-level hardware (4GB RAM) and intermittent internet connectivity.

The system runs a local quantized AI model (**Llama 3.2 3B via Ollama, Q2_K quantization**) entirely on-device, maintains a local vector database (**ChromaDB**) for retrieval-augmented generation, and synchronizes minimal data with AWS cloud services when connectivity is available.

**Core Architectural Principle:** 100% of learning features work at **0 kbps**. Cloud services are *enhancements* for institutional oversight, never *dependencies* for student learning.

### TL;DR for Judges

| | |
|---|---|
| **Problem** | 264M Indian students have laptops but no reliable internet — existing AI tools (ChatGPT, Khanmigo) are unusable at 0 kbps |
| **Solution** | **Dual-Brain Architecture**: Bedrock creates content (cloud) → Llama 3B delivers it (edge) → simple Streamlit teacher dashboard for MVP; Amazon Q Teacher Copilot planned for Phase 2 |
| **Result** | 100% AI tutoring offline — grading, RAG, quizzes, flashcards — all at 0 kbps. Cost: **$0.07/student/month** |
| **AWS Stack** | Bedrock ✅ · Lambda ✅ · AppSync ✅ · S3 ✅ — all MVP · Q Business (Phase 2) |
| **Hardware** | 4GB RAM · i3 CPU · No GPU · 2G/3G networks · $200 government laptops |
| **Demo** | **Student**: offline chat + quiz + AI grading + flashcards · **Teacher**: Streamlit dashboard with synced student progress |

### Out of Scope (MVP)

The following capabilities are explicitly **not included** in the current hackathon submission. They are documented here to clarify MVP boundaries and prevent scope confusion:

| Excluded Feature | Reason | Future Phase |
|------------------|--------|--------------|
| **Mobile App (Android/iOS)** | Requires React Native/Flutter + on-device inference runtimes (MLC LLM); desktop-first for MVP | Phase 3 |
| **Voice Input/Output** | Depends on Amazon Transcribe/Polly (cloud); violates offline-first for MVP | Phase 2 |
| **Handwriting OCR** | Requires Amazon Textract (cloud); nice-to-have, not core | Phase 2 |
| **Multi-language UI** | Hindi/Tamil/Telugu UI translations require localization effort; English-only for MVP | Phase 2 |
| **Video Playback** | Video caching excluded from 2GB constraint; transcript RAG is MVP | Phase 2 |
| **Peer-to-Peer Sync (Bluetooth)** | Mesh networking complexity; cloud sync sufficient for demo | Phase 3 |
| **Leaderboards / Gamification** | Requires DynamoDB GSI + multi-user state; solo mode sufficient for MVP | Phase 2 |
| **Parent Dashboard** | Out of scope; teacher dashboard covers institutional oversight | Phase 2+ |
| **Payment / Subscription** | Free for hackathon; monetization strategy not required | Post-MVP |
| **Admin Console (Fleet Management)** | Greengrass-based; single-device demo doesn't need it | Phase 2 |

### Assumptions & Dependencies

The following assumptions underpin the system design. Deviations may require architectural adjustments:

| Assumption | Dependency | Risk if Invalid |
|------------|------------|-----------------|
| **Ollama is pre-installed** | User follows installation guide or bundled installer | App won't start; clear error message guides user |
| **Python 3.9+ available** | Pre-installed on target devices or bundled | Streamlit won't run; installer handles this |
| **4GB RAM minimum** | Government laptop specs (verified for India programs) | OOM on <4GB; warning shown, degraded mode offered |
| **Windows/Linux/macOS desktop** | No ChromeOS, Android, iOS for MVP | Mobile requires Phase 3 architecture |
| **PDFs are text-extractable** | Scanned image PDFs won't embed properly | User warned; Textract (Phase 2) addresses this |
| **Intermittent connectivity (not zero)** | Students can sync at least weekly | Fully offline works, but content updates stall |
| **Teachers have stable internet** | Dashboard and Bedrock quiz generation are cloud-based | Teachers need connectivity; students don't |

---

## 1. Problem Statement

**The Access Gap:**  
Students in Tier-2 and Tier-3 regions of India frequently receive government-issued laptops (4GB–8GB RAM, Intel i3/i5 processors) but lack consistent internet connectivity. Existing EdTech solutions—including ChatGPT, Khanmigo, and similar platforms—require persistent streaming connections, rendering them unusable in offline environments.

**The Impact:**  
When connectivity fails, learning productivity drops to zero. Students lose access to AI-powered feedback, automated grading, and contextual explanations precisely when they need them most—at home, during self-study hours.

### 1.1 Competitive Landscape

| Solution | Offline Capability | Min Hardware | Cost | Limitation |
|----------|-------------------|--------------|------|------------|
| **ChatGPT / GPT-4** | ❌ None | N/A (cloud) | $20/month | 100% cloud-dependent; unusable at 0 kbps |
| **Khanmigo (Khan Academy)** | ❌ None | N/A (cloud) | $44/year | Streaming required; no offline mode |
| **Google Gemini** | ❌ None | N/A (cloud) | Free | Cloud-only; no edge deployment |
| **Duolingo** | ⚠️ Partial | 2GB RAM | Free/Premium | Limited offline; lessons only, no AI tutoring |
| **BYJU'S** | ⚠️ Video cache | 4GB RAM | ₹10K+/year | Video downloads only; no AI grading offline |
| **Studaxis (Ours)** | ✅ **100%** | **4GB RAM** | **Free** | Full AI tutoring, grading, RAG at 0 kbps |

**Differentiation:** Studaxis is the only solution offering **complete AI tutoring functionality offline** on entry-level hardware. Competitors either require constant connectivity (ChatGPT, Khanmigo) or offer limited offline features (video caching without AI interaction).

## 2. The User

### Primary Users

#### Primary User Group A: Learners in Resource-Constrained Environments

Students from Digital Deficit Zones with limited internet access, low-end devices, or affordability constraints.

- **Segment A1 (K–12 Students):**  
  Rural and semi-urban students from Class 8–12 following State Board or equivalent curricula.

- **Segment A2 (University Students):**  
  Tier-2 and Tier-3 Engineering and Science undergraduates who cannot access high-bandwidth MOOCs (e.g., Coursera, Udemy) and require offline-first upskilling solutions. 


#### Primary User Group B: Independent and Self-Paced Learners

Learners who use the platform independently for personal growth and skill development.

- **Segment B1 (Lifelong Learners):**  
  Individuals preparing for competitive examinations (Government jobs, Banking, SSC) or acquiring vocational skills using budget hardware.  
  *(May also belong to resource-constrained environments.)*

- **Segment B2 (Voluntary Offline-First Learners):**  
  Learners who may have access to stable internet and modern devices, yet intentionally adopt the platform because of its effectiveness, distraction-free design, and offline-first learning experience. Their usage is driven by preference and product value, not external constraints.


### Secondary User

**The Teacher/Admin:**
Educators tracking progress for the primary users via a unified cloud dashboard.
Teachers are optional platform participants and are required only in institutional deployments.
The system is fully usable without institutional onboarding.

> **Note:**  
> The platform supports a **Solo Learning Mode** for users who do not have access to teacher or institutional monitoring. (including all primary user groups, enabling learning both with and without teacher supervision)
> In such cases, learners can independently use all core learning features without being linked to an administrator or educator.


## 3. The Role of Generative AI

Generative AI is not an optional enhancement—it is fundamental to solving the problem described above. The following capabilities cannot be replicated with traditional rule-based systems:

- **Semantic Grading:** Evaluating subjective, free-form answers requires natural language understanding. Rule-based grading cannot assess explanations, reasoning, or partial correctness. Edge AI (Llama 3.2 3B) performs this evaluation locally without internet dependency.

- **Contextual Retrieval-Augmented Generation (RAG):** The local vector store (ChromaDB) replaces internet search functionality, enabling curriculum-grounded answers without hallucination risks or connectivity requirements.

- **Scalable Personalization:** A single teacher cannot provide individualized feedback to 50+ students simultaneously. AI enables 1-on-1 tutoring interactions at scale, with each student receiving personalized explanations and corrections.


## 4. Success Metrics

### Primary

- Offline Functionality: 100% core features work with 0kbps internet
- Sync Efficiency: <5KB delta payloads for 2G compatibility (<50KB upper bound)
- Hardware Compatibility: Runs on 4GB RAM devices (80%+ target devices)
- Latency: <10s local inference on minimum hardware (95% queries)

### Secondary

- Engagement: ≥20min daily usage
- Retention: 40%+ maintain 7-day streaks (first month)
- Learning: 15%+ quiz score improvement (30 days)
- Teacher Adoption: 60%+ use dashboard actively

### Technical

- Memory: ≤3GB peak RAM
- Storage: ≤2GB core installation (app + LLM + embedding model); ≤2.5GB total with 10 textbook embeddings
- Sync Success: 95%+ on 2G/3G
- UI Response: ≤200ms interactions


## 5. Functional Requirements

### 5.1 Core: Offline AI Tutor

**Req 1: Local Inference**

**User Story:** As a student with unreliable internet, I want to interact with an AI tutor completely offline, so that my learning is never interrupted by connectivity issues.

- WHEN offline, THE Local_AI_Engine SHALL process queries using local Llama 3.2 3B via Ollama
- WHEN queried, THE system SHALL respond within 10s on 4GB RAM, i3 CPU
- THE system SHALL consume ≤3GB RAM during processing
- WHEN starting, THE system SHALL verify Ollama availability and show errors if missing
- THE system SHALL support ≥4096 token context windows (Llama 3.2 3B supports up to 128K natively)
- THE system SHALL truncate older conversation history automatically to preserve context window limits.


**Req 2: Offline RAG**

**User Story:** As a student, I want to ask questions about my textbook content offline, so that I can get accurate answers grounded in my curriculum without internet access.

- WHEN queried, THE Vector_Store SHALL retrieve top 3 relevant chunks from local embeddings within 2s
- WHEN using RAG, THE system SHALL include source references (chapter, page) in responses
- THE Vector_Store SHALL store ≥10 textbooks (~3000 pages) within 500MB
- WHEN adding PDFs, THE system SHALL generate embeddings locally without internet using the bundled embedding model
- THE system SHALL use `all-MiniLM-L6-v2` (22M params, ~80MB) as the local embedding model — CPU-only, offline-capable, and ChromaDB's default

**Embedding Model Rationale:** `all-MiniLM-L6-v2` is selected for its minimal footprint (~80MB disk, ~100MB RAM), strong retrieval quality on English text, and zero-configuration integration with ChromaDB. It runs entirely on CPU without internet dependency. Alternative considered: Ollama-hosted embedding models (e.g., `nomic-embed-text` at ~274MB) — rejected due to larger storage footprint and redundant Ollama overhead.


**Req 3: Adaptive Difficulty**

**User Story:** As a student, I want to adjust the complexity of AI explanations to match my understanding level, so that I can learn at my own pace.

- WHEN selecting difficulty (Beginner/Intermediate/Expert), THE system SHALL modify AI system prompt
- WHEN Beginner, THE AI SHALL use simple vocabulary and step-by-step explanations
- WHEN Expert, THE AI SHALL use concise, advanced terminology
- WHEN changed, THE system SHALL persist preference in User_Stats


**Req 4: Hinglish Support**

**User Story:** As a student who thinks in a mix of Hindi and English, I want to type questions in Hinglish and receive understandable responses, so that language barriers don't hinder my learning.

- WHEN typing Hindi+English mix, THE Local_AI_Engine SHALL process mixed-language input
- WHEN responding to Hinglish queries, THE AI SHALL answer primarily in English with occasional Hindi terms for clarity
- WHEN explicitly requesting Hindi, THE system SHALL attempt bilingual responses (quality may vary)
- THE AI SHALL recognize common Hinglish patterns (e.g., "yeh concept samajh nahi aaya")

**Limitation Acknowledged:** Llama 3.2 3B is not specifically fine-tuned for Hinglish. Response quality for mixed-language queries is functional but not equivalent to English-only interactions.

**Phase 2 Roadmap:** Evaluation of Hinglish-optimized models including:
- **Airavata** (IIT-Madras): Hindi-English instruction-tuned model
- **IndicBERT / IndicTrans**: Indic language embeddings for improved RAG retrieval
- **OpenHathi** (Sarvam AI): Hindi-first LLM with code-mixing support

Model selection will prioritize quantization compatibility (≤2GB) and offline deployment feasibility.


### 5.2 Core: Smart Assessment

**Req 5: Red Pen Grading**

**User Story:** As a student, I want to see my incorrect answers marked up like a teacher's red pen corrections, so that I understand exactly what was wrong and how to improve.

- WHEN submitting incorrect answers, THE Quiz_Engine SHALL identify specific errors
- WHEN displaying grades, THE system SHALL show AI-generated text feedback highlighting errors and corrections
- WHEN showing corrections, THE system SHALL include brief explanations for each error
- THE system SHALL preserve original answer text for comparison
- WHEN multiple errors exist, THE system SHALL list each with specific feedback

**MVP Scope:** Text-based feedback highlighting errors and corrections. Visual markup (strikethrough, color-coded corrections) is a Phase 2 UI enhancement.


**Req 6: Subjective Auto-Grading**

**User Story:** As a student, I want the AI to grade my written answers to open-ended questions offline, so that I receive immediate feedback without waiting for teacher review.

- WHEN submitting subjective answers, THE Quiz_Engine SHALL use Local_AI_Engine for evaluation
- WHEN grading, THE system SHALL assign 0-10 scores with 0.5 granularity
- WHEN providing grades, THE system SHALL include specific feedback on strengths/improvements
- THE system SHALL evaluate accuracy, completeness, and clarity
- WHEN complete, THE system SHALL store score, feedback, and original answer in User_Stats


**Req 7: Panic Mode (Exam Simulator)**

**User Story:** As a student preparing for exams, I want a distraction-free test environment that simulates real exam conditions, so that I can practice under pressure without AI assistance.

- WHEN activated, THE system SHALL disable Chat_Interface and enter a dedicated exam view (maximized layout with non-essential UI elements hidden)
- WHEN starting, THE Quiz_Engine SHALL randomly select 5 questions and start timer
- WHILE active, THE system SHALL hide sidebar navigation, AI chat, textbook panels, and learning aids within the application
- WHEN timer expires or all submitted, THE AI SHALL grade all responses
- WHEN ending, THE system SHALL save results to User_Stats and restore normal UI layout
- THE system SHALL allow configurable duration (15/30/60 minutes)

**Implementation Note:** Panic Mode uses Streamlit's native layout controls (`st.set_page_config(layout="wide")`, conditional sidebar hiding, CSS injection) to create a focused exam environment. True OS-level fullscreen lock is not feasible in Streamlit; the implementation maximizes the browser viewport and removes all non-exam UI elements to simulate exam conditions.


### 5.3 Core: Cloud Sync & Management

**Req 8: Intelligent Sync (AWS AppSync)**

**User Story:** As a student, I want my progress to sync automatically and efficiently using modern GraphQL standards, so that I use the absolute minimum data required.

- WHEN offline, THE system SHALL queue all "Mutations" (Grade Updates, Streak Increments) locally.
- WHEN online, THE AppSync_Client SHALL execute a "Delta Sync" via GraphQL, sending only changed data fields.
- THE Sync Payload SHALL be minimized using GraphQL query selection (fetching only needed fields).
- WHEN connectivity is detected, THE system SHALL attempt sync within 30 seconds.

**MVP Scope:** Last-write-wins conflict resolution. Advanced conflict resolution (versioning, custom merge logic) and persistent WebSocket connections for real-time alerts are Phase 2 enhancements.


**Req 9: Teacher Content Distribution**

**User Story:** As a teacher, I want to generate quizzes using cloud AI and distribute them to students' devices when they sync, so that I can provide fresh assessment content without manual delivery.

- WHEN teacher creates content, THE system SHALL use Amazon Bedrock (Curriculum Engine) for question generation, summary creation, and Micro-Learning Unit decomposition
- WHEN ingesting raw textbook PDFs, THE Bedrock Curriculum Engine SHALL decompose chapters into quizzes, flashcard sets, and topic summaries optimized for edge delivery
- WHEN generated, THE system SHALL store in Cloud_Storage with target student metadata
- WHEN syncing, THE Sync_Manager SHALL download new assigned quiz content and Micro-Learning Units
- WHEN downloaded, THE system SHALL integrate into local Quiz_Engine without overwriting progress
- THE system SHALL support content versioning to prevent duplicate downloads

**Amazon Bedrock — The Curriculum Engine (Brain 1: Cloud)**

Amazon Bedrock is a **core pillar** of the Studaxis architecture, not an optional add-on. It powers the **cloud-side intelligence** that creates, plans, and analyzes — while the edge AI (Llama 3.2 3B) delivers, tutors, and grades.

**Dual-Brain Architecture:**
- **Brain 1 (Bedrock — Cloud):** Creates curriculum content, generates assessments, decomposes textbooks into Micro-Learning Units, summarizes analytics
- **Brain 2 (Llama — Edge):** Delivers tutoring, grades answers, provides explanations, runs RAG — all at 0 kbps

**What Bedrock Does (MVP):**

| Capability | Implementation |
|------------|----------------|
| Quiz Generation | Teachers input topic/chapter → Bedrock generates curriculum-aligned question sets |
| Content Decomposition | Raw textbook PDFs → Bedrock produces Micro-Learning Units (summaries, key concepts, practice problems) |
| Flashcard Authoring | Bedrock generates high-quality Q&A flashcard pairs from syllabus content |
| Analytics Summarization | Aggregated student sync data → Bedrock produces natural language performance reports |

> **Policy Constraint:**  
> Amazon Bedrock SHALL NOT be used for student chat, tutoring, grading, or learning-time interactions. It powers **content creation and analytics** (strategy), not **real-time learning** (tactics).

**Why Bedrock is the Right Choice:**

- **Managed Foundation Models:** No infrastructure to maintain; governed, safe GenAI usage
- **Scalable Content Pipeline:** One teacher can generate assessments for thousands of students via Bedrock batch inference
- **Cost Efficient:** Content is generated once (cloud) and consumed many times (edge) — no per-student API calls during learning
- **Curriculum Alignment:** Teachers upload syllabi; Bedrock generates domain-specific, exam-pattern-aligned content

**The Pitch:** *"We use Bedrock’s intelligence to pre-generate the tutoring content, and the edge to deliver it. Cloud for Strategy, Edge for Tactics."*

### Amazon Q Business — Teacher Copilot (Phase 2)

**User Story:** As a teacher managing 500+ students across multiple classes, I want to ask natural language questions about student performance data, so that I can quickly identify struggling students without reading raw sync logs.

Amazon Q Business is planned for Phase 2 integration into the Teacher Dashboard as an intelligent analytics agent — the **Teacher Copilot**. For MVP, the Teacher Dashboard provides Streamlit-based progress views with synced student statistics.

**The Problem:** Teachers don't have time to read hundreds of student sync logs, score tables, and engagement metrics manually.

**The MVP Solution — Streamlit Teacher Dashboard:** For the current submission, teachers view synced student progress via a simplified Streamlit dashboard displaying aggregated scores, streaks, and topic-wise performance.

**The Phase 2 Solution — S3 Data Lake + Amazon Q:** Amazon Q connects directly to the S3 bucket where student `User_Stats.json` files are already synced. A lightweight **AWS Lambda translator** converts raw JSON into natural language summaries, which Amazon Q indexes for teacher queries. No database required — S3 acts as the Data Lake.

**Data Pipeline (Phase 2):**
1. **Student Device** syncs and uploads `student_<id>_stats.json` to S3
2. **Lambda Trigger** fires on S3 upload → converts JSON to plain-text summary → saves to `/summaries/` subfolder
3. **Amazon Q** crawls the `/summaries/` folder and indexes the text files
4. **Teacher** asks natural language questions → Amazon Q reads the summaries and answers

| Teacher Query | Amazon Q Response |
|---------------|-------------------|
| *"Which students are failing in Algebra this week?"* | Returns ranked list with scores, trend arrows, and last-active dates |
| *"Generate a remedial quiz for students weak in Geometry"* | Identifies weak students → teacher uses Bedrock quiz tool to generate targeted content |
| *"Show me attendance trends for Class 10-B"* | Summarizes engagement patterns from sync metadata |
| *"What topics have the lowest average scores?"* | Aggregates quiz results across all synced students |

| Capability | Implementation |
|------------|----------------|
| Data Sources | Amazon Q indexes S3 bucket: `/summaries/` folder containing Lambda-generated natural language summaries of student stats |
| Lambda Translator | S3 trigger → converts `{"math_score": 8, "streak": 5}` → `"Student 101 has a Math Score of 8 and a 5-day streak."` → saves to `/summaries/` |
| Bedrock Integration | Teacher reads Q analytics → uses Bedrock to generate targeted remedial quizzes for weak areas identified by Q |
| Dashboard Integration | MVP: Streamlit-based teacher dashboard with progress views. Phase 2: Q accessed via Amazon Q Business API (`qbusiness` boto3 client) from the Teacher Dashboard; responses rendered in a native Streamlit chat UI |

**Why S3 Over DynamoDB:** Amazon Q is a RAG engine — it excels at reading documents (Text, PDF, JSON), not database rows. Using S3 eliminates the need for DynamoDB schemas, partition keys, and export logic. The Lambda translator ensures Q receives clean, human-readable summaries for perfect natural language responses. This is a **Data Lake Architecture** pattern — modern and AWS-native.

**Why Amazon Q is the Right Choice (Phase 2):**

- **Managed RAG Service:** Amazon Q Business is a fully managed RAG engine — it handles document ingestion, indexing, semantic search, and natural language response generation out of the box. No custom RAG pipeline or vector store needed on the cloud side.
- **Native S3 Connector:** Q has a built-in S3 data source connector. Point it at a bucket, it crawls and indexes automatically. Zero custom integration code.
- **No Infrastructure Overhead:** No servers to manage, no retrieval logic to write. Q abstracts the entire analytics-over-documents workflow into a single managed service.
- **Teacher-Friendly Interface:** Teachers ask questions in plain English ("Which students are failing?") and get human-readable answers. No SQL, no dashboards to learn, no data export.
- **Hackathon Judging Alignment:** AWS Hackathon 2026 explicitly requires "Must use Amazon Bedrock and/or Amazon Q." Bedrock is a core MVP component satisfying this requirement. Amazon Q is positioned as a Phase 2 enhancement that strengthens the institutional value proposition.
- **Flat Per-User Pricing:** At $3/user/month (Lite tier), 10 teachers cost ~$30/month — predictable and budget-friendly for pilot deployments with no surprise usage charges.
- **Alternative Rejected — Custom Dashboards:** Building Streamlit charts/tables for teacher analytics requires manual data processing code, SQL-like queries, and UI work. Q replaces all of this with a single chat interface over indexed documents.
- **Alternative Rejected — OpenSearch / Elasticsearch:** Powerful but requires cluster management, index tuning, and query DSL. Massively over-engineered for 500 students.


**Req 10: Hardware Validation**

**User Story:** As a student with limited hardware, I want the application to verify my device meets minimum requirements and provide clear guidance if it doesn't, so that I know whether I can use the system effectively.

- WHEN first launching, THE system SHALL check RAM, CPU, disk space
- IF RAM <4GB, THEN THE system SHALL warn but allow usage with disclaimers
- IF disk <2GB, THEN THE system SHALL display a 'Critical Storage Warning' but allow installation
- WHEN checks complete, THE system SHALL log specs to User_Stats for teacher visibility
- THE system SHALL provide optimization tips for minimum-spec hardware


### 5.4 Core: UX & Engagement

**Req 11: Streak System**

**User Story:** As a student, I want to maintain daily learning streaks that motivate me to study consistently, so that I build regular learning habits.

- WHEN completing ≥1 activity per day, THE system SHALL increment streak counter
- WHEN missing a day, THE system SHALL reset streak to zero
- WHEN updating, THE system SHALL display a flame icon (🔥) with streak number
- WHEN offline, THE system SHALL track streaks via local device time and sync later
- WHEN reaching milestones (7/30/100 days), THE system SHALL display achievement notifications and store badges in User_Stats


**Req 12: Modern UI Design**

**User Story:** As a student, I want a clean, modern interface that feels engaging to use, so that learning feels enjoyable rather than boring.

- THE UI SHALL support both dark and light themes with a user-accessible toggle
- THE system SHALL default to light theme on first launch; user preference SHALL persist in User_Stats
- WHEN toggling themes, THE system SHALL switch all UI surfaces, cards, text, and accents without page reload (CSS variable swap via Streamlit custom CSS injection)
- WHEN displaying interactive elements, THE system SHALL provide visual feedback (hover states, transitions)
- WHEN displaying cards and panels, THE system SHALL use consistent styling with rounded corners
- WHEN rendering chat, THE system SHALL visually distinguish user/AI messages
- THE system SHALL use a sidebar for navigation between features

**Theme Specifications:**
- **Light Theme (Default)**: Background #f8fafc, card surfaces with white fills and subtle shadows, deep blue accent (#2563eb), dark text (#1e293b)
- **Dark Theme**: Background #0a0a0f, card surfaces with glassmorphic blur (rgba white overlays), electric blue accent (#3b82f6), light text (#e2e8f0)
- Both themes SHALL maintain WCAG AA contrast ratios (≥4.5:1 for body text)

**MVP Scope:** Clean, functional Streamlit UI with custom CSS theming and light/dark toggle. Light theme is default. Glassmorphic styling (blur effects, gradients, animations) is applied as time permits — visual polish is secondary to core functionality.


**Req 13: Bento Grid Dashboard**

**User Story:** As a student, I want a well-organized home screen that displays all features in an attractive grid layout, so that I can quickly access different learning tools.

- WHEN loading, THE system SHALL display Bento Grid with cards for each feature (Chat, Quiz, Flashcards, Panic Mode)
- WHEN displaying, THE system SHALL arrange cards in responsive grid adapting to window size
- WHEN clicking cards, THE system SHALL navigate to feature with smooth transition
- THE dashboard SHALL show streak counter, recent activity, quick stats in dedicated cells
- WHEN offline, THE dashboard SHALL display connectivity status without disrupting layout


**Req 14: Contextual Doubt Button**

**User Story:** As a student, I want to quickly clarify specific words or concepts in the AI's response without losing my chat context, so that I can understand complex explanations better.

- WHEN an AI response is displayed, THE Chat_Interface SHALL show a "🤔 Clarify" button beneath each response
- WHEN clicked, THE system SHALL expand an inline text input where the student types or pastes the specific term/phrase to clarify
- WHEN submitted, THE AI SHALL provide a 50-100 word contextual explanation in the same chat thread
- THE clarification SHALL appear as a nested response within the existing conversation without clearing chat history
- THE system SHALL support doubt resolution for 1-50 word segments

**Implementation Note:** This design uses Streamlit-native components (button + expander + text input) rather than text-selection overlays, which require custom JavaScript components. The UX achieves the same goal — contextual clarification without losing chat state — using a pattern fully supported by Streamlit's component model.


### 5.5 Supporting Features

**Req 15: AI Flashcards**

**User Story:** As a student preparing for exams, I want the AI to automatically generate flashcards from my textbook chapters with spaced repetition scheduling, so that I can efficiently memorize key concepts and review them at optimal intervals.

- WHEN requesting flashcards, THE Local_AI_Engine SHALL generate ≥10 Q&A pairs per chapter using on-device inference
- WHEN teacher-curated flashcard sets are available (via Bedrock — see Req 9), THE system SHALL prefer them over locally generated cards
- WHEN generated, THE system SHALL store cards in JSON (≤50 bytes/card average)
- WHEN reviewing, THE system SHALL present cards one-at-a-time with flip animation
- WHEN marking Easy/Hard, THE system SHALL adjust review frequency via spaced repetition
- THE system SHALL support ≥1000 flashcards within 50KB storage

**Dual-Path Clarification:** Flashcards are generated via two paths: (1) **Bedrock** creates curated, high-quality sets when teachers use the Curriculum Engine (cloud, requires sync); (2) **Local AI** generates on-demand sets from embedded textbook content (offline, always available). Path 2 ensures flashcard functionality at 0 kbps.


**Req 16: Offline Content Management**

**User Story:** As a student, I want to manage which textbooks are stored locally on my device, so that I can optimize storage space while keeping relevant content accessible.

- WHEN viewing Content_Library, THE system SHALL display textbooks with download status and sizes
- WHEN selecting for download, THE system SHALL fetch PDF and generate embeddings during next sync
- WHEN storage limited, THE system SHALL allow textbook and embedding removal
- THE system SHALL prevent removal of textbooks with incomplete quizzes/flashcards
- WHEN removed, THE system SHALL free disk space immediately and update display


**Req 17: Session Persistence**

**User Story:** As a student, I want my chat conversations and quiz progress to be saved automatically, so that I can resume learning exactly where I left off even after closing the application.

- WHEN closing, THE system SHALL save all active chat history to local storage
- WHEN restarting, THE system SHALL restore most recent chat session automatically
- WHEN quiz in progress and closing, THE system SHALL save question number and answers
- WHEN resuming quiz, THE system SHALL restore exact state including timer position
- THE system SHALL maintain 7-day session history with automatic cleanup


**Req 18: Error Handling**

**User Story:** As a student, I want the application to handle errors gracefully without losing my work, so that technical issues don't disrupt my learning experience.

- IF AI timeout >30s, THEN THE system SHALL show timeout message and allow retry
- IF Vector_Store corrupted, THEN THE system SHALL attempt repair and fallback to PDF text search
- IF User_Stats corrupted, THEN THE system SHALL restore from recent backup and log incident
- WHEN critical errors occur, THE system SHALL preserve user input and allow recovery
- THE system SHALL log all errors locally while maintaining privacy


**Req 19: Progress Analytics (Teacher Dashboard)**

**User Story:** As a teacher, I want to view aggregated student progress data on a cloud dashboard, so that I can identify struggling students and adjust my teaching approach.

- WHEN viewing, THE system SHALL display avg scores, streaks, and topic-wise performance
- WHEN analyzing, THE dashboard SHALL highlight students with declining scores or broken streaks
- THE dashboard SHALL display data synced from student devices
- WHEN displaying, THE system SHALL anonymize PII unless authorized

**MVP Scope:** Simplified Streamlit-based teacher view displaying synced student statistics. Phase 2 adds Amazon Q Business for natural language analytics. Full-featured React dashboard with real-time updates, CSV exports, and advanced analytics is a Phase 2 enhancement.


**Req 20: Accessibility**

**User Story:** As a student with visual impairments or regional language preferences, I want the application to support accessibility features and multiple languages, so that learning is inclusive and accessible.

- WHEN enabling high-contrast, THE UI SHALL meet WCAG AA standards
- WHEN increasing font size, THE system SHALL scale all text proportionally without breaking layouts
- THE system SHALL support keyboard navigation with visible focus indicators
- THE system SHALL use semantic HTML elements and ARIA labels where Streamlit permits, to support assistive technologies on a best-effort basis

**Phase 2 Enhancements:**
- Regional language UI translations (Hindi/Tamil/Telugu) — English-only for MVP (see Out of Scope table)
- Full screen reader compatibility — requires migration to React for proper ARIA control


**Req 21: Video Caching & Video-Transcript RAG (Phase 2)**

**User Story:** As a student, I want to download lecture segments and ask questions about what the teacher said, so that I can learn complex topics visually without repeated streaming.

- WHEN downloading video, THE Sync_Manager SHALL fetch H.265 (HEVC) encoded clips (480p, ≤5 minutes each) to minimize storage.
- WHEN video is cached, THE system SHALL automatically index the video transcript into the Vector_Store.
- WHEN watching, THE user SHALL be able to pause and ask "Explain what the professor just said," and the AI SHALL answer using the transcript context.
- THE system SHALL treat video transcripts as the primary asset; video files are optional and deletable.
- IF storage is low, THE system SHALL suggest deleting video files while preserving transcripts for future Q&A.
- Video caching SHALL be optional, user-controlled, and excluded from the 2GB core installation constraint.

**Note:** Full video caching is designated Phase 2. The MVP focuses on transcript-based RAG without video file storage.


**Req 22: Autonomous Learner Mode (Solo Mode)**

**User Story:** As an independent learner without a teacher, I want to upload my own study materials and track my own progress, so that I can use the system for personal self-improvement.

- WHEN "Independent Learner" profile is selected, THE system SHALL hide "Pending Assignments" and "Teacher Sync" widgets.
- WHEN in Solo Mode, THE system SHALL enable "Local Ingest," allowing the user to drag-and-drop their own PDFs (e.g., Python Documentation, UPSC Prep) into the library.
- THE system SHALL generate embeddings from uploaded content and integrate them into the local Vector_Store.
- THE Dashboard SHALL reconfigure to show "Personal Mastery" metrics instead of "Class Ranking."

**Phase 2 Enhancement:** A visual "Personal Knowledge Graph" linking concepts across uploaded materials is planned for future releases.


## 6. Non-Functional Requirements

### 6.1 Performance Requirements

- **Response Time:** AI inference SHALL complete within 10s on minimum hardware (4GB RAM, i3 CPU) for 95% of queries
- **UI Responsiveness:** User interface interactions SHALL respond within 200ms
- **RAG Retrieval:** Vector store queries SHALL complete within 2s
- **Sync Detection:** Online connectivity SHALL be detected and sync initiated within 30s
- **Model Optimization:** The Local_AI_Engine SHALL utilize aggressive quantization (Q4_K_M or Q2_K) to fit within available memory


### 6.2 Resource Constraints

- **Memory:** Peak RAM usage SHALL NOT exceed 3GB during operation
- **Storage (Core):** Core installation (application + LLM model + embedding model) SHALL NOT exceed 2GB disk space. Breakdown: Llama 3.2 3B Q2_K (~1.1GB) + `all-MiniLM-L6-v2` (~80MB) + application code and dependencies (~100MB) = ~1.3GB core
- **Storage (User Content):** Textbook embeddings SHALL NOT exceed 500MB for 10 textbooks (~3000 pages); actual size varies by content density (300-500MB typical). Total system footprint with 10 textbooks: ≤2.5GB
- **Sync Payload:** Compressed synchronization data SHALL target <5KB per upload via GraphQL delta sync (metadata only; content synced separately). Upper bound: <50KB in degraded non-delta scenarios


### 6.3 Reliability Requirements

- **Offline Functionality:** 100% of core features SHALL work with 0kbps internet connectivity
- **Sync Success Rate:** 95%+ successful synchronization on 2G/3G networks
- **Data Integrity:** Zero data loss during sync failures or application crashes
- **Session Recovery:** Best-effort restoration of active sessions after unexpected closure; critical state (quiz progress, scores) persisted to disk after each interaction


### 6.4 Scalability Requirements

- **Flashcard Storage:** Support ≥1000 flashcards within 50KB storage
- **Context Window:** Support ≥4096 token context windows for AI conversations
- **Content Library:** Support ≥10 textbooks with full embedding generation
- **Session History:** Maintain 7-day session history with automatic cleanup


### 6.5 Usability Requirements

- **Hardware Compatibility:** Run on 80%+ of target devices (4GB RAM minimum)
- **Accessibility:** Meet WCAG AA standards when high-contrast mode is enabled
- **Keyboard Navigation:** Full keyboard navigation support with visible focus indicators
- **Language (MVP):** Support English and Hinglish input/output
- **Language (Phase 2):** Regional language UI translations (Hindi/Tamil/Telugu) deferred — English-only UI for MVP


### 6.6 Security & Privacy Requirements

- **Local Data:** All student data SHALL be stored locally with appropriate file permissions
- **Error Logging:** Error logs SHALL maintain student privacy (no PII in logs)
- **Teacher Dashboard:** PII SHALL be anonymized unless explicitly authorized
- **Data Transmission:** All cloud sync SHALL use encrypted connections (HTTPS/TLS)

### Privacy Controls

- The system SHALL provide opt-out controls for cloud synchronization.
- Opt-out controls exist to support learners who are privacy-sensitive or operating on shared or government-issued devices.
- When opt-out is enabled, all learning data SHALL remain strictly local.
- The system SHALL clearly indicate when cloud sync is disabled.

## 7. Technical Stack & Constraints

**Frontend:** Streamlit (Python) with custom CSS for glassmorphic design

**Edge Intelligence:**
- Ollama (Llama 3.2 3B with adaptive quantization: Q4_K_M on 6GB+ devices, Q2_K on 4GB devices)
- ChromaDB (local vector store) with `all-MiniLM-L6-v2` embedding model (~80MB, CPU-only, offline)

**Cloud Backend (Dual-Brain — Cloud Side):**
- Amazon Bedrock (Curriculum Engine — quiz generation, content decomposition, Micro-Learning Unit creation, analytics summarization)
- AWS Lambda (sync resolvers, content processing)
- AWS AppSync (GraphQL delta synchronization)
- AWS S3 (content distribution, teacher materials, student stats)
- Boto3 (Python SDK for AWS)
- Amazon Q Business (Phase 2 — Teacher Copilot for natural language analytics over S3 Data Lake)

**Development Constraints:**
- Target Platform: Windows/Linux/macOS desktop environments
- Python Version: 3.9+
- No GPU required (CPU-only inference)
- Offline-first architecture (internet as enhancement, not requirement)


## 8. Future Scope & Scalability Roadmap

This section presents the evolution path from the current hackathon MVP to enterprise-grade deployments. Each technology is selected to address specific constraints—bandwidth, multi-tenancy, accuracy—without violating the offline-first guarantee that is central to Studaxis.

For clarity, technologies are categorized by phase:
- **MVP (Current Submission):** Implemented and demonstrable
- **Phase 2:** Institutional scale; classroom model
- **Phase 3:** Network effects; peer-to-peer capabilities

---

### 8.1 Current MVP Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Inference** | Ollama + Llama 3.2 3B (Q2_K) | Single-binary deployment; ≤3GB RAM; no GPU required; Q2_K reduces model to ~1.1GB (~1.4GB runtime) |
| **Vector Store** | ChromaDB (local) | Zero-config embedded DB; ≤500MB for 10 textbooks |
| **State** | Local JSON / SQLite | Portable, human-readable, no server dependency |
| **UI** | Streamlit + Custom CSS | Rapid prototyping; Python-native; sufficient for demo |
| **Cloud Sync** | AWS AppSync (GraphQL) | Delta sync via GraphQL; conflict resolution; WebSocket for teacher alerts when online |
| **Blob Storage** | AWS S3 (presigned URLs) | Content distribution; teacher materials; video caching |
| **Curriculum Engine** | Amazon Bedrock (Claude 3 / Titan) | **CORE:** Auto-generates quizzes, summaries, Micro-Learning Units from raw PDFs; analytics summarization |
| **Teacher Copilot** | Streamlit Dashboard (MVP) / Amazon Q Business (Phase 2) | MVP: Streamlit-based progress views. Phase 2: NL analytics agent indexing S3 Data Lake via Lambda translator |

> **Design Principle — Dual-Brain Architecture:** Bedrock creates the intelligence (strategy). Edge AI delivers it (tactics). 100% of learning features work at 0 kbps. Cloud services power content generation and sync — never real-time learning. Phase 2 adds Amazon Q to make the intelligence queryable via natural language analytics.

---

### 8.1.1 Memory Budget Analysis (4GB Target Device)

Understanding system memory consumption is critical for deploying LLMs on resource-constrained hardware. The following analysis informed our quantization and architecture decisions.

| Component | Typical RAM | Notes |
|-----------|-------------|-------|
| Windows 10/11 (idle, optimized) | 1.0 – 1.3 GB | Services trimmed for education use |
| Python 3.11 runtime | 0.15 – 0.25 GB | Interpreter + core libraries |
| Streamlit process | 0.2 – 0.4 GB | Single-page app; no heavy dashboards |
| ChromaDB (lazy-loaded) | 0.1 – 0.3 GB | Embeddings paged from disk; not fully resident |
| all-MiniLM-L6-v2 (embedding model) | ~0.1 GB | 22M params; loaded on-demand for embedding generation |
| **Baseline (before LLM)** | **~1.6 – 2.3 GB** | Varies by OS configuration |

**Available for LLM:** On a 4GB system, approximately **1.8 – 2.5 GB** remains for the language model runtime.

#### Llama 3.2 3B Quantization Options

| Quantization | Model Size | Runtime RAM | Target Hardware |
|--------------|------------|-------------|-----------------|
| Q4_K_M | ~1.8 GB | ~2.2 GB | 6GB+ devices (preferred) |
| Q3_K_S | ~1.4 GB | ~1.7 GB | 4-6GB devices |
| **Q2_K** | **~1.1 GB** | **~1.4 GB** | **4GB devices** |

#### Design Rationale

1. **Adaptive Quantization:** The system detects available RAM at startup and selects the highest-quality quantization that fits. Q2_K is deployed only when Q4_K_M or Q3_K_S cannot be accommodated.

2. **RAG Compensates for Quantization Loss:** Lower quantization reduces model reasoning capacity. However, because all responses are grounded via retrieval from curriculum-specific content (ChromaDB), factual accuracy is preserved. The model functions as a *response formatter* for retrieved knowledge, not as the primary knowledge source.

3. **Target Hardware Validation:** Testing will be conducted on Intel i3-6006U (4GB DDR4) — representative of government-distributed student laptops in India. Inference is expected to complete within 8-12 seconds for typical queries.

> **Design Rationale:** Q2_K represents a deliberate trade-off: reduced model precision in exchange for hardware accessibility. This trade-off is acceptable because RAG constrains the model to curriculum-specific content, reducing reliance on the model's intrinsic knowledge. The model functions primarily as a *response formatter* for retrieved knowledge rather than as an independent knowledge source.

---

### 8.1.2 ChromaDB (MVP) vs DynamoDB (Phase 2) — Architectural Distinction

**Important:** These technologies serve fundamentally different purposes and are not interchangeable. ChromaDB is included in the MVP; DynamoDB is a Phase 2 addition for institutional scale.

| Aspect | ChromaDB (Edge — MVP) | DynamoDB (Cloud — Phase 2) |
|--------|-----------------|------------------|
| **Purpose** | Semantic retrieval for offline RAG | System of record for users, progress, sync |
| **Data Type** | Vector embeddings (textbook chunks) | Structured metadata (scores, streaks, assignments) |
| **Location** | Local device only | AWS Cloud |
| **Consistency** | Eventual (local-first) | Strong (authoritative) |
| **Access Control** | None (single-user device) | IAM + Cognito (multi-tenant) |
| **Use Case** | "What did the textbook say about X?" | "Show me this student's progress across devices" |

**Why Both (Phase 2+):**
- ChromaDB enables **offline intelligence** (RAG, semantic search) — **MVP**.
- DynamoDB enables **institutional oversight** (teacher visibility, cross-device recovery, leaderboards) — **Phase 2**.
- Using *only* ChromaDB would compromise consistency, access control, and real-time synchronization essential for teacher oversight at institutional scale.

---

### 8.2 AWS Backend & Data (Phase 2+)

#### 8.2.1 Amazon DynamoDB — Global Source of Truth

**Why:** Local JSON is sufficient for solo learners, but institutions need cross-device recovery, leaderboards, and analytics aggregation.

| Capability | Implementation |
|------------|----------------|
| Hybrid Persistence | Local-first writes → async upsync to DynamoDB when connectivity appears |
| Leaderboards | GSI on `score` partitioned by `ORG#<id>` for institution-scoped rankings |
| Conflict Resolution | `updated_at` timestamp + last-writer-wins; DynamoDB Streams for audit |
| Data Model | `pk = USER#<id>`, `sk = STAT#<course>#<date>`; single-table design |

**MVP Decision:** DynamoDB is deferred to Phase 2. For the current submission, local JSON/SQLite provides sufficient state management for single-device demonstration. DynamoDB becomes essential when institutional cross-device recovery and leaderboards are required.

---

#### 8.2.2 AWS Cognito — Institutional Multi-Tenancy

**Why:** Solo Learners' data must remain private. Institutional Students' aggregated progress must be visible *only* to authorized educators.

| Capability | Implementation |
|------------|----------------|
| User Pools | Secure authentication without building custom auth |
| Groups | `SOLO`, `SCHOOL_<id>`, `TEACHER_<id>` — RBAC at identity layer |
| Data Isolation | Teachers query DynamoDB with `begins_with(pk, 'SCHOOL#their_id')` |
| Federated Login | Optional Google/Microsoft SSO for institutions with existing IdPs |

**MVP Decision:** Identity is handled via local UUID for the current demonstration. Cognito integration is planned for Phase 2 when institutional multi-tenancy and role-based access control become requirements.

---

#### 8.2.3 AWS AppSync — Delta Sync via GraphQL ✅ (Included in MVP)

**Why:** HTTP REST sends full payloads. GraphQL lets the client request *only changed fields*, critical for 2G/3G where every byte matters.

| Capability | Implementation |
|------------|----------------|
| Delta Sync | `lastSyncTimestamp` sent; server returns only mutations since then |
| Conflict Resolution | MVP: `lastSyncTimestamp` + last-write-wins (sufficient for single-user-per-device). Phase 2: AppSync versioning + custom Lambda resolver for multi-device merges |
| Offline Mutations | AppSync SDK queues mutations locally; replays on reconnect |
| Bandwidth Savings | Typical sync payload drops from ~50KB (REST) to <5KB (GraphQL delta) |
| WebSocket Alerts | Persistent connection for teacher notifications when bandwidth permits |

**MVP Status:** AWS AppSync is included in the current submission (see Requirement 8). MVP uses timestamp-based last-write-wins conflict resolution, sufficient for the single-user-per-device model. Advanced conflict resolution (versioning + custom Lambda resolvers) is a Phase 2 enhancement for multi-device scenarios.

---

### 8.3 AI Intelligence

#### 8.3.1 Amazon Bedrock — Curriculum Engine & Distillation Pipeline

> Full specification, capability tables, and “Why Bedrock is the Right Choice” rationale: see **Req 9** above.

**Summary:** Bedrock is the **cloud brain** (Brain 1) of Studaxis — quiz generation, Micro-Learning Units, flashcard authoring, and analytics summarization. Content is created once in the cloud and consumed many times on the edge. Not used for student chat, tutoring, or grading.

**Phase 3 Extension — Knowledge Distillation:**

| Capability | Implementation |
|------------|----------------|
| Synthetic Data Generation | Bedrock creates curriculum-aligned Q&A pairs for model fine-tuning |
| Knowledge Distillation | Bedrock-generated synthetic outputs → LoRA fine-tuning of edge model |
| Model Improvement | Improved Q2_K accuracy without increasing model size |

**MVP Status:** Core MVP component. Knowledge distillation is Phase 3.

---

#### 8.3.2 Amazon Q Business — Teacher Copilot (Phase 2)

**Why:** Teachers managing hundreds of offline students cannot manually parse sync logs and score tables. Amazon Q provides natural language access to analytics — powered entirely by S3, no database required.

**MVP Status:** Deferred to Phase 2. For the current submission, teachers use a simplified Streamlit dashboard displaying synced student statistics. Amazon Q becomes the Teacher Copilot when institutional scale demands natural language analytics.

**Data Lake Architecture (Phase 2):** Amazon Q is a RAG engine that excels at reading documents. Instead of requiring DynamoDB exports, Q indexes natural language summaries generated by a Lambda translator from the same S3 bucket where student stats are already synced.

| Capability | Implementation |
|------------|----------------|
| Data Chat | Teachers ask questions in plain English: "Which students are failing in Algebra?" |
| Data Source | S3 Data Lake: `/summaries/` folder with Lambda-generated text summaries of student stats |
| Lambda Translator | S3 trigger converts `User_Stats.json` → human-readable text → saves to `/summaries/` for Q indexing |
| Workflow Triggers | Teacher reads Q insights → uses Bedrock quiz generation tool to create targeted remedial content for identified weak areas |
| Dashboard Integration | Phase 2: Accessed via Amazon Q Business API (`qbusiness` boto3 client) from the Teacher Dashboard; responses rendered in native Streamlit chat UI |

**Phase 2 Implementation:** Amazon Q connects directly to S3 — the same bucket where student `User_Stats.json` files are synced. A lightweight Lambda function (triggered on S3 upload) converts JSON stats into plain-text summaries that Q can index and query. This eliminates the need for DynamoDB schemas, partition keys, or database connectors. S3 acts as the Data Lake.

---

#### 8.3.3 Amazon Rekognition / Textract — Physical-to-Digital Intake

**Why:** Many students still take handwritten notes. Converting them to text unlocks AI grading and RAG retrieval.

| Capability | Implementation |
|------------|----------------|
| Handwriting OCR | Textract for structured text; Rekognition for scene text |
| Workflow | Student snaps photo → uploads on sync → Textract returns text → injected into local RAG |
| Offline Buffer | Photos queued locally until connectivity; processing is cloud-side |

**MVP Decision:** This capability is deferred to Phase 2. It is documented here to demonstrate the system's extensibility for physical-to-digital workflows without architectural changes.

---

### 8.4 Connectivity & Edge Management (Phase 2+)

#### 8.4.1 AWS IoT Core (MQTT) — Resilient Low-Bandwidth Sync

**Why:** Standard HTTP/REST fails on flickering 2G/3G signals. MQTT is designed for constrained networks.

| HTTP (REST) | MQTT (IoT Core) |
|-------------|-----------------|
| ~8000-byte headers | **2-byte fixed header** |
| Stateless; reconnect = full handshake | Persistent session; auto-resume |
| No offline awareness | **Device Shadows** — cloud holds "last known state" |

**Device Shadows Explained:**
- The student's laptop has a "shadow" (virtual twin) in AWS IoT Core.
- When offline, the laptop updates local state.
- When a 3-second 3G burst appears, the laptop "whispers" the delta to its shadow.
- The Teacher Dashboard reads the shadow, not the laptop. Teachers see "Last Known State" without requiring real-time connection.

**MVP Decision:** IoT Core is deferred to Phase 2. The current MVP uses AWS AppSync for synchronization. IoT Core becomes valuable when deploying to thousands of devices with intermittent 2G/3G connectivity where MQTT's 2-byte header provides significant bandwidth savings over HTTP.

---

#### 8.4.2 AWS IoT Greengrass — Edge Orchestration

**Why:** Managing local Llama components, secret rotation, and OTA model updates across thousands of devices requires an orchestrator.

| Capability | Implementation |
|------------|----------------|
| Component Management | Greengrass deploys/updates Ollama, ChromaDB, Sync Agent as "components" |
| Trickle Downloads | Model updates download in background chunks when idle bandwidth detected |
| Secret Management | Local encryption of API keys; rotated via Greengrass without user action |
| Fleet Monitoring | Central visibility into device health, model versions, storage usage |

**MVP Decision:** Greengrass is deferred to Phase 2/3. For single-device demonstration, manual deployment is sufficient. Greengrass becomes essential for fleet management when scaling to institutional deployments with OTA model updates.

---

### 8.5 Local Edge Optimization (Phase 3+)

#### 8.5.1 Direct LLM Runtimes: llama.cpp and MLC LLM

**Context:** Ollama provides a convenient abstraction over llama.cpp but introduces runtime overhead. For future deployments targeting sub-4GB devices or mobile platforms, direct integration with lower-level runtimes offers additional optimization opportunities.

| Capability | Benefit |
|------------|--------|
| Memory-Mapped Weights | Model weights loaded directly from disk reduce resident RAM requirements |
| Custom Quantization Formats | Fine-grained control over quantization (Q2_K_S, IQ2_XXS) for extreme memory constraints |
| Mobile Compilation | MLC LLM compiles models for Android/iOS, enabling future mobile expansion |
| Batched Inference | Multiple inference requests can be processed concurrently for shared-device scenarios (e.g., school computer labs) |

**MVP Decision:** Ollama is selected for the current submission due to its deployment simplicity and single-binary distribution model. Direct llama.cpp or MLC LLM integration is planned for Phase 3 when targeting devices with less than 4GB RAM or mobile platforms.

---

### 8.6 UI Technology Roadmap

| Phase | Technology | Rationale |
|-------|------------|-----------|
| **MVP (Current)** | Streamlit + Custom CSS | Rapid prototyping; Python-native; seamless integration with edge AI stack |
| **Phase 2 (Institutional)** | React + Vite + FastAPI | Enterprise-grade dashboards; improved state management; WebSocket support |
| **Phase 3 (Mobile)** | React Native / Flutter | Cross-platform mobile deployment; offline-first via SQLite + on-device inference |

#### Rationale for Streamlit in MVP

Streamlit is selected for the current submission based on the following considerations:

1. **Edge AI Integration:** Streamlit operates natively within the Python ecosystem, enabling seamless integration with Ollama, ChromaDB, and LangChain without polyglot complexity.
2. **Deployment Simplicity:** No Node.js or npm dependencies are required on student devices, reducing installation friction on resource-constrained hardware.
3. **Development Velocity:** Single-language stack accelerates iteration during the hackathon development cycle.
4. **Styling Capability:** Glassmorphic UI design is achievable via CSS injection within Streamlit's component model.

#### Rationale for React + Vite in Phase 2

For institutional deployments, the following limitations of Streamlit necessitate migration to React:

| Streamlit Limitation | React + Vite Solution |
|----------------------|-----------------------|
| UI re-renders cause performance bottlenecks | Virtual DOM enables efficient, targeted updates |
| Limited WebSocket support for persistent connections | Native WebSocket APIs handle real-time teacher notifications |
| Session state management is fragile under concurrent users | Component-based state management (Redux/Zustand) provides reliability |
| Single-threaded execution blocks UI responsiveness | Asynchronous rendering maintains responsiveness |

**Architectural Note:** The UI layer is intentionally decoupled from core intelligence and synchronization logic. This design enables technology migration without impacting the edge AI or cloud sync subsystems.

**MVP Decision:** Streamlit is appropriate for the current submission. The architecture explicitly supports React migration in Phase 2 without requiring backend modifications.

---

### 8.7 Architectural Clarifications

#### 8.7.1 Defining "Real-Time" and "WebSockets" in an Offline-First Context

Given that Studaxis is fundamentally an **offline-first** system, the use of terms like "real-time" and "WebSockets" in this document requires clarification to avoid misinterpretation.

**Context:** These technologies are employed exclusively for **teacher-side visibility** and **opportunistic synchronization**. They are never prerequisites for student learning functionality.

| Term | Definition in Studaxis | Clarification |
|------|------------------------|---------------|
| **WebSocket Connection** | An opportunistic persistent connection established with AWS AppSync when bandwidth is available. Used to deliver teacher notifications (e.g., new assignments). If unavailable, the system falls back to polling or deferred delivery on next sync. | This is not a streaming dependency. All learning features function identically whether the WebSocket is connected or not. |
| **Real-Time Sync** | Low-latency delta synchronization when connectivity is detected. Mutations (score updates, streak increments) queued locally during offline periods are transmitted when a network connection becomes available. | This describes sync *responsiveness*, not a connectivity *requirement*. |
| **Device Shadow (IoT Core)** | A cloud-side representation of the student device's last known state. Teachers view the shadow rather than querying the device directly, enabling visibility even when students are offline. | This provides eventual consistency, not live tracking. |

**Architectural Guarantee:**  
All student-facing features—including Chat, Quiz, Flashcards, and AI Grading—operate fully at **0 kbps**. WebSocket connectivity and real-time synchronization are architectural enhancements for institutional oversight; they are not dependencies for the core learning experience.

---

#### 8.7.2 Hybrid Database Architecture (Phase 2 Target)

> **Note:** This diagram shows the **Phase 2 target architecture**. The MVP uses AppSync + S3 + local JSON. DynamoDB, IoT Core, React dashboard, and MQTT are Phase 2 additions.

```
┌─────────────────────────────────────────────────────────────┐
│                      STUDENT DEVICE (EDGE)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ User_Stats  │  │  ChromaDB   │  │   Sync Queue        │  │
│  │   (JSON)    │  │  (Vectors)  │  │ (Pending Mutations) │  │
│  └──────┬──────┘  └─────────────┘  └──────────┬──────────┘  │
│         │                                      │             │
│         └──────────────┬───────────────────────┘             │
│                        ▼                                     │
│              ┌─────────────────┐                             │
│              │   Sync_Manager  │ ◄── Detects connectivity    │
│              └────────┬────────┘                             │
└───────────────────────┼─────────────────────────────────────┘
                        │ MQTT (Phase 2) or
                        │ HTTPS (MVP fallback)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                         AWS CLOUD                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  DynamoDB   │  │   AppSync   │  │  IoT Core Shadow    │  │
│  │ (Source of  │◄─┤  (GraphQL   │◄─┤ (Last Known State)  │  │
│  │  Truth) P2  │  │   Delta)    │  │   [Phase 2]        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────────────────────────────────────────────┐│
│  │         Teacher Dashboard (React - Phase 2)             ││
│  │   • Reads DynamoDB / Shadows                            ││
│  │   • Never queries student device directly               ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**Key Insight:** The student device is the *primary* data authority during learning. Cloud is *secondary*, used for recovery, cross-device continuity, and teacher visibility. This inverts the typical cloud-first EdTech model.

---

### 8.8 Technology Selection Summary

| Technology | Phase | Role | Why Not Now (if Future) |
|------------|-------|------|-------------------------|
| Ollama + Llama 3.2 3B (Q2_K) | MVP | Local Inference | ~1.1GB model (~1.4GB runtime); Q2_K for 4GB devices; RAG grounds accuracy |
| ChromaDB | MVP | Semantic Retrieval | Offline RAG; not for structured data |
| Streamlit | MVP | UI | Python-native; replaceable with React later |
| AWS AppSync | MVP | Delta Sync | GraphQL delta sync + conflict resolution + WebSocket alerts |
| AWS S3 | MVP | Blob Storage | PDFs, videos, teacher content |
| Amazon Bedrock (Claude 3 / Titan) | MVP | Curriculum Engine | **CORE:** Content generation, quiz authoring, Micro-Learning Units, analytics summarization |
| Amazon Q Business | Phase 2 | Teacher Copilot | NL analytics over S3 Data Lake via Lambda translator; deferred to Phase 2 for institutional scale |
| AWS Lambda | MVP | Sync Resolvers | Sync resolvers + content processing; Phase 2 adds JSON-to-text translator for Amazon Q indexing |
| DynamoDB | Phase 2 | Global State | System of record; adds sync complexity |
| Cognito | Phase 2 | Multi-Tenancy | Institutions not in scope for hackathon |
| Amplify | Phase 2 | Dashboard Hosting | React teacher dashboard + CI/CD |
| SNS | Phase 2 | Notifications | Assignment reminders; announcements |
| Transcribe + Polly | Phase 2 | Voice I/O | Accessibility; optional enhancement |
| IoT Core (MQTT) | Phase 2 | Low-BW Sync | Requires device provisioning |
| Greengrass | Phase 2 | Fleet Mgmt | Single-device demo doesn't need it |
| Rekognition/Textract | Phase 2 | OCR Intake | Nice-to-have, not core |
| llama.cpp / MLC LLM | Phase 3 | RAM Optimization | Ollama sufficient for 4GB target |
| React + Vite | Phase 2 | Enterprise UI | Streamlit sufficient for MVP |

---

### 8.9 Product Evolution Phases

This roadmap aligns feature expansion with operational maturity and user base growth.

```
                    ┌─────────────────────────────────────────┐
                    │   PHASE 1 (Hackathon MVP)               │
                    │   Bedrock-Powered Curriculum Engine      │
                    │   + Edge-Powered Learning Delivery       │
                    │   + Streamlit Teacher Dashboard          │
                    │                                         │
                    │   • Bedrock: quiz gen, content decomp    │
                    │   • Edge AI: tutoring, grading, RAG      │
                    │   • Streamlit: teacher progress views    │
                    │   • 100% offline learning capability     │
                    └─────────────────┬───────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
┌─────────────────────────────────┐       ┌─────────────────────────────────┐
│  PHASE 2 (Classroom Model)      │       │  PHASE 3 (Network Effect)       │
│  Institutional Scale            │       │  Offline Network at Scale       │
│                                 │       │                                 │
│  • Amazon Q Business Teacher     │       │  • Peer-to-peer syncing via     │
│    Copilot (NL analytics over    │       │    Bluetooth (no internet)      │
│    S3 Data Lake via Lambda)      │       │  • Students share notes and     │
│  • DynamoDB + Cognito RBAC       │       │    learning materials locally   │
│  • Amazon Q upgrades to          │       │  • Mesh network for classrooms  │
│    DynamoDB data source          │       │    without WiFi                 │
│  • Voice I/O (Transcribe/Polly)  │       │                                 │
│  • Teacher dashboard (React)     │       │                                 │
│  • IoT Core MQTT sync            │       │                                 │
└─────────────────────────────────┘       └─────────────────────────────────┘
```

---

### 8.10 Additional AWS Services (Future Scope)

#### 8.10.1 File Storage & Content Distribution

| Technology | Purpose | Phase |
|------------|---------|-------|
| **Amazon S3** | Store PDFs, notes, assignments; teacher uploads content; video caching | ✅ MVP |
| **CloudFront** | CDN for content distribution to reduce latency for institutional deployments | Phase 2 |

#### 8.10.2 Notifications & Messaging

| Technology | Purpose | Phase |
|------------|---------|-------|
| **Amazon SNS** | Assignment reminders; class announcements; streak alerts | Phase 2 |
| **Amazon SES** | Email notifications for teachers (weekly progress digests) | Phase 2 |

#### 8.10.3 Voice & Accessibility

| Technology | Purpose | Phase |
|------------|---------|-------|
| **Amazon Transcribe** | Voice input — students can speak questions instead of typing | Phase 2 |
| **Amazon Polly** | Voice output — AI responses read aloud for visually impaired or low-literacy users | Phase 2 |

**Rationale:** Voice I/O adds accessibility for inclusive learning. These are optional cloud enhancements that do not impact offline core functionality.

#### 8.10.4 AI-Powered Analytics & Teacher Intelligence

| Technology | Purpose | Phase |
|------------|---------|-------|
| **Amazon Bedrock (Claude 3 / Titan)** | Curriculum Engine — quiz generation, content decomposition, Micro-Learning Units, analytics summarization | ✅ MVP |
| **Amazon Q Business** | Teacher Copilot — natural language analytics over S3 Data Lake; teachers ask "Which students are failing Algebra?" | Phase 2 |
| **AWS Lambda** | Sync resolvers + content processing (MVP); JSON-to-text translator for Amazon Q indexing (Phase 2) | ✅ MVP (core) / Phase 2 (Q translator) |

**How Amazon Q Works (Phase 2 — S3 Data Lake):**
- Student stats JSON files land in **S3** via normal sync
- **Lambda trigger** converts JSON → natural language text summaries → saves to `/summaries/` subfolder
- Amazon Q indexes the **`/summaries/`** folder — no database needed
- Accessed via **Amazon Q Business API** (`qbusiness` boto3 client) in the Teacher Dashboard; responses rendered in native Streamlit chat UI
- Teacher reads Q analytics → uses **Bedrock quiz tool** to generate targeted remedial content (manual workflow, not automated trigger)
- Teachers get answers in **natural language** instead of reading raw JSON files

**MVP Teacher Dashboard:** For the current submission, teachers use a simplified Streamlit dashboard displaying synced student statistics (scores, streaks, topic-wise performance). Amazon Q integration is planned for Phase 2.

#### 8.10.5 Frontend Hosting & CI/CD

| Technology | Purpose | Phase |
|------------|---------|-------|
| **AWS Amplify** | Hosting React teacher dashboard; CI/CD pipeline; authentication integration with Cognito | Phase 2 |

**Where Amplify Fits:**
- Amplify hosts the **Teacher Dashboard** (React + Vite).
- Amplify CLI manages AppSync schema deployments.
- Amplify Auth wraps Cognito for seamless React integration.
- Student edge app remains **standalone** (no Amplify dependency).

#### 8.10.6 Institutional Scale (Phase 3+)

| Technology | Purpose | Why NOT Now |
|------------|---------|-------------|
| **AWS IAM** | Fine-grained org-level access control | Heavy ops overhead |
| **Cognito Groups** | Admin / Teacher / School role separation | Overkill for MVP |
| **Org-level DynamoDB partitioning** | School-scoped data isolation | Needed only at scale |
| **Cross-school analytics** | State/district-level dashboards | Future expansion |

---

### 8.11 Architecture Summary

> Detailed specifications: Bedrock & Amazon Q (Req 9), technology selection rationale (§8.1–8.10).

Studaxis employs a **Dual-Brain edge-cloud architecture** optimized for offline-first learning:

| Component | Role | Phase |
|-----------|------|-------|
| **Brain 1 — Amazon Bedrock** | Curriculum Engine: quizzes, MLUs, flashcards, analytics summaries | MVP |
| **Brain 2 — Llama 3.2 3B** | Edge delivery: tutoring, grading, RAG, adaptive difficulty — all at 0 kbps | MVP |
| **Amazon Q Business** | Teacher Copilot: NL analytics over S3 Data Lake via Lambda translator | Phase 2 |
| **AWS AppSync** | Delta sync via GraphQL for 2G/3G bandwidth efficiency | MVP |
| **Amazon S3** | Blob storage for PDFs, MLUs, teacher content; Data Lake for Q (Phase 2) | MVP |
| **Local JSON/SQLite** | Primary data store during learning sessions | MVP |
| **DynamoDB + Cognito** | Global state management + institutional multi-tenancy | Phase 2 |

**Architectural Guarantee:** All core student features operate fully at 0 kbps. Cloud powers content strategy (Bedrock) and sync (AppSync). Amazon Q (Phase 2) adds teacher intelligence via natural language analytics. DynamoDB and Cognito (Phase 2) add institutional scale without affecting the offline learning guarantee.

---

## 9. Risks & Mitigations

The following risks have been identified and addressed in the architecture:

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Ollama fails to start** | Medium | High — No AI functionality | Req 10 validates Ollama at startup; clear error messaging with installation guidance; fallback to PDF text search (Req 18) |
| **ChromaDB corruption** | Low | Medium — RAG unavailable | Automatic repair attempt; fallback to keyword-based PDF search; embeddings regenerated on next sync (Req 18) |
| **Model hallucination despite RAG** | Medium | Medium — Incorrect answers | RAG constrains responses to retrieved curriculum content; source citations enable verification; confidence thresholds flag uncertain responses |
| **Insufficient RAM on edge device** | Medium | High — OOM crash | Adaptive quantization (Q4_K_M → Q2_K); startup RAM check with warnings (Req 10); lazy-loading of ChromaDB |
| **Sync fails on 2G network** | High | Low — Learning continues offline | All features work at 0 kbps; mutations queued locally; exponential backoff retry; delta sync minimizes payload (Req 8) |
| **User_Stats data loss** | Low | High — Progress lost | Automatic backup after each quiz; restore from backup on corruption (Req 18); cloud sync provides secondary recovery |
| **Student manipulates local time for streaks** | Low | Low — Gamification abuse | Server-side streak validation on sync; anomaly detection flags time manipulation; streak integrity is secondary to learning |
| **PDF embeddings exceed storage budget** | Medium | Medium — Cannot add textbooks | 300-500MB budget for 10 textbooks; chunking optimization; user-controlled content removal (Req 16) |
| **Hinglish queries produce poor responses** | High | Medium — UX degradation | Limitation acknowledged in docs; English fallback; Phase 2 model evaluation (Airavata, OpenHathi) |
| **AppSync WebSocket drops frequently** | Medium | Low — Alerts delayed | Graceful degradation to polling; alerts delivered on next successful sync; not a learning dependency |

---

## 10. AWS Cost Estimate (MVP)

The following estimates are based on a pilot deployment of **500 students** with **10 teachers** over **30 days**.

### 10.1 Assumptions

- Students sync 2x daily when connectivity is available (50% of days)
- Each sync payload: ~5KB (GraphQL delta)
- Teachers generate 20 quizzes/month via Bedrock
- Content stored: 500MB PDFs + 100MB teacher materials
- Teacher dashboard: 100 page views/day

### 10.2 Cost Breakdown

| AWS Service | Usage | Monthly Cost | Notes |
|-------------|-------|--------------|-------|
| **AWS AppSync** | 15,000 sync operations | ~$0.60 | $4/million requests; delta sync minimizes calls |
| **AWS AppSync (Real-time)** | 500 connected minutes/day | ~$0.75 | WebSocket for teacher alerts; opportunistic |
| **Amazon S3** | 600MB storage + 5GB transfer | ~$0.25 | Minimal storage; presigned URLs for downloads |
| **Amazon Bedrock (Claude 3 / Titan)** | 200 quiz generations + 100 content decompositions (~200K tokens) | ~$3.00 | Curriculum Engine: quizzes, Micro-Learning Units, analytics summaries |
| **AWS Lambda** | 20,000 invocations (sync resolvers) | ~$0.00 | Free tier covers sync resolvers |
| **Amazon Q Business** | — | — | *Deferred to Phase 2; not included in MVP cost* |
| **Amazon CloudWatch** | Basic logging | ~$0.00 | Free tier sufficient for MVP |
| **Total (MVP)** | — | **~$5/month** | Excluding free tier benefits |

### 10.3 Cost at Scale (1,000 Schools — Phase 2 Estimate)

| Scenario | Students | Monthly Cost | Per-Student Cost |
|----------|----------|--------------|------------------|
| **Pilot (MVP)** | 500 | ~$5 | $0.010 |
| **Pilot + Amazon Q (Phase 2)** | 500 | ~$35 | $0.070 |
| **Regional (Phase 2)** | 50,000 | ~$150-300 | $0.003-0.006 |
| **National (Phase 3)** | 500,000 | ~$1,000-2,000 | $0.002-0.004 |

**Key Insight:** Offline-first architecture dramatically reduces cloud costs. Students consume AWS resources only during sync (seconds per day), not during learning (hours per day). This inverts the cost model of cloud-first EdTech platforms.

### 10.4 Business Model & Sustainability

Studaxis employs a **freemium + institutional licensing** model designed for sustainability without compromising access for resource-constrained learners.

#### Revenue Streams

| Tier | Target | Price | What's Included |
|------|--------|-------|------------------|
| **Free (Core)** | Individual students, solo learners | ₹0 | Full offline AI tutor, RAG, quizzes, flashcards, grading — all features at 0 kbps |
| **Institutional Lite** | Government schools, NGOs | ₹30–50/student/year (~$0.35–0.60) | Teacher Dashboard, Bedrock quiz generation, AppSync sync, priority support |
| **Institutional Pro** | Private schools, coaching centers | ₹200–500/student/year (~$2.40–6.00) | All Lite features + Amazon Q analytics, custom curriculum ingestion, branded UI, dedicated Bedrock content pipeline, SLA |
| **State/District License** | State education departments | Custom (per-district negotiation) | Bulk deployment, fleet management (Greengrass), state-level analytics, training workshops |

#### Why This Works

1. **Zero marginal cost for free tier:** Students run everything locally — no cloud cost per free user. The free tier is genuinely free, not loss-leading.
2. **Institutional value justification:** At ₹50/student/year, Studaxis costs less than a single textbook. Teachers save 5–10 hours/week on grading alone — the ROI is immediate.
3. **Government procurement alignment:** India's Samagra Shiksha Abhiyan allocates ₹500–2,000/student/year for educational materials. Studaxis fits within existing budget lines.
4. **AWS cost structure enables margins:** At ₹50/student/year revenue vs $0.07/student/month cloud cost (~₹70/year), margins are ~50%+ at institutional scale.

#### Go-to-Market Strategy

| Phase | Channel | Target | Timeline |
|-------|---------|--------|----------|
| **Pilot** | Direct outreach to 5–10 schools in Tier-2 cities | 500–2,000 students | Months 1–3 |
| **NGO Partnerships** | Pratham, Teach For India, Asha for Education | 10,000+ students | Months 3–6 |
| **Government Tenders** | State education department pilots (UP, Tamil Nadu, Karnataka) | 50,000+ students | Months 6–12 |
| **Open Source Community** | GitHub release with deployment guides | Organic adoption | Month 3+ |

#### Sustainability Guarantee

The free tier requires **zero ongoing cloud cost** — it is self-sustaining by design. Institutional licensing funds cloud infrastructure (Bedrock, Q, AppSync) and development. Even if all institutional revenue ceased, every student's offline learning experience would continue uninterrupted.

---

## 11. Development Methodology

### 11.1 AI-Assisted Development Workflow

Studaxis will be built using AI-assisted development tools throughout the engineering process, aligning with the hackathon's encouragement of AI-powered workflows.

| Development Phase | AI Tool Used | How It Will Be Used |
|---|---|---|
| **Architecture Design** | AWS Kiro's Agentic IDE | Iterate on Dual-Brain Architecture, evaluate trade-offs (ChromaDB vs FAISS, Q2_K vs Q4_K_M), stress-test design decisions through adversarial questioning |
| **Requirements Engineering** | AWS Kiro's Agentic IDE | Structure requirements from rough ideas into formal WHEN/SHALL specifications; generate competitive landscape analysis framework |
| **Code Generation** | AWS Kiro's Agentic IDE | Scaffold Streamlit UI components, Ollama API integration, ChromaDB embedding pipeline, AppSync GraphQL mutations, Lambda translator function |
| **Prompt Engineering** | AWS Kiro's Agentic IDE + manual iteration | Design system prompts for adaptive difficulty (Beginner/Intermediate/Expert), grading rubrics (0–10 scale), and Red Pen feedback formatting |
| **Debugging & Optimization** | AWS Kiro's Agentic IDE | Memory profiling on 4GB target hardware, optimizing ChromaDB lazy-loading, reducing Streamlit re-render overhead |
| **Documentation** | AWS Kiro's Agentic IDE | Generate initial drafts of design.md and requirements.md; human-reviewed and refined for accuracy, consistency, and completeness |
| **Cost Estimation** | Human-in-the-Loop | Calculate AWS pricing estimates, validate against AWS pricing pages, stress-test assumptions |

**Philosophy:** AI tools are expected to accelerate development velocity by ~3–4x, but every architectural decision, trade-off analysis, and technical claim will be human-validated. AI will generate drafts; humans will make decisions.

### 11.2 Validation Plan

While a full-scale user study is outside hackathon scope, the following validation activities will establish credibility beyond theoretical impact claims.

#### Validation Targets (During Prototyping)

| Validation | Method | Expected Result |
|---|---|---|
| **Hardware feasibility** | Test Llama 3.2 3B Q2_K on Intel i3-6006U, 4GB DDR4, Windows 10 | Inference expected to complete in 8–12s for typical queries; peak RAM ≤2.8GB |
| **RAG retrieval quality** | Embed 3 NCERT textbooks (Physics, Chemistry, Math — Class 12) into ChromaDB; test 50 curriculum questions | Top-3 retrieval should return relevant chunks for ≥90% of queries |
| **Sync payload measurement** | Measure GraphQL delta payloads for typical student sessions | Target average <5KB per sync; max <15KB |
| **Offline operation** | Disconnect network, run full session (chat + quiz + grading + flashcards) | 100% functionality expected at 0 kbps |

#### Planned Pilot (Post-Hackathon)

| Activity | Target | Timeline |
|---|---|---|
| **Teacher interviews** | 5 government school teachers in Lucknow, UP | Week 1–2 post-submission |
| **Student usability testing** | 20 Class 10–12 students with government laptops | Week 2–4 post-submission |
| **A/B quiz score comparison** | Compare quiz improvement: Studaxis users vs control group (30 days) | Month 2–3 |
| **Hinglish quality assessment** | Native Hinglish speakers rate AI response quality (1–5 scale) | Week 2–4 post-submission |

---

## 12. Glossary

The following terms are used throughout this document. Items marked **(MVP)** will be implemented in the current submission; items marked **(Future Scope)** are planned for subsequent phases.

- **Local_AI_Engine**: Quantized Llama 3.2 3B via Ollama for offline inference — Brain 2 (Edge/Tactical) of the Dual-Brain Architecture (MVP)
- **Curriculum_Engine**: Amazon Bedrock-powered cloud pipeline that generates quizzes, decomposes textbooks into Micro-Learning Units, authors flashcard sets, and summarizes analytics — Brain 1 (Cloud/Strategic) of the Dual-Brain Architecture (MVP)
- **Teacher_Copilot**: Amazon Q Business agent planned for Phase 2; accessed via `qbusiness` boto3 API from the Teacher Dashboard; will index S3 Data Lake (Lambda-generated natural language summaries of student stats) for teacher NL queries. MVP uses Streamlit dashboard for progress views (MVP: Streamlit dashboard / Phase 2: Amazon Q)
- **Lambda_Translator**: AWS Lambda function triggered on S3 upload; converts raw `User_Stats.json` into natural language text summaries for Amazon Q indexing — the bridge between student sync and teacher analytics (Phase 2)
- **Micro-Learning Unit (MLU)**: A Bedrock-generated content package containing a topic summary, key concepts, and practice problems — optimized for edge delivery and offline consumption (MVP)
- **Dual-Brain Architecture**: The architectural pattern where Amazon Bedrock handles content strategy (cloud) and Llama 3.2 3B handles learning delivery (edge); cloud creates intelligence, edge delivers it at 0 kbps (MVP)
- **Vector_Store**: ChromaDB with `all-MiniLM-L6-v2` embeddings (~80MB model) for semantic RAG retrieval; distinct from DynamoDB which serves as system of record (MVP)
- **Sync_Manager**: Python service for burst sync with cloud storage (MVP)
- **Cloud_Storage**: AWS S3 bucket for progress data, teacher content; Phase 2 adds Data Lake for Amazon Q indexing (MVP / Phase 2)
- **S3_Data_Lake**: The S3 bucket structure where student `User_Stats.json` files are synced, converted to text summaries by Lambda, and indexed by Amazon Q Business for teacher analytics — no database required (Phase 2)
- **AppSync_Client**: AWS AppSync GraphQL client for delta synchronization (MVP)
- **Chat_Interface**: Conversational UI for student-AI interaction (MVP)
- **Quiz_Engine**: Component for quiz generation, presentation, and grading (MVP)
- **Content_Library**: Local PDF textbooks and educational materials (MVP)
- **User_Stats**: Local JSON file with student progress, streaks, scores (MVP)
- **Teacher_Dashboard**: Cloud interface for progress monitoring; MVP uses Streamlit-based progress views. Phase 2 adds Amazon Q Business Teacher Copilot accessed via `qbusiness` boto3 API for NL analytics over S3 Data Lake (MVP: Streamlit / Phase 2: Amazon Q)
- **Panic Mode**: Exam simulator with timed, distraction-free environment (MVP)
- **Solo Mode**: Independent learning without teacher oversight (MVP)
- **Red Pen Grading**: AI-generated text feedback identifying errors and corrections; visual markup (strikethrough, colors) planned for Phase 2 (MVP: text-based)
- **Modern_UI**: Clean interface with Streamlit supporting dark and light themes via user toggle (default: light); glassmorphic styling (blur, gradients) applied as time permits (MVP: functional styling with theme toggle)
- **Hinglish**: Mixed Hindi-English language support (MVP)
- **RAG**: Retrieval-Augmented Generation for grounded AI responses (MVP)
- **Delta Sync**: Transmitting only changed data fields to minimize bandwidth; implemented via AppSync (MVP)
- **Q2_K Quantization**: 2-bit quantization reducing Llama 3.2 3B to ~1.1GB model size (~1.4GB runtime). Deployed adaptively on 4GB devices when higher quantizations cannot fit. RAG grounding ensures factual accuracy is preserved despite reduced model capacity. (MVP)
- **Amazon Q Business**: AWS managed AI assistant service planned for Phase 2 as Teacher Copilot; will index S3 Data Lake (Lambda-generated text summaries) to enable natural language analytics queries; uses Data Lake Architecture pattern (Future Scope — Phase 2)
- **DynamoDB**: Global source of truth for user data, progress, and leaderboards; Amazon Q upgrades to DynamoDB as data source when available (Future Scope — Phase 2)
- **Device Shadow**: AWS IoT Core virtual representation of device state in the cloud; enables "last known state" visibility for offline devices (Future Scope — Phase 2)
- **MQTT**: Message Queuing Telemetry Transport; lightweight pub/sub protocol with 2-byte headers, ideal for constrained networks (Future Scope — Phase 2)
- **Knowledge Distillation**: Training a smaller "student" model using outputs from a larger "teacher" model to improve accuracy without increasing size (Future Scope — Phase 3)
- **Hybrid Database**: Architecture where local storage (JSON/SQLite) is the primary authority during learning, with cloud (DynamoDB) as secondary for recovery and analytics (Future Scope — Phase 2)
- **AWS Amplify**: Hosting and CI/CD platform for React teacher dashboard; integrates with Cognito and AppSync (Future Scope — Phase 2)
- **Amazon SNS**: Simple Notification Service for push notifications, assignment reminders, and class announcements (Future Scope — Phase 2)
- **Amazon Transcribe**: Speech-to-text service enabling voice input for accessibility (Future Scope — Phase 2)
- **Amazon Polly**: Text-to-speech service enabling voice output for visually impaired users (Future Scope — Phase 2)
- **Peer-to-Peer Sync**: Bluetooth-based local sync between student devices without internet dependency (Future Scope — Phase 3)
- **Airavata**: Hindi-English instruction-tuned LLM from IIT-Madras; candidate for Phase 2 Hinglish improvement (Future Scope — Phase 2)
- **OpenHathi**: Hindi-first LLM from Sarvam AI with code-mining support; candidate for Phase 2 evaluation (Future Scope — Phase 2)


