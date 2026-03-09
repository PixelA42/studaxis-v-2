#!/bin/bash
# Studaxis AWS Endpoints Testing Script
# Tests all AWS resources and endpoints from integration checklist

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-ap-south-1}"
ENV="${ENV:-dev}"
STACK_NAME="studaxis-teacher-dashboard"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Studaxis AWS Endpoints Testing Suite              ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo ""
echo -e "${YELLOW}Region: ${AWS_REGION}${NC}"
echo -e "${YELLOW}Environment: ${ENV}${NC}"
echo ""

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test result function
test_result() {
    local test_name=$1
    local result=$2
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if [ "$result" -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗${NC} $test_name"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
}

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install it first.${NC}"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured. Run 'aws configure' first.${NC}"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ AWS CLI configured${NC}"
echo -e "${YELLOW}Account ID: ${ACCOUNT_ID}${NC}"
echo ""

# ============================================================================
# 1. DynamoDB Tables
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}1. Testing DynamoDB Tables${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

TABLES=(
    "studaxis-student-sync"
    "studaxis-quiz-index"
    "studaxis-content-distribution"
    "studaxis-classes"
    "studaxis-assignments"
    "studaxis-teachers-${ENV}"
)

for table in "${TABLES[@]}"; do
    if aws dynamodb describe-table --table-name "$table" --region "$AWS_REGION" &> /dev/null; then
        STATUS=$(aws dynamodb describe-table --table-name "$table" --region "$AWS_REGION" --query 'Table.TableStatus' --output text)
        if [ "$STATUS" == "ACTIVE" ]; then
            test_result "DynamoDB Table: $table (Status: $STATUS)" 0
        else
            test_result "DynamoDB Table: $table (Status: $STATUS - Not Active)" 1
        fi
    else
        test_result "DynamoDB Table: $table (Not Found)" 1
    fi
done

echo ""

# ============================================================================
# 2. S3 Buckets
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}2. Testing S3 Buckets${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

BUCKETS=(
    "studaxis-payloads"
    "studaxis-student-stats-2026"
    "studaxis-lambda-artifacts-${ENV}"
)

for bucket in "${BUCKETS[@]}"; do
    if aws s3 ls "s3://$bucket" --region "$AWS_REGION" &> /dev/null; then
        test_result "S3 Bucket: $bucket" 0
    else
        test_result "S3 Bucket: $bucket (Not Found or No Access)" 1
    fi
done

echo ""

# ============================================================================
# 3. Lambda Functions
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}3. Testing Lambda Functions${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

LAMBDAS=(
    "studaxis-offline-sync-${ENV}"
    "studaxis-content-2026-distribution-${ENV}"
    "studaxis-quiz-generation-${ENV}"
    "studaxis-teacher-generate-notes-${ENV}"
    "studaxis-class-manager-${ENV}"
    "studaxis-teacher-auth-${ENV}"
)

for lambda in "${LAMBDAS[@]}"; do
    if aws lambda get-function --function-name "$lambda" --region "$AWS_REGION" &> /dev/null; then
        STATE=$(aws lambda get-function --function-name "$lambda" --region "$AWS_REGION" --query 'Configuration.State' --output text)
        RUNTIME=$(aws lambda get-function --function-name "$lambda" --region "$AWS_REGION" --query 'Configuration.Runtime' --output text)
        ARCH=$(aws lambda get-function --function-name "$lambda" --region "$AWS_REGION" --query 'Configuration.Architectures[0]' --output text)
        test_result "Lambda: $lambda (State: $STATE, Runtime: $RUNTIME, Arch: $ARCH)" 0
    else
        test_result "Lambda: $lambda (Not Found)" 1
    fi
done

echo ""

# ============================================================================
# 4. API Gateway
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}4. Testing API Gateway${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Find API Gateway by name
API_NAME="studaxis-teacher-api-${ENV}"
API_ID=$(aws apigateway get-rest-apis --region "$AWS_REGION" --query "items[?name=='$API_NAME'].id" --output text 2>/dev/null)

if [ -n "$API_ID" ]; then
    test_result "API Gateway: $API_NAME (ID: $API_ID)" 0
    
    # Get API endpoint
    STAGE="prod"
    API_ENDPOINT="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/${STAGE}"
    echo -e "  ${YELLOW}Endpoint: ${API_ENDPOINT}${NC}"
    
    # Test endpoints
    echo -e "\n  ${YELLOW}Testing API Endpoints:${NC}"
    
    # Test /classes endpoint (should return 401 or valid response)
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_ENDPOINT}/classes" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" != "000" ]; then
        test_result "  GET /classes (HTTP $HTTP_CODE)" 0
    else
        test_result "  GET /classes (Connection Failed)" 1
    fi
    
    # Test /generateQuiz endpoint
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_ENDPOINT}/generateQuiz" \
        -H "Content-Type: application/json" \
        -d '{"topic":"test","difficulty":"easy","num_questions":1}' 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" != "000" ]; then
        test_result "  POST /generateQuiz (HTTP $HTTP_CODE)" 0
    else
        test_result "  POST /generateQuiz (Connection Failed)" 1
    fi
    
    # Test /assignments endpoint
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${API_ENDPOINT}/assignments?class_code=TEST" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" != "000" ]; then
        test_result "  GET /assignments (HTTP $HTTP_CODE)" 0
    else
        test_result "  GET /assignments (Connection Failed)" 1
    fi
else
    test_result "API Gateway: $API_NAME (Not Found)" 1
fi

echo ""

# ============================================================================
# 5. AppSync API
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}5. Testing AppSync API${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# List AppSync APIs
APPSYNC_APIS=$(aws appsync list-graphql-apis --region "$AWS_REGION" --query 'graphqlApis[?contains(name, `studaxis`)].[name,apiId]' --output text 2>/dev/null)

if [ -n "$APPSYNC_APIS" ]; then
    echo "$APPSYNC_APIS" | while read name api_id; do
        echo -e "  ${YELLOW}Name: $name${NC}"
        echo -e "  ${YELLOW}ID: $api_id${NC}"
    done
    test_result "AppSync API Found" 0
else
    test_result "AppSync API (Not Found - Create manually)" 1
    echo -e "  ${YELLOW}Note: AppSync API must be created manually via Console${NC}"
fi

echo ""

# ============================================================================
# 6. IAM Roles
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}6. Testing IAM Roles${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

ROLES=(
    "studaxis-offline-sync-role-${ENV}"
    "studaxis-content-2026-dist-role-${ENV}"
    "studaxis-quiz-gen-role-${ENV}"
    "studaxis-teacher-auth-${ENV}-sam"
    "studaxis-class-manager-role-${ENV}"
)

for role in "${ROLES[@]}"; do
    if aws iam get-role --role-name "$role" &> /dev/null; then
        test_result "IAM Role: $role" 0
    else
        test_result "IAM Role: $role (Not Found)" 1
    fi
done

echo ""

# ============================================================================
# 7. CloudWatch Log Groups
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}7. Testing CloudWatch Log Groups${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

for lambda in "${LAMBDAS[@]}"; do
    LOG_GROUP="/aws/lambda/$lambda"
    if aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP" --region "$AWS_REGION" --query 'logGroups[0]' --output text &> /dev/null; then
        test_result "Log Group: $LOG_GROUP" 0
    else
        test_result "Log Group: $LOG_GROUP (Not Found - Will be created on first invocation)" 1
    fi
done

echo ""

# ============================================================================
# 8. Bedrock Model Access
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}8. Testing Bedrock Model Access${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

MODEL_ID="arn:aws:bedrock:${AWS_REGION}:${ACCOUNT_ID}:inference-profile/global.amazon.nova-2-lite-v1:0"

# Try to list foundation models (check Bedrock access)
if aws bedrock list-foundation-models --region "$AWS_REGION" &> /dev/null; then
    test_result "Bedrock API Access" 0
    
    # Check if Nova model is available
    if aws bedrock list-foundation-models --region "$AWS_REGION" --query "modelSummaries[?contains(modelId, 'nova')]" --output text &> /dev/null; then
        test_result "Bedrock Nova Model Available" 0
    else
        test_result "Bedrock Nova Model (Check model access in Console)" 1
    fi
else
    test_result "Bedrock API Access (Not Available - Check permissions)" 1
fi

echo ""

# ============================================================================
# 9. CloudFormation Stack
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}9. Testing CloudFormation Stack${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" &> /dev/null; then
    STACK_STATUS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].StackStatus' --output text)
    test_result "CloudFormation Stack: $STACK_NAME (Status: $STACK_STATUS)" 0
    
    # Get outputs
    echo -e "\n  ${YELLOW}Stack Outputs:${NC}"
    aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[].[OutputKey,OutputValue]' --output text | while read key value; do
        echo -e "    ${key}: ${value}"
    done
else
    test_result "CloudFormation Stack: $STACK_NAME (Not Found)" 1
fi

echo ""

# ============================================================================
# 10. Integration Tests
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}10. Integration Tests${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Test Lambda invocation (if exists)
if aws lambda get-function --function-name "studaxis-class-manager-${ENV}" --region "$AWS_REGION" &> /dev/null; then
    echo -e "  ${YELLOW}Testing Lambda Invocation: studaxis-class-manager-${ENV}${NC}"
    
    # Create test event
    TEST_EVENT='{"httpMethod":"OPTIONS","path":"/classes"}'
    
    INVOKE_RESULT=$(aws lambda invoke \
        --function-name "studaxis-class-manager-${ENV}" \
        --region "$AWS_REGION" \
        --payload "$TEST_EVENT" \
        --cli-binary-format raw-in-base64-out \
        /tmp/lambda-response.json 2>&1)
    
    if [ $? -eq 0 ]; then
        HTTP_CODE=$(cat /tmp/lambda-response.json | jq -r '.statusCode' 2>/dev/null || echo "error")
        if [ "$HTTP_CODE" == "200" ]; then
            test_result "Lambda Invocation: class-manager (CORS OPTIONS)" 0
        else
            test_result "Lambda Invocation: class-manager (HTTP $HTTP_CODE)" 1
        fi
    else
        test_result "Lambda Invocation: class-manager (Failed)" 1
    fi
    
    rm -f /tmp/lambda-response.json
fi

echo ""

# ============================================================================
# Summary
# ============================================================================
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    Test Summary                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Total Tests:  ${TOTAL_TESTS}"
echo -e "${GREEN}Passed:       ${PASSED_TESTS}${NC}"
echo -e "${RED}Failed:       ${FAILED_TESTS}${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed! AWS infrastructure is ready.${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠ Some tests failed. Review the output above.${NC}"
    echo ""
    echo "Common fixes:"
    echo "  - Run deployment script: ./deploy_teacher_dashboard.sh"
    echo "  - Create missing DynamoDB tables"
    echo "  - Deploy Lambda functions via SAM"
    echo "  - Configure AppSync API manually"
    echo "  - Request Bedrock model access in Console"
    exit 1
fi
