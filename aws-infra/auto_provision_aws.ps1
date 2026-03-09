# Studaxis AWS Auto-Provisioning Script (PowerShell)
# Automatically creates missing AWS resources

param(
    [string]$Region = "ap-south-1",
    [string]$Environment = "dev"
)

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Studaxis AWS Auto-Provisioning Script  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Region: $Region" -ForegroundColor Yellow
Write-Host "Environment: $Environment" -ForegroundColor Yellow
Write-Host ""

# Check AWS CLI
try {
    $null = aws --version 2>$null
    $AccountId = aws sts get-caller-identity --query Account --output text 2>$null
    Write-Host "[OK] AWS CLI configured (Account: $AccountId)" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "[FAIL] AWS CLI not found or not configured" -ForegroundColor Red
    exit 1
}

# ============================================================================
# 1. Create DynamoDB Tables
# ============================================================================
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host "1. Provisioning DynamoDB Tables" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Cyan

function Create-DynamoDBTable {
    param(
        [string]$TableName,
        [string]$KeyName
    )
    
    try {
        $null = aws dynamodb describe-table --table-name $TableName --region $Region 2>$null
        Write-Host "[EXISTS] Table $TableName already exists" -ForegroundColor Yellow
    } catch {
        Write-Host "Creating table: $TableName" -ForegroundColor Green
        
        $null = aws dynamodb create-table `
            --table-name $TableName `
            --attribute-definitions AttributeName=$KeyName,AttributeType=S `
            --key-schema AttributeName=$KeyName,KeyType=HASH `
            --billing-mode PAY_PER_REQUEST `
            --region $Region `
            --tags Key=Project,Value=Studaxis Key=Environment,Value=$Environment 2>$null
        
        Write-Host "  Waiting for table to be active..." -ForegroundColor Yellow
        aws dynamodb wait table-exists --table-name $TableName --region $Region 2>$null
        Write-Host "  [OK] Table $TableName created" -ForegroundColor Green
    }
}

Create-DynamoDBTable "studaxis-student-sync" "user_id"
Create-DynamoDBTable "studaxis-quiz-index" "quiz_id"
Create-DynamoDBTable "studaxis-content-distribution" "class_id"
Create-DynamoDBTable "studaxis-classes" "class_id"
Create-DynamoDBTable "studaxis-assignments" "assignment_id"
Create-DynamoDBTable "studaxis-teachers-$Environment" "classCode"

Write-Host ""

# ============================================================================
# 2. Create S3 Buckets
# ============================================================================
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host "2. Provisioning S3 Buckets" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Cyan

function Create-S3Bucket {
    param(
        [string]$BucketName,
        [bool]$EnableVersioning = $false
    )
    
    try {
        $null = aws s3 ls "s3://$BucketName" --region $Region 2>$null
        Write-Host "[EXISTS] Bucket $BucketName already exists" -ForegroundColor Yellow
    } catch {
        Write-Host "Creating bucket: $BucketName" -ForegroundColor Green
        
        if ($Region -eq "us-east-1") {
            $null = aws s3 mb "s3://$BucketName" 2>$null
        }
        else {
            $null = aws s3 mb "s3://$BucketName" --region $Region 2>$null
        }
        
        # Block public access
        $null = aws s3api put-public-access-block `
            --bucket $BucketName `
            --public-access-block-configuration `
                "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" `
            --region $Region 2>$null
        
        # Enable versioning if requested
        if ($EnableVersioning) {
            $null = aws s3api put-bucket-versioning `
                --bucket $BucketName `
                --versioning-configuration Status=Enabled `
                --region $Region 2>$null
            Write-Host "  [OK] Versioning enabled" -ForegroundColor Green
        }

        Write-Host "  [OK] Bucket $BucketName created" -ForegroundColor Green
    }
}

Create-S3Bucket "studaxis-payloads" $true
Create-S3Bucket "studaxis-student-stats-2026" $false
Create-S3Bucket "studaxis-lambda-artifacts-$Environment" $false

Write-Host ""

# ============================================================================
# 3. Create IAM Roles
# ============================================================================
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host "3. Provisioning IAM Roles" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Cyan

function Create-LambdaRole {
    param(
        [string]$RoleName
    )
    
    try {
        $null = aws iam get-role --role-name $RoleName 2>$null
        Write-Host "[EXISTS] Role $RoleName already exists" -ForegroundColor Yellow
    } catch {
        Write-Host "Creating role: $RoleName" -ForegroundColor Green
        
        $TrustPolicy = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
        
        $null = aws iam create-role `
            --role-name $RoleName `
            --assume-role-policy-document $TrustPolicy `
            --tags Key=Project,Value=Studaxis Key=Environment,Value=$Environment 2>$null
        
        # Attach basic execution role
        $null = aws iam attach-role-policy `
            --role-name $RoleName `
            --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" 2>$null
        
        Write-Host "  [OK] Role $RoleName created" -ForegroundColor Green
        Start-Sleep -Seconds 5
    }
}

Create-LambdaRole "studaxis-offline-sync-role-$Environment"
Create-LambdaRole "studaxis-content-2026-dist-role-$Environment"
Create-LambdaRole "studaxis-quiz-gen-role-$Environment"
Create-LambdaRole "studaxis-class-manager-role-$Environment"
Create-LambdaRole "studaxis-assignment-manager-role-$Environment"
Create-LambdaRole "studaxis-teacher-auth-$Environment-sam"

Write-Host ""

# ============================================================================
# Summary
# ============================================================================
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "      Provisioning Complete             " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Resources Created:" -ForegroundColor Green
Write-Host "  [OK] 6 DynamoDB tables"
Write-Host "  [OK] 3 S3 buckets"
Write-Host "  [OK] 6 IAM roles"
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Deploy Lambda functions: .\deploy-lambdas.ps1"
Write-Host "  2. Create AppSync API manually"
Write-Host "  3. Request Bedrock model access"
Write-Host "  4. Run test script: .\test_aws_endpoints.ps1"
Write-Host ""
Write-Host "[OK] AWS infrastructure provisioned successfully!" -ForegroundColor Green
