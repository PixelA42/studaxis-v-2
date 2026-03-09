#!/bin/bash
# Studaxis Teacher Dashboard Deployment Script
# Deploys Lambda functions, creates DynamoDB tables, and sets up infrastructure

set -e

echo "🚀 Studaxis Teacher Dashboard Deployment"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-ap-south-1}"
STACK_NAME="studaxis-teacher-dashboard"
CLASSES_TABLE="studaxis-classes"
ASSIGNMENTS_TABLE="studaxis-assignments"
STUDENT_SYNC_TABLE="studaxis-student-sync"

echo -e "${YELLOW}Region: ${AWS_REGION}${NC}"
echo -e "${YELLOW}Stack: ${STACK_NAME}${NC}"
echo ""

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

echo -e "${GREEN}✓ AWS CLI configured${NC}"

# Step 1: Create DynamoDB Tables
echo ""
echo "📊 Step 1: Creating DynamoDB Tables"
echo "-----------------------------------"

create_table() {
    local table_name=$1
    local key_name=$2
    
    if aws dynamodb describe-table --table-name "$table_name" --region "$AWS_REGION" &> /dev/null; then
        echo -e "${YELLOW}⚠ Table $table_name already exists, skipping...${NC}"
    else
        echo "Creating table: $table_name"
        aws dynamodb create-table \
            --table-name "$table_name" \
            --attribute-definitions AttributeName="$key_name",AttributeType=S \
            --key-schema AttributeName="$key_name",KeyType=HASH \
            --billing-mode PAY_PER_REQUEST \
            --region "$AWS_REGION" \
            --tags Key=Project,Value=Studaxis Key=Environment,Value=Production \
            > /dev/null
        
        echo "Waiting for table to be active..."
        aws dynamodb wait table-exists --table-name "$table_name" --region "$AWS_REGION"
        echo -e "${GREEN}✓ Table $table_name created${NC}"
    fi
}

create_table "$CLASSES_TABLE" "class_id"
create_table "$ASSIGNMENTS_TABLE" "assignment_id"
create_table "$STUDENT_SYNC_TABLE" "user_id"

# Step 2: Deploy Lambda Functions
echo ""
echo "⚡ Step 2: Deploying Lambda Functions"
echo "------------------------------------"

cd lambda

if ! command -v sam &> /dev/null; then
    echo -e "${YELLOW}⚠ AWS SAM CLI not found. Skipping Lambda deployment.${NC}"
    echo "Install SAM CLI: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
else
    echo "Building Lambda functions..."
    sam build --use-container
    
    echo "Deploying Lambda functions..."
    sam deploy \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION" \
        --capabilities CAPABILITY_IAM \
        --parameter-overrides \
            ClassesTableName="$CLASSES_TABLE" \
            AssignmentsTableName="$ASSIGNMENTS_TABLE" \
            StudentSyncTableName="$STUDENT_SYNC_TABLE" \
        --no-confirm-changeset \
        --no-fail-on-empty-changeset
    
    echo -e "${GREEN}✓ Lambda functions deployed${NC}"
fi

cd ..

# Step 3: Get API Gateway URL
echo ""
echo "🌐 Step 3: Getting API Gateway URL"
echo "----------------------------------"

API_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")

if [ -n "$API_URL" ]; then
    echo -e "${GREEN}✓ API Gateway URL: $API_URL${NC}"
else
    echo -e "${YELLOW}⚠ Could not retrieve API Gateway URL${NC}"
fi

# Step 4: Deploy Teacher Dashboard Web App
echo ""
echo "🎨 Step 4: Building Teacher Dashboard"
echo "-------------------------------------"

cd teacher-dashboard-web

if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOF
VITE_API_GATEWAY_URL=$API_URL
VITE_APPSYNC_ENDPOINT=https://your-appsync-endpoint.appsync-api.$AWS_REGION.amazonaws.com/graphql
VITE_APPSYNC_API_KEY=your-api-key-here
VITE_TEACHER_BACKEND_URL=http://localhost:6782
EOF
    echo -e "${YELLOW}⚠ Created .env file. Please update VITE_APPSYNC_* values manually.${NC}"
fi

if command -v npm &> /dev/null; then
    echo "Installing dependencies..."
    npm install
    
    echo "Building React app..."
    npm run build
    
    echo -e "${GREEN}✓ Teacher dashboard built (dist/ folder)${NC}"
    echo ""
    echo "To deploy to Amplify:"
    echo "  1. Create Amplify app in AWS Console"
    echo "  2. Connect to your Git repository"
    echo "  3. Set build settings to use 'teacher-dashboard-web' as root"
    echo ""
    echo "Or deploy to S3:"
    echo "  aws s3 sync dist/ s3://your-bucket-name --delete"
else
    echo -e "${YELLOW}⚠ npm not found. Skipping build.${NC}"
fi

cd ..

# Step 5: Summary
echo ""
echo "✅ Deployment Complete!"
echo "======================"
echo ""
echo "Next Steps:"
echo "1. Update teacher-dashboard-web/.env with AppSync endpoint and API key"
echo "2. Deploy teacher dashboard to Amplify or S3"
echo "3. Update backend/.env with API Gateway URL"
echo "4. Test the integration:"
echo "   - Create a class in teacher dashboard"
echo "   - Generate a quiz using Bedrock"
echo "   - Assign quiz to class"
echo "   - Have student join class and sync"
echo ""
echo "Resources Created:"
echo "  - DynamoDB Tables: $CLASSES_TABLE, $ASSIGNMENTS_TABLE, $STUDENT_SYNC_TABLE"
echo "  - Lambda Functions: class_manager, quiz_generation, assignment_manager, offline_sync"
if [ -n "$API_URL" ]; then
    echo "  - API Gateway: $API_URL"
fi
echo ""
echo "Documentation: project_docs/TEACHER_DASHBOARD_INTEGRATION.md"
echo ""
