# Lambda Testing Guide - Studaxis
## Test S3/AppSync Real Sync Events

This guide covers testing the two Studaxis Lambda functions with realistic AppSync and S3 events.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Student Mobile App                          │
└──────────────┬─────────────────────────────────────┬────────────┘
               │                                     │
        ┌──────▼──────────┐              ┌──────────▼────────┐
        │  AppSync Query  │              │  AppSync Mutation │
        │ (Offline Ready) │              │  (Offline Sync)   │
        └──────┬──────────┘              └────────┬─────────┘
               │                                  │
        ┌──────▼──────────────────────────────────▼──────────┐
        │          AWS AppSync GraphQL API                  │
        └──────┬──────────────────────────────────┬──────────┘
               │                                  │
        ┌──────▼────────────────┐      ┌─────────▼─────────────┐
        │ ContentDistribution   │      │  OfflineSync Lambda   │
        │ Lambda (Content)      │      │  (Student Updates)    │
        └──────┬────────────────┘      └────────┬──────────────┘
               │                                 │
        ┌──────▼──────┐          ┌──────────────▼──────────┐
        │ DynamoDB    │          │  DynamoDB              │
        │ quiz-index  │          │  student-sync          │
        │ (metadata)  │          │  + S3 payloads         │
        └─────────────┘          └───────────────────────┘
```

---

## 📋 Testing Files Created

### 1. **test_events.py**
Factories for generating realistic AppSync and S3 events:

```python
# Offline Sync Events
OfflineSyncEventFactory.quiz_attempt()
OfflineSyncEventFactory.streak_update()
OfflineSyncEventFactory.batch_sync()

# Content Distribution Events
ContentDistributionEventFactory.fetch_offline_content()
ContentDistributionEventFactory.get_quiz_manifest()

# S3 Events
S3EventFactory.s3_quiz_uploaded()
S3EventFactory.s3_batch_sync_uploaded()
```

### 2. **lambda_test_runner.py**
Command-line test runner:
- 11 different test scenarios
- Mock AWS services or connect to real AWS
- Brief or detailed output formats

### 3. **lambda_integration_tests.py**
Full integration tests with:
- Mocked DynamoDB tables
- Mocked S3 client
- Complete event-to-response flows
- Error handling validation

### 4. **sam-template.yaml**
AWS SAM template for local testing:
- Deploy both Lambda functions for local testing
- Simulated API Gateway endpoints
- DynamoDB Local integration ready

---

## 🚀 Quick Start

### Option 1: Run Event Generation Tests (No AWS Required)

Generate and validate test events without invoking handlers:

```bash
# Show all available tests
python lambda_test_runner.py --list-tests

# Run all event generation tests
python lambda_test_runner.py all

# Run specific test group
python lambda_test_runner.py offline-sync
python lambda_test_runner.py content-distribution
python lambda_test_runner.py s3-events

# Run specific test
python lambda_test_runner.py offline-sync --test quiz_attempt

# Show only summary (brief mode)
python lambda_test_runner.py all --brief
```

### Option 2: Run Integration Tests (Docker AWS Services)

Run tests with mocked AWS services:

```bash
# Just run the tests (mocked AWS)
python lambda_integration_tests.py

# With pytest (requires pytest)
pip install pytest
pytest lambda_integration_tests.py -v
```

### Option 3: Test Against Real AWS

Deploy to AWS and test with real DynamoDB/S3:

```bash
# Build SAM template
sam build -t sam-template.yaml

# Deploy locally (requires Docker + DynamoDB Local)
sam local start-api --template sam-template.yaml

# In another terminal, run tests against real services
python lambda_test_runner.py all --use-real-aws
```

---

## 📝 Test Scenarios

### Offline Sync Lambda Tests

#### 1. **Quiz Attempt**
- Student submits completed quiz while offline
- **Input**: Quiz ID, score, questions answered, time spent
- **Expected**: DynamoDB record created in `student-sync` table
- **Validation**: Score is within 0-100, questions >= 0

```bash
python lambda_test_runner.py offline-sync --test quiz_attempt
```

#### 2. **Streak Update**
- Track student's daily learning streak
- **Input**: Student ID, current streak count, days in streak
- **Expected**: DynamoDB record updated with streak metadata
- **Validation**: Replicate in local storage

```bash
python lambda_test_runner.py offline-sync --test streak_update
```

#### 3. **Batch Sync**
- Multiple updates synced at once (when connectivity returns)
- **Input**: Array of quiz attempts + streak updates
- **Expected**: Atomic write to DynamoDB + S3 backup
- **Validation**: All records written or none (transaction)

```bash
python lambda_test_runner.py offline-sync --test batch_sync
```

#### 4. **Error Handling - Invalid Student ID**
- Validate error handling for edge cases
- **Input**: Empty/invalid student ID
- **Expected**: 400 error with clear message
- **Validation**: No partial writes

```bash
python lambda_test_runner.py offline-sync --test invalid_student_id
```

### Content Distribution Lambda Tests

#### 1. **Fetch Offline Content**
- Student requests available quizzes for offline download
- **Input**: Student ID, device ID, grade level, subjects
- **Expected**: List of available quizzes with pre-signed URLs
- **Validation**: URLs valid for 1 hour, can download quiz JSON

```bash
python lambda_test_runner.py content-distribution --test fetch_offline_content
```

#### 2. **Get Quiz Manifest**
- Fetch detailed metadata for specific quizzes
- **Input**: Student ID, list of quiz IDs
- **Expected**: Quiz metadata, file sizes, estimated download time
- **Validation**: All quizzes accessible by student

```bash
python lambda_test_runner.py content-distribution --test get_quiz_manifest
```

#### 3. **Incremental Sync**
- Only fetch quizzes updated since last sync
- **Input**: Student ID, sync token from previous fetch
- **Expected**: Only NEW/UPDATED quizzes returned
- **Validation**: Reduces bandwidth by ~80% on subsequent syncs

```bash
python lambda_test_runner.py content-distribution --test incremental_sync
```

### S3 Event Tests

#### 1. **Quiz Upload Event**
- Simulates S3 trigger when student uploads quiz attempt
- **Input**: S3 put object event with student/quiz metadata in key
- **Expected**: Lambda can parse metadata and route correctly
- **Validation**: Key pattern: `payloads/students/{studentId}/quizzes/{quizId}/{attemptId}.json`

```bash
python lambda_test_runner.py s3-events --test s3_quiz_uploaded
```

#### 2. **Batch Sync Upload Event**
- S3 trigger for batch sync files
- **Input**: S3 event with batch sync metadata in key
- **Expected**: Lambda processes batch and updates DynamoDB
- **Validation**: Key pattern: `payloads/students/{studentId}/syncs/{batchId}.json`

```bash
python lambda_test_runner.py s3-events --test s3_batch_sync_uploaded
```

---

## 🔬 Event Examples

### Quiz Attempt Event (AppSync Mutation)

```json
{
  "identity": {
    "claims": {
      "sub": "student-001",
      "cognito:username": "user#student-001"
    }
  },
  "arguments": {
    "input": {
      "studentId": "student-001",
      "quizId": "quiz-math-algebra-1",
      "score": 87.5,
      "questionsAnswered": 8,
      "timeSpentSeconds": 450,
      "attemptedAt": "2024-03-02T14:30:00+00:00",
      "deviceId": "device-iphone14",
      "offlineAttempt": true
    }
  },
  "request": {
    "headers": {
      "x-amzn-appsync-operation": "Mutation",
      "x-appsync-request-id": "uuid-xyz..."
    }
  }
}
```

### Fetch Offline Content Event (AppSync Query)

```json
{
  "identity": {
    "claims": {
      "sub": "student-001",
      "cognito:username": "user#student-001"
    }
  },
  "arguments": {
    "studentId": "student-001",
    "deviceId": "iphone-14-pro",
    "gradeLevel": "10",
    "subjects": ["math", "english", "science"],
    "syncToken": "",
    "requestedAt": "2024-03-02T14:35:00+00:00"
  },
  "request": {
    "headers": {
      "x-amzn-appsync-operation": "Query",
      "x-appsync-request-id": "uuid-abc..."
    }
  }
}
```

### S3 Quiz Upload Event

```json
{
  "Records": [
    {
      "s3": {
        "bucket": {
          "name": "studaxis-payloads"
        },
        "object": {
          "key": "payloads/students/student-001/quizzes/quiz-math-1/attempt-xyz123.json",
          "size": 2048,
          "eTag": "abc123def456"
        }
      },
      "eventName": "ObjectCreated:Put",
      "eventTime": "2024-03-02T14:40:00.000Z"
    }
  ]
}
```

---

## ✅ Validation Checklist

After running tests, verify:

### Offline Sync Lambda
- [ ] Quiz attempts create records in DynamoDB `student-sync` table
- [ ] Streak updates modify existing records correctly
- [ ] Batch syncs are atomic (all succeed or all fail)
- [ ] Invalid requests return proper error codes
- [ ] Sync metadata includes timestamp and device ID
- [ ] S3 backups created for audit trail

### Content Distribution Lambda
- [ ] `studaxis-quiz-index` table queried for available quizzes
- [ ] Pre-signed URLs valid for exactly 1 hour
- [ ] Student access validated before returning URLs
- [ ] Incremental sync tokens work correctly
- [ ] Response includes quiz metadata (title, questions, estimated time)
- [ ] Manifest format matches mobile app expectations

### S3 Event Processing
- [ ] S3 object keys parsed correctly
- [ ] Student ID and quiz ID extracted from key
- [ ] DynamoDB records updated within 2 seconds
- [ ] Failed S3 events trigger CloudWatch alarms
- [ ] Object contents validated before processing

---

## 🔍 Troubleshooting

### "ModuleNotFoundError: No module named 'handler'"

The actual Lambda handlers need to be present. Ensure:
```
aws-infra/lambda/
  ├── offline_sync/
  │   └── handler.py    ✓
  ├── content_distribution/
  │   └── handler.py    ✓
  ├── test_events.py    ✓
  └── lambda_test_runner.py
```

### "DynamoDB connection refused"

Running real AWS tests without credentials. Either:
1. Configure AWS credentials: `aws configure`
2. Remove `--use-real-aws` flag to use mocks only

### "S3 event parsing failed"

Validate event structure matches S3 EventBridge format. Check:
```json
{
  "Records": [{
    "s3": {
      "bucket": { "name": "bucket-name" },
      "object": { "key": "path/to/object.json" }
    }
  }]
}
```

---

## 📊 Performance Baselines

Expected performance metrics:

| Operation | Duration | Notes |
|-----------|----------|-------|
| Quiz Attempt Write | ~50ms | DynamoDB + optional S3 backup |
| Streak Update | ~30ms | Single item update |
| Batch Sync (5 items) | ~150ms | Atomic if supported |
| Content Fetch | ~100ms | DynamoDB query + URL generation |
| Manifest Query | ~80ms | 3-10 quizzes |
| S3 Event Process | ~200ms | Parse + DynamoDB update |

---

## 🚨 Error Codes Expected

### Offline Sync
- `400 ValidationError`: Missing required fields
- `401 Unauthorized`: Invalid student token
- `409 Conflict`: Duplicate sync attempt (idempotency key)
- `500 InternalError`: DynamoDB write failure

### Content Distribution
- `400 ValidationError`: Invalid grade level/subject
- `401 Unauthorized`: Student access denied
- `404 NotFound`: No quizzes available
- `503 ServiceUnavailable`: Quiz index unavailable

---

## 📚 Next Steps

1. **Deploy to AWS**: Use CloudFormation template to deploy Lambdas
2. **Connect AppSync**: Map resolvers to deployed Lambda functions
3. **Load Test**: Use `load_test.py` to simulate 100+ concurrent users
4. **Monitor**: Set up CloudWatch alarms for errors > 5%
5. **Document**: Update API docs with actual response examples

---

## 📖 File Reference

- [test_events.py](test_events.py) - Event factory classes
- [lambda_test_runner.py](lambda_test_runner.py) - CLI test runner
- [lambda_integration_tests.py](lambda_integration_tests.py) - Full integration tests
- [sam-template.yaml](sam-template.yaml) - Local deployment template
- [offline_sync/handler.py](offline_sync/handler.py) - Sync Lambda code
- [content_distribution/handler.py](content_distribution/handler.py) - Distribution Lambda code
