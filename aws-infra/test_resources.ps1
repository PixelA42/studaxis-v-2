# Studaxis AWS Resources Test Script
param(
    [string]$Region = "ap-south-1",
    [string]$Environment = "dev"
)

$TotalTests = 0
$PassedTests = 0
$FailedTests = 0

function Test-Resource {
    param([string]$Name, [bool]$Exists)
    $script:TotalTests++
    if ($Exists) {
        Write-Host "[PASS] $Name" -ForegroundColor Green
        $script:PassedTests++
    } else {
        Write-Host "[FAIL] $Name" -ForegroundColor Red
        $script:FailedTests++
    }
}

Write-Host "Studaxis AWS Resources Test" -ForegroundColor Cyan
Write-Host "Region: $Region" -ForegroundColor Yellow
Write-Host "Environment: $Environment" -ForegroundColor Yellow
Write-Host ""

# Test DynamoDB Tables
Write-Host "Testing DynamoDB Tables..." -ForegroundColor Cyan

$tables = @(
    "studaxis-student-sync",
    "studaxis-quiz-index",
    "studaxis-content-distribution",
    "studaxis-classes",
    "studaxis-assignments",
    "studaxis-teachers-$Environment"
)

foreach ($table in $tables) {
    try {
        $status = aws dynamodb describe-table --table-name $table --region $Region --query 'Table.TableStatus' --output text 2>$null
        Test-Resource "DynamoDB: $table" ($status -eq "ACTIVE")
    }
    catch {
        Test-Resource "DynamoDB: $table" $false
    }
}

Write-Host ""

# Test S3 Buckets
Write-Host "Testing S3 Buckets..." -ForegroundColor Cyan

$buckets = @(
    "studaxis-payloads",
    "studaxis-student-stats-2026",
    "studaxis-lambda-artifacts-$Environment"
)

foreach ($bucket in $buckets) {
    try {
        $null = aws s3 ls "s3://$bucket" --region $Region 2>$null
        Test-Resource "S3: $bucket" $true
    }
    catch {
        Test-Resource "S3: $bucket" $false
    }
}

Write-Host ""

# Test Lambda Functions
Write-Host "Testing Lambda Functions..." -ForegroundColor Cyan

$lambdas = @(
    "studaxis-offline-sync-$Environment",
    "studaxis-content-2026-distribution-$Environment",
    "studaxis-quiz-generation-$Environment",
    "studaxis-teacher-generate-notes-$Environment",
    "studaxis-class-manager-$Environment",
    "studaxis-teacher-auth-$Environment"
)

foreach ($lambda in $lambdas) {
    try {
        $state = aws lambda get-function --function-name $lambda --region $Region --query 'Configuration.State' --output text 2>$null
        Test-Resource "Lambda: $lambda" ($state -eq "Active")
    }
    catch {
        Test-Resource "Lambda: $lambda" $false
    }
}

Write-Host ""

# Test API Gateway
Write-Host "Testing API Gateway..." -ForegroundColor Cyan

$apiName = "studaxis-teacher-api-$Environment"
try {
    $apiId = aws apigateway get-rest-apis --region $Region --query "items[?name=='$apiName'].id" --output text 2>$null
    if ($apiId) {
        Test-Resource "API Gateway: $apiName" $true
        Write-Host "  Endpoint: https://$apiId.execute-api.$Region.amazonaws.com/prod" -ForegroundColor Yellow
    } else {
        Test-Resource "API Gateway: $apiName" $false
    }
}
catch {
    Test-Resource "API Gateway: $apiName" $false
}

Write-Host ""

# Test IAM Roles
Write-Host "Testing IAM Roles..." -ForegroundColor Cyan

$roles = @(
    "studaxis-offline-sync-role-$Environment",
    "studaxis-content-2026-dist-role-$Environment",
    "studaxis-quiz-gen-role-$Environment",
    "studaxis-class-manager-role-$Environment",
    "studaxis-teacher-auth-$Environment-sam"
)

foreach ($role in $roles) {
    try {
        $null = aws iam get-role --role-name $role 2>$null
        Test-Resource "IAM Role: $role" $true
    }
    catch {
        Test-Resource "IAM Role: $role" $false
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Total Tests:  $TotalTests"
Write-Host "Passed:       $PassedTests" -ForegroundColor Green
Write-Host "Failed:       $FailedTests" -ForegroundColor Red
Write-Host ""

if ($FailedTests -eq 0) {
    Write-Host "All tests passed!" -ForegroundColor Green
} else {
    Write-Host "Some tests failed. Review output above." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To create missing resources:" -ForegroundColor Yellow
    Write-Host "  1. Run: .\provision_resources.ps1"
    Write-Host "  2. Deploy Lambda: cd lambda; sam build; sam deploy"
    Write-Host "  3. Create AppSync API manually"
}
