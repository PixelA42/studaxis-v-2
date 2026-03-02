# Technology Stack

## Core Technologies

### Edge AI (Brain 2)
- **Runtime**: Ollama (local LLM server)
- **Model**: Llama 3.2 3B with adaptive quantization
  - Q4_K_M on 8GB+ RAM (best quality)
  - Q3_K_S on 6-8GB RAM (balanced)
  - Q2_K on 4-6GB RAM (~1.1GB, optimized for low RAM)
- **Context Window**: 4096 tokens (truncate older history automatically)
- **Inference Target**: <10s on i3 CPU, 4GB RAM

### Vector Store & RAG
- **Database**: ChromaDB (persistent, Python-native)
- **Embedding Model**: all-MiniLM-L6-v2 (22M params, ~80MB)
  - CPU-only, offline-capable, ChromaDB default
  - Alternative rejected: nomic-embed-text (~274MB, larger footprint)
- **RAG Config**: Top-K=3, chunk size=500 chars, overlap=50 chars
- **Capacity**: ≥10 textbooks (~3000 pages) within 500MB

### Frontend
- **Framework**: Streamlit (Python-based, rapid prototyping)
- **Styling**: Custom CSS for light/dark themes (default: light)
- **UI Pattern**: Bento grid layout, glassmorphic design (time permitting)
- **Navigation**: Sidebar with Dashboard, Chat, Quiz, Flashcards, Panic Mode, Settings

### Local Storage
- **Format**: JSON files (zero dependencies, human-readable)
- **Backup**: Automatic timestamped backups (keep last 7)
- **Files**: 
  - `data/user_stats.json` - progress, streaks, preferences
  - `data/chromadb/` - vector embeddings
  - `data/backups/` - user stats backups

## AWS Cloud Services (Brain 1)

### Content Generation
- **Amazon Bedrock**: Curriculum Engine (quiz generation, Micro-Learning Units)
  - Model: amazon.neo-lite-v2
  - Region: us-east-1
  - Use: Strategic content creation, not real-time tutoring

### Data Layer
- **DynamoDB**: Sync metadata storage (MVP)
  - Table: studaxis-student-sync
  - Partition Key: user_id
  - Attributes: current_streak, last_sync_timestamp, sync_status, device_id, last_payload_key, total_sessions, last_quiz_score
  - Capacity: On-Demand (pay-per-request)
  - Performance: <100ms reads, <50ms writes
- **S3**: Heavy payload storage
  - Buckets: studaxis-student-stats, studaxis-content, studaxis-payloads
  - Structure: quizzes/, textbooks/, chat_logs/{user_id}/
  - Encryption: SSE-S3 (AES-256)
  - Versioning: Enabled for quiz and textbook content
  - CORS: Enabled for dashboard pre-signed URL access
  - Lifecycle: Transition chat logs to Glacier after 90 days

### API & Compute
- **API Gateway**: REST endpoint for quiz generation
  - Authorization: IAM (AWS_IAM)
  - Throttling: 10 req/sec per teacher, burst 20
  - Timeout: 30 seconds
- **Lambda**: Serverless functions
  - Runtime: Python 3.11, arm64 (Graviton2)
  - Memory: 512 MB
  - Functions: Quiz generation, sync resolvers
  - Permissions: Bedrock, S3, DynamoDB, CloudWatch

### Sync Layer
- **AWS AppSync**: GraphQL delta sync (MVP)
  - Conflict Resolution: Timestamp-based (most recent write wins)
  - Payload Target: <5KB delta, <50KB upper bound
  - Retry: Exponential backoff, queue locally when offline
  - Mutations: Grade updates, streak increments queued offline
  - Field Selection: GraphQL queries fetch only needed fields

### Hosting Options
- **Option A (Amplify)**: Static hosting for React-wrapped Streamlit
  - CloudFront CDN, IAM-authenticated API calls
  - Lowest operational overhead
- **Option B (ECS/EC2)**: Containerized Streamlit deployment
  - ECS Fargate (serverless) or EC2 (t3.small/micro)
  - Application Load Balancer with HTTPS
  - Required for native Streamlit Python runtime

### Monitoring
- **CloudWatch**: Logs, metrics, alarms
  - Lambda execution logs with correlation IDs
  - DynamoDB read/write latency
  - API Gateway throttling metrics

## Phase 2 Additions (Planned)

- **Amazon Q Business**: Teacher Copilot for natural language analytics
  - Indexes S3 Data Lake (Lambda-generated text summaries)
  - Teachers ask: "Which students are failing Algebra?"
  - Access via qbusiness boto3 API from Teacher Dashboard
  - Pricing: $3/user/month (Lite tier), ~$30/month for 10 teachers
  - Data Pipeline: S3 upload → Lambda converts JSON → text summary → Q indexes
  - Native S3 connector, no database required
- **Lambda Translator**: JSON → text summaries for Q indexing
  - Converts `{"math_score": 8}` → "Student 101 has a Math Score of 8"
  - Triggered on S3 upload, saves to `/summaries/` folder
- **DynamoDB + Cognito**: Multi-tenancy for institutional deployments
- **Hinglish-Optimized Models**: Airavata (IIT-Madras), OpenHathi (Sarvam AI)
- **Advanced Conflict Resolution**: Versioning, custom merge logic
- **Real-time Alerts**: Persistent WebSocket connections via AppSync

## Python Dependencies

```
# Core
streamlit==1.31.0
chromadb==0.4.22
sentence-transformers==2.3.1
ollama==0.1.6

# Data Processing
pandas==2.1.4
numpy==1.26.3
PyPDF2==3.0.1
pdfplumber==0.10.3

# AWS Integration
boto3==1.34.34
awscli==1.32.34

# System Monitoring
psutil==5.9.8

# Utilities
python-dotenv==1.0.1
requests==2.31.0
```

## Common Commands

### Development

```bash
# Activate virtual environment
studaxis-vtwo-env\Scripts\activate  # Windows
source studaxis-vtwo-env/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Pull Ollama model
ollama pull llama3:3b

# Verify Ollama
ollama list

# Run hardware validation
python local-app/hardware_validator.py

# Test Ollama client
python local-app/utils/ollama_client.py

# Test local storage
python local-app/utils/local_storage.py

# Launch Streamlit app
streamlit run local-app/streamlit_app.py

# Launch on different port
streamlit run local-app/streamlit_app.py --server.port 8502
```

### AWS Operations

```bash
# Configure AWS CLI
aws configure

# Create S3 buckets
aws s3 mb s3://studaxis-student-stats --region ap-south-1
aws s3 mb s3://studaxis-content --region ap-south-1

# List S3 contents
aws s3 ls s3://studaxis-student-stats/

# Upload to S3
aws s3 cp file.json s3://studaxis-student-stats/

# Enable S3 versioning
aws s3api put-bucket-versioning \
  --bucket studaxis-student-stats \
  --versioning-configuration Status=Enabled

# List Lambda functions
aws lambda list-functions

# Invoke Lambda
aws lambda invoke --function-name studaxis-sync output.json
```

### Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_quiz_engine.py

# Run with coverage
pytest --cov=local-app tests/

# Property-based tests (Hypothesis)
pytest tests/ -k "property"
```

## Architecture Patterns

### Offline-First Design
- Cloud AI creates curriculum intelligence
- Edge AI delivers it without connectivity checks
- Learning sessions never blocked by network status
- Cloud is content creator and analytics engine, not real-time participant

### Data Separation
- Metadata (<4KB) → DynamoDB (fast queries)
- Heavy payloads (>4KB) → S3 (cost-efficient storage)
- DynamoDB stores S3 reference keys for payload access

### Atomic Sync Strategy
1. Upload payload to S3 first (idempotent)
2. Update DynamoDB with S3 reference
3. If DynamoDB fails, mark sync_status="pending" and retry
4. Use deterministic S3 keys to prevent duplicates

### Error Handling
- Exponential backoff with jitter for retries
- Queue mutations locally during offline periods
- Graceful degradation (show warnings, continue operation)
- Comprehensive CloudWatch logging with correlation IDs

## Performance Targets

- **DynamoDB**: <100ms read latency (p99)
- **Dashboard**: <2s page load (p95)
- **Quiz Generation**: <30s end-to-end (p95)
- **Local Inference**: <10s on minimum hardware (p95)
- **S3 Upload**: <5s for 10MB payload (p95)
- **UI Interactions**: <200ms response time

## Security

- **Encryption**: SSE-S3 for S3, AWS-managed keys for DynamoDB
- **Authentication**: IAM for API Gateway, HTTPS enforcement
- **Privacy**: All student data stored locally, cloud sync uses derived/anonymized metadata
- **Access Control**: Least-privilege IAM roles for Lambda/ECS
- **Pre-signed URLs**: 1-hour expiry for S3 access


## AWS Infrastructure Elevation (MVP)

### DynamoDB State Store
- **Table**: studaxis-student-sync
- **Schema**: user_id (PK), current_streak (Number), last_sync_timestamp (String), sync_status (String), device_id (String), last_payload_key (String), total_sessions (Number), last_quiz_score (Number)
- **Purpose**: Fast metadata queries (<100ms) without processing S3 payloads
- **Capacity**: On-Demand (pay-per-request)
- **Encryption**: AWS-managed keys
- **Point-in-Time Recovery**: Enabled

### API Gateway + Lambda Quiz Generation
- **Endpoint**: POST /generate-quiz
- **Authorization**: IAM (AWS_IAM)
- **Throttling**: 10 req/sec per teacher, burst 20, quota 1000/day
- **Lambda**: Python 3.11, arm64 (Graviton2), 512 MB, 30s timeout
- **Workflow**:
  1. Validate request (textbook_id, topic, difficulty, num_questions)
  2. Retrieve textbook context from S3
  3. Construct Bedrock prompt with pedagogical instructions
  4. Invoke Bedrock (streaming disabled)
  5. Parse and validate quiz JSON
  6. Generate unique quiz_id (UUID v4)
  7. Store to S3 at `quizzes/{quiz_id}.json`
  8. Generate pre-signed URL (1-hour expiry)
  9. Return quiz_id, s3_key, s3_url
  10. Log all steps to CloudWatch with correlation ID

### Teacher Dashboard Hosting Options

**Option A: AWS Amplify Gen 2**
- For React-wrapped Streamlit or static builds
- CloudFront CDN, IAM-authenticated API calls
- Lowest operational overhead and cost
- Static asset serving

**Option B: ECS Fargate / EC2**
- For native Streamlit Python runtime
- ECS Fargate (serverless) or EC2 (t3.small/micro)
- Application Load Balancer with HTTPS
- IAM roles for DynamoDB and S3 access
- Health check: `/healthz` endpoint
- Container port: 8501

### Data Separation Strategy
- Metadata (<4KB) → DynamoDB (fast queries)
- Heavy payloads (>4KB) → S3 (cost-efficient storage)
- DynamoDB stores S3 reference keys for payload access
- Teacher Dashboard queries DynamoDB without S3 calls
- Payload access via S3 reference when needed

## Bedrock as Curriculum Engine

**Role**: Brain 1 (Strategic Cloud) - creates intelligence, not real-time tutoring

**What Bedrock Does (MVP)**:
- Quiz generation from topic/chapter input
- Content decomposition (textbooks → Micro-Learning Units)
- Flashcard authoring (Q&A pairs from syllabus)
- Analytics summarization (aggregated student data → NL reports)

**What Bedrock Does NOT Do**:
- Student chat or tutoring (that's Edge AI)
- Real-time grading during learning sessions
- Live learning interactions

**Why Bedrock**:
- Managed foundation models (no infrastructure)
- Scalable content pipeline (one teacher → thousands of students)
- Cost efficient (generate once, consume many times)
- Curriculum alignment (domain-specific, exam-pattern-aligned)

**Policy**: Bedrock SHALL NOT be used for student chat, tutoring, grading, or learning-time interactions. It powers content creation and analytics (strategy), not real-time learning (tactics).

## Kiro IDE Integration

Kiro enables spec-driven infrastructure deployment, ensuring consistent and reproducible AWS resource provisioning. Use Kiro for:
- Architecture iteration and code scaffolding
- Prompt engineering for Bedrock integration
- Debugging and documentation drafting
- All AI-generated outputs require human review and validation
