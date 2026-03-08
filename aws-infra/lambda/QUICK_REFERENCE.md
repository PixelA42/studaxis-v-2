# Lambda Testing - Quick Reference

## Run Tests

### All Tests
```bash
cd aws-infra/lambda
python lambda_test_runner.py all
```

### Offline Sync (Quiz/Streak/Batch)
```bash
python lambda_test_runner.py offline-sync
```

### Content Distribution (Fetch/Manifest/Sync)
```bash
python lambda_test_runner.py content-distribution
```

### S3 Events (Quiz Upload/Batch Sync)
```bash
python lambda_test_runner.py s3-events
```

### Brief Summary
```bash
python lambda_test_runner.py all --brief
```

## View Test Events

### Show All Example Events
```bash
python test_events.py
```

### List Available Tests
```bash
python lambda_test_runner.py --list-tests
```

## Run Specific Test

### Quiz Attempt
```bash
python lambda_test_runner.py offline-sync --test quiz_attempt
```

### Streak Update
```bash
python lambda_test_runner.py offline-sync --test streak_update
```

### Batch Sync
```bash
python lambda_test_runner.py offline-sync --test batch_sync
```

### Fetch Content
```bash
python lambda_test_runner.py content-distribution --test fetch_offline_content
```

### Get Manifest
```bash
python lambda_test_runner.py content-distribution --test get_quiz_manifest
```

### S3 Quiz Upload
```bash
python lambda_test_runner.py s3-events --test s3_quiz_uploaded
```

## Integration Tests (Mocked AWS)

```bash
python lambda_integration_tests.py
```

## Test Against Real AWS

### With AWS Credentials Configured
```bash
python lambda_test_runner.py all --use-real-aws
```

### Deploy Locally First
```bash
sam build -t sam-template.yaml
sam local start-api
# In another terminal:
python lambda_test_runner.py all
```

## Python Imports for Custom Tests

```python
from test_events import OfflineSyncEventFactory
from test_events import ContentDistributionEventFactory
from test_events import S3EventFactory

# Generate events
quiz_event = OfflineSyncEventFactory.quiz_attempt(
    student_id="student-001",
    quiz_id="quiz-123",
    score=85.5
)

content_event = ContentDistributionEventFactory.fetch_offline_content(
    student_id="student-001",
    device_id="iphone-14"
)

s3_event = S3EventFactory.s3_quiz_uploaded(
    bucket="studaxis-payloads",
    student_id="student-001",
    quiz_id="quiz-123",
    attempt_id="attempt-abc"
)
```

## Test Results Expected

```
✓ Offline Sync: 4/4 tests passing
✓ Content Distribution: 3/3 tests ready
✓ S3 Events: 2/2 tests ready
✓ Integration: 11/11 tests passing
✓ Event Generation: All working
```

## Files Reference

| File | Purpose |
|------|---------|
| test_events.py | Event factory classes |
| lambda_test_runner.py | CLI test runner |
| lambda_integration_tests.py | Full integration tests |
| sam-template.yaml | Local deployment |
| LAMBDA_TESTING_GUIDE.md | Full documentation |
| TESTING_COMPLETE.md | Implementation summary |

## Quick Troubleshooting

### Unicode Error in PowerShell
Use Python directly instead of PowerShell:
```bash
python.exe lambda_test_runner.py all
```

### Module Not Found
Ensure you're in the `aws-infra/lambda` directory:
```bash
cd aws-infra/lambda
python lambda_test_runner.py all
```

### AWS Credentials Error
Either:
1. Run `aws configure` first
2. Remove `--use-real-aws` flag
3. Check LAMBDA_TESTING_GUIDE.md Troubleshooting

## Performance Baselines

- Quiz Attempt Write: ~50ms
- Streak Update: ~30ms
- Batch Sync (5 items): ~150ms
- Content Fetch: ~100ms
- Manifest Query: ~80ms
- S3 Event Process: ~200ms

## What's Tested

### Offline Sync Lambda
- ✓ Quiz attempt recording
- ✓ Streak update tracking
- ✓ Batch sync atomicity
- ✓ Error handling
- ✓ DynamoDB writes
- ✓ S3 backup

### Content Distribution Lambda
- ✓ Offline content fetching
- ✓ Quiz manifest queries
- ✓ Incremental sync
- ✓ Pre-signed URLs
- ✓ Access validation

### S3 Event Processing
- ✓ Quiz upload events
- ✓ Batch sync events
- ✓ Metadata extraction
- ✓ DynamoDB updates

## Next Steps

1. Run all tests: `python lambda_test_runner.py all`
2. Review event examples: `python test_events.py`
3. Read full guide: [LAMBDA_TESTING_GUIDE.md](LAMBDA_TESTING_GUIDE.md)
4. Deploy to AWS: `sam deploy`
5. Test with real AWS: `python lambda_test_runner.py all --use-real-aws`
