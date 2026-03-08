# Studaxis — AWS Integration Checklist

> **Purpose:** Migration steps from local/offline storage to AWS services.  
> **Reference:** `.kiro/specs/aws-infrastructure-elevation/`, `aws-infra/`, `backend/sync_manager.py`

---

## 1. Backend → AWS (Data & Auth)

### 1.1 Profile Storage

| # | Check | Current | Target | Notes |
|---|-------|---------|--------|-------|
| □ | Swap `profile.json` → DynamoDB | `backend/profile_store.py` reads/writes `data/profile.json` | DynamoDB table (e.g. `studaxis-profiles`) with `user_id` PK | `load_profile()`, `save_profile()` need boto3; profile scoped by JWT `user_id` |
| □ | Profile schema in DynamoDB | Single JSON file | `user_id` (PK), `profile_name`, `profile_mode`, `class_code`, `user_role`, `onboarding_complete` | Match `UserProfile` dataclass |
| □ | Backend profile API uses DynamoDB | `GET/POST /api/user/profile` call `load_profile()` | Resolve `user_id` from JWT; query/put DynamoDB | Auth-protected; `get_current_user` required |

### 1.2 User Auth (SQLite → Cloud)

| # | Check | Current | Target | Notes |
|---|-------|---------|--------|-------|
| □ | Swap `users.db` (SQLite) → DynamoDB/Cognito | `backend/database.py` uses `data/users.db` | Option A: DynamoDB `studaxis-users`; Option B: Amazon Cognito | Cognito: managed auth, MFA, password reset |
| □ | User table schema | `User` model: id, email, username, hashed_password, is_verified | DynamoDB: `user_id` PK, or Cognito User Pool | Migrate existing users if needed |
| □ | JWT validation | Local secret `STUDAXIS_JWT_SECRET` | Cognito JWT validation or keep custom JWT with KMS | Cognito issues JWTs; custom JWT can use KMS for signing |

### 1.3 OTP & Email

| # | Check | Current | Target | Notes |
|---|-------|---------|--------|-------|
| □ | Swap console OTP → SES real email | `auth_routes.py` `_send_otp_email()` prints to console | Amazon SES: `boto3.client('ses').send_email()` | Verify SES domain/email; use `_send_otp_email` for OTP body |
| □ | Verification email via SES | `email_service.py` uses SMTP (localhost) | SES for verification links | `send_verification_email()` → SES |
| □ | SES env vars | `STUDAXIS_SMTP_*` | `AWS_REGION`, `SES_FROM_EMAIL`, IAM role | No SMTP credentials; IAM for Lambda/ECS |

### 1.4 User Stats & Progress

| # | Check | Current | Target | Notes |
|---|-------|---------|--------|-------|
| □ | Add S3 sync for progress data | `user_stats.json` local only | Upload to S3 `studaxis-payloads/sync/{user_id}_stats.json` on sync | Lambda `offline_sync` already handles S3 trigger → DynamoDB |
| □ | Sync payload format | `SyncManager` sends AppSync mutations | S3 payload: `student_id`, `device_id`, `quiz_attempts`, `total_score`, `streak`, `last_sync` | Match `_write_student_aggregate_stats` in Lambda |
| □ | Delta sync (<5KB) | `SyncManager.try_sync()` → AppSync GraphQL | Keep AppSync for mutations; S3 for full payload backup | Per `.kiro/steering/tech.md` |

### 1.5 Flashcards & Content

| # | Check | Current | Target | Notes |
|---|-------|---------|--------|-------|
| □ | Flashcards sync to S3 | `flashcards.json` local only | Optional: `studaxis-payloads/flashcards/{user_id}.json` | For cross-device; lower priority |
| □ | Textbook PDFs | `data/sample_textbooks/` local | Optional: S3 `studaxis-content/textbooks/` | Phase 2; teacher uploads |

---

## 2. Backend → AWS (Sync & API)

### 2.1 Sync Manager → AppSync

| # | Check | Current | Target | Notes |
|---|-------|---------|--------|-------|
| □ | AppSync endpoint configured | `APPSYNC_ENDPOINT`, `APPSYNC_API_KEY` env | Deploy AppSync API; wire env in ECS/Lambda | `sync_manager.py` already uses these |
| □ | Sync mutations reach Lambda | `recordQuizAttempt`, `updateStreak` | Lambda `offline_sync` resolves to DynamoDB | Schema in `aws-infra/appsync/schema.graphql` |
| □ | S3 trigger for full payload | Manual or SyncManager upload | Upload to `s3://studaxis-payloads/sync/` → Lambda S3 trigger | Lambda `_is_s3_event` handles it |

### 2.2 Backend Deployment

| # | Check | Current | Target | Notes |
|---|-------|---------|--------|-------|
| □ | Deploy FastAPI → EC2/ECS | `python run.py` on localhost:6782 | ECS Fargate or EC2 (t3.small) | Containerize with Docker; serve SPA + API |
| □ | Dockerfile for FastAPI | None | `FROM python:3.11`; install deps; `uvicorn main:app` | Include `frontend/dist` for SPA |
| □ | ECS task IAM role | N/A | DynamoDB, S3, SES, Secrets Manager | Least privilege |
| □ | Load balancer / HTTPS | N/A | ALB + ACM certificate | Terminate TLS |
| □ | Environment variables | `.env` local | ECS task def or Secrets Manager | `STUDAXIS_JWT_SECRET`, `DYNAMODB_TABLE`, etc. |

---

## 3. Frontend → AWS

### 3.1 React SPA Hosting

| # | Check | Current | Target | Notes |
|---|-------|---------|--------|-------|
| □ | Deploy React build → S3 + CloudFront | `frontend/dist` served by FastAPI | S3 bucket + CloudFront distribution | Static hosting; cache at edge |
| □ | API base URL | `API_BASE = ""` (same origin) | `VITE_API_URL` for production API | Point to ALB/API Gateway |
| □ | CORS on backend | Localhost origins | Add CloudFront/ALB origin | Production domain |

### 3.2 Frontend Config for Production

| # | Check | Current | Target | Notes |
|---|-------|---------|--------|-------|
| □ | `VITE_API_URL` | Not set (proxy in dev) | `https://api.studaxis.com` or ALB URL | Build-time env for API calls |
| □ | `VITE_TEACHER_DASHBOARD_URL` | `https://teacher.studaxis.com` | Amplify URL when deployed | Onboarding teacher link |

### 3.3 Teacher Dashboard (AWS Amplify)

| # | Check | Current | Target | Notes |
|---|-------|---------|--------|-------|
| □ | Teacher dashboard → Amplify | `aws-infra/teacher-dashboard-web` | Amplify Hosting (static) | `amplify.yml` build config |
| □ | Teacher dashboard → DynamoDB | Mock/placeholder | Connect to `studaxis-student-sync`, `studaxis-quiz-index` | Use Amplify Data/API or direct boto3 |
| □ | Teacher dashboard → S3 | Placeholder | Presigned URLs for quiz content | `ContentDistribution` Lambda pattern |
| □ | Teacher dashboard → Bedrock | Streamlit `bedrock_client` | React calls API Gateway → Lambda → Bedrock | Quiz generation API |

---

## 4. AWS Infrastructure (Provisioning)

### 4.1 Core Resources

| # | Check | Service | Notes |
|---|-------|---------|-------|
| □ | DynamoDB: `studaxis-student-sync` | Sync metadata, quiz attempts | PK: `user_id`; Lambda `offline_sync` writes |
| □ | DynamoDB: `studaxis-quiz-index` | Quiz metadata | Content distribution Lambda |
| □ | DynamoDB: `studaxis-profiles` (new) | User profiles | If migrating from profile.json |
| □ | DynamoDB: `studaxis-users` (optional) | Auth users | If not using Cognito |
| □ | S3: `studaxis-payloads` | Sync payloads, quiz JSON | S3 trigger → Lambda |
| □ | S3: `studaxis-content` (optional) | Textbooks, MLUs | Phase 2 |
| □ | S3: Student app static (new) | React `dist` | CloudFront origin |

### 4.2 Lambda Functions

| # | Check | Function | Notes |
|---|-------|----------|-------|
| □ | `studaxis-offline-sync` | AppSync + S3 trigger | `aws-infra/lambda/offline_sync/handler.py` |
| □ | `studaxis-content-distribution` | Fetch content, presigned URLs | `aws-infra/lambda/content_distribution/` |
| □ | `studaxis-quiz-generation` | Bedrock quiz gen | `aws-infra/lambda/quiz_generation/` |

### 4.3 AppSync & API Gateway

| # | Check | Resource | Notes |
|---|-------|----------|-------|
| □ | AppSync API | GraphQL schema | `aws-infra/appsync/schema.graphql` |
| □ | API Gateway (Teacher) | REST for quiz gen | `sam-template.yaml` TeacherApi |
| □ | API Gateway (Student API) | Optional: front FastAPI | Or ALB directly to ECS |

### 4.4 SES & Cognito

| # | Check | Resource | Notes |
|---|-------|----------|-------|
| □ | SES verified identity | Email or domain | Production OTP/verification |
| □ | Cognito User Pool (optional) | If replacing custom auth | User signup, MFA, password reset |

---

## 5. Migration Order (Suggested)

1. **Phase 1 — Sync & Progress**
   - □ Wire `SyncManager` to real AppSync (env vars)
   - □ Deploy Lambda + DynamoDB + S3
   - □ Verify S3 upload → Lambda → DynamoDB

2. **Phase 2 — Email**
   - □ Swap OTP → SES
   - □ Swap verification email → SES

3. **Phase 3 — Profile**
   - □ Create DynamoDB profiles table
   - □ Implement `profile_store` DynamoDB backend
   - □ Scope profile by `user_id` (multi-user)

4. **Phase 4 — Auth (Optional)**
   - □ Evaluate Cognito vs DynamoDB users
   - □ Migrate users if needed

5. **Phase 5 — Deployment**
   - □ Dockerize FastAPI + SPA
   - □ Deploy to ECS/EC2
   - □ Deploy React to S3 + CloudFront
   - □ Deploy Teacher Dashboard to Amplify

---

## 6. Environment Variables (Production)

| Variable | Purpose | Example |
|----------|---------|---------|
| `APPSYNC_ENDPOINT` | GraphQL endpoint | `https://xxx.appsync-api.region.amazonaws.com/graphql` |
| `APPSYNC_API_KEY` | API key (or IAM) | From AppSync console |
| `DYNAMODB_TABLE_NAME` | Sync table | `studaxis-student-sync` |
| `S3_BUCKET_NAME` | Payloads | `studaxis-payloads` |
| `AWS_REGION` | Region | `ap-south-1` |
| `STUDAXIS_JWT_SECRET` | JWT signing | KMS or Secrets Manager |
| `SES_FROM_EMAIL` | OTP sender | `noreply@studaxis.com` |
| `STUDAXIS_VERIFY_BASE_URL` | Verification link base | `https://app.studaxis.com` |

---

## 7. Related Docs

- **Architecture:** `.kiro/DOCS_NEW/ARCHITECTURE_NEW.md`
- **Tech stack:** `.kiro/steering/tech.md`
- **AWS requirements:** `.kiro/specs/aws-infrastructure-elevation/requirements.md`
- **AWS design:** `.kiro/specs/aws-infrastructure-elevation/design.md`
- **Lambda SAM:** `aws-infra/lambda/sam-template.yaml`
- **AppSync schema:** `aws-infra/appsync/schema.graphql`
- **Teacher dashboard:** `aws-infra/teacher-dashboard-web/README.md`
- **Full integration:** `docs/INTEGRATION_CHECKLIST.md`

---

*Last updated: 2026-03*
