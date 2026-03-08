#!/bin/bash
# Studaxis MVP Deployment Script
# Creates: DynamoDB, S3, AppSync + Lambda (if not already deployed)
# Run from repo root: bash aws-infra/deploy_mvp.sh

set -e
REGION="${AWS_REGION:-ap-south-1}"
STACK_NAME="studaxis-mvp"

echo "=== Studaxis MVP Deployment ==="
echo "Region: $REGION"
echo ""

# 1. DynamoDB table
echo "[1/4] DynamoDB studaxis-student-sync..."
aws dynamodb describe-table --table-name studaxis-student-sync --region "$REGION" 2>/dev/null && \
  echo "  ✓ Table exists" || {
  aws dynamodb create-table \
    --table-name studaxis-student-sync \
    --attribute-definitions AttributeName=user_id,AttributeType=S \
    --key-schema AttributeName=user_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "$REGION"
  echo "  ✓ Created"
}

# 2. S3 bucket
echo "[2/4] S3 bucket studaxis-payloads..."
aws s3api head-bucket --bucket studaxis-payloads --region "$REGION" 2>/dev/null && \
  echo "  ✓ Bucket exists" || {
  aws s3api create-bucket --bucket studaxis-payloads --region "$REGION" --create-bucket-configuration LocationConstraint="$REGION"
  echo "  ✓ Created"
}

# 3. Lambda artifacts bucket (for SAM/CF)
echo "[3/4] Lambda artifacts bucket..."
aws s3api head-bucket --bucket studaxis-lambda-artifacts-dev --region "$REGION" 2>/dev/null && \
  echo "  ✓ Bucket exists" || {
  aws s3api create-bucket --bucket studaxis-lambda-artifacts-dev --region "$REGION" --create-bucket-configuration LocationConstraint="$REGION"
  echo "  ✓ Created"
}

# 4. AppSync + Lambda: Use existing CloudFormation or SAM
echo "[4/4] AppSync + Lambda..."
echo "  → Use: aws cloudformation deploy (main stack) or existing studaxis-vtwo stack"
echo "  → AppSync API already exists: studaxis-graphql-api"
echo "  → Lambda: studaxis-offline-sync"
echo ""
echo "=== Deployment summary ==="
APPSYNC_API=$(aws appsync list-graphql-apis --region "$REGION" --query "graphqlApis[?name=='studaxis-graphql-api'].apiId" --output text 2>/dev/null | head -1)
if [ -n "$APPSYNC_API" ]; then
  ENDPOINT=$(aws appsync get-graphql-api --api-id "$APPSYNC_API" --region "$REGION" --query "graphqlApi.uris.GRAPHQL" --output text)
  echo "APPSYNC_ENDPOINT=$ENDPOINT"
  echo "APPSYNC_API_ID=$APPSYNC_API"
  echo ""
  echo "Get API key from: https://${REGION}.console.aws.amazon.com/appsync/home?region=${REGION}#/${APPSYNC_API}/settings"
fi
echo ""
echo "Done."
