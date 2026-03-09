# Other Infrastructure Checklist

**Project:** Studaxis  
**Scope:** Non-AWS infrastructure, application configuration, and operational requirements derived from codebase analysis

---

## 1. Environment Configuration

### 1.1 Backend Environment Variables

- [ ] Create `backend/.env` from `.env.example`; never commit real values
- [ ] Required for production:
  - `STUDAXIS_JWT_SECRET` - Strong random secret (min 32 chars); change from default `studaxis-dev-secret-change-in-prod`
  - `STUDAXIS_SMTP_HOST`, `STUDAXIS_SMTP_PORT`, `STUDAXIS_SMTP_USER`, `STUDAXIS_SMTP_PASS` - For OTP and verification emails
  - `STUDAXIS_VERIFY_BASE_URL` - Production frontend URL (e.g. https://app.studaxis.com)
  - `STUDAXIS_BASE_PATH` - Backend data directory (default: backend dir)
  - `STUDAXIS_PORT` - API port (default: 6782)
- [ ] Optional (cloud sync): `AWS_REGION`, `APPSYNC_ENDPOINT`, `APPSYNC_API_KEY`, `S3_BUCKET_NAME`, `S3_BUCKET_STUDENT`, `S3_BUCKET_CONTENT`
- [ ] Optional (local AI): `OLLAMA_HOST`, `OLLAMA_BASE_URL`, `STUDAXIS_OLLAMA_MODEL`, `CHROMA_DB_PATH`, `EMBEDDING_MODEL`
- [ ] Optional: `OPENAI_API_KEY`, `DATABASE_URL` (if migrating from SQLite)
- [ ] Load order: `backend/.env` loaded by main.py via python-dotenv

### 1.2 Frontend (Student App) Environment Variables

- [ ] `VITE_API_PORT` - Backend port for dev proxy (default: 6782)
- [ ] `VITE_API_GATEWAY_URL` - API Gateway URL when using AWS (not local backend)
- [ ] Build-time only; no runtime secrets in frontend

### 1.3 Teacher Dashboard Web Environment Variables

- [ ] `VITE_TEACHER_BACKEND_URL` - FastAPI backend URL (e.g. http://localhost:6782 or https://api.studaxis.com)
- [ ] `VITE_API_GATEWAY_URL` - Teacher API Gateway base URL (quiz/notes generation)
- [ ] `VITE_APPSYNC_ENDPOINT`, `VITE_APPSYNC_API_KEY` - AppSync for sync status
- [ ] `VITE_SHOW_TEACHER_NOTES` - Optional feature flag
- [ ] Source: `aws-infra/teacher-dashboard-web/.env.example`

### 1.4 Teacher Dashboard (Streamlit) Environment Variables

- [ ] `STUDENT_STATS_BUCKET` - S3 bucket (default: studaxis-student-stats-2026)
- [ ] `SYNC_TABLE_NAME` - DynamoDB table (default: studaxis-student-sync)
- [ ] `QUIZ_INDEX_TABLE` - DynamoDB table (default: studaxis-quiz-index)
- [ ] `APPSYNC_ENDPOINT`, `APPSYNC_API_KEY` - AppSync config
- [ ] `S3_PAYLOADS_BUCKET`, `S3_REGION` - S3 config
- [ ] `TEACHER_API_ENDPOINT` - API Gateway URL
- [ ] `USE_API_GATEWAY` - true/false
- [ ] `BEDROCK_REGION` - Bedrock region (ap-south-1)

---

## 2. API Keys

- [ ] `OPENAI_API_KEY` - Listed in .env.example; verify if used (ai_integration_layer may support OpenAI)
- [ ] `APPSYNC_API_KEY` - For AppSync HTTP data source; store securely
- [ ] Never hardcode API keys in source; load from env or secrets manager
- [ ] Rotate keys periodically; document rotation procedure

---

## 3. SMTP/Email Providers

### 3.1 Current Implementation

- [ ] Uses smtplib (stdlib); supports Gmail with App Password
- [ ] Files: `backend/email_service.py`
- [ ] Functions: `send_otp_email()`, `send_verification_email()`, `send_email()`
- [ ] TLS on port 587; STARTTLS required
- [ ] Gmail: Enable 2-Step Verification; create App Password for Studaxis
- [ ] Alternate env names: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS (backward compat)

### 3.2 Production Recommendations

- [ ] Consider SendGrid, Mailgun, or AWS SES for deliverability
- [ ] Configure SPF/DKIM for custom domain
- [ ] Set up bounce/complaint handling
- [ ] Monitor email delivery rates

---

## 4. Authentication Security

### 4.1 Student Auth (JWT)

- [ ] JWT algorithm: HS256; secret from `STUDAXIS_JWT_SECRET`
- [ ] Token expiry: 7 days (JWT_EXPIRY_HOURS = 168)
- [ ] Password: bcrypt via passlib; never store plaintext
- [ ] OTP: In-memory store (`_otp_store`); 5-minute expiry; not persisted
- [ ] Email verification: Token in link; 24-hour expiry
- [ ] Validation: Username 3-20 chars (alphanumeric, underscore); password pattern (min 8, upper, lower, digit, special)
- [ ] Production: Use strong JWT secret; consider Redis for OTP if multi-instance

### 4.2 Teacher Auth

- [ ] Lambda `teacher_auth`: Login by classCode; lookup in DynamoDB studaxis-teachers
- [ ] Returns JWT for teacher dashboard
- [ ] Backend route: `POST /api/teacher/auth` with classCode
- [ ] Seed test teacher: `python scripts/seed_teacher.py --backend http://localhost:6782`

### 4.3 Class Code Verification

- [ ] `class_verify.py` - Verifies class code via backend or Lambda
- [ ] ClassVerifyUnavailableError handled in auth flow

---

## 5. Logging Systems

### 5.1 Backend Logging

- [ ] Python logging; format: `%(asctime)s [%(name)s] %(levelname)s: %(message)s`
- [ ] Key loggers: studaxis.main, studaxis.sync_orchestrator, studaxis.content_distribution
- [ ] Set LOG_LEVEL via env (DEBUG, INFO, WARNING, ERROR)
- [ ] Ensure no sensitive data (passwords, tokens) in logs
- [ ] Add request ID/correlation ID for tracing

### 5.2 Lambda Logging

- [ ] LOG_LEVEL env in Lambda (CloudFormation: LogLevel parameter)
- [ ] Structured logging with correlation ID (`_correlation_id()`)
- [ ] CloudWatch Logs automatically captures print/logger output

### 5.3 Frontend Logging

- [ ] Console for dev; consider remote logging (Sentry, LogRocket) for production errors
- [ ] PWA/service worker errors may need separate handling

---

## 6. Dependency Management

### 6.1 Backend (Python)

- [ ] No root requirements.txt; dependencies in backend imports
- [ ] Key packages: FastAPI, SQLAlchemy, PyJWT, passlib[bcrypt], python-dotenv, pydantic, boto3, uvicorn
- [ ] Create `backend/requirements.txt` with pinned versions for reproducible builds
- [ ] Run: `pip install -r backend/requirements.txt` (or equivalent)
- [ ] ChromaDB, sentence-transformers for RAG; Ollama for local AI

### 6.2 Frontend (Node)

- [ ] `frontend/package.json` - React 18, Vite, TypeScript, react-router-dom
- [ ] PWA: vite-plugin-pwa
- [ ] Charts: recharts
- [ ] Run: `npm install` in frontend/
- [ ] Lock file: package-lock.json; commit for reproducible builds

### 6.3 Teacher Dashboard Web

- [ ] `aws-infra/teacher-dashboard-web/package.json` - Separate React app
- [ ] Run: `npm install` in teacher-dashboard-web/

### 6.4 Teacher Dashboard (Streamlit)

- [ ] streamlit, boto3, pandas, plotly, requests, python-dotenv
- [ ] Optional: streamlit_autorefresh
- [ ] Create requirements.txt for Streamlit app

---

## 7. Containerization

- [ ] No Dockerfile in repo; backend and Lambdas run without containers
- [ ] If containerizing backend:
  - Base: python:3.11-slim
  - Install: uvicorn, backend deps
  - Expose: 6782
  - CMD: uvicorn backend.main:app --host 0.0.0.0 --port 6782
- [ ] Lambda: SAM/CloudFormation handles packaging; no custom Docker for Lambda in current setup
- [ ] ChromaDB/Ollama: Consider separate containers if bundling local AI

---

## 8. Build Processes

### 8.1 Backend

- [ ] No compiled build; run with `uvicorn backend.main:app --host 0.0.0.0 --port 6782`
- [ ] Or: `python main.py` from repo root (mounts SPA, runs uvicorn)
- [ ] Ensure PYTHONPATH includes backend/ when running from root

### 8.2 Frontend (Student)

- [ ] Build: `npm run build` (Vite) or `tsc -b && vite build`
- [ ] Output: `frontend/dist/`
- [ ] Backend serves `dist/` at / when present
- [ ] PWA: workbox precaches assets; excludes /api/

### 8.3 Teacher Dashboard Web

- [ ] Build: `npm run build` in teacher-dashboard-web/
- [ ] Output: dist/ for static hosting
- [ ] Deploy to S3, Amplify, or similar

### 8.4 Lambda

- [ ] Build: `sam build -t sam-template.yaml` from aws-infra/lambda/
- [ ] Deploy: `sam deploy` or deploy-lambdas.ps1
- [ ] Packaging: Each function zipped; upload to S3 or direct Lambda update

---

## 9. Rate Limiting

### 9.1 Backend

- [ ] Sync orchestrator: MIN_SYNC_INTERVAL = 10 seconds between syncs per device
- [ ] Implemented in `backend/sync_orchestrator.py`; returns "Rate limited - wait Xs"
- [ ] No global API rate limiter in FastAPI; consider slowapi or custom middleware for production

### 9.2 API Gateway

- [ ] Teacher API: ThrottlingRateLimit: 10, ThrottlingBurstLimit: 20 (CloudFormation)
- [ ] Protects Bedrock and Lambda from abuse
- [ ] Consider per-API-key quotas for teacher dashboard

### 9.3 Auth Routes

- [ ] OTP: Document recommends rate limiting (see docs/AUTH_EMAIL_OTP.md)
- [ ] Add rate limit on /request-otp, /login to prevent brute force
- [ ] Consider captcha or cooldown for repeated failed logins

---

## 10. Caching Layers

- [ ] No Redis/Memcached in current architecture
- [ ] OTP store: In-memory dict; lost on restart; not shared across instances
- [ ] Frontend: PWA caches static assets; navigateFallbackDenylist for /api/
- [ ] S3 presigned URLs: 1-hour expiry (PRESIGNED_URL_EXPIRY_SECONDS)
- [ ] Consider: API response caching for /api/textbooks, /api/quiz/history if read-heavy
- [ ] CloudFront: Cache static frontend; do not cache /api/

---

## 11. Background Workers

- [ ] No Celery/RQ; sync is request-driven ( SyncManager, SyncOrchestrator)
- [ ] Debouncing: 5s window before syncing (DEBOUNCE_WINDOW)
- [ ] Async: BackgroundTasks used in auth (e.g. send email)
- [ ] Lambda S3 trigger: Async processing of uploaded sync payloads
- [ ] For batch jobs (e.g. nightly stats): Consider Lambda scheduled trigger or Step Functions

---

## 12. Database Migrations

### 12.1 SQLite (backend/data/users.db)

- [ ] Schema: users table (id, email, username, hashed_password, is_verified, created_at)
- [ ] Migration in database.py: ALTER TABLE add is_verified if missing
- [ ] No Alembic/migration framework; manual schema updates
- [ ] For production: Adopt migration tool before RDS migration

### 12.2 DynamoDB

- [ ] No formal migrations; tables created by CloudFormation/SAM or provision scripts
- [ ] GSI changes require table recreate or separate migration
- [ ] Document schema for studaxis-student-sync (user_id PK; record_type for filtering)

---

## 13. Backup Strategies

### 13.1 SQLite

- [ ] Backup `backend/data/users.db` before upgrades
- [ ] Consider daily copy to S3 or EBS snapshot if on EC2
- [ ] user_stats.json, profile.json, flashcards.json: Per-user files in data/users/{user_id}/

### 13.2 DynamoDB

- [ ] Enable Point-in-Time Recovery (PITR) on critical tables
- [ ] CloudFormation enables PITR for studaxis-quiz-index
- [ ] Add PITR for studaxis-student-sync, studaxis-content-distribution
- [ ] On-demand backups for major releases

### 13.3 S3

- [ ] Enable versioning on studaxis-payloads
- [ ] Lifecycle rules: Move old sync/ files to Glacier after 90 days if cost-sensitive
- [ ] Cross-region replication for disaster recovery (optional)

### 13.4 ChromaDB

- [ ] Backup `backend/data/chromadb/` directory
- [ ] Recreate from textbooks if loss acceptable for RAG

---

## 14. Additional Operational Requirements

### 14.1 CORS

- [ ] Backend allows: localhost:5173, 127.0.0.1:5173, 3000, 8000, 6782, 6783
- [ ] Production: Add production domain(s) to allow_origins; avoid wildcard for credentialed requests
- [ ] Lambda/API Gateway: CORS headers set (Access-Control-Allow-Origin: * for OPTIONS; restrict for POST if needed)

### 14.2 Health Checks

- [ ] Backend: GET /api/health
- [ ] Ollama: GET /api/ollama/ping
- [ ] Use for ALB/load balancer health checks and readiness probes

### 14.3 Offline-First Behavior

- [ ] PWA: Service worker caches assets; offline navigation works for static routes
- [ ] API: 25s timeout (API_TIMEOUT_MS); graceful degradation when backend unreachable
- [ ] Sync: Queue when offline; retry with exponential backoff when online
- [ ] Store token in localStorage; survives refresh; cleared on 401

### 14.4 Seed Data

- [ ] Teachers: `python scripts/seed_teacher.py --backend http://localhost:6782`
- [ ] Sample textbooks: backend/data/sample_textbooks/
- [ ] Document seed steps for fresh deployments
