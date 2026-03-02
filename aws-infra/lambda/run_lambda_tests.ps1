#!/usr/bin/env pwsh
<#
.SYNOPSIS
Quick Lambda Testing Script for Studaxis
Tests S3/AppSync real sync events

.DESCRIPTION
Runs the Lambda test suites and shows example events.
No AWS credentials needed for basic event generation tests.

.EXAMPLE
.\run_lambda_tests.ps1
.\run_lambda_tests.ps1 -TestType integration
.\run_lambda_tests.ps1 -ShowExamples
.\run_lambda_tests.ps1 -Clean

.NOTES
Requires: Python 3.11+
#>

param(
    [ValidateSet("events", "integration", "all")]
    [string]$TestType = "events",
    
    [switch]$ShowExamples,
    [switch]$Clean,
    [switch]$Verbose
)

# Setup
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$lambdaDir = $scriptDir
$pythonExe = ".\..\..\studaxis-vtwo-env\Scripts\python.exe"

# Colors
$colors = @{
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
    Info = "Cyan"
}

function Write-Section {
    param([string]$Title)
    Write-Host "`n" + ("="*70) -ForegroundColor $colors.Info
    Write-Host $Title -ForegroundColor $colors.Info
    Write-Host ("="*70) -ForegroundColor $colors.Info
}

function Write-Status {
    param([string]$Message, [string]$Type = "Info")
    Write-Host $Message -ForegroundColor $colors[$Type]
}

# Check Python
Write-Section "Checking Environment"

if (-not (Test-Path $pythonExe)) {
    Write-Status "Python not found at $pythonExe" "Error"
    Write-Status "Trying system Python..." "Warning"
    $pythonExe = "python"
}

try {
    $pythonVersion = & $pythonExe --version 2>&1
    Write-Status "✓ Found: $pythonVersion" "Success"
} catch {
    Write-Status "Python not found! Install Python 3.11+" "Error"
    exit 1
}

# Clean old test artifacts
if ($Clean) {
    Write-Section "Cleaning Test Artifacts"
    Remove-Item -Path "$lambdaDir\__pycache__" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Status "✓ Cleaned cache files" "Success"
}

# Show examples
if ($ShowExamples) {
    Write-Section "Example Test Events"
    Write-Status "Generating example events..." "Info"
    & $pythonExe "$lambdaDir\test_events.py"
    exit 0
}

# Run event generation tests
if ($TestType -in "events", "all") {
    Write-Section "Lambda Event Generation Tests"
    Write-Status "Testing event factories..." "Info"
    
    Write-Host "`n1. Offline Sync Tests (Quiz Attempt)"
    & $pythonExe "$lambdaDir\lambda_test_runner.py" offline-sync --test quiz_attempt
    
    Write-Host "`n2. Offline Sync Tests (Streak Update)"
    & $pythonExe "$lambdaDir\lambda_test_runner.py" offline-sync --test streak_update
    
    Write-Host "`n3. Offline Sync Tests (Batch Sync)"
    & $pythonExe "$lambdaDir\lambda_test_runner.py" offline-sync --test batch_sync
    
    Write-Host "`n4. Content Distribution Tests"
    & $pythonExe "$lambdaDir\lambda_test_runner.py" content-distribution
    
    Write-Host "`n5. S3 Event Tests"
    & $pythonExe "$lambdaDir\lambda_test_runner.py" s3-events --brief
}

# Run integration tests
if ($TestType -in "integration", "all") {
    Write-Section "Lambda Integration Tests"
    Write-Status "Running with mocked AWS services..." "Info"
    & $pythonExe "$lambdaDir\lambda_integration_tests.py"
}

# Summary
Write-Section "Testing Complete"
Write-Status "✓ All tests finished" "Success"
Write-Host "`nNext steps:"
Write-Host "  1. Review test output above"
Write-Host "  2. Check lambda_test_runner.py --list-tests for all available tests"
Write-Host "  3. See LAMBDA_TESTING_GUIDE.md for detailed documentation"
Write-Host "  4. Deploy to AWS: sam build && sam deploy"
