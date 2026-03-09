# ═══════════════════════════════════════════════════════════════════════════
# Studaxis Lambda Manual Deployment Script (PowerShell)
# ═══════════════════════════════════════════════════════════════════════════
# Purpose: Deploy missing Lambda functions individually using AWS CLI
# Region: ap-south-1
# Environment: dev
# Account: 718980965213
# ═══════════════════════════════════════════════════════════════════════════

$ErrorActionPreference = "Continue"
$REGION = "ap-south-1"
$ACCOUNT_ID = "718980965213"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Studaxis Lambda Deployment Script   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Region: $REGION" -ForegroundColor Yellow
Write-Host "Account: $ACCOUNT_ID" -ForegroundColor Yellow
Write-Host ""

# Navigate to lambda directory
Set-Location lambda

# ═══════════════════════════════════════════════════════════════════════════
# Step 1: Create Deployment Packages
# ═══════════════════════════════════════════════════════════════════════════

Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host "1. Creating Deployment Packages" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host ""

# Teacher Auth
Write-Host "  -> Packaging teacher_auth..." -ForegroundColor White
if (Test-Path "teacher_auth.zip") { Remove-Item "teacher_auth.zip" -Force }
Compress-Archive -Path "teacher_auth\*" -DestinationPath "teacher_auth.zip" -Force
$size = [math]::Round((Get-Item "teacher_auth.zip").Length / 1KB, 2)
Write-Host "    [OK] Created teacher_auth.zip ($($size) KB)" -ForegroundColor Green

# Class Manager
Write-Host "  -> Packaging class_manager..." -ForegroundColor White
if (Test-Path "class_manager.zip") { Remove-Item "class_manager.zip" -Force }
Compress-Archive -Path "class_manager\*" -DestinationPath "class_manager.zip" -Force
$size = [math]::Round((Get-Item "class_manager.zip").Length / 1KB, 2)
Write-Host "    [OK] Created class_manager.zip ($($size) KB)" -ForegroundColor Green

# Teacher Generate Notes
Write-Host "  -> Packaging teacher_generate_notes..." -ForegroundColor White
if (Test-Path "teacher_generate_notes.zip") { Remove-Item "teacher_generate_notes.zip" -Force }
Compress-Archive -Path "teacher_generate_notes\*" -DestinationPath "teacher_generate_notes.zip" -Force
$size = [math]::Round((Get-Item "teacher_generate_notes.zip").Length / 1KB, 2)
Write-Host "    [OK] Created teacher_generate_notes.zip ($($size) KB)" -ForegroundColor Green

# Assignment Manager
Write-Host "  -> Packaging assignment_manager..." -ForegroundColor White
if (Test-Path "assignment_manager.zip") { Remove-Item "assignment_manager.zip" -Force }
Compress-Archive -Path "assignment_manager\*" -DestinationPath "assignment_manager.zip" -Force
$size = [math]::Round((Get-Item "assignment_manager.zip").Length / 1KB, 2)
Write-Host "    [OK] Created assignment_manager.zip ($($size) KB)" -ForegroundColor Green

Write-Host ""

# ═══════════════════════════════════════════════════════════════════════════
# Step 2: Deploy Lambda Functions
# ═══════════════════════════════════════════════════════════════════════════

Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host "2. Deploying Lambda Functions" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host ""

# -----------------------------------------------------------------
# Lambda 1: Teacher Auth
# -----------------------------------------------------------------

Write-Host "  [1/4] Deploying studaxis-teacher-auth-dev..." -ForegroundColor Yellow

# Check if function exists
$functionExists = $false
try {
    aws lambda get-function --function-name studaxis-teacher-auth-dev --region $REGION 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $functionExists = $true
        Write-Host "        Function already exists, updating code..." -ForegroundColor Yellow
        
        aws lambda update-function-code `
            --function-name studaxis-teacher-auth-dev `
            --zip-file fileb://teacher_auth.zip `
            --region $REGION `
            --architectures arm64 `
            --output json | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "        [OK] Code updated successfully" -ForegroundColor Green
        } else {
            Write-Host "        [FAIL] Code update failed" -ForegroundColor Red
        }
    }
} catch {
    $functionExists = $false
}

if (-not $functionExists) {
    Write-Host "        Creating new function..." -ForegroundColor Yellow

    $envVars = "Variables={LOG_LEVEL=INFO,TEACHERS_TABLE_NAME=studaxis-teachers-dev,STUDAXIS_JWT_SECRET=studaxis-dev-secret-change-in-prod}"
    aws lambda create-function `
        --function-name studaxis-teacher-auth-dev `
        --runtime python3.11 `
        --role "arn:aws:iam::${ACCOUNT_ID}:role/studaxis-teacher-auth-dev-sam" `
        --handler handler.lambda_handler `
        --zip-file fileb://teacher_auth.zip `
        --timeout 10 `
        --memory-size 256 `
        --architectures arm64 `
        --environment $envVars `
        --region $REGION `
        --output json | Out-Null

    if ($LASTEXITCODE -eq 0) {
        Write-Host "        [OK] Function created successfully" -ForegroundColor Green
    } else {
        Write-Host "        [FAIL] Function creation failed" -ForegroundColor Red
    }
}

Write-Host ""

# ─────────────────────────────────────────────────────────────────────────
# Lambda 2: Class Manager
# ─────────────────────────────────────────────────────────────────────────

Write-Host "  [2/4] Deploying studaxis-class-manager-dev..." -ForegroundColor Yellow

# Check if function exists
$functionExists = $false
try {
    aws lambda get-function --function-name studaxis-class-manager-dev --region $REGION 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $functionExists = $true
        Write-Host "        Function already exists, updating code..." -ForegroundColor Yellow
        
        aws lambda update-function-code `
            --function-name studaxis-class-manager-dev `
            --zip-file fileb://class_manager.zip `
            --region $REGION `
            --architectures arm64 `
            --output json | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "        [OK] Code updated successfully" -ForegroundColor Green
        } else {
            Write-Host "        [FAIL] Code update failed" -ForegroundColor Red
        }
    }
} catch {
    $functionExists = $false
}

if (-not $functionExists) {
    Write-Host "        Creating new function..." -ForegroundColor Yellow

    $envVars = "Variables={LOG_LEVEL=INFO,CLASSES_TABLE_NAME=studaxis-classes}"
    aws lambda create-function `
        --function-name studaxis-class-manager-dev `
        --runtime python3.11 `
        --role "arn:aws:iam::${ACCOUNT_ID}:role/studaxis-class-manager-role-dev" `
        --handler handler.lambda_handler `
        --zip-file fileb://class_manager.zip `
        --timeout 15 `
        --memory-size 256 `
        --architectures arm64 `
        --environment $envVars `
        --region $REGION `
        --output json | Out-Null

    if ($LASTEXITCODE -eq 0) {
        Write-Host "        [OK] Function created successfully" -ForegroundColor Green
    } else {
        Write-Host "        [FAIL] Function creation failed" -ForegroundColor Red
    }
}

Write-Host ""

# ─────────────────────────────────────────────────────────────────────────
# Lambda 3: Teacher Generate Notes
# ─────────────────────────────────────────────────────────────────────────

Write-Host "  [3/4] Deploying studaxis-teacher-generate-notes-dev..." -ForegroundColor Yellow

# Check if function exists
$functionExists = $false
try {
    aws lambda get-function --function-name studaxis-teacher-generate-notes-dev --region $REGION 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $functionExists = $true
        Write-Host "        Function already exists, updating code..." -ForegroundColor Yellow
        
        aws lambda update-function-code `
            --function-name studaxis-teacher-generate-notes-dev `
            --zip-file fileb://teacher_generate_notes.zip `
            --region $REGION `
            --architectures arm64 `
            --output json | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "        [OK] Code updated successfully" -ForegroundColor Green
        } else {
            Write-Host "        [FAIL] Code update failed" -ForegroundColor Red
        }
    }
} catch {
    $functionExists = $false
}

if (-not $functionExists) {
    Write-Host "        Creating new function..." -ForegroundColor Yellow
    
    # First, create the IAM role if it doesn't exist
    $roleExists = $false
    try {
        aws iam get-role --role-name studaxis-teacher-generate-notes-role-dev --region $REGION 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $roleExists = $true
        }
    } catch {
        $roleExists = $false
    }
    
    if (-not $roleExists) {
        Write-Host "        Creating IAM role..." -ForegroundColor Yellow

        # Write trust policy to file (ASCII to avoid BOM; AWS rejects BOM in JSON)
        $trustPolicy = @'
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
'@
        [System.IO.File]::WriteAllText("$PWD\trust-policy.json", $trustPolicy, [System.Text.UTF8Encoding]::new($false))

        aws iam create-role `
            --role-name studaxis-teacher-generate-notes-role-dev `
            --assume-role-policy-document file://trust-policy.json `
            --region $REGION `
            --output json | Out-Null

        # Attach basic execution policy
        aws iam attach-role-policy `
            --role-name studaxis-teacher-generate-notes-role-dev `
            --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" `
            --region $REGION

        # Inline policy for Bedrock, S3, DynamoDB (write file without BOM)
        $inlinePolicyJson = @"
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
"@
        [System.IO.File]::WriteAllText("$PWD\inline-policy.json", $inlinePolicyJson, [System.Text.UTF8Encoding]::new($false))

        aws iam put-role-policy `
            --role-name studaxis-teacher-generate-notes-role-dev `
            --policy-name BedrockS3DynamoDBAccess `
            --policy-document file://inline-policy.json `
            --region $REGION
        
        Write-Host "        [OK] IAM role created" -ForegroundColor Green
        
        # Wait for role to propagate
        Write-Host "        Waiting 10 seconds for IAM role to propagate..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
    }
    
    $envNotes = "Variables={LOG_LEVEL=INFO,S3_BUCKET_NAME=studaxis-payloads,CONTENT_DISTRIBUTION_TABLE=studaxis-content-distribution,BEDROCK_REGION=ap-south-1,BEDROCK_MODEL_ID=arn:aws:bedrock:ap-south-1:718980965213:inference-profile/global.amazon.nova-2-lite-v1:0,PRESIGNED_URL_EXPIRY_SECONDS=86400}"
    aws lambda create-function `
        --function-name studaxis-teacher-generate-notes-dev `
        --runtime python3.11 `
        --role "arn:aws:iam::${ACCOUNT_ID}:role/studaxis-teacher-generate-notes-role-dev" `
        --handler handler.lambda_handler `
        --zip-file fileb://teacher_generate_notes.zip `
        --timeout 60 `
        --memory-size 512 `
        --architectures arm64 `
        --environment $envNotes `
        --region $REGION `
        --output json | Out-Null

    if ($LASTEXITCODE -eq 0) {
        Write-Host "        [OK] Function created successfully" -ForegroundColor Green
    } else {
        Write-Host "        [FAIL] Function creation failed" -ForegroundColor Red
    }
}

Write-Host ""

# -----------------------------------------------------------------
# Lambda 4: Assignment Manager
# -----------------------------------------------------------------

Write-Host "  [4/4] Deploying studaxis-assignment-manager-dev..." -ForegroundColor Yellow

$functionExists = $false
try {
    aws lambda get-function --function-name studaxis-assignment-manager-dev --region $REGION 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $functionExists = $true
        Write-Host "        Function already exists, updating code..." -ForegroundColor Yellow
        
        aws lambda update-function-code `
            --function-name studaxis-assignment-manager-dev `
            --zip-file fileb://assignment_manager.zip `
            --region $REGION `
            --architectures arm64 `
            --output json | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "        [OK] Code updated successfully" -ForegroundColor Green
        } else {
            Write-Host "        [FAIL] Code update failed" -ForegroundColor Red
        }
    }
} catch {
    $functionExists = $false
}

if (-not $functionExists) {
    Write-Host "        Creating new function..." -ForegroundColor Yellow
    # Ensure role exists (create if missing, with DynamoDB access to studaxis-assignments)
    $roleExists = $false
    try {
        aws iam get-role --role-name studaxis-assignment-manager-role-dev 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { $roleExists = $true }
    } catch { $roleExists = $false }
    if (-not $roleExists) {
        Write-Host "        Creating IAM role studaxis-assignment-manager-role-dev..." -ForegroundColor Yellow
        # Write trust policy to file (UTF-8 no BOM so AWS accepts the JSON)
        $trustPolicy = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
        [System.IO.File]::WriteAllText("$PWD\assignment-manager-trust.json", $trustPolicy, [System.Text.UTF8Encoding]::new($false))
        aws iam create-role --role-name studaxis-assignment-manager-role-dev --assume-role-policy-document file://assignment-manager-trust.json --region $REGION | Out-Null
        Remove-Item "assignment-manager-trust.json" -Force -ErrorAction SilentlyContinue

        aws iam attach-role-policy --role-name studaxis-assignment-manager-role-dev --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" --region $REGION | Out-Null

        $dynamoPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:Scan",
        "dynamodb:Query",
        "dynamodb:DeleteItem"
      ],
      "Resource": "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/studaxis-assignments*"
    }
  ]
}
"@
        [System.IO.File]::WriteAllText("$PWD\assignment-manager-dynamo-policy.json", $dynamoPolicy, [System.Text.UTF8Encoding]::new($false))
        aws iam put-role-policy --role-name studaxis-assignment-manager-role-dev --policy-name DynamoDBAssignments --policy-document file://assignment-manager-dynamo-policy.json --region $REGION | Out-Null
        Remove-Item "assignment-manager-dynamo-policy.json" -Force -ErrorAction SilentlyContinue
        Write-Host "        [OK] Role created" -ForegroundColor Green
        Start-Sleep -Seconds 10
    }
    $envAssign = "Variables={LOG_LEVEL=INFO,ASSIGNMENTS_TABLE_NAME=studaxis-assignments}"
    aws lambda create-function `
        --function-name studaxis-assignment-manager-dev `
        --runtime python3.11 `
        --role "arn:aws:iam::${ACCOUNT_ID}:role/studaxis-assignment-manager-role-dev" `
        --handler handler.lambda_handler `
        --zip-file fileb://assignment_manager.zip `
        --timeout 15 `
        --memory-size 256 `
        --architectures arm64 `
        --environment $envAssign `
        --region $REGION `
        --output json | Out-Null

    if ($LASTEXITCODE -eq 0) {
        Write-Host "        [OK] Function created successfully" -ForegroundColor Green
    } else {
        Write-Host "        [FAIL] Function creation failed (ensure role studaxis-assignment-manager-role-dev exists)" -ForegroundColor Red
    }
}

Write-Host ""

# ═══════════════════════════════════════════════════════════════════════════
# Step 3: Update content-distribution-dev (rename from content-2026)
# ═══════════════════════════════════════════════════════════════════════════

Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host "3. Updating Existing Content Distribution Lambda" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host ""

Write-Host "  -> Packaging content_distribution..." -ForegroundColor White
if (Test-Path "content_distribution.zip") { Remove-Item "content_distribution.zip" -Force }
Compress-Archive -Path "content_distribution\*" -DestinationPath "content_distribution.zip" -Force
$size = [math]::Round((Get-Item "content_distribution.zip").Length / 1KB, 2)
Write-Host "    [OK] Created content_distribution.zip ($($size) KB)" -ForegroundColor Green

Write-Host "  -> Updating studaxis-content-distribution-dev..." -ForegroundColor Yellow

aws lambda update-function-code `
    --function-name studaxis-content-distribution-dev `
    --zip-file fileb://content_distribution.zip `
    --region $REGION `
    --architectures arm64 `
    --output json | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "    [OK] Code updated successfully" -ForegroundColor Green
} else {
    Write-Host "    [FAIL] Code update failed" -ForegroundColor Red
}

Write-Host ""

# -----------------------------------------------------------------
# Step 4: Connect Lambda to API Gateway
# -----------------------------------------------------------------

Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host "4. Connecting Lambda Functions to API Gateway" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host ""

$API_ID = "yjyn9jsugc"

Write-Host "  API Gateway ID: $API_ID" -ForegroundColor White
Write-Host "  Endpoint: https://$API_ID.execute-api.$REGION.amazonaws.com/prod" -ForegroundColor White
Write-Host ""
Write-Host "  [WARN] Manual steps required in AWS Console:" -ForegroundColor Yellow
Write-Host "    1. Go to API Gateway -> $API_ID" -ForegroundColor White
Write-Host "    2. Create resources and methods:" -ForegroundColor White
Write-Host "       - POST /auth -> studaxis-teacher-auth-dev" -ForegroundColor White
Write-Host "       - GET/POST /classes -> studaxis-class-manager-dev" -ForegroundColor White
Write-Host "       - POST /generateQuiz -> studaxis-quiz-generation-dev" -ForegroundColor White
Write-Host "       - GET/POST /assignments, DELETE /assignments/{id} -> studaxis-assignment-manager-dev" -ForegroundColor White
Write-Host "       - POST /teacher/generateNotes -> studaxis-teacher-generate-notes-dev" -ForegroundColor White
Write-Host "    3. Deploy API to 'dev' stage" -ForegroundColor White
Write-Host ""

# -----------------------------------------------------------------
# Step 5: Verification
# -----------------------------------------------------------------

Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host "5. Verification" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Cyan
Write-Host ""

Write-Host "  Checking deployed Lambda functions..." -ForegroundColor White
Write-Host ""

$functions = @(
    "studaxis-teacher-auth-dev",
    "studaxis-class-manager-dev",
    "studaxis-teacher-generate-notes-dev",
    "studaxis-assignment-manager-dev",
    "studaxis-content-distribution-dev"
)

foreach ($func in $functions) {
    try {
        $result = aws lambda get-function --function-name $func --region $REGION --query 'Configuration.[State,Runtime,MemorySize]' --output text 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    [OK] $func" -ForegroundColor Green
            Write-Host "      $result" -ForegroundColor Gray
        } else {
            Write-Host "    [FAIL] $func (not found)" -ForegroundColor Red
        }
    } catch {
        Write-Host "    [FAIL] $func (error)" -ForegroundColor Red
    }
}

Write-Host ""

# ═══════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════

Write-Host "========================================" -ForegroundColor Green
Write-Host "         Deployment Complete            " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Run test script: ..\test_resources.ps1" -ForegroundColor White
Write-Host "  2. Configure API Gateway endpoints (see Step 4 above)" -ForegroundColor White
Write-Host "  3. Create AppSync API (see aws-infra/GET_API_KEY.md)" -ForegroundColor White
Write-Host "  4. Update environment variables in:" -ForegroundColor White
Write-Host "     - teacher-dashboard-web/.env" -ForegroundColor White
Write-Host "     - backend/.env" -ForegroundColor White
Write-Host ""

# Return to original directory
Set-Location ..
