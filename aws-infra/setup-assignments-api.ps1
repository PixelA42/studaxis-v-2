# Wire /assignments to Assignment Manager Lambda on API Gateway (yjyn9jsugc)
# Run from repo root or aws-infra. Requires: Lambda studaxis-assignment-manager-dev already deployed.
# Uses stage: dev (change $STAGE if your API uses a different stage)
# Optional: .\setup-assignments-api.ps1 -LambdaName "your-lambda-name"

param(
    [string]$LambdaName = "studaxis-assignment-manager-dev"
)

$ErrorActionPreference = "Stop"
$REGION = "ap-south-1"
$ACCOUNT_ID = "718980965213"
$API_ID = "yjyn9jsugc"
$STAGE = "dev"
$LAMBDA_NAME = $LambdaName

Write-Host "API Gateway: $API_ID" -ForegroundColor Cyan
Write-Host "Stage: $STAGE" -ForegroundColor Cyan
Write-Host "Lambda: $LAMBDA_NAME" -ForegroundColor Cyan
Write-Host ""

# Get Lambda ARN
$ErrorActionPreference = "Continue"
$LAMBDA_ARN = (aws lambda get-function --function-name $LAMBDA_NAME --region $REGION --query "Configuration.FunctionArn" --output text 2>$null)
$ErrorActionPreference = "Stop"
if (-not $LAMBDA_ARN) {
    Write-Host "[FAIL] Lambda '$LAMBDA_NAME' not found in region $REGION." -ForegroundColor Red
    Write-Host ""
    Write-Host "Listing Lambdas with 'assignment' in the name:" -ForegroundColor Yellow
    $ErrorActionPreference = "Continue"
    aws lambda list-functions --region $REGION --query "Functions[?contains(FunctionName,'assignment')].FunctionName" --output text 2>$null
    $ErrorActionPreference = "Stop"
    Write-Host ""
    Write-Host "To use a different Lambda, run: .\setup-assignments-api.ps1 -LambdaName <FunctionName>" -ForegroundColor Cyan
    Write-Host "To deploy the default Lambda first, run from aws-infra: .\deploy-lambdas.ps1" -ForegroundColor Cyan
    exit 1
}
Write-Host "[OK] Lambda ARN: $LAMBDA_ARN" -ForegroundColor Green

# Permission for API Gateway to invoke Lambda
Write-Host "Adding API Gateway invoke permission to Lambda..." -ForegroundColor Yellow
aws lambda add-permission --function-name $LAMBDA_NAME --statement-id "apigateway-invoke-assignments" --action lambda:InvokeFunction --principal apigateway.amazonaws.com --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*" --region $REGION 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "  (Permission may already exist)" -ForegroundColor Gray } else { Write-Host "  [OK] Permission added" -ForegroundColor Green }

# Get root resource id
$ROOT_ID = aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query "items[?path=='/'].id" --output text
if (-not $ROOT_ID) {
    Write-Host "[FAIL] Could not get API root resource id" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Root resource id: $ROOT_ID" -ForegroundColor Green

# Check if /assignments already exists
$ASSIGNMENTS_RESOURCE_ID = aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query "items[?pathPart=='assignments' && parentId=='$ROOT_ID'].id" --output text 2>$null
if (-not $ASSIGNMENTS_RESOURCE_ID) {
    Write-Host "Creating resource /assignments..." -ForegroundColor Yellow
    $createRes = aws apigateway create-resource --rest-api-id $API_ID --parent-id $ROOT_ID --path-part "assignments" --region $REGION --output json
    $ASSIGNMENTS_RESOURCE_ID = ($createRes | ConvertFrom-Json).id
    Write-Host "  [OK] Created /assignments (id: $ASSIGNMENTS_RESOURCE_ID)" -ForegroundColor Green
} else {
    Write-Host "[OK] /assignments already exists (id: $ASSIGNMENTS_RESOURCE_ID)" -ForegroundColor Green
}

$INTEGRATION_URI = "arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/${LAMBDA_ARN}/invocations"

# PUT POST /assignments
Write-Host "Putting POST /assignments..." -ForegroundColor Yellow
aws apigateway put-method --rest-api-id $API_ID --resource-id $ASSIGNMENTS_RESOURCE_ID --http-method POST --authorization-type NONE --region $REGION 2>$null
aws apigateway put-integration --rest-api-id $API_ID --resource-id $ASSIGNMENTS_RESOURCE_ID --http-method POST --type AWS_PROXY --integration-http-method POST --uri $INTEGRATION_URI --region $REGION | Out-Null
Write-Host "  [OK] POST /assignments" -ForegroundColor Green

# PUT GET /assignments
Write-Host "Putting GET /assignments..." -ForegroundColor Yellow
aws apigateway put-method --rest-api-id $API_ID --resource-id $ASSIGNMENTS_RESOURCE_ID --http-method GET --authorization-type NONE --region $REGION 2>$null
aws apigateway put-integration --rest-api-id $API_ID --resource-id $ASSIGNMENTS_RESOURCE_ID --http-method GET --type AWS_PROXY --integration-http-method POST --uri $INTEGRATION_URI --region $REGION | Out-Null
Write-Host "  [OK] GET /assignments" -ForegroundColor Green

# PUT OPTIONS /assignments (CORS)
Write-Host "Putting OPTIONS /assignments (CORS)..." -ForegroundColor Yellow
aws apigateway put-method --rest-api-id $API_ID --resource-id $ASSIGNMENTS_RESOURCE_ID --http-method OPTIONS --authorization-type NONE --region $REGION 2>$null
aws apigateway put-integration --rest-api-id $API_ID --resource-id $ASSIGNMENTS_RESOURCE_ID --http-method OPTIONS --type MOCK --request-templates "{\"application/json\":\"{\\\"statusCode\\\": 200}\"}" --region $REGION | Out-Null
aws apigateway put-method-response --rest-api-id $API_ID --resource-id $ASSIGNMENTS_RESOURCE_ID --http-method OPTIONS --status-code 200 --response-parameters "method.response.header.Access-Control-Allow-Headers=false,method.response.header.Access-Control-Allow-Methods=false,method.response.header.Access-Control-Allow-Origin=false" --region $REGION 2>$null
aws apigateway put-integration-response --rest-api-id $API_ID --resource-id $ASSIGNMENTS_RESOURCE_ID --http-method OPTIONS --status-code 200 --response-parameters "{\"method.response.header.Access-Control-Allow-Headers\":\"'Content-Type,Authorization'\",\"method.response.header.Access-Control-Allow-Methods\":\"'POST,GET,DELETE,OPTIONS'\",\"method.response.header.Access-Control-Allow-Origin\":\"'*'\"}" --region $REGION 2>$null
Write-Host "  [OK] OPTIONS /assignments" -ForegroundColor Green

# Create /assignments/{id}
$ID_RESOURCE_ID = aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query "items[?pathPart=='{id}' && parentId=='$ASSIGNMENTS_RESOURCE_ID'].id" --output text 2>$null
if (-not $ID_RESOURCE_ID) {
    Write-Host "Creating resource /assignments/{id}..." -ForegroundColor Yellow
    $createId = aws apigateway create-resource --rest-api-id $API_ID --parent-id $ASSIGNMENTS_RESOURCE_ID --path-part "{id}" --region $REGION --output json
    $ID_RESOURCE_ID = ($createId | ConvertFrom-Json).id
    Write-Host "  [OK] Created /assignments/{id} (id: $ID_RESOURCE_ID)" -ForegroundColor Green
} else {
    Write-Host "[OK] /assignments/{id} exists (id: $ID_RESOURCE_ID)" -ForegroundColor Green
}

# PUT DELETE /assignments/{id}
Write-Host "Putting DELETE /assignments/{id}..." -ForegroundColor Yellow
aws apigateway put-method --rest-api-id $API_ID --resource-id $ID_RESOURCE_ID --http-method DELETE --authorization-type NONE --region $REGION 2>$null
aws apigateway put-integration --rest-api-id $API_ID --resource-id $ID_RESOURCE_ID --http-method DELETE --type AWS_PROXY --integration-http-method POST --uri $INTEGRATION_URI --region $REGION | Out-Null
Write-Host "  [OK] DELETE /assignments/{id}" -ForegroundColor Green

# Deploy API
Write-Host "Deploying API to stage '$STAGE'..." -ForegroundColor Yellow
aws apigateway create-deployment --rest-api-id $API_ID --stage-name $STAGE --region $REGION 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Deployed." -ForegroundColor Green
} else {
    Write-Host "[WARN] Deployment failed. Create stage '$STAGE' in API Gateway console if needed." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Done. Assignments endpoints:" -ForegroundColor Cyan
Write-Host "  POST   .../$STAGE/assignments" -ForegroundColor White
Write-Host "  GET    .../$STAGE/assignments?class_code=CLASSCODE" -ForegroundColor White
Write-Host "  DELETE .../$STAGE/assignments/{id}" -ForegroundColor White
