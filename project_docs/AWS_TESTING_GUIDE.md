# AWS Endpoints Testing Guide

## Overview

This guide explains how to test all AWS resources and endpoints for the Studaxis platform using automated CLI scripts.

## Prerequisites

- AWS CLI installed and configured
- Valid AWS credentials with appropriate permissions
- Access to ap-south-1 region (or your configured region)

## Quick Start

### Linux/Mac

```bash
cd aws-infra
chmod +x test_aws_endpoints.sh
./test_aws_endpoints.sh
```

### Windows (PowerShell)

```powershell
cd aws-infra
.\test_aws_endpoints.ps1
```

### Custom Region/Environment

```bash
# Linux/Mac
AWS_REGION=us-east-1 ENV=prod ./test_aws_endpoints.sh

# Windows
.\test_aws_endpoints.ps1 -Region us-east-1 -Environment prod
```

## What Gets Tested

### 1. DynamoDB Tables (6 tables)
- ✅ studaxis-student-sync
- ✅ studaxis-quiz-index
- ✅ studaxis-content-distribution
- ✅ studaxis-classes
- ✅ studaxis-assignments
- ✅ studaxis-teachers-{env}

**Checks**: Table existence, ACTIVE status

### 2. S3 Buckets (3 buckets)
- ✅ studaxis-payloads
- ✅ studaxis-student-stats-2026
- ✅ studaxis-lambda-artifacts-{env}

**Checks**: Bucket existence, access permissions

### 3. Lambda Functions (6 functions)
- ✅ studaxis-offline-sync-{env}
- ✅ studaxis-content-2026-distribution-{env}
- ✅ studaxis-quiz-generation-{env}
- ✅ studaxis-teacher-generate-notes-{env}
- ✅ studaxis-class-manager-{env}
- ✅ studaxis-teacher-auth-{env}

**Checks**: Function existence, state, runtime, architecture

### 4. API Gateway
- ✅ studaxis-teacher-api-{env}
- ✅ GET /classes endpoint
- ✅ POST /generateQuiz endpoint
- ✅ GET /assignments endpoint

**Checks**: API existence, endpoint connectivity, HTTP responses

### 5. AppSync API
- ✅ GraphQL API existence
- ✅ Endpoint URL

**Checks**: API configuration (manual creation required)

### 6. IAM Roles (5 roles)
- ✅ studaxis-offline-sync-role-{env}
- ✅ studaxis-content-2026-dist-role-{env}
- ✅ studaxis-quiz-gen-role-{env}
- ✅ studaxis-teacher-auth-{env}-sam
- ✅ studaxis-class-manager-role-{env}

**Checks**: Role existence, trust policies

### 7. CloudWatch Log Groups
- ✅ /aws/lambda/* for each function

**Checks**: Log group existence (created on first invocation)

### 8. Bedrock Model Access
- ✅ Bedrock API access
- ✅ Amazon Nova model availability

**Checks**: API permissions, model access

### 9. CloudFormation Stack
- ✅ studaxis-teacher-dashboard stack
- ✅ Stack outputs

**Checks**: Stack status, outputs

### 10. Integration Tests
- ✅ Lambda invocation test (CORS OPTIONS)

**Checks**: End-to-end Lambda execution

## Sample Output

```
╔════════════════════════════════════════════════════════╗
║     Studaxis AWS Endpoints Testing Suite              ║
╚════════════════════════════════════════════════════════╝

Region: ap-south-1
Environment: dev

✓ AWS CLI configured
Account ID: 123456789012

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Testing DynamoDB Tables
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ DynamoDB Table: studaxis-student-sync (Status: ACTIVE)
✓ DynamoDB Table: studaxis-quiz-index (Status: ACTIVE)
✓ DynamoDB Table: studaxis-content-distribution (Status: ACTIVE)
✓ DynamoDB Table: studaxis-classes (Status: ACTIVE)
✓ DynamoDB Table: studaxis-assignments (Status: ACTIVE)
✗ DynamoDB Table: studaxis-teachers-dev (Not Found)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. Testing S3 Buckets
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ S3 Bucket: studaxis-payloads
✓ S3 Bucket: studaxis-student-stats-2026
✗ S3 Bucket: studaxis-lambda-artifacts-dev (Not Found)

...

╔════════════════════════════════════════════════════════╗
║                    Test Summary                        ║
╚════════════════════════════════════════════════════════╝

Total Tests:  45
Passed:       38
Failed:       7

⚠ Some tests failed. Review the output above.
```

## Interpreting Results

### ✓ Green Checkmark
Resource exists and is properly configured. No action needed.

### ✗ Red X
Resource is missing or misconfigured. See troubleshooting below.

## Troubleshooting

### DynamoDB Table Not Found

**Solution**: Create the table
```bash
aws dynamodb create-table \
  --table-name studaxis-classes \
  --attribute-definitions AttributeName=class_id,AttributeType=S \
  --key-schema AttributeName=class_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ap-south-1
```

Or run the deployment script:
```bash
./deploy_teacher_dashboard.sh
```

### Lambda Function Not Found

**Solution**: Deploy Lambda functions
```bash
cd aws-infra/lambda
sam build
sam deploy --guided
```

### S3 Bucket Not Found

**Solution**: Create the bucket
```bash
aws s3 mb s3://studaxis-payloads --region ap-south-1
```

### API Gateway Not Found

**Solution**: Deploy via CloudFormation/SAM
```bash
cd aws-infra/lambda
sam deploy
```

### AppSync API Not Found

**Solution**: Create manually in AWS Console
1. Go to AWS AppSync Console
2. Create API → "Build from scratch"
3. Copy schema from `aws-infra/appsync/schema.graphql`
4. Configure resolvers

### IAM Role Not Found

**Solution**: Roles are created by CloudFormation/SAM during Lambda deployment
```bash
cd aws-infra/lambda
sam deploy
```

### Bedrock Access Denied

**Solution**: Request model access
1. Go to AWS Bedrock Console
2. Model access → Request access
3. Select "Amazon Nova" models
4. Wait for approval (~5 minutes)

### API Endpoint Returns 403/401

**Expected**: API Gateway uses IAM authentication. 401/403 responses indicate the endpoint exists but requires authentication.

**Solution**: This is normal. The test verifies connectivity, not authentication.

### Lambda Invocation Failed

**Possible causes**:
- Lambda doesn't exist
- IAM permissions missing
- Lambda in error state

**Solution**: Check CloudWatch Logs
```bash
aws logs tail /aws/lambda/studaxis-class-manager-dev --follow
```

## Manual Verification

### Test DynamoDB Table

```bash
aws dynamodb describe-table \
  --table-name studaxis-classes \
  --region ap-south-1
```

### Test S3 Bucket

```bash
aws s3 ls s3://studaxis-payloads/
```

### Test Lambda Function

```bash
aws lambda get-function \
  --function-name studaxis-class-manager-dev \
  --region ap-south-1
```

### Test API Gateway

```bash
# Get API ID
aws apigateway get-rest-apis \
  --region ap-south-1 \
  --query "items[?name=='studaxis-teacher-api-dev']"

# Test endpoint
curl https://YOUR_API_ID.execute-api.ap-south-1.amazonaws.com/prod/classes
```

### Test AppSync

```bash
aws appsync list-graphql-apis --region ap-south-1
```

### Invoke Lambda Directly

```bash
aws lambda invoke \
  --function-name studaxis-class-manager-dev \
  --region ap-south-1 \
  --payload '{"httpMethod":"OPTIONS","path":"/classes"}' \
  --cli-binary-format raw-in-base64-out \
  response.json

cat response.json
```

## Continuous Testing

### Run Before Deployment

```bash
# Test current state
./test_aws_endpoints.sh

# Deploy changes
./deploy_teacher_dashboard.sh

# Verify deployment
./test_aws_endpoints.sh
```

### Automated Testing in CI/CD

Add to GitHub Actions:

```yaml
- name: Test AWS Endpoints
  run: |
    cd aws-infra
    chmod +x test_aws_endpoints.sh
    ./test_aws_endpoints.sh
  env:
    AWS_REGION: ap-south-1
    ENV: prod
```

## Expected Results

### Fresh Deployment
- **Passed**: 0-10 tests (no resources yet)
- **Failed**: 35-45 tests
- **Action**: Run deployment script

### After Deployment
- **Passed**: 35-40 tests
- **Failed**: 5-10 tests (AppSync, some IAM roles)
- **Action**: Manual AppSync setup

### Production Ready
- **Passed**: 40-45 tests
- **Failed**: 0-5 tests (optional resources)
- **Action**: None, ready to use

## Performance Benchmarks

- **Test Duration**: ~30-60 seconds
- **API Calls**: ~50 AWS API calls
- **Cost**: $0.00 (within free tier)

## Security Notes

- Tests use read-only operations (describe, list, get)
- No data is modified or deleted
- Safe to run in production
- Requires minimal IAM permissions:
  - `dynamodb:DescribeTable`
  - `s3:ListBucket`
  - `lambda:GetFunction`
  - `apigateway:GET`
  - `iam:GetRole`
  - `logs:DescribeLogGroups`

## Next Steps

After all tests pass:

1. ✅ Update environment variables in dashboards
2. ✅ Test end-to-end integration (see QUICK_START guide)
3. ✅ Deploy teacher dashboard to production
4. ✅ Configure monitoring and alarms
5. ✅ Set up CI/CD pipeline

## Support

For issues:
1. Check CloudWatch Logs for Lambda errors
2. Review IAM permissions
3. Verify region configuration
4. Check AWS service quotas
5. Consult AWS_INTEGRATION_CHECKLIST.md

---

**Last Updated**: March 2026  
**Tested With**: AWS CLI v2.x, Python 3.11, PowerShell 7.x
