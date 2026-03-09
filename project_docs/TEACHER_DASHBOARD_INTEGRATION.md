# Teacher Dashboard Integration Guide

## Overview

This document explains the complete integration between the teacher dashboard, AWS backend, and student applications for the Studaxis platform.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Teacher Dashboard (React)                 │
│  - Class Management                                          │
│  - Quiz Generation (Bedrock)                                 │
│  - Assignment Creation                                       │
│  - Student Analytics                                         │
└────────────┬────────────────────────────────────────────────┘
             │
             ├─── API Gateway (REST) ───┐
             │                           │
             ├─── AppSync (GraphQL) ────┤
             │                           │
             v                           v
┌────────────────────────┐    ┌──────────────────────────┐
│   Lambda Functions     │    │   DynamoDB Tables        │
│  - class_manager       │───▶│  - studaxis-classes      │
│  - quiz_generation     │    │  - studaxis-assignments  │
│  - assignment_manager  │    │  - studaxis-student-sync │
│  - offline_sync        │    └──────────────────────────┘
└────────────────────────┘
             │
             v
┌────────────────────────────────────────────────────────────┐
│              Student App (FastAPI + React)                  │
│  - Fetches assignments via class_code                       │
│  - Receives notifications                                   │
│  - Syncs progress to AWS                                    │
│  - 100% offline-first learning                              │
└────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Teacher Creates Class

**Frontend**: `Classes.tsx` → `createClass()`
**API**: `POST /classes`
**Lambda**: `class_manager/handler.py`
**DynamoDB**: `studaxis-classes` table

```typescript
// Teacher creates class
const newClass = await createClass(teacherId, "Physics Grade 10");
// Returns: { class_id, class_code: "ABC123", class_name, teacher_id }
```

**DynamoDB Record**:
```json
{
  "class_id": "uuid-1234",
  "teacher_id": "teacher_001",
  "class_name": "Physics Grade 10",
  "class_code": "ABC123",
  "created_at": "2026-03-09T10:00:00Z"
}
```

### 2. Student Joins Class

**Student App**: Settings → Enter class code "ABC123"
**API**: `GET /classes/verify?code=ABC123`
**Lambda**: `class_manager/handler.py` → `verify_class_code()`

```python
# Student profile updated
profile.class_code = "ABC123"
profile.class_id = "uuid-1234"
profile.teacher_linked = True
```

### 3. Teacher Generates Quiz (Bedrock)

**Frontend**: `QuizGenerator.tsx` → `generateQuiz()`
**API**: `POST /generateQuiz`
**Lambda**: `quiz_generation/handler.py`
**Bedrock**: `amazon.nova-2-lite-v1:0`

```typescript
const quiz = await fetch(`${API_GATEWAY_URL}/generateQuiz`, {
  method: 'POST',
  body: JSON.stringify({
    topic: "Newton's Laws of Motion",
    difficulty: "medium",
    num_questions: 5
  })
});
// Returns: { quiz_title, questions: [...], generated_at, model }
```

**Quiz Structure**:
```json
{
  "quiz_title": "Newton's Laws of Motion Quiz",
  "topic": "Physics",
  "difficulty": "medium",
  "questions": [
    {
      "question": "State Newton's second law",
      "question_type": "mcq",
      "options": ["A. F=ma", "B. F=mv", "C. F=m/a", "D. F=a/m"],
      "correct_answer": "A. F=ma",
      "answer": "A. F=ma",
      "explanation": "Force equals mass times acceleration"
    }
  ],
  "generated_at": "2026-03-09T10:30:00Z",
  "model": "amazon.nova-2-lite-v1:0"
}
```

### 4. Teacher Assigns Quiz to Class

**Frontend**: `AssignmentsManager.tsx` → `createAssignment()`
**API**: `POST /assignments`
**Lambda**: `assignment_manager/handler.py`
**DynamoDB**: `studaxis-assignments` table

```typescript
await createAssignment({
  teacher_id: "teacher_001",
  class_code: "ABC123",
  content_type: "quiz",
  content_id: "quiz_5678",
  title: "Newton's Laws Quiz",
  description: "Complete by Friday",
  due_date: "2026-03-15T23:59:59Z",
  content_data: quizData // Full quiz JSON
});
```

**DynamoDB Record**:
```json
{
  "assignment_id": "assign_9999",
  "teacher_id": "teacher_001",
  "class_code": "ABC123",
  "content_type": "quiz",
  "content_id": "quiz_5678",
  "title": "Newton's Laws Quiz",
  "description": "Complete by Friday",
  "due_date": "2026-03-15T23:59:59Z",
  "created_at": "2026-03-09T10:35:00Z",
  "status": "active",
  "content_data": "{...quiz JSON...}"
}
```

### 5. Student Syncs and Receives Assignment

**Student App**: Background sync or manual sync button
**API**: `GET /api/student/assignments?class_code=ABC123`
**Backend**: `backend/main.py` → Fetches from Lambda

```python
# Student syncs
assignments = await get_student_assignments(user_id, class_code)
# Returns: [{ assignment_id, title, content_type, due_date, completed: false }]

# Create notification
notification = {
    "id": str(uuid.uuid4()),
    "type": "assignment",
    "title": "New Quiz Assigned",
    "message": "Newton's Laws Quiz - Due Friday",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "read": False,
    "assignment_id": "assign_9999"
}
```

### 6. Student Completes Assignment

**Student App**: Takes quiz → submits answers
**API**: `POST /api/quiz/{quiz_id}/submit`
**Backend**: Grades locally with Ollama, updates stats

```python
# Grade quiz
results = grade_quiz_answers(quiz, student_answers)
score = sum(r["score"] for r in results)

# Update stats
update_quiz_stats(user_id, score, max_score, topic)
update_streak(user_id)

# Mark assignment complete
await mark_assignment_complete(user_id, assignment_id, score)

# Enqueue for cloud sync
enqueue_sync(user_id, "assignment_complete", {
    "assignment_id": assignment_id,
    "score": score,
    "completed_at": datetime.now(timezone.utc).isoformat()
})
```

### 7. Progress Syncs to Cloud

**Student App**: Background sync when online
**API**: AppSync GraphQL mutation `recordQuizAttempt`
**Lambda**: `offline_sync/handler.py`
**DynamoDB**: `studaxis-student-sync` table

```graphql
mutation RecordQuizAttempt {
  recordQuizAttempt(
    userId: "student_001"
    classCode: "ABC123"
    quizId: "quiz_5678"
    score: 4
    totalQuestions: 5
    subject: "Physics"
    difficulty: "medium"
    deviceId: "laptop_xyz"
    completedAtLocal: "2026-03-10T14:30:00Z"
  ) {
    attemptId
    userId
    score
    accuracyPercentage
    syncedAt
  }
}
```

**DynamoDB Records**:

**Individual Attempt**:
```json
{
  "user_id": "student_001_quiz_5678_1710079800",
  "record_type": "quiz_attempt",
  "userId": "student_001",
  "quizId": "quiz_5678",
  "score": 4,
  "totalQuestions": 5,
  "accuracyPercentage": 80.0,
  "subject": "Physics",
  "difficulty": "medium",
  "completedAtLocal": "2026-03-10T14:30:00Z",
  "syncedAt": "2026-03-10T14:31:00Z"
}
```

**Aggregate Metadata** (for teacher dashboard):
```json
{
  "user_id": "student_001",
  "class_code": "ABC123",
  "current_streak": 5,
  "device_id": "laptop_xyz",
  "last_quiz_date": "2026-03-10",
  "last_quiz_score": 4,
  "last_sync_timestamp": "2026-03-10T14:31:00Z",
  "total_sessions": 12,
  "sync_status": "synced"
}
```

### 8. Teacher Views Student Progress

**Frontend**: `Analytics.tsx` → `listStudentProgresses()`
**API**: AppSync GraphQL query
**Lambda**: `content_distribution/handler.py` (AppSync resolver)
**DynamoDB**: Scans `studaxis-student-sync` with `class_code` filter

```graphql
query ListStudentProgresses {
  listStudentProgresses(class_code: "ABC123", limit: 100) {
    items {
      user_id
      class_code
      current_streak
      last_quiz_date
      last_sync_timestamp
    }
  }
}
```

**Teacher Dashboard Display**:
- Total students in class
- Average streak
- Recent quiz scores
- Assignment completion rates
- Weak topics (aggregated from quiz attempts)

## API Endpoints Reference

### Class Management (API Gateway)

| Method | Endpoint | Lambda | Purpose |
|--------|----------|--------|---------|
| POST | `/classes` | `class_manager` | Create new class |
| GET | `/classes?teacher_id=X` | `class_manager` | List teacher's classes |
| GET | `/classes/verify?code=X` | `class_manager` | Verify class code (student join) |

### Quiz Generation (API Gateway)

| Method | Endpoint | Lambda | Purpose |
|--------|----------|--------|---------|
| POST | `/generateQuiz` | `quiz_generation` | Generate quiz via Bedrock |
| POST | `/generateNotes` | `quiz_generation` | Generate study notes via Bedrock |

### Assignment Management (API Gateway)

| Method | Endpoint | Lambda | Purpose |
|--------|----------|--------|---------|
| POST | `/assignments` | `assignment_manager` | Create assignment |
| GET | `/assignments?class_code=X` | `assignment_manager` | List class assignments |
| GET | `/assignments/student?user_id=X&class_code=Y` | `assignment_manager` | Get student assignments |
| POST | `/assignments/complete` | `assignment_manager` | Mark assignment complete |
| DELETE | `/assignments/{id}` | `assignment_manager` | Delete assignment |

### Student Progress (AppSync GraphQL)

| Type | Operation | Lambda | Purpose |
|------|-----------|--------|---------|
| Query | `listStudentProgresses` | `content_distribution` | Get all students in class |
| Query | `getStudentAssignments` | `assignment_manager` | Get assignments for student |
| Mutation | `recordQuizAttempt` | `offline_sync` | Sync quiz result |
| Mutation | `updateStreak` | `offline_sync` | Sync streak update |
| Subscription | `onNewAssignment` | - | Real-time assignment notifications |

### Student Backend (FastAPI)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/student/assignments?class_code=X` | Fetch assignments for class |
| POST | `/api/student/assignment-complete` | Mark assignment done |
| GET | `/api/notifications` | Get student notifications |
| POST | `/api/quiz/{id}/submit` | Submit quiz answers |
| POST | `/api/sync` | Trigger cloud sync |

## Environment Variables

### Teacher Dashboard (.env)

```bash
VITE_API_GATEWAY_URL=https://xyz.execute-api.ap-south-1.amazonaws.com/prod
VITE_APPSYNC_ENDPOINT=https://abc.appsync-api.ap-south-1.amazonaws.com/graphql
VITE_APPSYNC_API_KEY=da2-xxxxxxxxxxxxx
VITE_TEACHER_BACKEND_URL=http://localhost:6782
```

### Student Backend (.env)

```bash
STUDAXIS_BASE_PATH=./backend
AWS_REGION=ap-south-1
APPSYNC_ENDPOINT=https://abc.appsync-api.ap-south-1.amazonaws.com/graphql
APPSYNC_API_KEY=da2-xxxxxxxxxxxxx
API_GATEWAY_URL=https://xyz.execute-api.ap-south-1.amazonaws.com/prod
OLLAMA_BASE_URL=http://localhost:11434
```

### Lambda Functions

```bash
LOG_LEVEL=INFO
BEDROCK_REGION=ap-south-1
BEDROCK_MODEL_ID=arn:aws:bedrock:ap-south-1:...:inference-profile/global.amazon.nova-2-lite-v1:0
DYNAMODB_TABLE_NAME=studaxis-student-sync
CLASSES_TABLE_NAME=studaxis-classes
ASSIGNMENTS_TABLE_NAME=studaxis-assignments
S3_BUCKET_NAME=studaxis-payloads
```

## DynamoDB Table Schemas

### studaxis-classes

```
PK: class_id (String)
Attributes:
  - teacher_id (String)
  - class_name (String)
  - class_code (String) [GSI]
  - created_at (String, ISO 8601)
```

### studaxis-assignments

```
PK: assignment_id (String)
Attributes:
  - teacher_id (String)
  - class_code (String) [GSI]
  - content_type (String: "quiz" | "notes")
  - content_id (String)
  - title (String)
  - description (String)
  - due_date (String, ISO 8601)
  - created_at (String, ISO 8601)
  - status (String: "active" | "deleted")
  - content_data (String, JSON)
```

### studaxis-student-sync

```
PK: user_id (String)
Attributes:
  - class_code (String)
  - current_streak (Number)
  - device_id (String)
  - last_quiz_date (String, YYYY-MM-DD)
  - last_quiz_score (Number)
  - last_sync_timestamp (String, ISO 8601)
  - total_sessions (Number)
  - sync_status (String: "synced" | "pending" | "error")
  - record_type (String: "student_aggregate" | "quiz_attempt")
```

## Deployment Checklist

### 1. Deploy Lambda Functions

```bash
cd aws-infra/lambda
sam build
sam deploy --guided
```

### 2. Create DynamoDB Tables

```bash
aws dynamodb create-table \
  --table-name studaxis-classes \
  --attribute-definitions AttributeName=class_id,AttributeType=S \
  --key-schema AttributeName=class_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

aws dynamodb create-table \
  --table-name studaxis-assignments \
  --attribute-definitions AttributeName=assignment_id,AttributeType=S \
  --key-schema AttributeName=assignment_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### 3. Deploy AppSync API

```bash
cd aws-infra/appsync
# Update schema.graphql
# Configure resolvers in AWS Console or via CDK/CloudFormation
```

### 4. Deploy Teacher Dashboard

```bash
cd aws-infra/teacher-dashboard-web
npm install
npm run build
# Deploy to Amplify or S3 + CloudFront
```

### 5. Configure Student Backend

```bash
cd backend
pip install -r requirements.txt
# Update .env with AWS credentials
uvicorn main:app --host 0.0.0.0 --port 6782
```

## Testing Flow

### End-to-End Test

1. **Teacher creates class**:
   ```bash
   curl -X POST https://api.studaxis.com/classes \
     -H "Content-Type: application/json" \
     -d '{"teacher_id":"T001","class_name":"Test Class"}'
   # Returns: {"class_id":"C001","class_code":"ABC123"}
   ```

2. **Student joins class**:
   ```bash
   # In student app settings, enter code: ABC123
   # Verifies via GET /classes/verify?code=ABC123
   ```

3. **Teacher generates quiz**:
   ```bash
   curl -X POST https://api.studaxis.com/generateQuiz \
     -H "Content-Type: application/json" \
     -d '{"topic":"Physics","difficulty":"easy","num_questions":3}'
   ```

4. **Teacher assigns quiz**:
   ```bash
   curl -X POST https://api.studaxis.com/assignments \
     -H "Content-Type: application/json" \
     -d '{"teacher_id":"T001","class_code":"ABC123","content_type":"quiz","content_id":"Q001","title":"Physics Quiz 1"}'
   ```

5. **Student syncs and sees assignment**:
   ```bash
   # Student app calls: GET /api/student/assignments?class_code=ABC123
   # Notification created automatically
   ```

6. **Student completes quiz**:
   ```bash
   # Student takes quiz offline
   # Submits: POST /api/quiz/Q001/submit
   # Marks complete: POST /api/student/assignment-complete
   ```

7. **Progress syncs to cloud**:
   ```bash
   # Background sync calls AppSync mutation recordQuizAttempt
   # DynamoDB updated with score and metadata
   ```

8. **Teacher views analytics**:
   ```bash
   # Dashboard queries: listStudentProgresses(class_code: "ABC123")
   # Shows student progress, streaks, scores
   ```

## Offline-First Guarantees

1. **Student Learning**: 100% offline with Ollama (Brain 2)
2. **Quiz Taking**: Fully offline, graded locally
3. **Flashcards**: Generated and reviewed offline
4. **Sync Queue**: Mutations queued when offline, synced when online
5. **Assignment Fetch**: Cached locally after first sync
6. **Notifications**: Stored locally, no cloud dependency

## Security Considerations

1. **API Gateway**: IAM authentication for teacher endpoints
2. **AppSync**: API key auth (MVP), Cognito in Phase 2
3. **Class Codes**: 6-character alphanumeric, collision-resistant
4. **Student Privacy**: Solo learners (class_code="SOLO") never visible to teachers
5. **Data Encryption**: SSE-S3 for S3, AWS-managed keys for DynamoDB
6. **CORS**: Restricted to dashboard domain in production

## Performance Targets

- **Quiz Generation**: <30s (Bedrock inference)
- **Assignment Creation**: <500ms (DynamoDB write)
- **Student Sync**: <2s for <5KB payload
- **Dashboard Load**: <2s (p95)
- **Analytics Query**: <100ms (DynamoDB scan with filter)

## Troubleshooting

### Student not receiving assignments

1. Check `class_code` in student profile matches teacher's class
2. Verify assignment `status` is "active" in DynamoDB
3. Check student sync logs for errors
4. Ensure API Gateway URL is correct in student .env

### Teacher can't see student progress

1. Verify AppSync endpoint and API key
2. Check student has synced at least once (online)
3. Confirm `class_code` filter in GraphQL query
4. Check DynamoDB for student records with matching `class_code`

### Quiz generation fails

1. Check Bedrock model ID and region
2. Verify IAM permissions for Lambda → Bedrock
3. Check CloudWatch logs for Lambda errors
4. Ensure request payload is valid JSON

## Future Enhancements (Phase 2)

- Real-time assignment notifications via AppSync subscriptions
- Amazon Q Business for natural language analytics
- Cognito authentication for multi-tenancy
- Advanced conflict resolution for offline edits
- Parent dashboard with read-only access
- Leaderboards and gamification
