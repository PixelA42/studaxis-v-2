# Studaxis AWS Resource Provisioning
param(
    [string]$Region = "ap-south-1",
    [string]$Environment = "dev"
)

Write-Host "Studaxis AWS Auto-Provisioning" -ForegroundColor Cyan
Write-Host "Region: $Region" -ForegroundColor Yellow
Write-Host "Environment: $Environment" -ForegroundColor Yellow
Write-Host ""

# Check AWS CLI
try {
    $AccountId = aws sts get-caller-identity --query Account --output text 2>$null
    Write-Host "AWS CLI configured (Account: $AccountId)" -ForegroundColor Green
    Write-Host ""
}
catch {
    Write-Host "AWS CLI not found or not configured" -ForegroundColor Red
    exit 1
}

# Create DynamoDB Tables
Write-Host "Creating DynamoDB Tables..." -ForegroundColor Cyan

$tables = @(
    @{Name="studaxis-content-distribution"; Key="class_id"},
    @{Name="studaxis-classes"; Key="class_id"},
    @{Name="studaxis-assignments"; Key="assignment_id"},
    @{Name="studaxis-teachers-$Environment"; Key="classCode"}
)

foreach ($table in $tables) {
    $tableName = $table.Name
    $keyName = $table.Key
    
    try {
        $null = aws dynamodb describe-table --table-name $tableName --region $Region 2>$null
        Write-Host "  Table $tableName already exists" -ForegroundColor Yellow
    }
    catch {
        Write-Host "  Creating table: $tableName" -ForegroundColor Green
        
        aws dynamodb create-table `
            --table-name $tableName `
            --attribute-definitions AttributeName=$keyName,AttributeType=S `
            --key-schema AttributeName=$keyName,KeyType=HASH `
            --billing-mode PAY_PER_REQUEST `
            --region $Region `
            --tags Key=Project,Value=Studaxis Key=Environment,Value=$Environment | Out-Null
        
        Write-Host "    Waiting for table to be active..." -ForegroundColor Yellow
        aws dynamodb wait table-exists --table-name $tableName --region $Region
        Write-Host "    Table created successfully" -ForegroundColor Green
    }
}

Write-Host ""

# Create IAM Roles
Write-Host "Creating IAM Roles..." -ForegroundColor Cyan

$roles = @(
    "studaxis-content-2026-dist-role-$Environment",
    "studaxis-class-manager-role-$Environment",
    "studaxis-teacher-auth-$Environment-sam",
    "studaxis-teacher-generate-notes-role-$Environment"
)

$trustPolicy = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

foreach ($roleName in $roles) {
    try {
        $null = aws iam get-role --role-name $roleName 2>$null
        Write-Host "  Role $roleName already exists" -ForegroundColor Yellow
    }
    catch {
        Write-Host "  Creating role: $roleName" -ForegroundColor Green
        
        aws iam create-role `
            --role-name $roleName `
            --assume-role-policy-document $trustPolicy `
            --tags Key=Project,Value=Studaxis Key=Environment,Value=$Environment | Out-Null
        
        aws iam attach-role-policy `
            --role-name $roleName `
            --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" | Out-Null
        
        Write-Host "    Role created successfully" -ForegroundColor Green
        Start-Sleep -Seconds 3
    }
}

Write-Host ""
Write-Host "Provisioning Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Resources Created:" -ForegroundColor Cyan
Write-Host "  - 4 DynamoDB tables"
Write-Host "  - 4 IAM roles"
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Deploy Lambda functions: cd lambda; sam build; sam deploy"
Write-Host "  2. Create AppSync API manually"
Write-Host "  3. Run test script: .\test_aws_endpoints.ps1"
Write-Host ""
