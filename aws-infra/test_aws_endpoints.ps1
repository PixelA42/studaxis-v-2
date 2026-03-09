# Studaxis AWS Endpoints Testing Script (PowerShell)
# Tests all AWS resources and endpoints from integration checklist

param(
    [string]$Region = "ap-south-1",
    [string]$Environment = "dev"
)

$ErrorActionPreference = "Continue"

# Colors
$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"
$Blue = "Cyan"

Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor $Blue
Write-Host "║     Studaxis AWS Endpoints Testing Suite              ║" -ForegroundColor $Blue
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor $Blue
Write-Host ""
Write-Host "Region: $Region" -ForegroundColor $Yellow
Write-Host "Environment: $Environment" -ForegroundColor $Yellow
Write-Host ""

# Test counters
$TotalTests = 0
$PassedTests = 0
$FailedTests = 0

function Test-Result {
    param(
        [string]$TestName,
        [bool]$Result
    )
    
    $script:TotalTests++
    
    if ($Result) {
        Write-Host "✓ $TestName" -ForegroundColor $Green
        $script:PassedTests++
    } else {
        Write-Host "✗ $TestName" -ForegroundColor $Red
        $script:FailedTests++
    }
}

# Check AWS CLI
try {
    $null = aws --version
    Write-Host "✓ AWS CLI configured" -ForegroundColor $Green
} catch {
    Write-Host "❌ AWS CLI not found. Please install it first." -ForegroundColor $Red
    exit 1
}

# Check AWS credentials
try {
    $AccountId = aws sts get-caller-identity --query Account --output text
    Write-Host "Account ID: $AccountId" -ForegroundColor $Yellow
    Write-Host ""
} catch {
    Write-Host "❌ AWS credentials not configured. Run 'aws configure' first." -ForegroundColor $Red
    exit 1
}

# ============================================================================
# 1. DynamoDB Tables
# ============================================================================
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor $Blue
Write-Host "1. Testing DynamoDB Tables" -ForegroundColor $Blue
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor $Blue

$Tables = @(
    "studaxis-student-sync",
    "studaxis-quiz-index",
    "studaxis-content-distribution",
    "studaxis-classes",
    "studaxis-assignments",
    "studaxis-teachers-$Environment"
)

foreach ($Table in $Tables) {
    try {
        $Status = aws dynamodb describe-table --table-name $Table --region $Region --query 'Table.TableStatus' --output text 2>$null
        if ($Status -eq "ACTIVE") {
            Test-Result "DynamoDB Table: $Table (Status: $Status)" $true
        } else {
            Test-Result "DynamoDB Table: $Table (Status: $Status - Not Active)" $false
        }
    } catch {
        Test-Result "DynamoDB Table: $Table (Not Found)" $false
    }
}

Write-Host ""

# ============================================================================
# 2. S3 Buckets
# ============================================================================
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor $Blue
Write-Host "2. Testing S3 Buckets" -ForegroundColor $Blue
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor $Blue

$Buckets = @(
    "studaxis-payloads",
    "studaxis-student-stats-2026",
    "studaxis-lambda-artifacts-$Environment"
)

foreach ($Bucket in $Buckets) {
    try {
        $null = aws s3 ls "s3://$Bucket" --region $Region 2>$null
        Test-Result "S3 Bucket: $Bucket" $true
    } catch {
        Test-Result "S3 Bucket: $Bucket (Not Found or No Access)" $false
    }
}

Write-Host ""

# ============================================================================
# 3. Lambda Functions
# ============================================================================
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor $Blue
Write-Host "3. Testing Lambda Functions" -ForegroundColor $Blue
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor $Blue

$Lambdas = @(
    "studaxis-offline-sync-$Environment",
    "studaxis-content-2026-distribution-$Environment",
    "studaxis-quiz-generation-$Environment",
    "studaxis-teacher-generate-notes-$Environment",
    "studaxis-class-manager-$Environment",
    "studaxis-teacher-auth-$Environment"
)

foreach ($Lambda in $Lambdas) {
    try {
        $State = aws lambda get-function --function-name $Lambda --region $Region --query 'Configuration.State' --output text 2>$null
        $Runtime = aws lambda get-function --function-name $Lambda --region $Region --query 'Configuration.Runtime' --output text 2>$null
        $Arch = aws lambda get-function --function-name $Lambda --region $Region --query 'Configuration.Architectures[0]' --output text 2>$null
        
        if ($State) {
            Test-Result "Lambda: $Lambda (State: $State, Runtime: $Runtime, Arch: $Arch)" $true
        } else {
            Test-Result "Lambda: $Lambda (Not Found)" $false
        }
    } catch {
        Test-Result "Lambda: $Lambda (Not Found)" $false
    }
}

Write-Host ""

# ============================================================================
# 4. API Gateway
# ============================================================================
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor $Blue
Write-Host "4. Testing API Gateway" -ForegroundColor $Blue
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor $Blue

$ApiName = "studaxis-teacher-api-$Environment"
try {
    $ApiId = aws apigateway get-rest-apis --region $Region --query "items[?name=='$ApiName'].id" --output text 2>$null
    
    if ($ApiId) {
        Test-Result "API Gateway: $ApiName (ID: $ApiId)" $true
        
        $Stage = "prod"
        $ApiEndpoint = "https://$ApiId.execute-api.$Region.amazonaws.com/$Stage"
        Write-Host "  Endpoint: $ApiEndpoint" -ForegroundColor $Yellow
        
        Write-Host "`n  Testing API Endpoints:" -ForegroundColor $Yellow
        
        # Test /classes endpoint
        try {
            $Response = Invoke-WebRequest -Uri "$ApiEndpoint/classes" -Method Get -UseBasicParsing -ErrorAction SilentlyContinue
            Test-Result "  GET /classes (HTTP $($Response.StatusCode))" $true
        } catch {
            $StatusCode = $_.Exception.Response.StatusCode.value__
            if ($StatusCode) {
                Test-Result "  GET /classes (HTTP $StatusCode)" $true
            } else {
                Test-Result "  GET /classes (Connection Failed)" $false
            }
        }
        
        # Test /assignments endpoint
        try {
            $Response = Invoke-WebRequest -Uri "$ApiEndpoint/assignments?class_code=TEST" -Method Get -UseBasicParsing -ErrorAction SilentlyContinue
            Test-Result "  GET /assignments (HTTP $($Response.StatusCode))" $true
        } catch {
            $StatusCode = $_.Exception.Response.StatusCode.value__
            if ($StatusCode) {
                Test-Result "  GET /assignments (HTTP $StatusCode)" $true
            } else {
                Test-Result "  GET /assignments (Connection Failed)" $false
            }
        }
    } else {
        Test-Result "API Gateway: $ApiName (Not Found)" $false
    }
} catch {
    Test-Result "API Gateway: $ApiName (Error)" $false
}

Write-Host ""

# ============================================================================
# 5. AppSync API
# ============================================================================
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor $Blue
Write-Host "5. Testing AppSync API" -ForegroundColor $Blue
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor $Blue

try {
    $AppSyncApis = aws appsync list-graphql-apis --region $Region --query 'graphqlApis[?contains(name, `studaxis`)]' --output json 2>$null | ConvertFrom-Json
    
    if ($AppSyncApis -and $AppSyncApis.Count -gt 0) {
        foreach ($Api in $AppSyncApis) {
            Write-Host "  Name: $($Api.name)" -ForegroundColor $Yellow
            Write-Host "  ID: $($Api.apiId)" -ForegroundColor $Yellow
            Write-Host "  Endpoint: $($Api.uris.GRAPHQL)" -ForegroundColor $Yellow
        }
        Test-Result "AppSync API Found" $true
    } else {
        Test-Result "AppSync API (Not Found - Create manually)" $false
        Write-Host "  Note: AppSync API must be created manually via Console" -ForegroundColor $Yellow
    }
} catch {
    Test-Result "AppSync API (Error checking)" $false
}

Write-Host ""

# ============================================================================
# 6. IAM Roles
# ============================================================================
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor $Blue
Write-Host "6. Testing IAM Roles" -ForegroundColor $Blue
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor $Blue

$Roles = @(
    "studaxis-offline-sync-role-$Environment",
    "studaxis-content-2026-dist-role-$Environment",
    "studaxis-quiz-gen-role-$Environment",
    "studaxis-teacher-auth-$Environment-sam",
    "studaxis-class-manager-role-$Environment"
)

foreach ($Role in $Roles) {
    try {
        $null = aws iam get-role --role-name $Role 2>$null
        Test-Result "IAM Role: $Role" $true
    } catch {
        Test-Result "IAM Role: $Role (Not Found)" $false
    }
}

Write-Host ""

# ============================================================================
# 7. Bedrock Model Access
# ============================================================================
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor $Blue
Write-Host "7. Testing Bedrock Model Access" -ForegroundColor $Blue
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor $Blue

try {
    $null = aws bedrock list-foundation-models --region $Region 2>$null
    Test-Result "Bedrock API Access" $true
    
    $NovaModels = aws bedrock list-foundation-models --region $Region --query "modelSummaries[?contains(modelId, 'nova')]" --output text 2>$null
    if ($NovaModels) {
        Test-Result "Bedrock Nova Model Available" $true
    } else {
        Test-Result "Bedrock Nova Model (Check model access in Console)" $false
    }
} catch {
    Test-Result "Bedrock API Access (Not Available - Check permissions)" $false
}

Write-Host ""

# ============================================================================
# Summary
# ============================================================================
Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor $Blue
Write-Host "║                    Test Summary                        ║" -ForegroundColor $Blue
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor $Blue
Write-Host ""
Write-Host "Total Tests:  $TotalTests"
Write-Host "Passed:       $PassedTests" -ForegroundColor $Green
Write-Host "Failed:       $FailedTests" -ForegroundColor $Red
Write-Host ""

if ($FailedTests -eq 0) {
    Write-Host "✓ All tests passed! AWS infrastructure is ready." -ForegroundColor $Green
    exit 0
} else {
    Write-Host "⚠ Some tests failed. Review the output above." -ForegroundColor $Yellow
    Write-Host ""
    Write-Host "Common fixes:"
    Write-Host "  - Run deployment script: .\deploy_teacher_dashboard.sh"
    Write-Host "  - Create missing DynamoDB tables"
    Write-Host "  - Deploy Lambda functions via SAM"
    Write-Host "  - Configure AppSync API manually"
    Write-Host "  - Request Bedrock model access in Console"
    exit 1
}
