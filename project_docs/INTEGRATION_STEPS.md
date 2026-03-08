# Integration Steps — Studaxis

**Data flows and integration between Edge (Student) and Cloud (AWS)**

---

## 1. Sync Cycle: 8-Step Round-Trip

This is the complete round-trip of the Dual-Brain Architecture. Steps 1–4 happen on sync (seconds). Steps 5–6 are available immediately. Steps 7–8 are teacher-initiated (minutes to hours).

| Step | Actor | Action | Where |
|------|-------|--------|-------|
| **1** | Student | Completes activity (quiz, chat, flashcard review) → `User_Stats.json` updated locally | Edge |
| **2** | Sync_Manager | Detects connectivity → checks network status every 30 seconds | Edge |
| **3** | Sync_Manager | Constructs delta payload → only changed fields since `lastSyncTimestamp` (~5KB) | Edge |
| **4** | AppSync_Client | Sends AppSync mutation → GraphQL delta sync via HTTPS | Edge → Cloud |
| **5** | Lambda / S3 | S3 upload triggered → `student_<id>_stats.json` lands in S3 bucket | Cloud |
| **6** | Teacher | Views dashboard → sees aggregated student progress | Cloud |
| **7** | Teacher | Generates remedial content via Bedrock Curriculum Engine → targeted quizzes | Cloud |
| **8** | Student | Next sync → new quiz content downloaded to device → integrated into local Quiz_Engine | Cloud → Edge |

**Phase 2 Enhancement (Amazon Q):** Steps 5–6 expand: Lambda fires on S3 event → converts JSON to NL summary → Amazon Q indexes summaries → teachers ask NL questions ("Which students are failing Algebra?") → Q responds in plain English.

---

## 2. Quiz Generation Workflow Integration

End-to-end flow when a teacher generates a quiz:

| Step | Component | Action |
|------|-----------|--------|
| 1 | Teacher Dashboard | Teacher clicks "Generate Quiz" with topic/chapter |
| 2 | Teacher Dashboard | Sends POST request to API Gateway (quiz generation endpoint) |
| 3 | API Gateway | Validates payload, invokes Quiz_Lambda |
| 4 | Quiz_Lambda | Logs request to CloudWatch (correlation ID) |
| 5 | Quiz_Lambda | Calls Amazon Bedrock with textbook context in prompt |
| 6 | Amazon Bedrock | Returns AI-generated quiz content (JSON) |
| 7 | Quiz_Lambda | Validates response format |
| 8 | Quiz_Lambda | Stores quiz in S3_Payload_Store with unique object key |
| 9 | Quiz_Lambda | Registers metadata in DynamoDB (`studaxis-quiz-index`) |
| 10 | Quiz_Lambda | Returns S3 object key to Teacher Dashboard |
| 11 | Content Distribution | When student syncs, Lambda `content_distribution` fetches quiz from S3 |
| 12 | Student Device | Sync_Manager downloads quiz → integrates into local Quiz_Engine |

**Integration points:** API Gateway → Lambda, Lambda → Bedrock, Lambda → S3, Lambda → DynamoDB, Sync_Manager → AppSync → Lambda.

---

## 3. Data Separation (DynamoDB vs S3)

| Data Type | Storage | Size | Purpose |
|-----------|---------|------|---------|
| Sync metadata | DynamoDB (`studaxis-student-sync`) | <4KB | User ID, streak, last sync timestamp, sync status |
| Heavy payloads | S3 (`studaxis-payloads`) | Variable | Full `User_Stats.json`, quiz content, PDFs |
| Quiz metadata | DynamoDB (`studaxis-quiz-index`) | <4KB | Quiz ID, target class, S3 object key reference |
| Student stats | S3 (`studaxis-student-stats-2026`) | Variable | `student_<id>_stats.json` full payloads |

**Principle:** Dashboard queries DynamoDB for fast reads (<100ms). Heavy payloads fetched from S3 only when needed (e.g. pre-signed URLs for quiz content).

---

## 4. Content Distribution (Teacher → Student)

| Step | Component | Action |
|------|-----------|--------|
| 1 | Teacher | Assigns quiz to class via Teacher Dashboard |
| 2 | Content Distributor | Writes quiz metadata to DynamoDB with `class_code`, S3 key |
| 3 | Student | Syncs (online) → AppSync/ Lambda fetches pending assignments |
| 4 | Lambda | Queries `studaxis-quiz-index` by `user_id` / `class_code` |
| 5 | Lambda | Generates pre-signed S3 URL for quiz JSON |
| 6 | Student Device | Downloads quiz via pre-signed URL |
| 7 | Sync_Manager | Integrates quiz into local Quiz_Engine without overwriting progress |
| 8 | Content versioning | Prevents duplicate downloads; supports updates |

---

## 5. Connectivity-Independent Architecture

| Scenario | Behavior |
|----------|----------|
| **Offline** | Edge_AI (Ollama + ChromaDB) runs 100%; Sync_Manager queues mutations locally |
| **Online** | Sync_Manager flushes queue → AppSync delta sync → S3 upload |
| **Intermittent** | Retry with exponential backoff; mutations queued until sync succeeds |
| **First-time sync** | Student progress uploaded; teacher content downloaded (if assigned) |
| **Post-sync** | Learning continues offline with newly downloaded content |

**Guarantee:** Learning is never blocked by connectivity. Cloud is enhancement, not dependency.
