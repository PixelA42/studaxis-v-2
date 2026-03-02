# Project Structure

## Directory Layout

```
studaxis-vtwo/
├── local-app/              # Student-facing edge application
│   ├── streamlit_app.py    # Main Streamlit UI (bento grid, navigation)
│   ├── hardware_validator.py  # RAM/CPU checks, quantization recommendations
│   ├── quiz_engine.py      # Quiz presentation, submission, AI grading
│   ├── flashcard_engine.py # Flashcard generation, spaced repetition
│   ├── rag_engine.py       # ChromaDB RAG pipeline
│   ├── sync_manager.py     # Cloud sync logic (DynamoDB + S3)
│   └── utils/
│       ├── __init__.py
│       ├── ollama_client.py   # Ollama wrapper (inference, grading, RAG)
│       └── local_storage.py   # JSON persistence, backup/restore
│
├── aws-infra/              # Cloud infrastructure (Brain 1)
│   ├── lambda/
│   │   ├── sync_resolver.py       # AppSync GraphQL resolver
│   │   └── bedrock_content_gen.py # Quiz generation via Bedrock
│   ├── teacher-dashboard/
│   │   └── dashboard_app.py       # Streamlit teacher UI
│   └── cloudformation/
│       └── template.yaml          # AWS resource definitions
│
├── shared/                 # Common schemas and constants
│   ├── constants.py        # Shared config (models, prompts, limits)
│   └── schemas/
│       ├── user_stats_schema.json    # User progress structure
│       └── quiz_content_schema.json  # Quiz format specification
│
├── data/                   # Local storage (gitignored)
│   ├── chromadb/           # Vector store embeddings
│   ├── backups/            # User stats backups (last 7)
│   ├── sample_textbooks/   # PDF storage for RAG
│   └── user_stats.json     # Current user progress
│
├── tests/                  # Unit and property-based tests
│   ├── test_quiz_engine.py
│   ├── test_sync_manager.py
│   ├── test_rag_engine.py
│   └── test_ollama_client.py
│
├── .kiro/                  # Kiro IDE configuration
│   ├── specs/              # Feature specifications
│   │   └── aws-infrastructure-elevation/
│   │       ├── design.md
│   │       ├── design1.md
│   │       ├── requirements.md
│   │       └── tasks.md
│   └── steering/           # AI assistant guidance (this folder)
│       ├── product.md
│       ├── tech.md
│       └── structure.md
│
├── .env.example            # Local app config template
├── .env.aws.example        # AWS config template
├── .gitignore              # Git exclusions
├── requirements.txt        # Python dependencies
├── init.py                 # Initialization script
└── README.md               # Project documentation
```

## Component Responsibilities

### Local App (Edge - Brain 2)

**streamlit_app.py**
- Main UI entry point with page routing
- Sidebar navigation (Dashboard, Chat, Quiz, Flashcards, Panic Mode, Settings)
- Session state management
- Hardware validation on startup
- Theme management (light/dark toggle, default: light)

**hardware_validator.py**
- RAM, CPU, disk space validation
- Quantization recommendation (Q2_K/Q3_K_S/Q4_K_M based on available RAM)
- Runtime memory monitoring
- Optimization tips generation
- Standalone testing capability

**quiz_engine.py**
- Quiz loading from local storage or S3
- Question presentation and answer submission
- AI grading integration via ollama_client
- Score calculation and Red Pen feedback
- Results storage in user_stats.json

**flashcard_engine.py**
- Flashcard generation from textbook chapters
- Spaced repetition scheduling (Easy: 7 days, Medium: 3 days, Hard: 1 day)
- Review interface with difficulty marking
- Progress tracking

**rag_engine.py**
- ChromaDB initialization and management
- PDF text extraction (PyPDF2, pdfplumber)
- Text chunking (500 chars, 50 overlap)
- Embedding generation (all-MiniLM-L6-v2)
- Semantic search (top-K=3)
- Source reference tracking

**sync_manager.py**
- Network connectivity detection
- Offline mutation queueing
- Atomic sync strategy (S3 first, then DynamoDB)
- Exponential backoff retry logic
- Delta payload construction (<5KB target)

**utils/ollama_client.py**
- Ollama connection verification
- Text generation with temperature control
- RAG-powered generation with context chunks
- Semantic grading with Red Pen feedback
- Error handling and timeouts
- Standalone testing capability

**utils/local_storage.py**
- JSON-based user stats management
- Automatic timestamped backups (keep last 7)
- Streak tracking and updates
- Chat history management (keep last 50 messages)
- Delta sync preparation
- Backup/restore functionality

### AWS Infrastructure (Cloud - Brain 1)

**lambda/sync_resolver.py**
- AppSync GraphQL mutation handler
- S3 upload for student progress
- DynamoDB metadata updates
- Error handling and logging

**lambda/bedrock_content_gen.py**
- API Gateway request handler
- Bedrock prompt construction
- Quiz generation via Amazon Neo Lite v2
- S3 storage with unique keys
- Pre-signed URL generation (1-hour expiry)
- CloudWatch logging with correlation IDs

**teacher-dashboard/dashboard_app.py**
- Streamlit-based teacher UI
- DynamoDB metadata queries (<100ms)
- S3 payload fetching via reference keys
- Aggregated student progress views
- Quiz generation interface

**cloudformation/template.yaml**
- DynamoDB table definitions
- S3 bucket configurations
- Lambda function resources
- API Gateway setup
- IAM roles and policies

### Shared Resources

**constants.py**
- Model configurations (Ollama, Bedrock, embedding models)
- Quantization mappings by RAM
- Hardware requirements and limits
- System prompts by difficulty level
- RAG configuration (chunk size, top-K)
- UI themes (dark/light color schemes)
- Error and success messages
- Feature flags for phased rollout
- API timeouts and retry settings

**schemas/user_stats_schema.json**
- User ID and sync metadata
- Streak tracking structure
- Quiz statistics (total, correct, average score)
- Flashcard statistics (reviewed, mastered, due)
- Chat history format
- Preferences (difficulty, theme, language)
- Hardware info

**schemas/quiz_content_schema.json**
- Quiz metadata (ID, textbook, topic, difficulty)
- Question structure (ID, type, text, options)
- Correct answers and explanations
- Rubrics for free-response questions
- Generation metadata (model, timestamp, teacher ID)

## Data Flow Patterns

### Offline Learning Session
1. Student launches app → hardware_validator checks specs
2. Student asks question → rag_engine retrieves chunks → ollama_client generates response
3. Student takes quiz → quiz_engine presents questions → ollama_client grades answers
4. Results saved to local user_stats.json → sync_manager queues for next sync

### Online Sync Cycle
1. sync_manager detects connectivity
2. Constructs delta payload (only changed fields since last_sync_timestamp)
3. Uploads payload to S3 (idempotent with deterministic keys)
4. Updates DynamoDB metadata with S3 reference
5. If DynamoDB fails, marks sync_status="pending" and retries on next cycle

### Teacher Content Generation
1. Teacher accesses dashboard → queries DynamoDB for student metadata
2. Teacher requests quiz generation → API Gateway → Lambda
3. Lambda invokes Bedrock with textbook context
4. Bedrock returns quiz JSON → Lambda stores in S3
5. Lambda returns S3 key and pre-signed URL to dashboard
6. Next student sync downloads new quiz content

## File Naming Conventions

### Python Modules
- Snake_case for files: `quiz_engine.py`, `local_storage.py`
- PascalCase for classes: `QuizEngine`, `LocalStorage`, `OllamaClient`
- Snake_case for functions: `load_quiz()`, `grade_answer()`, `update_streak()`

### Data Files
- JSON for structured data: `user_stats.json`, `quiz_content.json`
- JSONL for logs: `chat_logs/{user_id}/{session_id}.jsonl`
- Timestamped backups: `user_stats_YYYYMMDD_HHMMSS.json`

### S3 Keys
- Quizzes: `quizzes/{quiz_id}.json`
- Textbooks: `textbooks/{textbook_id}.pdf`
- Chat logs: `chat_logs/{user_id}/{session_id}.jsonl`
- Student stats: `students/{user_id}/stats.json`

### DynamoDB Keys
- Partition key: `user_id` (String)
- Attributes: snake_case (`current_streak`, `last_sync_timestamp`)

## Testing Structure

### Unit Tests
- One test file per module: `test_quiz_engine.py`, `test_sync_manager.py`
- Test standalone components with mocked dependencies
- Focus on edge cases, error conditions, boundary values

### Property-Based Tests
- Use Hypothesis for Python, fast-check for TypeScript
- Tag with feature and property: `# Feature: aws-infrastructure-elevation, Property 1`
- Minimum 100 iterations per property test
- Test universal correctness across input space

### Integration Tests
- End-to-end workflows (chat → RAG → response)
- Sync flow (offline queue → online upload → DynamoDB + S3)
- Teacher dashboard (metadata query → payload fetch)

## Git Workflow

### Tracked Files
- All Python source code (`.py`)
- Configuration templates (`.env.example`, `.env.aws.example`)
- Schemas and constants (`shared/`)
- Requirements and initialization (`requirements.txt`, `init.py`)
- Directory structure markers (`.gitkeep`)

### Ignored Files
- Virtual environments (`studaxis-vtwo-env/`, `venv/`)
- Python cache (`__pycache__/`, `*.pyc`)
- Secrets (`.env`, `.env.aws`)
- Data and models (`data/`, `chromadb/`)
- IDE settings (`.vscode/`, `.idea/`)
- Logs and temp files (`*.log`, `*.tmp`)

## Module Import Patterns

### Local App Imports
```python
# Absolute imports from project root
from utils.ollama_client import OllamaClient
from utils.local_storage import LocalStorage
from shared.constants import OLLAMA_MODEL, RAG_TOP_K

# Relative imports within utils
from .local_storage import LocalStorage
```

### AWS Lambda Imports
```python
# Standard library
import json
import boto3
from datetime import datetime

# AWS SDK clients
s3 = boto3.client('s3')
dynamodb = boto3.client('dynamodb')
bedrock = boto3.client('bedrock-runtime')
```

## Configuration Management

### Environment Variables
- Local app: `.env` (gitignored, created from `.env.example`)
- AWS infra: `.env.aws` (gitignored, created from `.env.aws.example`)
- Shared constants: `shared/constants.py` (tracked)

### Secrets Handling
- Never commit `.env` or `.env.aws`
- Use AWS Secrets Manager for production credentials
- Use IAM roles for Lambda/ECS (no hardcoded keys)
- Pre-signed URLs for temporary S3 access

## Deployment Structure

### Local App Deployment
- Bundled installer with Python + Ollama + dependencies
- User runs `init.py` for first-time setup
- Streamlit app launches via `streamlit run local-app/streamlit_app.py`

### AWS Deployment
- CloudFormation stack for infrastructure
- Lambda functions deployed via ZIP or container images
- Teacher dashboard on Amplify (static) or ECS (containerized)
- S3 buckets and DynamoDB tables provisioned via IaC


## AWS Infrastructure Components

### DynamoDB Table Structure

**studaxis-student-sync**
```json
{
  "user_id": "student_12345",           // Partition Key
  "current_streak": 7,                  // Number
  "last_sync_timestamp": "2024-01-15T14:30:00Z",  // ISO 8601
  "sync_status": "synced",              // "synced" | "pending" | "error"
  "device_id": "laptop_abc123",         // Optional
  "last_payload_key": "chat_logs/student_12345/session_xyz.jsonl",
  "total_sessions": 42,
  "last_quiz_score": 85
}
```

### S3 Bucket Structure

**studaxis-payloads**
```
studaxis-payloads/
├── quizzes/
│   └── {quiz_id}.json              // Bedrock-generated quizzes
├── textbooks/
│   └── {textbook_id}.pdf           // Teacher-uploaded content
├── chat_logs/
│   └── {user_id}/
│       └── {session_id}.jsonl      // Gzipped, JSONL format
└── summaries/                       // Phase 2: For Amazon Q
    └── {user_id}_summary.txt       // Lambda-generated NL summaries
```

### API Gateway Endpoints

**POST /generate-quiz**
```json
// Request
{
  "textbook_id": "physics_grade10",
  "topic": "Newton's Laws of Motion",
  "difficulty": "easy" | "medium" | "hard",
  "num_questions": 5  // 1-20
}

// Response (Success)
{
  "quiz_id": "quiz_a1b2c3d4",
  "s3_key": "quizzes/quiz_a1b2c3d4.json",
  "s3_url": "https://studaxis-payloads.s3.amazonaws.com/...",
  "expires_at": "2024-01-15T15:30:00Z"
}

// Response (Error)
{
  "error": "ValidationError",
  "message": "num_questions must be between 1 and 20"
}
```

### Lambda Function Structure

**aws-infra/lambda/bedrock_content_gen.py**
```python
# Environment Variables
BEDROCK_MODEL_ID = "amazon.neo-lite-v2"
S3_BUCKET_NAME = "studaxis-payloads"
DYNAMODB_TABLE_NAME = "studaxis-student-sync"
LOG_LEVEL = "INFO"

# IAM Permissions Required
# - bedrock:InvokeModel
# - s3:PutObject
# - logs:CreateLogGroup, logs:CreateLogStream, logs:PutLogEvents
# - dynamodb:PutItem (optional)

# Function Logic (10 steps)
# 1. Validate request payload
# 2. Retrieve textbook context from S3
# 3. Construct Bedrock prompt
# 4. Invoke Bedrock (streaming disabled)
# 5. Parse and validate quiz JSON
# 6. Generate unique quiz_id (UUID v4)
# 7. Store to S3
# 8. Generate pre-signed URL (1-hour expiry)
# 9. Return response
# 10. Log with correlation ID
```

### ECS Task Definition (Option B)

```yaml
Family: teacher-dashboard
NetworkMode: awsvpc
RequiresCompatibilities: [FARGATE]
Cpu: 512
Memory: 1024

ContainerDefinitions:
  - Name: streamlit-dashboard
    Image: {account}.dkr.ecr.{region}.amazonaws.com/teacher-dashboard:latest
    PortMappings:
      - ContainerPort: 8501
        Protocol: tcp
    Environment:
      - Name: DYNAMODB_TABLE
        Value: studaxis-student-sync
      - Name: S3_BUCKET
        Value: studaxis-payloads
    LogConfiguration:
      LogDriver: awslogs
      Options:
        awslogs-group: /ecs/teacher-dashboard
        awslogs-region: us-east-1
        awslogs-stream-prefix: ecs

TaskRoleArn: arn:aws:iam::{account}:role/ECSTaskRole
ExecutionRoleArn: arn:aws:iam::{account}:role/ECSExecutionRole
```

## Correctness Properties (Testing)

### Property-Based Testing
- Framework: Hypothesis (Python), fast-check (TypeScript)
- Minimum iterations: 100 per property test
- Timeout: 60 seconds per test
- Shrinking: Enabled

### Tagging Convention
```python
# Feature: aws-infrastructure-elevation, Property 1: DynamoDB Schema Validation
@given(st.text(), st.integers(min_value=0), st.datetimes())
def test_dynamodb_schema_validation(user_id, streak, timestamp):
    record = create_sync_record(user_id, streak, timestamp)
    assert validate_dynamodb_schema(record)
```

### Key Properties to Test
1. DynamoDB Schema Validation (user_id PK, correct types)
2. Sync Atomicity with Retry (S3 success → DynamoDB retry)
3. Metadata Query Performance (<100ms)
4. HTTPS Endpoint Enforcement
5. Dashboard Response Time (<2s)
6. Quiz Generation End-to-End (<30s)
7. Quiz Generation Error Handling (500 on Bedrock failure)
8. API Gateway Authentication (403 without IAM)
9. Data Separation by Size (<4KB → DynamoDB, >4KB → S3)
10. Metadata-Only Query Optimization (no S3 calls)
11. Payload Access via Reference (S3 key from DynamoDB)
12. Quiz Lambda Logging (correlation IDs)
13. Bedrock Prompt Context Inclusion
14. Quiz Response Format Validation
15. Offline Learning Continuity
16. S3 Object Key Uniqueness (UUID v4)
17. Cloud Content Generation Connectivity Requirement

## Error Handling Patterns

### DynamoDB Errors
- **Throttling**: Exponential backoff (100ms, 200ms, 400ms, 800ms, 1600ms), max 5 retries
- **Item Not Found**: Return empty state (streak=0, last_sync=null)
- **Validation Error**: Reject immediately, log as ERROR

### S3 Errors
- **Access Denied (403)**: No retry, log as CRITICAL
- **Object Not Found (404)**: Return error, log as WARNING
- **Timeout**: Single retry with exponential backoff, return 504 if fails

### Bedrock Errors
- **Throttling**: Return 429 with Retry-After header
- **Validation Error**: Return 400 with details
- **Model Error**: Return 500, log full response
- **Content Filtering**: Return 400 with policy violation message

### Sync Service Errors
- **Network Loss**: Queue locally, retry every 5 minutes
- **Partial Failure**: Mark sync_status="pending", retry DynamoDB on next cycle
- **Corrupted Payload**: Skip, log ERROR, continue with next item
