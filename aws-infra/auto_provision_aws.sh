#!/bin/bash
# Studaxis AWS Auto-Provisioning Script
# Automatically creates missing AWS resources based on integration checklist

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
AWS_REGION="${AWS_REGION:-ap-south-1}"
ENV="${ENV:-dev}"
STACK_NAME="studaxis-teacher-dashboard"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Studaxis AWS Auto-Provisioning Script             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Region: ${AWS_REGION}${NC}"
echo -e "${YELLOW}Environment: ${ENV}${NC}"
echo ""

# Check prerequisites
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Install: https://aws.amazon.com/cli/${NC}"
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured. Run: aws configure${NC}"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ AWS CLI configured (Account: ${ACCOUNT_ID})${NC}"
echo ""

# ============================================================================
# 1. Create DynamoDB Tables
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}1. Provisioning DynamoDB Tables${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

create_dynamodb_table() {
    local table_name=$1
    local key_name=$2
    local gsi_config=$3
    
    if aws dynamodb describe-table --table-name "$table_name" --region "$AWS_REGION" &> /dev/null; then
        echo -e "${YELLOW}⚠ Table $table_name already exists${NC}"
    else
        echo -e "${GREEN}Creating table: $table_name${NC}"
        
        if [ -z "$gsi_config" ]; then
            # Simple table without GSI
            aws dynamodb create-table \
                --table-name "$table_name" \
                --attribute-definitions AttributeName="$key_name",AttributeType=S \
                --key-schema AttributeName="$key_name",KeyType=HASH \
                --billing-mode PAY_PER_REQUEST \
                --region "$AWS_REGION" \
                --tags Key=Project,Value=Studaxis Key=Environment,Value="$ENV" \
                > /dev/null
        else
            # Table with GSI
            eval "aws dynamodb create-table \
                --table-name '$table_name' \
                $gsi_config \
                --billing-mode PAY_PER_REQUEST \
                --region '$AWS_REGION' \
                --tags Key=Project,Value=Studaxis Key=Environment,Value='$ENV' \
                > /dev/null"
        fi
        
        echo "  Waiting for table to be active..."
        aws dynamodb wait table-exists --table-name "$table_name" --region "$AWS_REGION"
        echo -e "${GREEN}  ✓ Table $table_name created${NC}"
    fi
}

# studaxis-student-sync (main sync table)
create_dynamodb_table "studaxis-student-sync" "user_id"

# studaxis-quiz-index (quiz metadata)
create_dynamodb_table "studaxis-quiz-index" "quiz_id"

# studaxis-content-distribution (class content with composite key)
if aws dynamodb describe-table --table-name "studaxis-content-distribution" --region "$AWS_REGION" &> /dev/null; then
    echo -e "${YELLOW}⚠ Table studaxis-content-distribution already exists${NC}"
else
    echo -e "${GREEN}Creating table: studaxis-content-distribution${NC}"
    aws dynamodb create-table \
        --table-name "studaxis-content-distribution" \
        --attribute-definitions \
            AttributeName=class_id,AttributeType=S \
            AttributeName=content_id,AttributeType=S \
        --key-schema \
            AttributeName=class_id,KeyType=HASH \
            AttributeName=content_id,KeyType=RANGE \
        --billing-mode PAY_PER_REQUEST \
        --region "$AWS_REGION" \
        --tags Key=Project,Value=Studaxis Key=Environment,Value="$ENV" \
        > /dev/null
    
    echo "  Waiting for table to be active..."
    aws dynamodb wait table-exists --table-name "studaxis-content-distribution" --region "$AWS_REGION"
    echo -e "${GREEN}  ✓ Table studaxis-content-distribution created${NC}"
fi

# studaxis-classes (class management with GSI)
if aws dynamodb describe-table --table-name "studaxis-classes" --region "$AWS_REGION" &> /dev/null; then
    echo -e "${YELLOW}⚠ Table studaxis-classes already exists${NC}"
else
    echo -e "${GREEN}Creating table: studaxis-classes${NC}"
    aws dynamodb create-table \
        --table-name "studaxis-classes" \
        --attribute-definitions \
            AttributeName=class_id,AttributeType=S \
            AttributeName=class_code,AttributeType=S \
        --key-schema AttributeName=class_id,KeyType=HASH \
        --global-secondary-indexes \
            "[{
                \"IndexName\": \"class_code-index\",
                \"KeySchema\": [{\"AttributeName\":\"class_code\",\"KeyType\":\"HASH\"}],
                \"Projection\": {\"ProjectionType\":\"ALL\"}
            }]" \
        --billing-mode PAY_PER_REQUEST \
        --region "$AWS_REGION" \
        --tags Key=Project,Value=Studaxis Key=Environment,Value="$ENV" \
        > /dev/null
    
    echo "  Waiting for table to be active..."
    aws dynamodb wait table-exists --table-name "studaxis-classes" --region "$AWS_REGION"
    echo -e "${GREEN}  ✓ Table studaxis-classes created${NC}"
fi

# studaxis-assignments (assignment tracking)
create_dynamodb_table "studaxis-assignments" "assignment_id"

# studaxis-teachers-{env} (teacher auth)
create_dynamodb_table "studaxis-teachers-${ENV}" "classCode"

echo ""

# ============================================================================
# 2. Create S3 Buckets
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}2. Provisioning S3 Buckets${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

create_s3_bucket() {
    local bucket_name=$1
    local enable_versioning=$2
    
    if aws s3 ls "s3://$bucket_name" --region "$AWS_REGION" &> /dev/null; then
        echo -e "${YELLOW}⚠ Bucket $bucket_name already exists${NC}"
    else
        echo -e "${GREEN}Creating bucket: $bucket_name${NC}"
        
        if [ "$AWS_REGION" == "us-east-1" ]; then
            aws s3 mb "s3://$bucket_name"
        else
            aws s3 mb "s3://$bucket_name" --region "$AWS_REGION"
        fi
        
        # Block public access
        aws s3api put-public-access-block \
            --bucket "$bucket_name" \
            --public-access-block-configuration \
                "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" \
            --region "$AWS_REGION"
        
        # Enable versioning if requested
        if [ "$enable_versioning" == "true" ]; then
            aws s3api put-bucket-versioning \
                --bucket "$bucket_name" \
                --versioning-configuration Status=Enabled \
                --region "$AWS_REGION"
            echo "  ✓ Versioning enabled"
        fi
        
        # Add tags
        aws s3api put-bucket-tagging \
            --bucket "$bucket_name" \
            --tagging "TagSet=[{Key=Project,Value=Studaxis},{Key=Environment,Value=$ENV}]" \
            --region "$AWS_REGION"
        
        echo -e "${GREEN}  ✓ Bucket $bucket_name created${NC}"
    fi
}

create_s3_bucket "studaxis-payloads" "true"
create_s3_bucket "studaxis-student-stats-2026" "false"
create_s3_bucket "studaxis-lambda-artifacts-${ENV}" "false"

# Create folder structure in studaxis-payloads
echo "  Creating folder structure in studaxis-payloads..."
echo "" | aws s3 cp - "s3://studaxis-payloads/quizzes/.keep" --region "$AWS_REGION" 2>/dev/null || true
echo "" | aws s3 cp - "s3://studaxis-payloads/notes/.keep" --region "$AWS_REGION" 2>/dev/null || true
echo "" | aws s3 cp - "s3://studaxis-payloads/sync/.keep" --region "$AWS_REGION" 2>/dev/null || true

echo ""

# ============================================================================
# 3. Create IAM Roles for Lambda
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}3. Provisioning IAM Roles${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

create_lambda_role() {
    local role_name=$1
    local policy_document=$2
    
    if aws iam get-role --role-name "$role_name" &> /dev/null; then
        echo -e "${YELLOW}⚠ Role $role_name already exists${NC}"
    else
        echo -e "${GREEN}Creating role: $role_name${NC}"
        
        # Trust policy for Lambda
        TRUST_POLICY='{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }'
        
        aws iam create-role \
            --role-name "$role_name" \
            --assume-role-policy-document "$TRUST_POLICY" \
            --tags Key=Project,Value=Studaxis Key=Environment,Value="$ENV" \
            > /dev/null
        
        # Attach basic execution role
        aws iam attach-role-policy \
            --role-name "$role_name" \
            --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        
        # Attach custom policy if provided
        if [ -n "$policy_document" ]; then
            POLICY_NAME="${role_name}-policy"
            POLICY_ARN=$(aws iam create-policy \
                --policy-name "$POLICY_NAME" \
                --policy-document "$policy_document" \
                --query 'Policy.Arn' \
                --output text 2>/dev/null || echo "")
            
            if [ -n "$POLICY_ARN" ]; then
                aws iam attach-role-policy \
                    --role-name "$role_name" \
                    --policy-arn "$POLICY_ARN"
            fi
        fi
        
        echo -e "${GREEN}  ✓ Role $role_name created${NC}"
        sleep 10  # Wait for IAM propagation
    fi
}

# Offline Sync Role
OFFLINE_SYNC_POLICY='{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["dynamodb:PutItem", "dynamodb:UpdateItem"],
            "Resource": "arn:aws:dynamodb:'$AWS_REGION':'$ACCOUNT_ID':table/studaxis-student-sync"
        },
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject"],
            "Resource": "arn:aws:s3:::studaxis-payloads/sync/*"
        }
    ]
}'
create_lambda_role "studaxis-offline-sync-role-${ENV}" "$OFFLINE_SYNC_POLICY"

# Content Distribution Role
CONTENT_DIST_POLICY='{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"],
            "Resource": [
                "arn:aws:dynamodb:'$AWS_REGION':'$ACCOUNT_ID':table/studaxis-student-sync",
                "arn:aws:dynamodb:'$AWS_REGION':'$ACCOUNT_ID':table/studaxis-quiz-index"
            ]
        },
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject"],
            "Resource": "arn:aws:s3:::studaxis-payloads/*"
        }
    ]
}'
create_lambda_role "studaxis-content-2026-dist-role-${ENV}" "$CONTENT_DIST_POLICY"

# Quiz Generation Role
QUIZ_GEN_POLICY='{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["bedrock:InvokeModel"],
            "Resource": "arn:aws:bedrock:'$AWS_REGION'::foundation-model/*"
        },
        {
            "Effect": "Allow",
            "Action": ["s3:PutObject"],
            "Resource": "arn:aws:s3:::studaxis-payloads/quizzes/*"
        }
    ]
}'
create_lambda_role "studaxis-quiz-gen-role-${ENV}" "$QUIZ_GEN_POLICY"

# Class Manager Role
CLASS_MGR_POLICY='{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"],
            "Resource": "arn:aws:dynamodb:'$AWS_REGION':'$ACCOUNT_ID':table/studaxis-classes"
        }
    ]
}'
create_lambda_role "studaxis-class-manager-role-${ENV}" "$CLASS_MGR_POLICY"

# Teacher Auth Role
TEACHER_AUTH_POLICY='{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["dynamodb:GetItem"],
            "Resource": "arn:aws:dynamodb:'$AWS_REGION':'$ACCOUNT_ID':table/studaxis-teachers-'$ENV'"
        }
    ]
}'
create_lambda_role "studaxis-teacher-auth-${ENV}-sam" "$TEACHER_AUTH_POLICY"

echo ""

# ============================================================================
# 4. Deploy Lambda Functions (if SAM template exists)
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}4. Deploying Lambda Functions${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ -f "lambda/sam-template.yaml" ]; then
    if command -v sam &> /dev/null; then
        echo -e "${GREEN}Building Lambda functions with SAM...${NC}"
        cd lambda
        sam build --use-container 2>/dev/null || sam build
        
        echo -e "${GREEN}Deploying Lambda functions...${NC}"
        sam deploy \
            --stack-name "$STACK_NAME" \
            --region "$AWS_REGION" \
            --capabilities CAPABILITY_IAM \
            --parameter-overrides \
                Environment="$ENV" \
                ClassesTableName="studaxis-classes" \
                AssignmentsTableName="studaxis-assignments" \
                StudentSyncTableName="studaxis-student-sync" \
            --no-confirm-changeset \
            --no-fail-on-empty-changeset
        
        cd ..
        echo -e "${GREEN}✓ Lambda functions deployed${NC}"
    else
        echo -e "${YELLOW}⚠ SAM CLI not found. Skipping Lambda deployment.${NC}"
        echo "  Install SAM: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
    fi
else
    echo -e "${YELLOW}⚠ SAM template not found. Skipping Lambda deployment.${NC}"
    echo "  Create lambda/sam-template.yaml to enable automated deployment"
fi

echo ""

# ============================================================================
# 5. Create API Gateway (if not created by SAM)
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}5. Checking API Gateway${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

API_NAME="studaxis-teacher-api-${ENV}"
API_ID=$(aws apigateway get-rest-apis --region "$AWS_REGION" --query "items[?name=='$API_NAME'].id" --output text 2>/dev/null)

if [ -n "$API_ID" ]; then
    echo -e "${GREEN}✓ API Gateway exists: $API_NAME (ID: $API_ID)${NC}"
else
    echo -e "${YELLOW}⚠ API Gateway not found${NC}"
    echo "  API Gateway is typically created by SAM deployment"
    echo "  Run: cd lambda && sam deploy"
fi

echo ""

# ============================================================================
# 6. Configure AppSync (Manual Step)
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}6. AppSync Configuration${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "${YELLOW}⚠ AppSync API must be created manually${NC}"
echo ""
echo "Steps:"
echo "  1. Go to AWS AppSync Console"
echo "  2. Create API → 'Build from scratch'"
echo "  3. Name: studaxis-graphql-api"
echo "  4. Copy schema from: aws-infra/appsync/schema.graphql"
echo "  5. Create API key in Settings"
echo "  6. Configure resolvers for:"
echo "     - listStudentProgresses → Lambda: content_distribution"
echo "     - recordQuizAttempt → Lambda: offline_sync"
echo ""

# ============================================================================
# 7. Request Bedrock Model Access
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}7. Bedrock Model Access${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if aws bedrock list-foundation-models --region "$AWS_REGION" &> /dev/null; then
    echo -e "${GREEN}✓ Bedrock API access confirmed${NC}"
    
    # Check Nova model
    NOVA_MODELS=$(aws bedrock list-foundation-models --region "$AWS_REGION" --query "modelSummaries[?contains(modelId, 'nova')]" --output text 2>/dev/null)
    if [ -n "$NOVA_MODELS" ]; then
        echo -e "${GREEN}✓ Amazon Nova models available${NC}"
    else
        echo -e "${YELLOW}⚠ Amazon Nova models not accessible${NC}"
        echo "  Request access:"
        echo "  1. Go to AWS Bedrock Console"
        echo "  2. Model access → Request access"
        echo "  3. Select 'Amazon Nova' models"
        echo "  4. Wait ~5 minutes for approval"
    fi
else
    echo -e "${YELLOW}⚠ Bedrock API not accessible${NC}"
    echo "  Check IAM permissions for bedrock:ListFoundationModels"
fi

echo ""

# ============================================================================
# Summary
# ============================================================================
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                 Provisioning Complete                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Resources Created:"
echo "  ✓ 6 DynamoDB tables"
echo "  ✓ 3 S3 buckets"
echo "  ✓ 5 IAM roles"
echo "  ✓ Lambda functions (if SAM deployed)"
echo ""
echo "Manual Steps Required:"
echo "  1. Create AppSync API (see instructions above)"
echo "  2. Request Bedrock model access (if needed)"
echo "  3. Update environment variables:"
echo "     - teacher-dashboard-web/.env"
echo "     - backend/.env"
echo ""
echo "Next Steps:"
echo "  1. Run test script: ./test_aws_endpoints.sh"
echo "  2. Deploy Lambda functions: cd lambda && sam deploy"
echo "  3. Configure AppSync API"
echo "  4. Test integration: See QUICK_START guide"
echo ""
echo -e "${GREEN}✓ AWS infrastructure provisioned successfully!${NC}"

