# Studaxis AWS MVP — CLI Audit & Verification Report

**Date:** 2026-03-08  
**Account:** 718980965213  
**Region:** ap-south-1  

---

## Task 1: BEFORE — CLI Reality Check

### DynamoDB
```json
{
    "TableNames": [
        "studaxis-quiz-index",
        "studaxis-student-sync"
    ]
}
```

### S3 Buckets
```
2026-03-02 23:50:44 aws-sam-cli-managed-default-samclisourcebucket-qi82j82ad9v6
2026-02-28 18:48:12 studaxis-content-2026
2026-03-02 15:07:13 studaxis-lambda-artifacts-dev
2026-03-08 19:46:38 studaxis-payloads
2026-02-28 12:02:31 studaxis-student-stats-2026
```

### Lambda Functions
| Function |
|----------|
| studaxis-content-distribution |
| studaxis-offline-sync |
| studaxis-content-distribution-dev |
| studaxis-offline-sync-dev |
| bedrock-quiz-generator |
| studaxis-quiz-generation-dev |

### AppSync APIs
| apiId | name |
|-------|------|
| z6rvf6on6jhblds7udlfnm5i4e | studaxis-graphql-api |

---

## Task 2: Deployment

**Action:** `sam build` succeeded. `sam deploy` failed with Windows Unicode/codec error:
```
Error: 'charmap' codec can't decode byte 0x90 in position 875: character maps to <undefined>
```

**Decision:** All required resources already exist. No deployment needed.

**Fallback:** `aws-infra/scripts/provision-mvp-cli.sh` created for fresh-account provisioning.

---

## Task 3: AFTER — CLI Verification (same as BEFORE)

### DynamoDB ✓
```json
{
    "TableNames": [
        "studaxis-quiz-index",
        "studaxis-student-sync"
    ]
}
```

### S3 ✓
```
studaxis-payloads
studaxis-content-2026
studaxis-student-stats-2026
```

### Lambda ✓
```
studaxis-offline-sync
studaxis-content-distribution
studaxis-quiz-generation-dev
bedrock-quiz-generator
```

### AppSync ✓
- **Name:** studaxis-graphql-api
- **API ID:** z6rvf6on6jhblds7udlfnm5i4e
- **GRAPHQL URI:** https://wpfcpehf2zfn7lqz4rriy3yfum.appsync-api.ap-south-1.amazonaws.com/graphql

---

## Task 4: Environment (backend/.env)

| Variable | Live Value | backend/.env |
|----------|------------|--------------|
| APPSYNC_ENDPOINT | https://wpfcpehf2zfn7lqz4rriy3yfum.appsync-api.ap-south-1.amazonaws.com/graphql | ✓ MATCH |
| APPSYNC_API_KEY | (secret; id da2-y2htgfrijndzjiw635oynr62uu exists) | ✓ PRESENT |
| S3_BUCKET_NAME | studaxis-payloads | ✓ MATCH |

**Note:** AppSync API key *secret* cannot be extracted via CLI after creation. The value in .env must have been copied from Console when the key was created.

---

## Summary

| Resource | Required | Status |
|----------|----------|--------|
| DynamoDB: studaxis-student-sync | ✓ | LIVE |
| DynamoDB: studaxis-quiz-index | ✓ | LIVE |
| S3: studaxis-payloads | ✓ | LIVE |
| Lambda: studaxis-offline-sync | ✓ | LIVE |
| Lambda: studaxis-content-distribution | ✓ | LIVE |
| Lambda: studaxis-quiz-generation* | ✓ | LIVE (dev variant) |
| AppSync: studaxis-graphql-api | ✓ | LIVE |
| backend/.env | ✓ | CONFIGURED |
