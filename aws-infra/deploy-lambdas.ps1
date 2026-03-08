# Deploy Lambda code for offline_sync and content_distribution
# Run from repo root: .\aws-infra\deploy-lambdas.ps1
# Requires: sam build completed, AWS CLI configured

$ErrorActionPreference = "Stop"
$Region = "ap-south-1"
$LambdaDir = Join-Path $PSScriptRoot "lambda"

Push-Location $LambdaDir

# Ensure build is fresh
sam build -t sam-template.yaml

# Deploy Lambdas (use stack if exists, or update function code directly)
# The studaxis-vtwo stack may manage these; check which functions exist
$functions = @(
    "studaxis-offline-sync-dev",
    "studaxis-content-2026-distribution-dev"
)

foreach ($fn in $functions) {
    $zipPath = ".aws-sam\build\$fn\*.zip"
    if (Test-Path $zipPath) {
        $zipFile = Get-ChildItem $zipPath | Select-Object -First 1
        Write-Host "Updating $fn from $($zipFile.FullName)..."
        aws lambda update-function-code --function-name $fn --zip-file "fileb://$($zipFile.FullName)" --region $Region 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Updated $fn"
        } else {
            Write-Host "  (Function may have different name in your account)"
        }
    }
}

Pop-Location
Write-Host "Done. AppSync schema already updated via: aws appsync start-schema-creation"
