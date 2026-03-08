# Studaxis — Student & Teacher Integration Checklist

> This pulls together items from `INTEGRATION_CHECKLIST.md`, `AWS_INTEGRATION_CHECKLIST.md`, `PROJECT_COMPLETION_CHECKLIST.md`, and the codebase.

---

## 1. Student Integration

| # | Check | Component | Current / Target |
|---|-------|------------|------------------|
| □ | Signup → OTP → Onboarding | `auth_routes.py` + `OnboardingFlow.tsx` | OTP printed to console; `postVerifyOtp` → navigate to `/onboarding` |
| □ | Student role selection | `OnboardingFlow` step `role` | Student vs Teacher; student → profile step |
| □ | Profile: name, mode, class code | `OnboardingFlow` step `profile` | Solo vs Teacher-linked; class code (4+ chars) for linked |
| □ | Class code validation | `OnboardingFlow` | Must be 4+ chars when `profile_mode === "teacher_linked_provisional"` |
| □ | Profile persisted | `postCompleteOnboarding` | `POST /api/auth/complete-onboarding` → `profile.json` |
| □ | Profile scoped by user | `backend/main.py` | `_load_user_stats(user_id)`, `data/users/{user_id}/user_stats.json` |
| □ | Auth-protect profile API | `GET/POST /api/user/profile` | Use `Depends(get_current_user)`; scope by JWT `user_id` |

---

## 2. Quiz Endpoints

| # | Check | Endpoint | Notes |
|---|-------|----------|-------|
| □ | Get quiz content | `GET /api/quiz/{id}` | Stub for default, quick, panic; extend for S3/Bedrock content |
| □ | Submit quiz answers | `POST /api/quiz/{id}/submit` | Grades answers, updates user_stats, enqueues sync (main.py:1281) |
| □ | Panic mode generate (textbook) | `POST /api/quiz/panic/generate/textbook` | RAG + Ollama from textbook |
| □ | Panic mode generate (weblink) | `POST /api/quiz/panic/generate/weblink` | Fetch URL + RAG |
| □ | Panic mode generate (files) | `POST /api/quiz/panic/generate/files` | FormData upload |
| □ | Panic grade-one | `POST /api/quiz/panic/grade-one` | Per-question AI grading |
| □ | Panic finalize | `POST /api/quiz/panic/finalize` | Persist scores, update stats, enqueue sync |
| □ | Quiz submit → sync queue | `_enqueue_panic_quiz_for_sync` | `SyncManager.enqueue_quiz_sync()` when `sync_enabled` |
| □ | Wire to real quiz storage | `main.py` | Replace stub `QUIZ_ITEMS` with S3/Bedrock content when available |

---

## 3. User Stats

| # | Check | Endpoint / Path | Notes |
|---|-------|-----------------|-------|
| □ | Load user stats | `GET /api/user/stats` | Auth-protected; `_load_user_stats(user_id)` |
| □ | Update user stats | `PUT /api/user/stats` | Merges with existing; preferences, theme, streak |
| □ | Per-user path | `data/users/{user_id}/user_stats.json` | Backend uses per-user paths |
| □ | Dashboard reads stats | `getUserStats()` in `api.ts` | Streak, quiz stats, flashcard stats |
| □ | Settings persist via stats | `PUT /api/user/stats` | Theme, sync_enabled, difficulty |

---

## 4. S3 & Sync

| # | Check | Component | Notes |
|---|-------|-----------|-------|
| □ | S3 buckets exist | AWS | `studaxis-payloads`, `studaxis-student-stats`, `studaxis-content` |
| □ | SyncManager → AppSync | `sync_manager.py` | `APPSYNC_ENDPOINT`, `APPSYNC_API_KEY` |
| □ | Full payload → S3 | Backend | Upload `{user_id}_stats.json` to `s3://studaxis-payloads/sync/` on sync |
| □ | S3 trigger → Lambda | `offline_sync/handler.py` | S3 event in `sync/` → `_write_student_aggregate_stats` |
| □ | S3 payload format | Lambda expects | `student_id`, `device_id`, `quiz_attempts`, `total_score`, `streak`, `last_sync` |
| □ | SyncManager S3 upload | Backend | Add S3 upload step in `try_sync()` for full payload backup |
| □ | Quiz content in S3 | Teacher dashboard | `content_uploader.py` → `studaxis-payloads/quizzes/` |
| □ | Presigned URLs | ContentDistribution Lambda | For student app to fetch quiz JSON from S3 |

---

## 5. Class Code (Teacher ↔ Student)

| # | Check | Component | Notes |
|---|-------|-----------|-------|
| □ | Profile stores `class_code` | `UserProfile` / `profile.json` | `class_code` persisted on complete onboarding |
| □ | Onboarding: linked mode | `OnboardingFlow` step `profile` | Mode "Join a Class" → class code input |
| □ | Teacher creates class code | Teacher Dashboard | Classes page: generate/share class code |
| □ | Student joins via class code | Student onboarding | Enter 4+ char code; stored in profile |
| □ | Teacher filters by class | Teacher Dashboard / DynamoDB | Filter students by `class_code` |
| □ | Backend: class_code in profile API | `main.py` | `GET /api/user/profile` returns `class_code` |
| □ | AppSync/DynamoDB: class_code | Schema | Add `class_code` to sync metadata if needed for teacher queries |

---

## 6. Student Dashboard Integration

| # | Check | Component | Notes |
|---|-------|-----------|-------|
| □ | Dashboard loads real data | `DashboardPage` | `getUserStats()` → streak, quiz avg, flashcards mastered |
| □ | Redirect if no profile | `ProtectedRoute` / Dashboard | Redirect to `/onboarding` if `!profile.profile_name` |
| □ | Streak display | Dashboard | From `user_stats.streak` |
| □ | Quiz stats | Dashboard | From `user_stats.quiz_stats` |
| □ | Flashcards due | Dashboard | `GET /api/dashboard/flashcards` or `/api/flashcards/due` |
| □ | Sync bar/status | Dashboard | `GET /api/sync/status`; show pending/online |

---

## 7. Teacher Dashboard Integration

| # | Check | Component | Notes |
|---|-------|-----------|-------|
| □ | Teacher onboarding redirect | `OnboardingFlow` step `done` | `user_role === "teacher"` → Open Teacher Dashboard, then `handleComplete()` |
| □ | `VITE_TEACHER_DASHBOARD_URL` | Env | Default `https://teacher.studaxis.com`; Amplify URL in prod |
| □ | Teacher dashboard routes | `aws-infra/teacher-dashboard-web` | DashboardOverview, Classes, Students, Analytics, Settings |
| □ | Students page: real data | `Students.tsx` | Replace `PLACEHOLDER_STUDENTS` with DynamoDB/AppSync |
| □ | Query by class_code | Backend / DynamoDB | `listStudentProgresses` with filter on `class_code` |
| □ | CloudSyncStatus | `CloudSyncStatus.tsx` | Connect to real sync status API |
| □ | Manual sync | `ManualSyncButton` | `POST /api/sync` or teacher backend |
| □ | Quiz content: S3 + DynamoDB | `content_uploader.py` | Publish quiz → S3 + DynamoDB index |
| □ | Quiz generation: Bedrock | `quiz_generation/handler.py` | API Gateway → Lambda → Bedrock → S3 |

---

## 8. End-to-End Flows to Verify

| # | Flow | Steps |
|---|------|-------|
| □ | Student signup → dashboard | Signup → OTP → verify → onboarding (role=student) → profile (class code optional) → setup → done → dashboard |
| □ | Teacher signup → dashboard | Signup → OTP → verify → onboarding (role=teacher) → done → Teacher Dashboard opens |
| □ | Student quiz → sync | Take quiz → submit → `POST /api/quiz/{id}/submit` → `_save_user_stats` → `enqueue_quiz_sync` → `try_sync` → AppSync |
| □ | Teacher sees student data | Student syncs → Lambda → DynamoDB → Teacher Dashboard queries `listStudentProgresses` |
| □ | Student streak → sync | Streak update → `enqueue_streak_sync` → `try_sync` → AppSync `updateStreak` |
| □ | S3 full-payload fallback | Backend uploads `{user_id}_stats.json` to S3 → Lambda S3 trigger → DynamoDB aggregate |

---

## 9. Environment Variables (Student Backend)

| Variable | Purpose |
|----------|---------|
| `APPSYNC_ENDPOINT` | GraphQL endpoint for sync |
| `APPSYNC_API_KEY` | API key for AppSync |
| `VITE_API_PORT` | Backend port for Vite proxy |
| `VITE_TEACHER_DASHBOARD_URL` | Teacher dashboard URL |
| `STUDAXIS_JWT_SECRET` | JWT signing |

---

## 10. Key File References

| Area | Files |
|------|-------|
| Student onboarding | `frontend/src/pages/OnboardingFlow.tsx` |
| Student dashboard | `frontend/src/pages/Dashboard.tsx` |
| Quiz API | `backend/main.py` (quiz endpoints), `frontend/src/services/api.ts` (postQuizSubmit) |
| User stats | `backend/main.py` (`_load_user_stats`, `_save_user_stats`) |
| Sync | `backend/sync_manager.py`, `aws-infra/lambda/offline_sync/handler.py` |
| Teacher dashboard | `aws-infra/teacher-dashboard-web/`, `aws-infra/teacher-dashboard/app.py` |
| S3/Content | `aws-infra/teacher-dashboard/utils/content_uploader.py`, `aws-infra/lambda/content_distribution/` |
| AppSync schema | `aws-infra/appsync/schema.graphql` |

---

## Suggested Integration Order

1. **Student & user stats** — Ensure per-user paths and auth-protected profile/stats APIs.

2. **Quiz → sync** — Confirm `POST /api/quiz/{id}/submit` updates stats and enqueues sync; `SyncManager.try_sync()` is wired to AppSync.

3. **S3 full-payload upload** — Add S3 upload in SyncManager for `{user_id}_stats.json`; configure S3 trigger on Lambda.

4. **Class code flow** — Teacher Dashboard creates classes; students enter class code in onboarding.

5. **Teacher dashboard data** — Replace placeholders with DynamoDB/AppSync queries; filter by `class_code` where needed.
