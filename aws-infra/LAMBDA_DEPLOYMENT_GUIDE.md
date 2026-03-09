# Lambda Deployment Guide

## Quick Start

Deploy all missing Lambda functions with one command:

### Option 1: Git Bash (Recommended)
```bash
cd aws-infra
./deploy-lambdas.sh
```

### Option 2: PowerShell
```powershell
cd aws-infra
.\deploy-lambdas.ps1
```

## What Gets Deployed

The script will:

1. **Create deployment packages** (ZIP files) for:
   - `teacher_auth` → Teacher authentication Lambda
   - `class_manager` → Class management Lambda
   - `teacher_generate_notes` → Notes generation Lambda

2. **Deploy/Update Lambda functions**:
   - `studaxis-teacher-auth-dev` (NEW)
   - `studaxis-class-manager-dev` (NEW)
   - `studaxis-teacher-generate-notes-dev` (NEW)
   - `studaxis-content-distribution-dev` (UPDATE existing)

3. **Create IAM role** (if needed):
   - `studaxis-teacher-generate-notes-role-dev` with Bedrock, S3, and DynamoDB permissions

4. **Verify deployment** by checking all Lambda functions are active

## Prerequisites

- AWS CLI configured with credentials
- Region: `ap-south-1`
- Account: `718980965213`
- Existing IAM roles:
  - `studaxis-teacher-auth-dev-sam` ✓
  - `studaxis-class-manager-role-dev` ✓

## Manual Steps After Deployment

### 1. Connect Lambda to API Gateway

Go to AWS Console → API Gateway → `studaxis-teacher-api-dev` (ID: `yjyn9jsugc`)

Create these integrations:

| Method | Path | Lambda Function |
|--------|------|----------------|
| POST | `/auth` | `studaxis-teacher-auth-dev` |
| POST | `/api/teacher/auth` | `studaxis-teacher-auth-dev` |
| GET | `/classes` | `studaxis-class-manager-dev` |
| POST | `/classes` | `studaxis-class-manager-dev` |
| GET | `/classes/verify` | `studaxis-class-manager-dev` |
| POST | `/teacher/generateNotes` | `studaxis-teacher-generate-notes-dev` |
| POST | `/generateNotes` | `studaxis-teacher-generate-notes-dev` |

**Steps:**
1. Click "Create Resource" for each path
2. Click "Create Method" and select method type
3. Choose "Lambda Function" integration
4. Select the corresponding function
5. Enable "Lambda Proxy Integration"
6. Click "Actions" → "Deploy API" → Stage: `prod`

### 2. Create AppSync API

See `GET_API_KEY.md` for detailed instructions.

Quick steps:
1. Go to AWS AppSync Console
2. Create API → "Build from scratch"
3. Name: `studaxis-graphql-api`
4. Copy schema from `appsync/schema.graphql`
5. Create API key in Settings
6. Configure resolvers:
   - `listStudentProgresses` → `studaxis-content-distribution-dev`
   - `recordQuizAttempt` → `studaxis-offline-sync-dev`
   - `fetchOfflineContent` → `studaxis-content-distribution-dev`

### 3. Update Environment Variables

**Teacher Dashboard Web** (`teacher-dashboard-web/.env`):
```bash
VITE_API_GATEWAY_URL=https://yjyn9jsugc.execute-api.ap-south-1.amazonaws.com/prod
VITE_APPSYNC_ENDPOINT=<your-appsync-endpoint>
VITE_APPSYNC_API_KEY=<your-api-key>
```

**Student Backend** (`backend/.env`):
```bash
AWS_REGION=ap-south-1
APPSYNC_ENDPOINT=<your-appsync-endpoint>
APPSYNC_API_KEY=<your-api-key>
API_GATEWAY_URL=https://yjyn9jsugc.execute-api.ap-south-1.amazonaws.com/prod
```

## Verification

Run the test script to verify all resources:

```powershell
.\test_resources.ps1
```

Expected result: **21/21 tests passing** (100%)

## Troubleshooting

### Lambda creation fails with "Role not found"

Wait 10-15 seconds for IAM role to propagate, then retry:
```bash
./deploy-lambdas.sh
```

### "AccessDeniedException" when creating Lambda

Check your AWS credentials have these permissions:
- `lambda:CreateFunction`
- `lambda:UpdateFunctionCode`
- `iam:CreateRole`
- `iam:AttachRolePolicy`
- `iam:PutRolePolicy`

### ZIP file too large

The script creates minimal packages. If you see size errors:
1. Remove `__pycache__` folders
2. Remove `.pyc` files
3. Don't include virtual environments

### Function exists but update fails

Delete the function and recreate:
```bash
aws lambda delete-function --function-name studaxis-teacher-auth-dev --region ap-south-1
./deploy-lambdas.sh
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Teacher Dashboard                         │
│                    (React + Vite)                            │
└────────────┬────────────────────────────────────────────────┘
             │
             ├─── API Gateway (REST) ───┐
             │   yjyn9jsugc              │
             │                           │
             ├─── AppSync (GraphQL) ────┤
             │   (to be created)         │
             │                           v
             │                  ┌──────────────────────┐
             │                  │   Lambda Functions   │
             │                  │  ✓ offline-sync      │
             │                  │  ✓ quiz-generation   │
             │                  │  ✓ content-dist      │
             │                  │  ✓ class-manager     │
             │                  │  ✓ teacher-auth      │
             │                  │  ✓ generate-notes    │
             │                  └──────────┬───────────┘
             │                             │
             │                             v
             │                  ┌──────────────────────┐
             │                  │   DynamoDB Tables    │
             │                  │  ✓ All 6 tables      │
             │                  └──────────────────────┘
             │                             │
             │                             v
             │                  ┌──────────────────────┐
             │                  │   S3 Buckets         │
             │                  │  ✓ All 3 buckets     │
             │                  └──────────────────────┘
             v
┌────────────────────────────────────────────────────────────┐
│              Student Backend (FastAPI)                      │
│              http://localhost:6782                          │
└────────────────────────────────────────────────────────────┘
```

## Lambda Function Details

### studaxis-teacher-auth-dev
- **Purpose**: Teacher authentication via class code
- **Runtime**: Python 3.11 (arm64)
- **Memory**: 256 MB
- **Timeout**: 10 seconds
- **Environment**:
  - `TEACHERS_TABLE_NAME=studaxis-teachers-dev`
  - `STUDAXIS_JWT_SECRET=studaxis-dev-secret-change-in-prod`
- **IAM Role**: `studaxis-teacher-auth-dev-sam`
- **Permissions**: DynamoDB GetItem on `studaxis-teachers-dev`

### studaxis-class-manager-dev
- **Purpose**: Multi-class management (create, list, verify codes)
- **Runtime**: Python 3.11 (arm64)
- **Memory**: 256 MB
- **Timeout**: 15 seconds
- **Environment**:
  - `CLASSES_TABLE_NAME=studaxis-classes`
- **IAM Role**: `studaxis-class-manager-role-dev`
- **Permissions**: DynamoDB PutItem, GetItem, Query, Scan on `studaxis-classes`

### studaxis-teacher-generate-notes-dev
- **Purpose**: Generate study notes via Bedrock, store in S3
- **Runtime**: Python 3.11 (arm64)
- **Memory**: 512 MB
- **Timeout**: 60 seconds
- **Environment**:
  - `S3_BUCKET_NAME=studaxis-payloads`
  - `CONTENT_DISTRIBUTION_TABLE=studaxis-content-distribution`
  - `BEDROCK_REGION=ap-south-1`
  - `BEDROCK_MODEL_ID=arn:aws:bedrock:ap-south-1:718980965213:inference-profile/global.amazon.nova-2-lite-v1:0`
- **IAM Role**: `studaxis-teacher-generate-notes-role-dev`
- **Permissions**: 
  - Bedrock InvokeModel
  - S3 GetObject, PutObject, HeadObject on `studaxis-payloads/*`
  - DynamoDB PutItem on `studaxis-content-distribution`

### studaxis-content-distribution-dev
- **Purpose**: Fetch offline content (quizzes, notes) for students
- **Runtime**: Python 3.11 (arm64)
- **Memory**: 256 MB
- **Timeout**: 15 seconds
- **Environment**:
  - `DYNAMODB_TABLE_NAME=studaxis-student-sync`
  - `QUIZ_INDEX_TABLE=studaxis-quiz-index`
  - `CONTENT_DISTRIBUTION_TABLE=studaxis-content-distribution`
  - `S3_BUCKET_NAME=studaxis-payloads`
- **IAM Role**: `studaxis-content-2026-dist-role-dev`
- **Permissions**: 
  - DynamoDB GetItem, Query, Scan on multiple tables
  - S3 GetObject on `studaxis-payloads/*` (pre-signing only)

## Cost Estimate

### Lambda Invocations (per month)
- 1M requests: $0.20
- Compute (arm64): $0.0000133334/GB-second
- **Total Lambda**: ~$2-3/month for 100 students

### API Gateway
- 1M requests: $3.50/month

### Total Monthly Cost
- **100 students**: ~$16/month ($0.16/student)
- **1000 students**: ~$85/month ($0.085/student)

## Support

For issues or questions:
1. Check CloudWatch Logs: `/aws/lambda/<function-name>`
2. Review IAM permissions
3. Verify environment variables
4. Test with sample payloads in `lambda/payloads/`

---

**Last Updated**: March 9, 2026  
**Region**: ap-south-1  
**Environment**: dev  
**Account**: 718980965213
