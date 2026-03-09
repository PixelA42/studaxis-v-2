#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# Studaxis Lambda Manual Deployment Script (Bash)
# ═══════════════════════════════════════════════════════════════════════════
# Purpose: Deploy missing Lambda functions individually using AWS CLI
# Region: ap-south-1
# Environment: dev
# Account: 718980965213
# ═══════════════════════════════════════════════════════════════════════════

set -e

REGION="ap-south-1"
ACCOUNT_ID="718980965213"

echo "╔════════════════════════════════════════════════════════╗"
echo "║     Studaxis Lambda Manual Deployment Script          ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo ""

# Navigate to lambda directory
cd lambda

# ═══════════════════════════════════════════════════════════════════════════
# Step 1: Create Deployment Packages
# ═══════════════════════════════════════════════════════════════════════════

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Creating Deployment Packages"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Teacher Auth
echo "  → Packaging teacher_auth..."
rm -f teacher_auth.zip
cd teacher_auth && zip -r ../teacher_auth.zip . && cd ..
SIZE=$(du -h teacher_auth.zip | cut -f1)
echo "    ✓ Created teacher_auth.zip ($SIZE)"

# Class Manager
echo "  → Packaging class_manager..."
rm -f class_manager.zip
cd class_manager && zip -r ../class_manager.zip . && cd ..
SIZE=$(du -h class_manager.zip | cut -f1)
echo "    ✓ Created class_manager.zip ($SIZE)"

# Teacher Generate Notes
echo "  → Packaging teacher_generate_notes..."
rm -f teacher_generate_notes.zip
cd teacher_generate_notes && zip -r ../teacher_generate_notes.zip . && cd ..
SIZE=$(du -h teacher_generate_notes.zip | cut -f1)
echo "    ✓ Created teacher_generate_notes.zip ($SIZE)"

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# Step 2: Deploy Lambda Functions
# ═══════════════════════════════════════════════════════════════════════════

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. Deploying Lambda Functions"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ─────────────────────────────────────────────────────────────────────────
# Lambda 1: Teacher Auth
# ─────────────────────────────────────────────────────────────────────────

echo "  [1/3] Deploying studaxis-teacher-auth-dev..."

if aws lambda get-function --function-name studaxis-teacher-auth-dev --region $REGION &>/dev/null; then
    echo "        Function already exists, updating code..."
    aws lambda update-function-code \
        --function-name studaxis-teacher-auth-dev \
        --zip-file fileb://teacher_auth.zip \
        --region $REGION \
        --architectures arm64 \
        --output json > /dev/null
    echo "        ✓ Code updated successfully"
else
    echo "        Creating new function..."
    aws lambda create-function \
        --function-name studaxis-teacher-auth-dev \
        --runtime python3.11 \
        --role "arn:aws:iam::${ACCOUNT_ID}:role/studaxis-teacher-auth-dev-sam" \
        --handler handler.lambda_handler \
        --zip-file fileb://teacher_auth.zip \
        --timeout 10 \
        --memory-size 256 \
        --architectures arm64 \
        --environment "Variables={LOG_LEVEL=INFO,TEACHERS_TABLE_NAME=studaxis-teachers-dev,STUDAXIS_JWT_SECRET=studaxis-dev-secret-change-in-prod}" \
        --region $REGION \
        --output json > /dev/null
    echo "        ✓ Function created successfully"
fi

echo ""

# ─────────────────────────────────────────────────────────────────────────
# Lambda 2: Class Manager
# ─────────────────────────────────────────────────────────────────────────

echo "  [2/3] Deploying studaxis-class-manager-dev..."

if aws lambda get-function --function-name studaxis-class-manager-dev --region $REGION &>/dev/null; then
    echo "        Function already exists, updating code..."
    aws lambda update-function-code \
        --function-name studaxis-class-manager-dev \
        --zip-file fileb://class_manager.zip \
        --region $REGION \
        --architectures arm64 \
        --output json > /dev/null
    echo "        ✓ Code updated successfully"
else
    echo "        Creating new function..."
    aws lambda create-function \
        --function-name studaxis-class-manager-dev \
        --runtime python3.11 \
        --role "arn:aws:iam::${ACCOUNT_ID}:role/studaxis-class-manager-role-dev" \
        --handler handler.lambda_handler \
        --zip-file fileb://class_manager.zip \
        --timeout 15 \
        --memory-size 256 \
        --architectures arm64 \
        --environment "Variables={LOG_LEVEL=INFO,CLASSES_TABLE_NAME=studaxis-classes}" \
        --region $REGION \
        --output json > /dev/null
    echo "        ✓ Function created successfully"
fi

echo ""

# ─────────────────────────────────────────────────────────────────────────
# Lambda 3: Teacher Generate Notes
# ─────────────────────────────────────────────────────────────────────────

echo "  [3/3] Deploying studaxis-teacher-generate-notes-dev..."

# Check if IAM role exists, create if not
if ! aws iam get-role --role-name studaxis-teacher-generate-notes-role-dev --region $REGION &>/dev/null; then
    echo "        Creating IAM role..."
    
    # Create trust policy
    cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
    
    aws iam create-role \
        --role-name studaxis-teacher-generate-notes-role-dev \
        --assume-role-policy-document file://trust-policy.json \
        --region $REGION \
        --output json > /dev/null
    
    # Attach basic execution policy
    aws iam attach-role-policy \
        --role-name studaxis-teacher-generate-notes-role-dev \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" \
        --region $REGION
    
    # Create inline policy
    cat > inline-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:HeadObject"],
      "Resource": "arn:aws:s3:::studaxis-payloads/*"
    },
    {
      "Effect": "Allow",
      "Action": ["dynamodb:PutItem"],
      "Resource": "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/studaxis-content-distribution"
    }
  ]
}
EOF
    
    aws iam put-role-policy \
        --role-name studaxis-teacher-generate-notes-role-dev \
        --policy-name BedrockS3DynamoDBAccess \
        --policy-document file://inline-policy.json \
        --region $REGION
    
    echo "        ✓ IAM role created"
    echo "        Waiting 10 seconds for IAM role to propagate..."
    sleep 10
fi

if aws lambda get-function --function-name studaxis-teacher-generate-notes-dev --region $REGION &>/dev/null; then
    echo "        Function already exists, updating code..."
    aws lambda update-function-code \
        --function-name studaxis-teacher-generate-notes-dev \
        --zip-file fileb://teacher_generate_notes.zip \
        --region $REGION \
        --architectures arm64 \
        --output json > /dev/null
    echo "        ✓ Code updated successfully"
else
    echo "        Creating new function..."
    aws lambda create-function \
        --function-name studaxis-teacher-generate-notes-dev \
        --runtime python3.11 \
        --role "arn:aws:iam::${ACCOUNT_ID}:role/studaxis-teacher-generate-notes-role-dev" \
        --handler handler.lambda_handler \
        --zip-file fileb://teacher_generate_notes.zip \
        --timeout 60 \
        --memory-size 512 \
        --architectures arm64 \
        --environment "Variables={LOG_LEVEL=INFO,S3_BUCKET_NAME=studaxis-payloads,CONTENT_DISTRIBUTION_TABLE=studaxis-content-distribution,BEDROCK_REGION=ap-south-1,BEDROCK_MODEL_ID=arn:aws:bedrock:ap-south-1:718980965213:inference-profile/global.amazon.nova-2-lite-v1:0,PRESIGNED_URL_EXPIRY_SECONDS=86400}" \
        --region $REGION \
        --output json > /dev/null
    echo "        ✓ Function created successfully"
fi

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# Step 3: Update content-distribution-dev
# ═══════════════════════════════════════════════════════════════════════════

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. Updating Existing Content Distribution Lambda"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "  → Packaging content_distribution..."
rm -f content_distribution.zip
cd content_distribution && zip -r ../content_distribution.zip . && cd ..
SIZE=$(du -h content_distribution.zip | cut -f1)
echo "    ✓ Created content_distribution.zip ($SIZE)"

echo "  → Updating studaxis-content-distribution-dev..."
aws lambda update-function-code \
    --function-name studaxis-content-distribution-dev \
    --zip-file fileb://content_distribution.zip \
    --region $REGION \
    --architectures arm64 \
    --output json > /dev/null
echo "    ✓ Code updated successfully"

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# Step 4: Verification
# ═══════════════════════════════════════════════════════════════════════════

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "  Checking deployed Lambda functions..."
echo ""

FUNCTIONS=(
    "studaxis-teacher-auth-dev"
    "studaxis-class-manager-dev"
    "studaxis-teacher-generate-notes-dev"
    "studaxis-content-distribution-dev"
)

for func in "${FUNCTIONS[@]}"; do
    if aws lambda get-function --function-name $func --region $REGION &>/dev/null; then
        STATE=$(aws lambda get-function --function-name $func --region $REGION --query 'Configuration.State' --output text)
        RUNTIME=$(aws lambda get-function --function-name $func --region $REGION --query 'Configuration.Runtime' --output text)
        MEMORY=$(aws lambda get-function --function-name $func --region $REGION --query 'Configuration.MemorySize' --output text)
        echo "    ✓ $func"
        echo "      State: $STATE, Runtime: $RUNTIME, Memory: ${MEMORY}MB"
    else
        echo "    ✗ $func (not found)"
    fi
done

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════

echo "╔════════════════════════════════════════════════════════╗"
echo "║              Deployment Complete                       ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "Next Steps:"
echo "  1. Run test script: ../test_resources.ps1"
echo "  2. Configure API Gateway endpoints:"
echo "     - POST /auth → studaxis-teacher-auth-dev"
echo "     - GET/POST /classes → studaxis-class-manager-dev"
echo "     - POST /teacher/generateNotes → studaxis-teacher-generate-notes-dev"
echo "  3. Create AppSync API (see aws-infra/GET_API_KEY.md)"
echo "  4. Update environment variables in:"
echo "     - teacher-dashboard-web/.env"
echo "     - backend/.env"
echo ""

# Return to original directory
cd ..
