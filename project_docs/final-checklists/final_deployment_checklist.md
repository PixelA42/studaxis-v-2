# Final Deployment Checklist

**Project:** Studaxis  
**Purpose:** Consolidated pre-release validation for safe production deployment  
**Use:** Final gate before go-live; run each section in order

---

## 1. Pre-Deployment Checklist

- [ ] All code changes merged and tagged (e.g. v1.0.0)
- [ ] Backend `.env` configured; no dev defaults in production
- [ ] Frontend build succeeds: `cd frontend && npm run build`
- [ ] Teacher dashboard web build succeeds: `cd aws-infra/teacher-dashboard-web && npm run build`
- [ ] SAM build succeeds: `cd aws-infra/lambda && sam build -t sam-template.yaml`
- [ ] Database migrations applied (SQLite schema current; DynamoDB tables exist)
- [ ] Required env vars documented and validated (see other_infrastructure_checklist.md)
- [ ] Deployment runbook updated with production URLs and secrets locations
- [ ] Rollback procedure documented (Lambda versions, DB restore, frontend revert)

---

## 2. Security Verification Checklist

- [ ] `STUDAXIS_JWT_SECRET` is strong random value; not default dev secret
- [ ] SMTP credentials stored securely; not in repo or env files in source control
- [ ] CORS allow_origins restricted to production domain(s); no wildcard for credentialed routes
- [ ] API Gateway uses AWS_IAM or API key; no unauthenticated access to sensitive endpoints
- [ ] DynamoDB tables: No public access; IAM roles use least privilege
- [ ] S3 buckets: Block public access; bucket policy allows only service roles
- [ ] No secrets in frontend build (VITE_* vars checked; no API keys)
- [ ] HTTPS enforced for all production endpoints
- [ ] OTP/verification tokens have expiry; in-memory store acceptable or Redis for multi-instance
- [ ] Password validation enforced (backend auth_routes.py patterns)
- [ ] Class code verification working for teacher-linked students

---

## 3. Infrastructure Readiness Checklist

### AWS Resources

- [ ] DynamoDB: studaxis-student-sync, studaxis-quiz-index, studaxis-content-distribution, studaxis-classes, studaxis-teachers-{env}
- [ ] S3: studaxis-payloads, studaxis-student-stats-2026, studaxis-lambda-artifacts-{env}
- [ ] Lambda: All six functions deployed and invocable
- [ ] API Gateway: studaxis-teacher-api-{env} deployed; stage exists
- [ ] AppSync: Schema created; data sources configured; resolvers point to Lambdas
- [ ] Bedrock: Model access granted (Nova); region ap-south-1
- [ ] S3 trigger: offline_sync Lambda subscribed to studaxis-payloads/sync/*.json

### Backend Hosting

- [ ] FastAPI backend deployed (EC2/ECS/App Runner or equivalent)
- [ ] Port 6782 (or configured port) reachable from frontend origin
- [ ] Health check: GET /api/health returns 200
- [ ] Ollama/ChromaDB available if local AI used; else Ollama fallback disabled
- [ ] SQLite DB path writable; data directory has correct permissions

### Frontend Hosting

- [ ] Student app (frontend/dist) deployed to S3+CloudFront or static host
- [ ] Teacher dashboard web deployed; VITE_TEACHER_BACKEND_URL points to production API
- [ ] PWA manifest and service worker work offline for cached routes
- [ ] STUDAXIS_VERIFY_BASE_URL matches production frontend URL for email links

---

## 4. Application Readiness Checklist

- [ ] Auth flow: Signup, login, OTP, email verification end-to-end
- [ ] Teacher auth: classCode login returns JWT; dashboard loads
- [ ] Sync: Student stats sync to DynamoDB (AppSync or S3 trigger)
- [ ] Quiz generation: API Gateway /generateQuiz returns valid quiz JSON
- [ ] Notes generation: /generateNotes and /teacher/generateNotes work
- [ ] Content distribution: fetchOfflineContent returns manifest with presigned URLs
- [ ] Flashcards, quiz take, chat, textbooks: Core flows functional
- [ ] Rate limiting: Sync respects MIN_SYNC_INTERVAL; no rapid-fire syncs
- [ ] Error handling: 401 triggers logout; 5xx surfaced to user appropriately
- [ ] Class code verification: Students can join class; teacher sees progress

---

## 5. Performance and Scaling Checklist

- [ ] Lambda cold start acceptable (< 3s for sync/content; < 5s for Bedrock)
- [ ] API Gateway throttling configured: 10 req/sec, burst 20
- [ ] DynamoDB: PAY_PER_REQUEST or provisioned sufficient for expected load
- [ ] S3 presigned URL expiry (3600s) appropriate for offline caching
- [ ] Frontend: Chunk splitting (react-vendor, router, recharts) reduces initial load
- [ ] Backend: No N+1 queries; session handling correct for concurrent users
- [ ] Bedrock: Handle 429 throttling with retry; timeout 30s sufficient
- [ ] Connection pooling: boto3 clients reused across Lambda invocations (current pattern)

---

## 6. Monitoring and Logging Checklist

- [ ] CloudWatch Log Groups: All Lambdas; retention 14 days
- [ ] CloudWatch Alarms: Lambda errors, API Gateway 5xx
- [ ] API Gateway: TracingEnabled true; access logs if needed
- [ ] Backend: Logs shipped to CloudWatch or centralized logging
- [ ] Correlation IDs: Present in Lambda logs for traceability
- [ ] Dashboard: CloudWatch dashboard for key metrics
- [ ] Alerting: SNS topic for alarms; on-call notified
- [ ] No PII in logs (emails hashed or redacted)

---

## 7. Disaster Recovery Checklist

- [ ] DynamoDB: PITR enabled on studaxis-student-sync, studaxis-quiz-index, studaxis-content-distribution
- [ ] S3: Versioning on studaxis-payloads
- [ ] SQLite: Backup strategy (daily copy or EBS snapshot)
- [ ] Lambda: Previous versions retained for rollback
- [ ] Documentation: Restore procedure for each component
- [ ] RTO/RPO targets defined and tested
- [ ] Cross-region: Optional replication for critical data

---

## 8. Final Go-Live Checklist

- [ ] Pre-deployment and security checklists completed
- [ ] Infrastructure and application checklists completed
- [ ] Staging environment tested with production-like config
- [ ] DNS/domain: Production URLs resolve correctly
- [ ] SSL/TLS: Certificates valid; no mixed content warnings
- [ ] Smoke test: Signup, login, create quiz, sync, view dashboard
- [ ] Rollback plan confirmed and rehearsed
- [ ] Team notified of go-live; support ready
- [ ] Post-launch: Monitor errors, latency, and user feedback for 24–48 hours
- [ ] Document any post-go-live issues and remediation

---

## Quick Reference: Key Endpoints and Resources

| Component | Endpoint/Resource |
|-----------|-------------------|
| Student frontend | Production URL (e.g. https://app.studaxis.com) |
| Backend API | https://api.studaxis.com or EC2/ECS URL:6782 |
| Teacher API Gateway | https://{api-id}.execute-api.ap-south-1.amazonaws.com/{env} |
| Teacher dashboard web | https://dashboard.studaxis.com or S3/CloudFront URL |
| AppSync GraphQL | https://{api-id}.appsync-api.ap-south-1.amazonaws.com/graphql |
| Health check | GET /api/health |

---

## Sign-Off

- [ ] Technical lead approval
- [ ] Security review complete
- [ ] Operations team ready for monitoring
- [ ] Go-live date/time confirmed
