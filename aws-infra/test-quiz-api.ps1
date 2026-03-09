# Quick test for POST /generateQuiz (quiz generation)
# Run from repo root or aws-infra. Requires PowerShell.

$base = "https://yjyn9jsugc.execute-api.ap-south-1.amazonaws.com/dev"
$url = "$base/generateQuiz"
$body = '{"topic":"Gravity","difficulty":"medium","num_questions":2}'

Write-Host "Testing: POST $url" -ForegroundColor Cyan
Write-Host ""

try {
    $response = Invoke-WebRequest -Uri $url -Method POST -Body $body -ContentType "application/json" -UseBasicParsing
    Write-Host "Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host $response.Content
} catch {
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
    $reader.BaseStream.Position = 0
    Write-Host $reader.ReadToEnd()
}
