# Design Document: Studaxis

> **Version 1.0** | February 2026 | AWS Hackathon 2026 Submission

## 1. Problem Statement

Tier-2 and Tier-3 students in India own government-issued laptops (4GB-8GB RAM, i3/i5 CPUs) but lack consistent internet access. Current EdTech platforms like ChatGPT and Khanmigo require continuous streaming, rendering them unusable offline. When connectivity fails, learning productivity drops to zero—no AI feedback, no grading, no explanations. This creates a digital divide where students with intermittent connectivity cannot access modern AI-powered education tools.

## 2. Limitations of Existing Solutions

> See [requirements.md §1.1](requirements.md) for detailed competitive landscape analysis.

- **Internet Dependency**: Platforms like ChatGPT, Khanmigo, and MOOCs require persistent high-bandwidth connections
- **Streaming Architecture**: Cloud-based AI models cannot function without real-time connectivity
- **Cost Barriers**: Data costs for streaming AI interactions are prohibitive for resource-constrained students
- **Hardware Assumptions**: Most EdTech assumes modern devices with reliable internet, excluding 80%+ of target users
- **No Offline Grading**: Subjective answer evaluation requires teacher intervention or cloud processing

## 3. Proposed Solution

Studaxis is an offline-first AI tutoring system built on a **Dual-Brain Architecture**: **Amazon Bedrock** (Brain 1 — Cloud) powers the Curriculum Engine — generating quizzes, Micro-Learning Units, and analytics summaries from raw textbooks — while a quantized **Llama 3.2 3B** model (Brain 2 — Edge) delivers tutoring, grading, and RAG-powered explanations entirely on-device. A ChromaDB vector store provides curriculum-grounded RAG, and AWS AppSync syncs minimal progress data (<5KB delta payloads) when connectivity is available. A simplified Streamlit Teacher Dashboard provides progress views for MVP; **Amazon Q Business** is planned for Phase 2 as the Teacher Copilot, indexing an S3 Data Lake (via a Lambda JSON-to-text translator) to enable natural language analytics queries. The system transforms intermittent connectivity from a blocker into an enhancement.

## 4. Design Principles

### Offline-First Architecture
Cloud AI (Bedrock) creates the curriculum intelligence; edge AI (Llama) delivers it. Learning sessions are never blocked by connectivity checks; the system treats the cloud as a content creator and analytics engine, not a real-time participant in learning.

### Resource Efficiency
Designed for 4GB RAM, i3 CPUs, no GPU. Peak memory ≤3GB, core installation ≤2GB (app + LLM + embedding model), total footprint ≤2.5GB with 10 textbook embeddings.
Memory is dynamically managed using model unloading, embedding caching, and chunked inference to remain within limits.

### Bandwidth Optimization
Delta sync via GraphQL transmits only changed fields. Sync payloads target <5KB (delta) / <50KB (upper bound). Video encoding (H.265 at 480p) is a Phase 2 enhancement.

### Privacy-First
All student data stored locally. All cloud synchronization operates on derived and anonymized metadata only; no raw responses, chat transcripts, or live learning signals are transmitted. PII anonymized in teacher dashboards unless authorized.

### Semantic Intelligence
Local AI enables subjective grading, contextual RAG, and adaptive difficulty—impossible with rule-based systems.

### Inclusive Design
Hinglish input/output support (MVP), regional language UI translations (Hindi/Tamil/Telugu — Phase 2), WCAG AA accessibility, keyboard navigation. Dark/light theme toggle for user comfort and varied lighting conditions (MVP).

## 5. System Architecture Overview

### Local Device Layer
- **Ollama Runtime**: Runs quantized Llama 3.2 3B (adaptive: Q4_K_M on 6GB+, Q2_K on 4GB devices)
- **ChromaDB Vector Store**: Stores textbook embeddings for RAG retrieval using `all-MiniLM-L6-v2` (~80MB, CPU-only, offline)
- **Streamlit Frontend**: Python-based UI with custom CSS theming
- **Local Storage**: JSON files for user stats, session history, flashcards

### Intelligence Layer
- **Local_AI_Engine**: Processes queries, grades answers, generates explanations
- **Quiz_Engine**: Generates, presents, and grades assessments
- **RAG Pipeline**: Retrieves relevant textbook chunks, augments AI responses

### Sync Layer
- **Sync_Manager**: Queues mutations offline, executes delta sync when online
- **AppSync_Client**: GraphQL client for delta sync
- **Content_Distributor**: Downloads teacher-assigned quizzes and materials

### Cloud Layer
- **Amazon Bedrock (Curriculum Engine)**: Brain 1 of the Dual-Brain Architecture. Generates quizzes, decomposes textbooks into Micro-Learning Units (summaries, key concepts, practice problems), authors flashcard sets, and summarizes analytics. Bedrock creates the intelligence; the edge delivers it. Not used for student chat, tutoring, or grading during learning sessions.
- **Amazon Q Business (Teacher Copilot — Phase 2)**: Planned for Phase 2 as a natural language analytics agent accessed via `qbusiness` boto3 API from the Teacher Dashboard. Teachers will ask questions like "Which students are failing Algebra?" and Q will index the S3 Data Lake (Lambda-generated text summaries of student stats) to provide answers.
- **AWS Lambda**: Sync resolvers and content processing for MVP. Phase 2 adds JSON-to-text translator triggered on S3 upload; converts raw `User_Stats.json` into human-readable text summaries for Amazon Q indexing.
- **AWS S3**: Stores student progress, teacher content, Micro-Learning Units. Phase 2 adds Data Lake structure for Amazon Q.
- **Teacher_Dashboard**: Streamlit-based progress view for MVP; Amazon Q Copilot integration in Phase 2.

**Data Flow**: Student queries → Local_AI_Engine → Vector_Store retrieval → Response generation → User_Stats update → Sync queue → Cloud (when online)

### Architecture Diagram

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
                        │ GraphQL (AppSync)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                         AWS CLOUD                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   AWS S3    │  │   AppSync   │  │  Amazon Bedrock     │  │
│  │ (Storage +  │◄─┤  (GraphQL   │  │  (Curriculum Engine) │  │
│  │  Blobs)     │  │   Delta)    │  │  Quiz Gen / MLUs    │  │
│  └──────┬──────┘  └─────────────┘  └─────────────────────┘  │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │          Teacher Dashboard (Streamlit — MVP)            │ │
│  │   • Views synced student progress                       │ │
│  │   • Aggregated scores, streaks, topic performance       │ │
│  │   • Never queries student device directly               │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │          Phase 2 Addition: Amazon Q Copilot             │ │
│  │   • Lambda JSON → Text Translator                      │ │
│  │   • Amazon Q indexes /summaries/ in S3 Data Lake       │ │
│  │   • Teachers ask NL questions about student data        │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Key Insight:** Dual-Brain Architecture — Bedrock creates intelligence (strategy), edge AI delivers it (tactics). Student device is the *primary* data authority. Cloud is *secondary*, used for content generation and sync. Phase 2 adds Amazon Q to make the intelligence queryable via natural language analytics over S3 Data Lake.

### Data Flow: What Happens When a Student Syncs

1. **Student completes activity** (quiz, chat, flashcard review) → `User_Stats.json` updated locally
2. **Sync_Manager detects connectivity** → checks network status every 30 seconds
3. **Delta payload constructed** → only changed fields since `lastSyncTimestamp` (~5KB)
4. **AppSync mutation sent** → GraphQL delta sync via HTTPS to AWS cloud
5. **S3 upload triggered** → `student_<id>_stats.json` lands in S3 bucket
6. **Teacher views dashboard** → Streamlit dashboard displays aggregated student progress (MVP)
7. **Teacher generates remedial content** → reads dashboard insights, uses Bedrock Curriculum Engine to create targeted quizzes
8. **Next student sync** → new quiz content downloaded to device → integrated into local Quiz_Engine seamlessly

> This 8-step cycle is the complete round-trip of the Dual-Brain Architecture. Steps 1–4 happen on sync (seconds). Steps 5–6 are available immediately. Steps 7–8 are teacher-initiated (minutes to hours).

**Phase 2 Enhancement (Amazon Q):** Steps 5–6 expand: Lambda fires on S3 event → converts JSON to NL summary → Amazon Q indexes summaries → teachers ask NL questions ("Which students are failing Algebra?") → Q responds in plain English.

## 6. User Types and Access Modes

### Primary Users

**Segment A: Resource-Constrained Learners**
- A1: K-12 students (Class 8-12) in rural/semi-urban areas
- A2: Tier-2/3 engineering/science undergraduates

**Segment B: Independent Learners**
- B1: Competitive exam prep (SSC, Banking, Government jobs)
- B2: Voluntary offline-first learners seeking distraction-free study

### Secondary Users
- **Teachers/Admins**: Monitor progress via cloud dashboard, distribute content

### Solo Mode
Independent learners without teacher oversight. Hides "Pending Assignments" and "Teacher Sync" widgets. Enables local PDF ingestion for self-study. Displays "Personal Mastery" metrics instead of class rankings.

## 7. User Flow

1. **Launch**: System checks hardware (RAM, CPU, disk), verifies Ollama availability
2. **Dashboard**: Bento grid displays Chat, Quiz, Flashcards, Panic Mode, streak counter
3. **Chat Interaction**: Student asks question → Vector_Store retrieves textbook chunks → AI generates grounded response with source references
4. **Adaptive Difficulty**: Student selects Beginner/Intermediate/Expert → System adjusts prompt complexity
5. **Quiz Taking**: Student starts quiz → AI presents questions → Student submits answers → AI grades with text feedback
6. **Panic Mode**: Student activates exam simulator → Maximized exam view, timer starts, AI assistance hidden during exam → Auto-grade on completion
7. **Flashcard Review**: AI generates cards from chapter → Spaced repetition scheduling → Student marks Easy/Hard
8. **Sync**: When online, Sync_Manager uploads progress delta, downloads new teacher content
9. **Session Persistence**: On close, system saves chat history and quiz state → Restores on restart

## 8. Key Features

- **Curriculum Engine (Bedrock)**: Auto-generates quizzes, Micro-Learning Units, flashcard sets, and analytics summaries from raw textbook PDFs — Brain 1 (Cloud)
- **Teacher Copilot (Amazon Q — Phase 2)**: Natural language analytics agent for Phase 2 — teachers will ask "Which students are failing?" and Q will query S3 Data Lake. MVP uses Streamlit dashboard for progress views
- **Offline AI Tutor**: Local Llama 3.2 3B inference with <10s response time — Brain 2 (Edge)
- **Curriculum-Grounded RAG**: ChromaDB retrieves textbook chunks, prevents hallucination
- **Semantic Grading**: AI evaluates subjective answers with 0-10 scoring and feedback
- **Red Pen Feedback**: Text-based error identification and corrections (visual markup Phase 2)
- **Panic Mode**: Distraction-free exam simulator with timer and auto-grading (maximized layout, non-exam UI hidden)
- **Hinglish Support**: Mixed Hindi-English input and bilingual explanations
- **Adaptive Difficulty**: Beginner/Intermediate/Expert prompt tuning
- **AI Flashcards**: Auto-generated Q&A pairs with spaced repetition
- **Video Caching + RAG (Phase 2)**: H.265 videos with transcript indexing; MVP focuses on text/PDF RAG
- **Streak System**: Daily engagement tracking with milestone badges
- **Modern UI**: Clean Streamlit interface with custom CSS, dark/light theme toggle (default: dark), glassmorphic polish as time permits
- **Solo Mode**: Independent learning with silent background sync, no teacher linkage required
- **Delta Sync**: GraphQL-based minimal data transmission (<5KB delta / <50KB upper bound)
- **Teacher Dashboard**: Streamlit-based progress view for MVP; receives summarized metrics, not raw answers. Phase 2 adds Amazon Q Copilot accessed via `qbusiness` boto3 API for NL analytics (S3 Data Lake). React version with Cognito RBAC also in Phase 2.

## 9. Technical Decisions and Rationale

### Ollama + Llama 3.2 3B
- **Why**: Runs on CPU-only hardware; adaptive quantization selects Q4_K_M (6GB+) or Q2_K (4GB) based on available RAM
- **Trade-off**: Q2_K reduces precision but RAG compensates by grounding responses in curriculum
- **Alternative Rejected**: Cloud APIs (require internet), larger models (exceed memory)

### ChromaDB + all-MiniLM-L6-v2
- **Why**: Lightweight vector store, Python-native, <500MB for 10 textbooks. Uses `all-MiniLM-L6-v2` (22M params, ~80MB) as embedding model — CPU-only, offline, ChromaDB default
- **Alternative Rejected**: Pinecone/Weaviate (cloud-dependent), FAISS (no persistence layer), Ollama embeddings via `nomic-embed-text` (~274MB — larger footprint)

### Streamlit
- **Why**: Rapid prototyping, Python ecosystem, custom CSS for glassmorphic design
- **Alternative Rejected**: React (slower development), Electron (larger bundle size)

### AWS AppSync (GraphQL)
- **Why**: Delta sync reduces bandwidth, GraphQL field selection minimizes payloads
- **Conflict Resolution**: Timestamp-based (most recent write prevails); sufficient for single-user-per-device model
- **Alternative Rejected**: REST (larger payloads), Firebase (vendor lock-in)

### Amazon Bedrock (Curriculum Engine)
- **Why**: Brain 1 (Cloud Strategy) — generates quizzes, Micro-Learning Units, flashcards, and analytics summaries from raw PDFs. Content created once in cloud, consumed many times on edge.
- **Not Used For**: Student chat, live tutoring, or grading — those are Brain 2 (Edge Tactics).
- **Alternative Rejected**: Cloud APIs for real-time learning (violates offline-first)

> Full capability tables, data pipeline, and "Why Bedrock" rationale: see [requirements.md §5.3 — Req 9](requirements.md).

### Amazon Q Business (Teacher Copilot — Phase 2)
- **Why**: Managed RAG service over S3 Data Lake — teachers ask NL questions ("Which students are failing Algebra?"), Q reads Lambda-generated summaries and responds.
- **Phase**: Phase 2 implementation. MVP uses Streamlit dashboard for teacher progress views.
- **Data Pipeline (Phase 2)**: S3 upload → Lambda converts JSON → text summary → `/summaries/` → Q indexes via native S3 connector
- **Alternative Rejected**: Custom dashboards (manual data processing), OpenSearch (over-engineered for 500 students)

> Full data pipeline, query examples, pricing, and "Why Amazon Q" rationale: see [requirements.md §5.3 — Amazon Q Business](requirements.md).


### H.265 Video Encoding
- **Why**: 50% smaller than H.264 at same quality, critical for 2G/3G sync
- **Alternative Rejected**: H.264 (larger files), streaming (requires persistent connection)

### Local JSON Storage
- **Why**: Zero dependencies, human-readable, easy backup/restore
- **Alternative Rejected**: SQLite (overkill for small data), cloud DB (defeats offline-first)

## 10. Constraints and Trade-offs

### Model Limitations
- 3B parameter model less capable than GPT-4 or Claude
- May struggle with complex reasoning or niche topics
- **Mitigation**: RAG grounds responses in curriculum, reducing hallucination

### Hardware Requirements
- 4GB RAM minimum excludes older devices
- i3 CPU results in 8-10s inference latency
- **Mitigation**: Optimize prompts, cache frequent queries, provide hardware tips

### Storage Constraints
- 2GB core installation limit (app + LLM + embedding model); 2.5GB total with textbook embeddings
- Video caching (Phase 2) would compete with embeddings for disk space
- **Mitigation**: User-controlled content management, suggest deletions when low

### Sync Reliability
- 2G/3G networks may fail mid-sync
- Timestamp-based conflict resolution (most recent write prevails)
- **Mitigation**: Queue mutations locally, retry with exponential backoff

### Grading Accuracy
- AI grading may miss nuanced errors or cultural context
- No guarantee of parity with human teacher evaluation
- **Mitigation**: Show confidence scores, allow teacher override in dashboard

### Hinglish Limitations
- Llama 3.2 3B not fine-tuned for Hindi-English code-mixing
- Response quality lower than English-only queries
- **Mitigation**: Phase 2 evaluates Airavata (IIT-Madras), OpenHathi (Sarvam AI) for better Hinglish support

## 11. Scalability and Future Scope

### Short-Term (3-6 months)
- Amazon Q Business Teacher Copilot (NL analytics over S3 Data Lake)
- DynamoDB + Cognito for institutional multi-tenancy
- Amazon Q upgrades to DynamoDB as richer data source
- Voice input/output for accessibility (Transcribe + Polly)
- IoT Core MQTT for low-bandwidth sync

### Medium-Term (6-12 months)
- Knowledge distillation: Bedrock generates synthetic data to fine-tune edge model via LoRA
- Federated learning via AWS (Lambda aggregation + S3 model distribution)
- Mobile app (Android) with MLC LLM on-device inference
- Integration with government education portals

### Long-Term (1-2 years)
- On-device model training for personalization
- Blockchain-based credential verification
- Multi-language expansion (Bengali, Marathi, Gujarati)
- Teacher training modules and content authoring tools

### Technical Scalability
- Current architecture supports 1000+ students per teacher
- S3 + AppSync scale horizontally without code changes
- Local-first design eliminates server bottlenecks

## 12. Impact and Use Cases

### Educational Impact
- **Access**: India has 264 million school-enrolled students (UDISE+ 2023-24); over 60% in rural areas lack reliable broadband (TRAI 2024). Studaxis brings AI tutoring to these students without connectivity dependency.
- **Equity**: State government laptop programs (UP Free Laptop Yojana, Tamil Nadu Laptop Scheme, and similar initiatives) have distributed millions of devices — yet without offline AI software, they remain underutilized for self-study. Studaxis activates this dormant hardware.
- **Personalization**: India's average pupil-teacher ratio is 26:1 nationally, reaching 40:1+ in rural government schools (UDISE+). AI enables 1-on-1 tutoring at scale — something no human staffing model can achieve.

### Validation Targets
- **Hardware Feasibility**: Llama 3.2 3B Q2_K will be tested on Intel i3-6006U (4GB DDR4) — inference expected to complete in 8–12s, peak RAM ≤2.8GB
- **RAG Quality**: Target ≥90% relevant retrieval rate across 50 curriculum questions using 3 NCERT textbooks
- **Sync Efficiency**: Delta sync payloads will target an average of <5KB per sync
- **Offline Operation**: Full session (chat + quiz + grading + flashcards) will be validated at 0 kbps

> See [requirements.md §11.2](requirements.md) for full validation methodology and planned pilot studies.

### Social Impact
- **Economic Mobility**: India produces 1.5 million engineering graduates annually, yet only ~45% are considered employable (Aspiring Minds). Better AI-assisted preparation directly improves exam scores, placement rates, and upward mobility.
- **Language Inclusion**: 57% of Indian students are educated in Hindi-medium or regional-language schools (NCERT). Hinglish support reduces the English proficiency barrier that excludes them from global AI tools like ChatGPT.
- **Teacher Efficiency**: With 1.02 million teacher vacancies nationwide (MoE 2024), AI-automated grading frees existing teachers for high-touch interventions where human judgment matters most.

### Technical Impact
- **Proof of Concept**: Demonstrates that a 3B-parameter model on a $200 government laptop can deliver meaningful AI tutoring — challenging the assumption that AI requires cloud infrastructure
- **Replicability**: The Dual-Brain Architecture (cloud creates, edge delivers) is applicable to healthcare (diagnostics at rural PHCs), agriculture (crop advisory at 0 kbps), and vocational training
- **Open Source Potential**: India's 1.4 million schools across 600+ districts present a massive distribution opportunity; open-sourcing enables government and NGO adoption at national scale

### Use Cases
1. **Rural School**: 50 students share 10 laptops, sync progress weekly at internet cafe
2. **Exam Prep**: Engineering student practices coding problems offline during commute
3. **Teacher Training**: Educator uses dashboard to identify struggling students, adjusts curriculum
4. **Solo Learner**: Government job aspirant uploads UPSC prep PDFs, studies with AI-powered Q&A
5. **Video Learning (Phase 2)**: Student downloads lecture, pauses to ask "Explain this theorem," gets instant AI response

## 13. Demo Script

The following 5-minute demo flow is designed to showcase all four evaluation criteria in sequence.

### Act 1: The Problem (30s)
- Show a map of India's digital connectivity gaps (TRAI data)
- Open ChatGPT → disconnect WiFi → show it fails. "This is what 264 million students experience."

### Act 2: Offline AI Tutor — Brain 2 in Action (90s)
- Launch Studaxis on a real i3/4GB laptop (or equivalent)
- **WiFi is OFF** throughout this entire act
- Ask a Physics question in Hinglish → show RAG-grounded response with source citations
- Take a 3-question quiz → show AI grading with Red Pen feedback (0–10 scores)
- Show flashcard generation from an NCERT chapter
- Activate Panic Mode → show exam simulator with timer

### Act 3: The Cloud Brain — Brain 1 in Action (60s)
- **Switch to Teacher Dashboard** (WiFi ON)
- Show Streamlit Teacher Dashboard: aggregated student scores, streaks, topic-wise performance
- Show Bedrock Curriculum Engine: generate a remedial quiz from a textbook chapter
- Show the quiz appearing on the student device after sync
- Mention Phase 2: "Amazon Q will let teachers ask natural language questions — 'Which students are failing Algebra?' — over this same data"

### Act 4: Architecture & Business (60s)
- Show Dual-Brain Architecture diagram
- Highlight AWS stack: Bedrock + Lambda + AppSync + S3 — all MVP; Amazon Q planned for Phase 2
- Flash cost slide: $0.07/student/month, freemium + institutional licensing model
- Show the 10-step sync cycle diagram

### Act 5: Impact & Close (30s)
- Show validation targets: 8–12s inference, ≥90% RAG accuracy, <5KB sync payloads
- "Cloud for Strategy. Edge for Tactics. 100% learning at 0 kbps."

> **Demo Environment Checklist:** Laptop with Ollama pre-installed, 3 NCERT textbooks pre-embed
ded, User_Stats pre-populated with sample data, AWS services configured and live.

## 14. AI-Assisted Development

Studaxis will be built using AI-assisted development tools throughout the engineering process. AWS Kiro's Agentic IDE will be used for architecture iteration, code scaffolding, prompt engineering, debugging, and documentation drafting. All AI-generated outputs will be human-reviewed and validated.

> See [requirements.md §11.1](requirements.md) for detailed AI tool usage by development phase.

## 15. Business Model

Studaxis employs a **freemium + institutional licensing** model. The free tier (full offline AI tutoring) costs zero to operate — students run everything locally. Revenue comes from institutional licensing (₹30–500/student/year) covering Teacher Dashboard, Bedrock content generation, and Phase 2 additions like Amazon Q analytics. Target channels: government school tenders, NGO partnerships (Pratham, Teach For India), and open-source community adoption.

> See [requirements.md §10.4](requirements.md) for detailed pricing tiers, GTM strategy, and sustainability analysis.

> See [requirements.md §11](requirements.md) for Development Methodology, AI-assisted workflow, and validation plan.

## 16. Glossary

- **Dual-Brain Architecture**: Bedrock (Brain 1/Cloud) creates content intelligence; Llama (Brain 2/Edge) delivers learning at 0 kbps; Phase 2 adds Amazon Q to make it queryable for teachers via S3 Data Lake
- **Curriculum_Engine**: Amazon Bedrock-powered pipeline that generates quizzes, Micro-Learning Units, flashcard sets, and analytics summaries
- **Micro-Learning Unit (MLU)**: Bedrock-generated content package containing topic summary, key concepts, and practice problems — optimized for edge delivery
- **Teacher_Copilot**: Amazon Q Business agent planned for Phase 2; will be accessed via `qbusiness` boto3 API from the Teacher Dashboard; indexes S3 Data Lake (Lambda-generated text summaries) for natural language analytics queries. MVP uses Streamlit dashboard for progress views (MVP: Streamlit / Phase 2: Amazon Q)
- **Lambda_Translator**: AWS Lambda function triggered on S3 upload; converts `User_Stats.json` → natural language text summaries for Amazon Q indexing (Phase 2)
- **Local_AI_Engine**: Quantized Llama 3.2 3B via Ollama for offline inference (Brain 2/Edge)
- **Vector_Store**: ChromaDB with `all-MiniLM-L6-v2` embeddings (~80MB model) for semantic RAG retrieval
- **RAG**: Retrieval-Augmented Generation—combining vector search with AI generation
- **Sync_Manager**: Python service for burst sync with cloud storage
- **AppSync_Client**: AWS AppSync GraphQL client for delta synchronization
- **Quiz_Engine**: Component for quiz generation, presentation, and grading
- **Panic Mode**: Exam simulator with timed, distraction-free environment
- **Solo Mode**: Independent learning where cloud sync occurs silently in the background, without requiring teacher linkage or supervision
- **Red Pen Grading**: AI-generated text feedback identifying errors and corrections; visual markup (strikethrough, colors) planned for Phase 2
- **Modern_UI**: Clean interface with Streamlit supporting dark and light themes via user toggle (default: dark); glassmorphic styling (blur, gradients) applied as time permits
- **Hinglish**: Mixed Hindi-English language support
- **Delta Sync**: Transmitting only changed data fields to minimize bandwidth
- **Q4_K_M**: 4-bit quantization method for model compression
- **Q2_K**: 2-bit quantization reducing Llama 3.2 3B to ~1.1GB; deployed on 4GB devices when higher quantizations cannot fit
- **Spaced Repetition**: Flashcard algorithm adjusting review frequency based on difficulty
- **Amazon Q Business**: AWS managed RAG service planned for Phase 2 as Teacher Copilot; will index S3 Data Lake via native S3 connector for natural language analytics — no database dependency (Phase 2)
- **S3_Data_Lake**: S3 bucket structure where student stats are synced, converted to text summaries by Lambda, and indexed by Amazon Q for teacher queries (Phase 2)
