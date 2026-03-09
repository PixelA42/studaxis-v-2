# AWS Integration Checklist

**Project:** Studaxis  
**Architecture:** Offline-first AI tutoring platform with FastAPI backend, React frontend, Lambda functions, DynamoDB, S3, and AppSync  
**Region:** ap-south-1 (primary)

---

## 1. AWS Account Setup

### 1.1 IAM Roles

- [ ] Create Lambda execution roles with least-privilege policies per function
  - `studaxis-offline-sync-role-{env}` - DynamoDB PutItem/UpdateItem on studaxis-student-sync
  - `studaxis-content-2026-dist-role-{env}` - DynamoDB GetItem/Query/Scan, S3 GetObject (presign only)
  - `studaxis-quiz-gen-role-{env}` - bedrock:InvokeModel
  - `studaxis-teacher-auth-{env}-sam` - DynamoDB GetItem on studaxis-teachers
  - `studaxis-class-manager` - DynamoDB PutItem/GetItem/Scan/Query on studaxis-classes
  - `studaxis-teacher-generate-notes` - Bedrock, S3 PutObject/GetObject, DynamoDB PutItem on studaxis-content-distribution
- [ ] Ensure each role has `AWSLambdaBasicExecutionRole` (CloudWatch Logs)
- [ ] Configure assume-role policy: `lambda.amazonaws.com` as principal for all Lambda roles

### 1.2 IAM Policies

- [ ] DynamoDB: Scope policies to specific table ARNs (not `*`)
  - Offline sync: `dynamodb:PutItem`, `dynamodb:UpdateItem` on studaxis-student-sync
  - Content distribution: `dynamodb:GetItem` on studaxis-student-sync; `dynamodb:Scan`, `dynamodb:Query` on studaxis-quiz-index
  - Teacher auth: `dynamodb:GetItem` on studaxis-teachers-{env}
- [ ] S3: Scope to bucket and prefix (e.g. `studaxis-payloads/quizzes/*`, `studaxis-payloads/sync/*`)
  - Content distribution: `s3:GetObject` for presigning (no ListBucket)
  - Teacher generate notes: `s3:PutObject`, `s3:GetObject`, `s3:HeadObject` on studaxis-payloads
- [ ] Bedrock: Restrict to inference profile ARN if possible; avoid `Resource: "*"` in production

### 1.3 Least Privilege Configuration

- [ ] Remove unnecessary S3 ListBucket if only GetObject/PutObject required
- [ ] Use resource-level permissions (table ARN) not account-wide
- [ ] Separate dev/staging/prod roles using `${Environment}` parameter

### 1.4 Access Key Management

- [ ] Avoid long-lived access keys for CI/CD; use OIDC (GitHub Actions) or IAM roles
- [ ] Rotate access keys quarterly if used for deploy scripts
- [ ] Store deploy credentials in AWS Secrets Manager or GitHub Secrets (never in repo)

---

## 2. Compute Layer

### 2.1 Lambda (Primary - Detected Architecture)

- [ ] Deploy Lambda functions per `aws-infra/lambda/sam-template.yaml` or `aws-infra/cloudformation/lambda-functions.yaml`
  - `studaxis-offline-sync-{env}` - AppSync + S3 trigger; Runtime Python 3.11; arm64; 256MB; 10s
  - `studaxis-content-2026-distribution-{env}` - AppSync resolver; Runtime Python 3.11; arm64; 256MB; 15s
  - `studaxis-quiz-generation-{env}` - API Gateway; Runtime Python 3.11; arm64; 512MB; 30s
  - `studaxis-teacher-generate-notes-{env}` - API Gateway; Runtime Python 3.11; 512MB; 60s
  - `studaxis-class-manager-{env}` - API Gateway; 256MB; 15s
  - `studaxis-teacher-auth-{env}` - API Gateway; 256MB; 10s
- [ ] Use arm64 (Graviton2) for cost savings on all Lambdas
- [ ] Configure S3 trigger for offline_sync: prefix `sync/`, suffix `.json` on `studaxis-payloads`
- [ ] Ensure Lambda code is deployed from `studaxis-lambda-artifacts-{env}` S3 bucket (CloudFormation references this)

### 2.2 Backend (FastAPI) Hosting Options

- [ ] **Option A - EC2:** Single instance for dev; use user-data to install Python, run uvicorn
- [ ] **Option B - ECS Fargate:** Containerize backend; run behind ALB
- [ ] **Option C - App Runner:** Simpler alternative to ECS for containerized API
- [ ] **Current:** Backend runs locally (uvicorn) or on any host; no Dockerfile in repo yet
- [ ] If containerizing: Create Dockerfile from `backend/`, expose port 6782, set `STUDAXIS_BASE_PATH`

### 2.3 Teacher Dashboard (Streamlit) Hosting

- [ ] Streamlit app at `aws-infra/teacher-dashboard/app.py` - consider EC2, ECS, or Streamlit Cloud
- [ ] Configure `STUDENT_STATS_BUCKET`, `SYNC_TABLE_NAME`, `QUIZ_INDEX_TABLE`, `APPSYNC_ENDPOINT`, `APPSYNC_API_KEY`, `S3_PAYLOADS_BUCKET`, `TEACHER_API_ENDPOINT`

### 2.4 Teacher Dashboard Web (React)

- [ ] Static build from `aws-infra/teacher-dashboard-web/` deploy to S3 + CloudFront or Amplify Hosting
- [ ] Set `VITE_TEACHER_BACKEND_URL`, `VITE_API_GATEWAY_URL`, `VITE_APPSYNC_ENDPOINT`, `VITE_APPSYNC_API_KEY` at build time

---

## 3. Networking

### 3.1 VPC Design

- [ ] Lambda functions: Default (no VPC) unless DynamoDB/S3 access requires VPC endpoints
- [ ] If FastAPI backend on EC2/ECS: Place in private subnets with NAT for outbound (SMTP, AWS APIs)
- [ ] Create VPC endpoints for DynamoDB and S3 if high throughput to reduce data transfer cost

### 3.2 Subnets

- [ ] Public subnets for ALB, NAT Gateway (if used)
- [ ] Private subnets for backend, database (if migrating SQLite to RDS)

### 3.3 Security Groups

- [ ] Backend (EC2/ECS): Allow ingress 6782 from ALB only; egress to SMTP (587), HTTPS (443), DynamoDB/S3 endpoints
- [ ] ALB: Allow 80/443 from 0.0.0.0/0; forward to backend target group

### 3.4 NAT Gateways

- [ ] One NAT per AZ if backend in private subnet needs outbound internet (email, Ollama fallback)

### 3.5 Load Balancers

- [ ] ALB for FastAPI backend when hosted on EC2/ECS
- [ ] API Gateway is regional; no ALB for Lambda-backed APIs
- [ ] CloudFront in front of S3 (teacher dashboard static) for HTTPS and caching

---

## 4. Storage and Database

### 4.1 DynamoDB

- [ ] Create/provision tables per `aws-infra/scripts/provision-mvp-cli.sh` or CloudFormation
  - `studaxis-student-sync` - PK: user_id; used for sync metadata, quiz attempts; schema must match Lambda expectations (see `offline_sync/handler.py`)
  - `studaxis-quiz-index` - PK: quiz_id; quiz metadata, s3_key
  - `studaxis-content-distribution` - PK: class_id, SK: content_id; notes/assignments per class
  - `studaxis-classes` - PK: class_id; GSI: teacher_id-index, class_code-index
  - `studaxis-teachers-{env}` - PK: classCode (teacher auth)
- [ ] Enable Point-in-Time Recovery on critical tables (QuizIndexDynamoDBTable in CloudFormation)
- [ ] Enable SSE (server-side encryption) on tables
- [ ] Use PAY_PER_REQUEST (on-demand) billing for variable workload

### 4.2 S3

- [ ] Create buckets:
  - `studaxis-payloads` - Quiz JSON, notes, sync payloads; folder structure: `quizzes/`, `notes/{class_id}/`, `sync/`
  - `studaxis-student-stats-2026` - Teacher dashboard student stats (Streamlit)
  - `studaxis-lambda-artifacts-{env}` - Lambda deployment packages (zip)
- [ ] Enable versioning on studaxis-payloads for audit/recovery
- [ ] Configure bucket policy: deny public access; allow Lambda/service roles only
- [ ] Set lifecycle rules if old sync payloads can be archived/deleted

### 4.3 RDS

- [ ] Not used in current architecture; backend uses SQLite (`backend/data/users.db`)
- [ ] For production scale: Plan migration to RDS (PostgreSQL) with SQLAlchemy; update `database.py` DATABASE_URL

### 4.4 EFS

- [ ] Not used; consider for shared ChromaDB/embedding storage if multi-instance backend

---

## 5. Secrets and Environment Management

### 5.1 AWS Secrets Manager

- [ ] Store `STUDAXIS_JWT_SECRET` in Secrets Manager; reference from Lambda/backend
- [ ] Store SMTP credentials (`STUDAXIS_SMTP_USER`, `STUDAXIS_SMTP_PASS`) in Secrets Manager
- [ ] Store AppSync API key if not using IAM auth for AppSync

### 5.2 Parameter Store

- [ ] Store non-sensitive config: `STUDAXIS_VERIFY_BASE_URL`, `LOG_LEVEL`, `PRESIGNED_URL_EXPIRY_SECONDS`
- [ ] Use `/studaxis/{env}/` prefix for parameter hierarchy

### 5.3 Environment Variable Protection

- [ ] Never commit `.env` or real credentials; use `.env.example` as template
- [ ] Backend loads from `backend/.env` via python-dotenv
- [ ] Lambda env vars via CloudFormation/SAM; avoid hardcoding in handler
- [ ] Frontend: Use `VITE_*` prefixed vars only; never expose secrets to client

---

## 6. Email Systems

### 6.1 AWS SES Integration

- [ ] Replace SMTP with SES for production (backend `email_service.py` uses smtplib)
- [ ] Verify sender domain/email in SES
- [ ] Request production access (move out of sandbox) for arbitrary recipients
- [ ] Update `email_service.py` to use boto3 SES client instead of smtplib

### 6.2 SMTP Configuration (Current)

- [ ] Set `STUDAXIS_SMTP_HOST` (e.g. smtp.gmail.com), `STUDAXIS_SMTP_PORT` (587)
- [ ] Set `STUDAXIS_SMTP_USER`, `STUDAXIS_SMTP_PASS` (Gmail: use App Password, not account password)
- [ ] Set `STUDAXIS_SMTP_FROM` (default: SMTP_USER or noreply@studaxis.local)
- [ ] Set `STUDAXIS_VERIFY_BASE_URL` to production frontend URL for verification links
- [ ] Set `STUDAXIS_SMTP_TIMEOUT` (default 15) if needed
- [ ] Strip spaces from SMTP_PASS (Gmail app passwords may copy with spaces)
- [ ] Test: OTP and verification emails must reach user inbox

### 6.3 Domain Verification

- [ ] Add SPF, DKIM records for sending domain if using custom domain
- [ ] Verify domain in SES before production send

---

## 7. Logging and Monitoring

### 7.1 CloudWatch Logs

- [ ] Lambda log groups created by CloudFormation/SAM (e.g. `/aws/lambda/studaxis-offline-sync-dev`)
- [ ] Set retention: 14 days (CloudFormation); 7 days (SAM template)
- [ ] Ensure log groups exist for all Lambdas: offline_sync, content_distribution, quiz_generation, teacher_generate_notes, class_manager, teacher_auth
- [ ] Backend: Add structured JSON logging; ship to CloudWatch Logs via agent or API

### 7.2 Metrics

- [ ] Enable API Gateway metrics: Count, Latency, 4XXError, 5XXError
- [ ] Lambda: Invocations, Duration, Errors, Throttles (built-in)
- [ ] DynamoDB: ConsumedReadCapacity, ConsumedWriteCapacity (if provisioned)
- [ ] Create CloudWatch dashboard for Teacher API and sync Lambdas

### 7.3 Alarms

- [ ] Lambda: Error rate > 5% over 5 min
- [ ] API Gateway: 5XX > 10 in 5 min
- [ ] DynamoDB: Throttled requests (if provisioned mode)
- [ ] SNS topic for alarm notifications

### 7.4 Tracing

- [ ] API Gateway stage: `TracingEnabled: true` (CloudFormation)
- [ ] Enable X-Ray for Lambda and API Gateway; integrate with CloudWatch

---

## 8. Security

### 8.1 WAF

- [ ] Attach AWS WAF to API Gateway or CloudFront if public-facing
- [ ] Rate-based rule: Block IPs exceeding threshold
- [ ] Geo-blocking if applicable

### 8.2 Shield

- [ ] Shield Standard enabled by default; consider Shield Advanced for DDoS protection if critical

### 8.3 IAM Best Practices

- [ ] MFA for root and console users
- [ ] Use roles for EC2/ECS task execution; avoid access keys on instances
- [ ] Review IAM Access Analyzer for unintended public access
- [ ] Enable CloudTrail for API activity

### 8.4 Audit Logging

- [ ] Enable CloudTrail for management events (Create, Delete, etc.)
- [ ] Enable data events for S3 (studaxis-payloads) if compliance required
- [ ] Store trail logs in dedicated S3 bucket with lifecycle

---

## 9. CI/CD

### 9.1 CodeBuild

- [ ] Create build project for Lambda: `sam build` then `sam deploy` or zip upload
- [ ] Build spec: Install SAM CLI, Python 3.11; build from `aws-infra/lambda/`
- [ ] Store artifacts in `studaxis-lambda-artifacts-{env}` S3 bucket

### 9.2 CodePipeline

- [ ] Source: GitHub (webhook) or CodeCommit
- [ ] Build: CodeBuild (Lambda + frontend)
- [ ] Deploy: CloudFormation (Lambda stack) or Lambda update-function-code
- [ ] Add manual approval for production stage

### 9.3 GitHub Integration

- [ ] Use GitHub Actions with OIDC to assume AWS role (no long-lived keys)
- [ ] Workflow: Build SAM, deploy to dev on push; deploy to prod on release
- [ ] Alternative: Use `aws-infra/deploy-lambdas.ps1` for manual deploy (PowerShell)

### 9.4 Deployment Automation

- [ ] Script `deploy-lambdas.ps1` updates Lambda code from `sam build` output
- [ ] Run `sam build -t sam-template.yaml` from `aws-infra/lambda/` before deploy
- [ ] Ensure `studaxis-offline-sync-dev`, `studaxis-content-2026-distribution-dev` exist before update
- [ ] AppSync schema: `aws appsync start-schema-creation` for GraphQL API updates

---

## 10. Cost Optimization

### 10.1 Instance Sizing

- [ ] Lambda: 256MB for sync/content-dist; 512MB for Bedrock (quiz/notes); monitor and adjust
- [ ] Backend (if EC2): Start with t3.small; use Cost Explorer to right-size

### 10.2 Auto Scaling

- [ ] Lambda: No scaling config needed (managed)
- [ ] EC2/ECS: Configure target tracking (CPU/memory) for backend
- [ ] DynamoDB: PAY_PER_REQUEST avoids over-provisioning

### 10.3 Usage Monitoring

- [ ] Set Cost Explorer budgets for Studaxis project (tag: Project=Studaxis)
- [ ] Alert when Lambda invocations exceed expected (e.g. 100k/month)
- [ ] Monitor Bedrock token usage (Nova model costs)
- [ ] S3 storage and request costs for studaxis-payloads

---

## Summary: Key AWS Resources

| Resource | Name/Pattern | Purpose |
|----------|--------------|---------|
| DynamoDB | studaxis-student-sync | Sync metadata, quiz attempts |
| DynamoDB | studaxis-quiz-index | Quiz metadata, s3_key |
| DynamoDB | studaxis-content-distribution | Notes per class |
| DynamoDB | studaxis-classes | Class management |
| DynamoDB | studaxis-teachers-{env} | Teacher auth by classCode |
| S3 | studaxis-payloads | Quiz JSON, notes, sync payloads |
| S3 | studaxis-student-stats-2026 | Teacher dashboard stats |
| S3 | studaxis-lambda-artifacts-{env} | Lambda deployment artifacts |
| Lambda | studaxis-offline-sync | AppSync + S3 trigger |
| Lambda | studaxis-content-2026-distribution | AppSync resolver |
| Lambda | studaxis-quiz-generation | API Gateway + Bedrock |
| Lambda | studaxis-teacher-generate-notes | API Gateway + Bedrock + S3 |
| Lambda | studaxis-class-manager | API Gateway + DynamoDB |
| Lambda | studaxis-teacher-auth | API Gateway + DynamoDB |
| API Gateway | studaxis-teacher-api-{env} | Teacher REST API |
| AppSync | (configured separately) | GraphQL for sync |
| Bedrock | global.amazon.nova-2-lite-v1:0 | Quiz/notes generation |
