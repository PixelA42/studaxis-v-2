# Studaxis Lambda Deployment Script (Simple Version)
# Run from: aws-infra directory

$ErrorActionPreference = "Continue"
$REGION = "ap-south-1"
$ACCOUNT_ID = "718980965213"

Write-Host "=== Studaxis Lambda Deployment ===" -ForegroundColor Cyan
Write-Host "Region: $REGION" -ForegroundColor Yellow
Write-Host "Account: $ACCOUNT_ID" -ForegroundColor Yellow
Write-Host ""

# Navigate to lambda directory
Set-Location lambda

# Step 1: Create ZIP packages
Write-Host "Step 1: Creating deployment packages..." -ForegroundColor Cyan
Write-Host ""

if (Test-Path "teacher_auth.zip") { Remove-Item "teacher_auth.zip" -Force }
Compress-Archive -Path "teacher_auth\*" -DestinationPath "teacher_auth.zip" -Force
Write-Host "  Created teacher_auth.zip" -ForegroundColor Green

if (Test-Path "class_manager.zip") { Remove-Item "class_manager.zip" -Force }
Compress-Archive -Path "class_manager\*" -DestinationPath "class_manager.zip" -Force
Write-Host "  Created class_manager.zip" -ForegroundColor Green

if (Test-Path "teacher_generate_notes.zip") { Remove-Item "teacher_generate_notes.zip" -Force }
Compress-Archive -Path "teacher_generate_notes\*" -DestinationPath "teacher_generate_notes.zip" -Force
Write-Host "  Created teacher_generate_notes.zip" -ForegroundColor Green

if (Test-Path "content_distribution.zip") { Remove-Item "content_distribution.zip" -Force }
Compress-Archive -Path "content_distribution\*" -DestinationPath "content_distribution.zip" -Force
Write-Host "  Created content_distribution.zip" -ForegroundColor Green

Write-Host ""

# Step 2: Deploy Lambda functions
Write-Host "Step 2: Deploying Lambda functions..." -ForegroundColor Cyan
Write-Host ""

# Lambda 1: Teacher Auth
Write-Host "[1/4] Deploying studaxis-teacher-auth-dev..." -ForegroundColor Yellow

$checkAuth = aws lambda get-function --function-name studaxis-teacher-auth-dev --region $REGION 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Function exists, updating code..." -ForegroundColor Yellow
    aws lambda update-function-code `
        --function-name studaxis-teacher-auth-dev `
        --zip-file fileb://teacher_auth.zip `
        --region $REGION `
        --output json | Out-Null
    Write-Host "  Updated successfully" -ForegroundColor Green
} else {
    Write-Host "  Creating new function..." -ForegroundColor Yellow
    aws lambda create-function `
        --function-name studaxis-teacher-auth-dev `
        --runtime python3.11 `
        --role "arn:aws:iam::${ACCOUNT_ID}:role/studaxis-teacher-auth-dev-sam" `
        --handler handler.lambda_handler `
        --zip-file fileb://teacher_auth.zip `
        --timeout 10 `
        --memory-size 256 `
        --architectures arm64 `
        --environment '{\"Variables\":{\"LOG_LEVEL\":\"INFO\",\"TEACHERS_TABLE_NAME\":\"studaxis-teachers-dev\",\"STUDAXIS_JWT_SECRET\":\"studaxis-dev-secret-change-in-prod\"}}' `
        --region $REGION `
        --output json | Out-Null
    Write-Host "  Created successfully" -ForegroundColor Green
}

Write-Host ""

# Lambda 2: Class Manager
Write-Host "[2/4] Deploying studaxis-class-manager-dev..." -ForegroundColor Yellow

$checkClass = aws lambda get-function --function-name studaxis-class-manager-dev --region $REGION 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Function exists, updating code..." -ForegroundColor Yellow
    aws lambda update-function-code `
        --function-name studaxis-class-manager-dev `
        --zip-file fileb://class_manager.zip `
        --region $REGION `
        --output json | Out-Null
    Write-Host "  Updated successfully" -ForegroundColor Green
} else {
    Write-Host "  Creating new function..." -ForegroundColor Yellow
    aws lambda create-function `
        --function-name studaxis-class-manager-dev `
        --runtime python3.11 `
        --role "arn:aws:iam::${ACCOUNT_ID}:role/studaxis-class-manager-role-dev" `
        --handler handler.lambda_handler `
        --zip-file fileb://class_manager.zip `
        --timeout 15 `
        --memory-size 256 `
        --architectures arm64 `
        --environment '{\"Variables\":{\"LOG_LEVEL\":\"INFO\",\"CLASSES_TABLE_NAME\":\"studaxis-classes\"}}' `
        --region $REGION `
        --output json | Out-Null
    Write-Host "  Created successfully" -ForegroundColor Green
}

Write-Host ""

# Lambda 3: Teacher Generate Notes
Write-Host "[3/4] Deploying studaxis-teacher-generate-notes-dev..." -ForegroundColor Yellow

# Check if IAM role exists
$checkRole = aws iam get-role --role-name studaxis-teacher-generate-notes-role-dev 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Creating IAM role..." -ForegroundColor Yellow
    
    # Create trust policy file
    @'
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
'@ | Out-File -FilePath "trust-policy.json" -Encoding utf8
    
    aws iam create-role `
        --role-name studaxis-teacher-generate-notes-role-dev `
        --assume-role-policy-document file://trust-policy.json `
        --output json | Out-Null
    
    aws iam attach-role-policy `
        --role-name studaxis-teacher-generate-notes-role-dev `
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    
    # Create inline policy file
    @'
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
      "Resource": "arn:aws:dynamodb:ap-south-1:718980965213:table/studaxis-content-distribution"
    }
  ]
}
'@ | Out-File -FilePath "inline-policy.json" -Encoding utf8
    
    aws iam put-role-policy `
        --role-name studaxis-teacher-generate-notes-role-dev `
        --policy-name BedrockS3DynamoDBAccess `
        --policy-document file://inline-policy.json
    
    Write-Host "  IAM role created, waiting 10 seconds..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
}

$checkNotes = aws lambda get-function --function-name studaxis-teacher-generate-notes-dev --region $REGION 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Function exists, updating code..." -ForegroundColor Yellow
    aws lambda update-function-code `
        --function-name studaxis-teacher-generate-notes-dev `
        --zip-file fileb://teacher_generate_notes.zip `
        --region $REGION `
        --output json | Out-Null
    Write-Host "  Updated successfully" -ForegroundColor Green
} else {
    Write-Host "  Creating new function..." -ForegroundColor Yellow
    aws lambda create-function `
        --function-name studaxis-teacher-generate-notes-dev `
        --runtime python3.11 `
        --role "arn:aws:iam::${ACCOUNT_ID}:role/studaxis-teacher-generate-notes-role-dev" `
        --handler handler.lambda_handler `
        --zip-file fileb://teacher_generate_notes.zip `
        --timeout 60 `
        --memory-size 512 `
        --architectures arm64 `
        --environment '{\"Variables\":{\"LOG_LEVEL\":\"INFO\",\"S3_BUCKET_NAME\":\"studaxis-payloads\",\"CONTENT_DISTRIBUTION_TABLE\":\"studaxis-content-distribution\",\"BEDROCK_REGION\":\"ap-south-1\",\"BEDROCK_MODEL_ID\":\"arn:aws:bedrock:ap-south-1:718980965213:inference-profile/global.amazon.nova-2-lite-v1:0\",\"PRESIGNED_URL_EXPIRY_SECONDS\":\"86400\"}}' `
        --region $REGION `
        --output json | Out-Null
    Write-Host "  Created successfully" -ForegroundColor Green
}

Write-Host ""

# Lambda 4: Update Content Distribution
Write-Host "[4/4] Updating studaxis-content-distribution-dev..." -ForegroundColor Yellow

aws lambda update-function-code `
    --function-name studaxis-content-distribution-dev `
    --zip-file fileb://content_distribution.zip `
    --region $REGION `
    --output json | Out-Null
Write-Host "  Updated successfully" -ForegroundColor Green

Write-Host ""

# Step 3: Verification
Write-Host "Step 3: Verifying deployments..." -ForegroundColor Cyan
Write-Host ""

$functions = @(
    "studaxis-teacher-auth-dev",
    "studaxis-class-manager-dev",
    "studaxis-teacher-generate-notes-dev",
    "studaxis-content-distribution-dev"
)

foreach ($func in $functions) {
    $check = aws lambda get-function --function-name $func --region $REGION 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK: $func" -ForegroundColor Green
    } else {
        Write-Host "  FAIL: $func" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Run: ..\test_resources.ps1" -ForegroundColor White
Write-Host "  2. Configure API Gateway endpoints" -ForegroundColor White
Write-Host "  3. Create AppSync API" -ForegroundColor White
Write-Host ""

# Return to original directory
Set-Location ..
