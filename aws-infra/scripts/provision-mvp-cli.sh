#!/bin/bash
# Studaxis MVP — provision missing resources via raw AWS CLI
# Use when SAM deploy fails (e.g. Windows Unicode bug) or for fresh accounts.
# Run from repo root: bash aws-infra/scripts/provision-mvp-cli.sh
set -e
REGION="${AWS_REGION:-ap-south-1}"

echo "[1/4] DynamoDB: studaxis-student-sync"
aws dynamodb create-table \
  --table-name studaxis-student-sync \
  --attribute-definitions AttributeName=user_id,AttributeType=S AttributeName=class_code,AttributeType=S \
  --key-schema AttributeName=user_id,KeyType=HASH AttributeName=class_code,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region "$REGION" 2>/dev/null || echo "  (exists)"

echo "[2/4] DynamoDB: studaxis-quiz-index"
aws dynamodb create-table \
  --table-name studaxis-quiz-index \
  --attribute-definitions AttributeName=quiz_id,AttributeType=S \
  --key-schema AttributeName=quiz_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region "$REGION" 2>/dev/null || echo "  (exists)"

echo "[3/4] S3: studaxis-payloads"
aws s3 mb "s3://studaxis-payloads" --region "$REGION" 2>/dev/null || echo "  (exists)"

echo "[4/4] Verify"
aws dynamodb list-tables --region "$REGION"
aws s3 ls --region "$REGION" | grep studaxis
echo "Done. Lambdas and AppSync require SAM/CDK/Console; run sam deploy when SAM works."
