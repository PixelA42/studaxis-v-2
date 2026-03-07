# Lambda Test Payloads

Use these payloads when invoking the offline_sync Lambda via AWS CLI.

> **PowerShell:** Inline JSON in `--payload '...'` often fails on Windows (parse errors). Use `file://` instead.

## Quiz Attempt

From `aws-infra/lambda/`:

```powershell
aws lambda invoke --function-name studaxis-offline-sync-dev --payload file://payloads/quiz_attempt.json output.json; Get-Content output.json
```

## Streak Update

```powershell
aws lambda invoke --function-name studaxis-offline-sync-dev --payload file://payloads/streak_update.json output.json; Get-Content output.json
```

## S3 Trigger (alternative)

To test S3 trigger mode, upload a JSON file to `s3://studaxis-payloads/sync/` with structure:
```json
{
  "student_id": "student-001",
  "current_streak": 5,
  "last_quiz_score": 85,
  "last_sync_timestamp": "2026-03-07T12:00:00Z"
}
```
The Lambda will be invoked automatically by the S3 event.
