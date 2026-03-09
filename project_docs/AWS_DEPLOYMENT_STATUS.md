# AWS Deployment Status - Studaxis

## Current Status: 81% Complete (17/21 resources)

### ✅ Successfully Deployed (17 resources)

#### DynamoDB Tables (6/6) ✓
- ✅ studaxis-student-sync
- ✅ studaxis-quiz-index
- ✅ studaxis-content-distribution
- ✅ studaxis-classes
- ✅ studaxis-assignments
- ✅ studaxis-teachers-dev

#### S3 Buckets (3/3) ✓
- ✅ studaxis-payloads
- ✅ studaxis-student-stats-2026
- ✅ studaxis-lambda-artifacts-dev

#### Lambda Functions (2/6) ⚠️
- ✅ studaxis-offline-sync-dev
- ✅ studaxis-quiz-generation-dev
- ❌ studaxis-content-2026-distribution-dev
- ❌ studaxis-teacher-generate-notes-dev
- ❌ studaxis-class-manager-dev
- ❌ studaxis-teacher-auth-dev

#### API Gateway (1/1) ✓
- ✅ studaxis-teacher-api-dev
  - Endpoint: https://yjyn9jsugc.execute-api.ap-south-1.amazonaws.com/prod

#### IAM Roles (5/5) ✓
- ✅ studaxis-offline-sync-role-dev
- ✅ studaxis-content-2026-dist-role-dev
- ✅ studaxis-quiz-gen-role-dev
- ✅ studaxis-class-manager-role-dev
- ✅ studaxis-teacher-auth-dev-sam

### ❌ Missing Resources (4 Lambda functions)

The following Lambda functions need to be deployed:
1. studaxis-content-2026-distribution-dev
2. studaxis-teacher-generate-notes-dev
3. studaxis-class-manager-dev
4. studaxis-teacher-auth-dev

## Next Steps

### Step 1: Deploy Missing Lambda Functions (15 minutes)

```powershell
# Navigate to lambda directory
cd lambda

# Build Lambda functions
sam build

# Deploy to AWS
sam deploy --guided
```

**SAM Deploy Configuration:**
```
Stack Name: studaxis-teacher-dashboard
AWS Region: ap-south-1
Parameter Environment: dev
Confirm changes before deploy: Y
Allow SAM CLI IAM role creation: Y
Save arguments to configuration file: Y
SAM configuration file: samconfig.toml
```

### Step 2: Create AppSync API (5 minutes)

**Manual Steps:**
1. Go to AWS AppSync Console: https://console.aws.amazon.com/appsync
2. Click "Create API"
3. Select "Build from scratch"
4. API name: `studaxis-graphql-api`
5. Click "Create"

**Configure Schema:**
1. Go to "Schema" tab
2. Copy content from: `aws-infra/appsync/schema.graphql`
3. Paste and click "Save Schema"

**Create API Key:**
1. Go to "Settings" tab
2. Under "API Keys", click "Create API key"
3. Note the API key (starts with `da2-`)
4. Note the GraphQL endpoint URL

**Configure Resolvers:**
1. Go to "Schema" tab
2. Find `listStudentProgresses` query
3. Attach data source: Lambda → `studaxis-content-2026-distribution-dev`
4. Find `recordQuizAttempt` mutation
5. Attach data source: Lambda → `studaxis-offline-sync-dev`

### Step 3: Request Bedrock Model Access (5 minutes)

1. Go to AWS Bedrock Console: https://console.aws.amazon.com/bedrock
2. Click "Model access" in left sidebar
3. Click "Request model access"
4. Select "Amazon Nova" models
5. Click "Request model access"
6. Wait ~5 minutes for approval

### Step 4: Update Environment Variables

**Teacher Dashboard Web (.env):**
```bash
VITE_API_GATEWAY_URL=https://yjyn9jsugc.execute-api.ap-south-1.amazonaws.com/prod
VITE_APPSYNC_ENDPOINT=<your-appsync-endpoint>
VITE_APPSYNC_API_KEY=<your-api-key>
VITE_TEACHER_BACKEND_URL=http://localhost:6782
```

**Student Backend (.env):**
```bash
STUDAXIS_BASE_PATH=./backend
AWS_REGION=ap-south-1
APPSYNC_ENDPOINT=<your-appsync-endpoint>
APPSYNC_API_KEY=<your-api-key>
API_GATEWAY_URL=https://yjyn9jsugc.execute-api.ap-south-1.amazonaws.com/prod
OLLAMA_BASE_URL=http://localhost:11434
```

### Step 5: Verify Deployment

```powershell
# Run test script
.\test_resources.ps1

# Expected result: 21/21 tests passing
```

## Troubleshooting

### Lambda Deployment Fails

**Check SAM template exists:**
```powershell
ls lambda/sam-template.yaml
```

**If missing, check for template.yaml:**
```powershell
ls lambda/template.yaml
```

**View CloudFormation events:**
```powershell
aws cloudformation describe-stack-events `
  --stack-name studaxis-teacher-dashboard `
  --region ap-south-1 `
  --max-items 20
```

### AppSync Connection Issues

**Test AppSync endpoint:**
```powershell
# List APIs
aws appsync list-graphql-apis --region ap-south-1

# Get API details
aws appsync get-graphql-api --api-id <your-api-id> --region ap-south-1
```

### Bedrock Access Denied

**Check model access status:**
```powershell
aws bedrock list-foundation-models --region ap-south-1
```

**If no models listed:**
- Request access in Bedrock Console
- Wait 5-10 minutes
- Try again

## Cost Estimate

### Current Monthly Cost (100 students)
- DynamoDB: $1.00 (on-demand, within free tier)
- S3: $0.50 (minimal storage)
- Lambda: $2.00 (1M requests/month)
- API Gateway: $3.50 (1M requests/month)
- AppSync: $4.00 (1M queries/month)
- Bedrock: $5.00 (500 quiz generations/month)
- **Total: ~$16/month** ($0.16/student/month)

### Scaling to 1000 students
- **Total: ~$85/month** ($0.085/student/month)

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Teacher Dashboard                         │
│                    (React + Vite)                            │
└────────────┬────────────────────────────────────────────────┘
             │
             ├─── API Gateway (REST) ───┐
             │   ✅ yjyn9jsugc           │
             │                           │
             ├─── AppSync (GraphQL) ────┤
             │   ❌ Not created yet      │
             │                           v
             │                  ┌──────────────────────┐
             │                  │   Lambda Functions   │
             │                  │  ✅ offline-sync     │
             │                  │  ✅ quiz-generation  │
             │                  │  ❌ content-dist     │
             │                  │  ❌ class-manager    │
             │                  │  ❌ teacher-auth     │
             │                  │  ❌ generate-notes   │
             │                  └──────────┬───────────┘
             │                             │
             │                             v
             │                  ┌──────────────────────┐
             │                  │   DynamoDB Tables    │
             │                  │  ✅ All 6 tables     │
             │                  └──────────────────────┘
             │                             │
             │                             v
             │                  ┌──────────────────────┐
             │                  │   S3 Buckets         │
             │                  │  ✅ All 3 buckets    │
             │                  └──────────────────────┘
             v
┌────────────────────────────────────────────────────────────┐
│              Student Backend (FastAPI)                      │
│              http://localhost:6782                          │
└────────────────────────────────────────────────────────────┘
```

## Quick Commands

```powershell
# Test current status
.\test_resources.ps1

# Deploy Lambda functions
cd lambda
sam build
sam deploy

# List all resources
aws dynamodb list-tables --region ap-south-1
aws lambda list-functions --region ap-south-1
aws s3 ls
aws apigateway get-rest-apis --region ap-south-1

# Check CloudFormation stack
aws cloudformation describe-stacks `
  --stack-name studaxis-teacher-dashboard `
  --region ap-south-1
```

## Success Criteria

- [x] All DynamoDB tables created (6/6)
- [x] All S3 buckets created (3/3)
- [x] All IAM roles created (5/5)
- [x] API Gateway deployed (1/1)
- [ ] All Lambda functions deployed (2/6)
- [ ] AppSync API created (0/1)
- [ ] Bedrock access granted (0/1)

**Current Progress: 81% (17/21)**
**Target: 100% (21/21)**

## Timeline

- ✅ Infrastructure setup: Complete
- ⏳ Lambda deployment: 15 minutes
- ⏳ AppSync configuration: 5 minutes
- ⏳ Bedrock access: 5 minutes
- ⏳ Testing & verification: 5 minutes

**Total remaining time: ~30 minutes**

---

**Last Updated:** March 9, 2026
**Account ID:** 718980965213
**Region:** ap-south-1
**Environment:** dev
