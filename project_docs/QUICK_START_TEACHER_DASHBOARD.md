# Quick Start: Teacher Dashboard Integration

## Overview

This guide will help you set up the complete teacher dashboard with class management, quiz generation, assignments, and student analytics in under 30 minutes.

## Prerequisites

- AWS Account with Bedrock access
- AWS CLI configured (`aws configure`)
- Node.js 18+ and npm
- Python 3.11+
- (Optional) AWS SAM CLI for Lambda deployment

## Step 1: Deploy AWS Infrastructure (10 min)

```bash
cd aws-infra
chmod +x deploy_teacher_dashboard.sh
./deploy_teacher_dashboard.sh
```

This script will:
- ✅ Create DynamoDB tables (classes, assignments, student-sync)
- ✅ Deploy Lambda functions (class_manager, quiz_generation, assignment_manager, offline_sync)
- ✅ Set up API Gateway endpoints
- ✅ Build teacher dashboard React app

## Step 2: Configure AppSync (5 min)

### Create AppSync API

1. Go to AWS AppSync Console
2. Create new API → "Build from scratch"
3. Name: `studaxis-graphql-api`
4. Copy the schema from `aws-infra/appsync/schema.graphql`
5. Create API key (Settings → API Keys → Create)
6. Note the GraphQL endpoint URL

### Configure Resolvers

For `listStudentProgresses`:
- Data source: Lambda → `content_distribution`
- Request mapping: Use `aws-infra/appsync/resolver-listStudentProgresses.js`

For `recordQuizAttempt`:
- Data source: Lambda → `offline_sync`
- Direct Lambda invocation

## Step 3: Update Environment Variables (3 min)

### Teacher Dashboard

Edit `aws-infra/teacher-dashboard-web/.env`:

```bash
VITE_API_GATEWAY_URL=https://xyz123.execute-api.ap-south-1.amazonaws.com/prod
VITE_APPSYNC_ENDPOINT=https://abc456.appsync-api.ap-south-1.amazonaws.com/graphql
VITE_APPSYNC_API_KEY=da2-xxxxxxxxxxxxxxxxxx
VITE_TEACHER_BACKEND_URL=http://localhost:6782
```

### Student Backend

Edit `backend/.env`:

```bash
STUDAXIS_BASE_PATH=./backend
AWS_REGION=ap-south-1
APPSYNC_ENDPOINT=https://abc456.appsync-api.ap-south-1.amazonaws.com/graphql
APPSYNC_API_KEY=da2-xxxxxxxxxxxxxxxxxx
API_GATEWAY_URL=https://xyz123.execute-api.ap-south-1.amazonaws.com/prod
OLLAMA_BASE_URL=http://localhost:11434
```

## Step 4: Start Student Backend (2 min)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 6782
```

Verify: http://localhost:6782/api/health

## Step 5: Start Teacher Dashboard (2 min)

```bash
cd aws-infra/teacher-dashboard-web
npm install
npm run dev
```

Access: http://localhost:5173

## Step 6: Test the Integration (8 min)

### 6.1 Teacher Creates Class

1. Open teacher dashboard: http://localhost:5173
2. Go to "Classes" page
3. Click "Create Class"
4. Enter: "Physics Grade 10"
5. Note the class code (e.g., "ABC123")

### 6.2 Teacher Generates Quiz

1. Go to "Quiz Generator" page
2. Enter topic: "Newton's Laws of Motion"
3. Select difficulty: "Medium"
4. Number of questions: 5
5. Click "Generate Quiz"
6. Wait ~20s for Bedrock to generate

### 6.3 Teacher Assigns Quiz

1. Go to "Assignments" page
2. Click "Create Assignment"
3. Select content type: "Quiz"
4. Enter title: "Newton's Laws Quiz"
5. Set due date (optional)
6. Click "Create"

### 6.4 Student Joins Class

1. Open student app (React frontend or Streamlit)
2. Go to Settings
3. Enter class code: "ABC123"
4. Click "Join Class"
5. Profile updated with `class_code` and `teacher_linked: true`

### 6.5 Student Syncs and Sees Assignment

1. Click "Sync" button in student app
2. Backend calls: `GET /api/student/assignments?class_code=ABC123`
3. Assignment appears in notifications
4. Student can now take the quiz

### 6.6 Student Completes Quiz

1. Student opens quiz from assignments
2. Answers questions (graded locally by Ollama)
3. Submits quiz
4. Score calculated and saved locally
5. Assignment marked complete
6. Queued for cloud sync

### 6.7 Progress Syncs to Cloud

1. When online, background sync triggers
2. AppSync mutation `recordQuizAttempt` called
3. DynamoDB updated with score and metadata
4. Teacher can now see progress

### 6.8 Teacher Views Analytics

1. Go to "Analytics" page in teacher dashboard
2. Select class: "Physics Grade 10"
3. View student progress:
   - Current streaks
   - Quiz scores
   - Assignment completion
   - Last sync timestamp

## Verification Checklist

- [ ] Teacher can create classes
- [ ] Teacher can generate quizzes via Bedrock
- [ ] Teacher can assign content to classes
- [ ] Student can join class with code
- [ ] Student receives assignment notifications
- [ ] Student can complete assignments offline
- [ ] Progress syncs to cloud when online
- [ ] Teacher can view student analytics

## Common Issues

### Quiz generation fails

**Error**: "Bedrock model not found"

**Solution**: 
1. Check Bedrock model ID in Lambda environment variables
2. Verify region supports `amazon.nova-2-lite-v1:0`
3. Request model access in Bedrock console

### Student not receiving assignments

**Error**: Assignments list is empty

**Solution**:
1. Verify `class_code` in student profile matches teacher's class
2. Check API Gateway URL in student backend .env
3. Ensure assignment status is "active" in DynamoDB
4. Check browser console for API errors

### Teacher can't see student progress

**Error**: "No students found"

**Solution**:
1. Verify AppSync endpoint and API key in teacher dashboard .env
2. Ensure student has synced at least once (online)
3. Check DynamoDB `studaxis-student-sync` table for records
4. Verify `class_code` filter in GraphQL query

### Sync fails

**Error**: "Network error" or "Unauthorized"

**Solution**:
1. Check AppSync API key is valid
2. Verify CORS settings in API Gateway
3. Check CloudWatch logs for Lambda errors
4. Ensure DynamoDB tables exist and have correct permissions

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Teacher Dashboard                         │
│                    (React + Vite)                            │
│  http://localhost:5173                                       │
└────────────┬────────────────────────────────────────────────┘
             │
             ├─── API Gateway (REST) ───┐
             │   /classes                │
             │   /generateQuiz           │
             │   /assignments            │
             │                           │
             ├─── AppSync (GraphQL) ────┤
             │   listStudentProgresses   │
             │   recordQuizAttempt       │
             │                           v
             │                  ┌──────────────────────┐
             │                  │   Lambda Functions   │
             │                  │  - class_manager     │
             │                  │  - quiz_generation   │
             │                  │  - assignment_mgr    │
             │                  │  - offline_sync      │
             │                  └──────────┬───────────┘
             │                             │
             │                             v
             │                  ┌──────────────────────┐
             │                  │   DynamoDB Tables    │
             │                  │  - classes           │
             │                  │  - assignments       │
             │                  │  - student-sync      │
             │                  └──────────────────────┘
             │
             v
┌────────────────────────────────────────────────────────────┐
│              Student Backend (FastAPI)                      │
│              http://localhost:6782                          │
│  - Fetches assignments                                      │
│  - Syncs progress                                           │
│  - Manages notifications                                    │
└────────────┬───────────────────────────────────────────────┘
             │
             v
┌────────────────────────────────────────────────────────────┐
│              Student Frontend (React)                       │
│  - 100% offline learning                                    │
│  - Local AI (Ollama)                                        │
│  - Sync when online                                         │
└────────────────────────────────────────────────────────────┘
```

## Next Steps

1. **Deploy to Production**:
   - Deploy teacher dashboard to AWS Amplify
   - Set up custom domain
   - Enable HTTPS

2. **Add More Features**:
   - Real-time notifications via AppSync subscriptions
   - Bulk assignment creation
   - Student performance reports
   - Export analytics to CSV

3. **Optimize**:
   - Add DynamoDB GSI for faster queries
   - Enable CloudFront CDN
   - Set up CloudWatch alarms

4. **Scale**:
   - Add Cognito for multi-teacher authentication
   - Implement rate limiting
   - Set up backup and disaster recovery

## Support

- Documentation: `project_docs/TEACHER_DASHBOARD_INTEGRATION.md`
- Architecture: `project_docs/ARCHITECTURE.md`
- API Reference: `project_docs/API_REFERENCE.md`

## Cost Estimate

For 100 students, 10 teachers:

- DynamoDB: ~$1/month (on-demand)
- Lambda: ~$2/month (1M requests)
- API Gateway: ~$3.50/month (1M requests)
- AppSync: ~$4/month (1M queries)
- Bedrock: ~$5/month (500 quiz generations)
- **Total: ~$15.50/month** ($0.155/student/month)

## Success Metrics

After deployment, track:

- ✅ Teacher adoption: 60%+ use dashboard actively
- ✅ Assignment completion: 70%+ students complete on time
- ✅ Sync success rate: 95%+ syncs succeed
- ✅ Quiz generation time: <30s (p95)
- ✅ Dashboard load time: <2s (p95)

---

**Ready to launch!** 🚀

For questions or issues, check the troubleshooting section or review the full integration guide.
