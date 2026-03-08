# Tasks: AWS Infrastructure Elevation

## Overview

This task list implements the AWS infrastructure elevation for the StudAxis EdTech platform, integrating DynamoDB for sync metadata, API Gateway + Lambda for quiz generation, AWS Amplify for dashboard hosting, and optional ECS/EC2 deployment. The implementation maintains the Dual-Brain Architecture where Amazon Bedrock (Strategic Cloud Brain) generates curriculum content while local Ollama (Edge AI) provides offline tutoring.

## Task Breakdown

### Phase 1: Foundation & Data Layer

#### Task 1: DynamoDB State Store Implementation

**Description:** Create DynamoDB table for storing lightweight sync metadata (User ID, Current Streak, Last Sync Timestamp) to enable fast teacher dashboard queries without processing heavy S3 payloads.

**Acceptance Criteria:**
- DynamoDB table `studaxis-student-sync` created with user_id as partition key
- Table configured with On-Demand capacity mode
- Point-in-Time Recovery enabled
- AWS-managed encryption enabled
- Table schema includes: user_id (String), current_streak (Number), last_sync_timestamp (String), sync_status (String), device_id (String), last_payload_key (String), total_sessions (Number), last_quiz_score (Number)

**Sub-tasks:**
- [ ] 1.1 Create DynamoDB table using AWS CDK or CloudFormation
- [ ] 1.2 Configure table capacity mode and encryption settings
- [ ] 1.3 Create IAM roles for table access (read/write permissions)
- [ ] 1.4 Write unit tests for table schema validation
- [ ] 1.5 Document table access patterns and performance requirements

**Dependencies:** None

**Estimated Effort:** 4 hours

---

#### Task 2: S3 Payload Store Configuration

**Description:** Configure S3 bucket for storing heavy payloads (quizzes, textbooks, chat logs) with proper lifecycle policies, versioning, and encryption.

**Acceptance Criteria:**
- S3 bucket `studaxis-payloads` created with folder structure: quizzes/, textbooks/, chat_logs/
- Versioning enabled for quiz and textbook content
- Lifecycle policy configured to transition chat logs to Glacier after 90 days
- SSE-S3 (AES-256) encryption enabled
- CORS configuration enabled for dashboard pre-signed URL access
- Bucket policy restricts access to authorized IAM roles only

**Sub-tasks:**
- [ ] 2.1 Create S3 bucket with appropriate naming and region
- [ ] 2.2 Configure bucket versioning and lifecycle policies
- [ ] 2.3 Enable SSE-S3 encryption
- [ ] 2.4 Configure CORS for dashboard access
- [ ] 2.5 Create IAM policies for bucket access (PutObject, GetObject)
- [ ] 2.6 Write integration tests for S3 upload/download operations

**Dependencies:** None

**Estimated Effort:** 3 hours

---

#### Task 3: Sync Service Integration

**Description:** Implement atomic sync logic that writes metadata to DynamoDB and payloads to S3 with retry mechanisms and idempotency guarantees.

**Acceptance Criteria:**
- Sync service uploads payload to S3 first (idempotent operation)
- Sync service updates DynamoDB with S3 reference after successful upload
- Exponential backoff retry logic implemented (S3: max 3 retries, DynamoDB: max 5 retries)
- If DynamoDB write fails after S3 success, sync_status marked as "pending" for next cycle
- Deterministic S3 keys used (user_id + timestamp) to prevent duplicates
- Sync operations complete within 30 seconds of connectivity detection

**Sub-tasks:**
- [ ] 3.1 Implement S3 upload function with retry logic
- [ ] 3.2 Implement DynamoDB update function with retry logic
- [ ] 3.3 Create atomic sync orchestration function
- [ ] 3.4 Implement exponential backoff with jitter
- [ ] 3.5 Add idempotency checks using deterministic keys
- [ ] 3.6 Write unit tests for sync atomicity and retry scenarios
- [ ] 3.7 Write integration tests for partial failure scenarios

**Dependencies:** Task 1, Task 2

**Estimated Effort:** 8 hours

---

### Phase 2: API Layer & Quiz Generation

#### Task 4: API Gateway Quiz Endpoint

**Description:** Create API Gateway REST endpoint for quiz generation requests with IAM authentication, request validation, and throttling.

**Acceptance Criteria:**
- REST API created with resource `/generate-quiz` and POST method
- IAM (AWS_IAM) authorization configured
- Request validation enabled with schema enforcement
- Request schema validates: textbook_id (string), topic (string), difficulty (enum), num_questions (number 1-20)
- Response schema defined for success and error cases
- Throttling configured: 10 req/sec per teacher, burst 20, quota 1000/day
- Lambda proxy integration configured with 30-second timeout
- CORS headers configured for dashboard access

**Sub-tasks:**
- [ ] 4.1 Create API Gateway REST API
- [ ] 4.2 Define request/response models and schemas
- [ ] 4.3 Configure IAM authorization
- [ ] 4.4 Implement request validation
- [ ] 4.5 Configure throttling and quota limits
- [ ] 4.6 Set up Lambda proxy integration
- [ ] 4.7 Configure CORS settings
- [ ] 4.8 Write integration tests for authentication and validation

**Dependencies:** None

**Estimated Effort:** 5 hours

---

#### Task 5: Quiz Lambda Function

**Description:** Implement Lambda function that orchestrates Bedrock quiz generation, validates responses, stores to S3, and returns pre-signed URLs.

**Acceptance Criteria:**
- Lambda function created with Python 3.11 runtime, 512MB memory, 30-second timeout, arm64 architecture
- Environment variables configured: BEDROCK_MODEL_ID, S3_BUCKET_NAME, DYNAMODB_TABLE_NAME, LOG_LEVEL
- IAM permissions granted: bedrock:InvokeModel, s3:PutObject, logs:*, dynamodb:PutItem
- Function validates request payload (textbook_id, topic, difficulty, num_questions)
- Function retrieves textbook context from S3 if not in request
- Function constructs Bedrock prompt with pedagogical instructions
- Function invokes Bedrock (amazon.neo-lite-v2) and waits for complete response
- Function validates quiz JSON structure before storing
- Function generates unique quiz_id (UUID v4) and stores to S3 at quizzes/{quiz_id}.json
- Function generates pre-signed URL with 1-hour expiry
- Function logs all steps to CloudWatch with correlation ID
- Error handling implemented for: Bedrock throttling (429), validation errors (400), S3 failures (500), timeouts (504)

**Sub-tasks:**
- [ ] 5.1 Create Lambda function with runtime configuration
- [ ] 5.2 Implement request payload validation
- [ ] 5.3 Implement textbook context retrieval from S3
- [x] 5.4 Construct Bedrock prompt with pedagogical instructions
- [x] 5.5 Implement Bedrock invocation with error handling *(via Converse API, amazon.nova-2-lite-v1:0, ap-south-1)*
- [x] 5.6 Implement quiz JSON validation *(regex fence + brace-extraction fallback parser)*
- [ ] 5.7 Implement S3 storage with unique key generation
- [ ] 5.8 Implement pre-signed URL generation
- [ ] 5.9 Implement CloudWatch logging with correlation IDs
- [x] 5.10 Implement comprehensive error handling *(ValidationException, throttling, JSON parse errors)*
- [ ] 5.11 Write unit tests for all function logic
- [ ] 5.12 Write integration tests with mocked Bedrock responses

> **Note:** Steps 5.4–5.6 and 5.10 implemented directly in teacher dashboard
> (`utils/bedrock_client.py`) using the Bedrock **Converse API** (boto3 ≥ 1.34).
> Quiz + lesson notes generation working end-to-end with Word/PDF export.
> Lambda wrapper (5.1–5.3, 5.7–5.9) remains for future serverless deployment.

**Dependencies:** Task 2, Task 4

**Estimated Effort:** 12 hours

---

### Phase 3: Dashboard Hosting

#### Task 6: AWS Amplify Dashboard Deployment (Option A)

**Description:** Deploy Teacher Dashboard using AWS Amplify Gen 2 for static hosting with CloudFront CDN distribution.

**Acceptance Criteria:**
- Amplify app created and connected to repository
- Build configuration (amplify.yml) created with npm build commands
- Environment variables configured: REACT_APP_API_GATEWAY_URL, REACT_APP_DYNAMODB_TABLE, REACT_APP_S3_BUCKET
- CloudFront distribution automatically provisioned
- HTTPS endpoint provided for dashboard access
- Dashboard loads within 2 seconds under normal network conditions
- Dashboard integrates with DynamoDB for reading sync metadata
- Dashboard integrates with API Gateway for quiz generation
- Continuous deployment configured from main branch

**Sub-tasks:**
- [ ] 6.1 Create Amplify app and connect to repository
- [ ] 6.2 Configure amplify.yml build specification
- [ ] 6.3 Set environment variables in Amplify console
- [ ] 6.4 Configure IAM role for Amplify to access DynamoDB and S3
- [ ] 6.5 Deploy initial version and verify HTTPS endpoint
- [ ] 6.6 Test dashboard load time and functionality
- [ ] 6.7 Configure continuous deployment
- [ ] 6.8 Document deployment process

**Dependencies:** Task 1, Task 4

**Estimated Effort:** 6 hours

---

#### Task 7: ECS/EC2 Dashboard Deployment (Option B)

**Description:** Deploy containerized Teacher Dashboard on ECS Fargate or EC2 with Application Load Balancer for Streamlit applications requiring Python runtime.

**Acceptance Criteria:**
- Docker image created for Streamlit dashboard application
- ECR repository created and image pushed
- ECS task definition created: Family=teacher-dashboard, NetworkMode=awsvpc, Cpu=512, Memory=1024
- Container definition includes: Image from ECR, Port 8501, Environment variables (DYNAMODB_TABLE, S3_BUCKET)
- CloudWatch Logs configured for container logging
- IAM task role created with permissions for DynamoDB and S3 access
- IAM execution role created for ECS task execution
- Application Load Balancer created (internet-facing, HTTPS:443)
- ACM certificate provisioned for HTTPS
- Target group configured (IP targets, port 8501, health check /healthz)
- Security groups configured (ALB: allow 443 from 0.0.0.0/0, ECS: allow 8501 from ALB SG)
- ECS service created with Fargate launch type
- Dashboard accessible via HTTPS endpoint within 2 seconds

**Sub-tasks:**
- [ ] 7.1 Create Dockerfile for Streamlit dashboard
- [ ] 7.2 Build and test Docker image locally
- [ ] 7.3 Create ECR repository and push image
- [ ] 7.4 Create ECS task definition with container configuration
- [ ] 7.5 Create IAM task role and execution role
- [ ] 7.6 Configure CloudWatch Logs
- [ ] 7.7 Request/import ACM certificate for HTTPS
- [ ] 7.8 Create Application Load Balancer
- [ ] 7.9 Configure target group and health checks
- [ ] 7.10 Configure security groups
- [ ] 7.11 Create ECS service with Fargate launch type
- [ ] 7.12 Test dashboard access and functionality
- [ ] 7.13 Document deployment and scaling procedures

**Dependencies:** Task 1, Task 4

**Estimated Effort:** 10 hours

---

### Phase 4: Testing & Validation

#### Task 8: Property-Based Testing Implementation

**Description:** Implement property-based tests using Hypothesis (Python) to validate correctness properties across the infrastructure.

**Acceptance Criteria:**
- Property 1 (DynamoDB Schema Validation): Test validates all records contain user_id (PK), current_streak (Number), last_sync_timestamp (ISO 8601)
- Property 2 (Sync Atomicity): Test validates retry logic when S3 succeeds but DynamoDB fails
- Property 3 (Metadata Query Performance): Test validates DynamoDB reads complete within 100ms
- Property 4 (HTTPS Enforcement): Test validates all dashboard URLs use HTTPS protocol
- Property 5 (Dashboard Response Time): Test validates dashboard loads within 2 seconds
- Property 6 (Quiz Generation Workflow): Test validates end-to-end workflow returns S3 key within 30 seconds
- Property 7 (Quiz Error Handling): Test validates Lambda returns 500 when Bedrock fails
- Property 8 (API Authentication): Test validates API Gateway rejects requests without IAM credentials (403)
- Property 9 (Data Separation): Test validates metadata <4KB goes to DynamoDB, payloads >4KB go to S3
- Property 10 (Metadata-Only Queries): Test validates dashboard queries DynamoDB without S3 calls
- All tests run with minimum 100 iterations
- Tests include tagging comments referencing design document properties
- Test configuration includes 60-second timeout and shrinking enabled

**Sub-tasks:**
- [ ] 8.1 Set up Hypothesis testing framework
- [ ] 8.2 Implement Property 1: DynamoDB Schema Validation
- [ ] 8.3 Implement Property 2: Sync Atomicity with Retry
- [ ] 8.4 Implement Property 3: Metadata Query Performance
- [ ] 8.5 Implement Property 4: HTTPS Endpoint Enforcement
- [ ] 8.6 Implement Property 5: Dashboard Response Time
- [ ] 8.7 Implement Property 6: Quiz Generation End-to-End Workflow
- [ ] 8.8 Implement Property 7: Quiz Generation Error Handling
- [ ] 8.9 Implement Property 8: API Gateway Authentication
- [ ] 8.10 Implement Property 9: Data Separation by Size
- [ ] 8.11 Implement Property 10: Metadata-Only Query Optimization
- [ ] 8.12 Configure test suite with proper iterations and timeouts
- [ ] 8.13 Document property-based testing strategy

**Dependencies:** Task 1, Task 2, Task 3, Task 4, Task 5, Task 6 or Task 7

**Estimated Effort:** 16 hours

---

#### Task 9: Integration Testing

**Description:** Implement end-to-end integration tests for complete workflows across all infrastructure components.

**Acceptance Criteria:**
- Test 1: Teacher generates quiz → Bedrock creates content → Quiz stored in S3 → Dashboard displays quiz
- Test 2: Student completes session → Sync Service uploads to DynamoDB + S3 → Dashboard shows updated streak
- Test 3: Student goes offline → Edge AI continues tutoring → Connectivity restored → Sync uploads queued data
- Test environment uses AWS CDK to deploy isolated test stack
- Tests use DynamoDB Local for fast unit tests
- Tests use LocalStack for S3 mocking in CI/CD
- Tests use Bedrock sandbox environment for integration tests
- All tests pass with 95%+ success rate

**Sub-tasks:**
- [ ] 9.1 Set up test environment with AWS CDK
- [ ] 9.2 Configure DynamoDB Local for unit tests
- [ ] 9.3 Configure LocalStack for S3 mocking
- [ ] 9.4 Implement Test 1: Quiz generation workflow
- [ ] 9.5 Implement Test 2: Sync workflow
- [ ] 9.6 Implement Test 3: Offline-to-online workflow
- [ ] 9.7 Create test data fixtures
- [ ] 9.8 Document integration testing procedures

**Dependencies:** Task 1, Task 2, Task 3, Task 4, Task 5, Task 6 or Task 7

**Estimated Effort:** 12 hours

---

#### Task 10: Performance Testing

**Description:** Conduct load testing to validate performance benchmarks under concurrent load.

**Acceptance Criteria:**
- Load test scenario 1: 100 concurrent teachers accessing dashboard
- Load test scenario 2: 50 concurrent quiz generation requests
- Load test scenario 3: 1000 student devices syncing simultaneously
- DynamoDB read latency < 100ms (p99)
- Dashboard page load < 2 seconds (p95)
- Quiz generation < 30 seconds (p95)
- S3 upload < 5 seconds for 10MB payload (p95)
- CloudWatch Synthetics configured for dashboard availability monitoring
- Artillery or Locust configured for API Gateway load testing
- DynamoDB metrics tracked for read/write latency

**Sub-tasks:**
- [ ] 10.1 Set up Artillery or Locust for load testing
- [ ] 10.2 Configure CloudWatch Synthetics for dashboard monitoring
- [ ] 10.3 Execute load test scenario 1 (dashboard access)
- [ ] 10.4 Execute load test scenario 2 (quiz generation)
- [ ] 10.5 Execute load test scenario 3 (sync operations)
- [ ] 10.6 Collect and analyze performance metrics
- [ ] 10.7 Identify and document performance bottlenecks
- [ ] 10.8 Implement performance optimizations if needed
- [ ] 10.9 Document performance testing results

**Dependencies:** Task 1, Task 2, Task 3, Task 4, Task 5, Task 6 or Task 7

**Estimated Effort:** 10 hours

---

### Phase 5: Security & Monitoring

#### Task 11: Security Hardening

**Description:** Implement security best practices including authentication, encryption, and least-privilege IAM policies.

**Acceptance Criteria:**
- API Gateway rejects requests without valid IAM credentials
- Dashboard enforces HTTPS (HTTP redirects to HTTPS)
- IAM roles follow least-privilege principle
- S3 encryption at rest verified (SSE-S3)
- DynamoDB encryption with AWS-managed keys verified
- Pre-signed URLs expire after 1 hour
- Security group rules follow principle of least access
- XSS protection implemented in dashboard (input sanitization)
- CSRF protection implemented for quiz generation endpoint
- Security testing completed with no critical vulnerabilities

**Sub-tasks:**
- [ ] 11.1 Verify API Gateway IAM authentication
- [ ] 11.2 Configure HTTPS enforcement on dashboard
- [ ] 11.3 Review and optimize IAM policies for least privilege
- [ ] 11.4 Verify S3 and DynamoDB encryption settings
- [ ] 11.5 Implement pre-signed URL expiration
- [ ] 11.6 Review and optimize security group rules
- [ ] 11.7 Implement XSS protection in dashboard
- [ ] 11.8 Implement CSRF protection for API endpoints
- [ ] 11.9 Conduct security testing and penetration testing
- [ ] 11.10 Document security architecture and best practices

**Dependencies:** Task 1, Task 2, Task 4, Task 5, Task 6 or Task 7

**Estimated Effort:** 8 hours

---

#### Task 12: Monitoring & Logging

**Description:** Implement comprehensive monitoring and logging using CloudWatch for operational visibility.

**Acceptance Criteria:**
- CloudWatch Logs configured for Lambda function with correlation IDs
- CloudWatch Logs configured for ECS containers (if using Option B)
- CloudWatch metrics tracked for: DynamoDB read/write latency, API Gateway request count, Lambda invocation count, S3 upload/download operations
- CloudWatch alarms configured for: Lambda errors, API Gateway 5xx errors, DynamoDB throttling, S3 access denied errors
- CloudWatch dashboard created showing key metrics
- Log retention policies configured (30 days for Lambda, 90 days for audit logs)
- Structured logging implemented with JSON format
- Error logs include sufficient context for debugging

**Sub-tasks:**
- [ ] 12.1 Configure CloudWatch Logs for Lambda function
- [ ] 12.2 Configure CloudWatch Logs for ECS containers (if applicable)
- [ ] 12.3 Set up CloudWatch metrics for all services
- [ ] 12.4 Create CloudWatch alarms for critical errors
- [ ] 12.5 Build CloudWatch dashboard for operational visibility
- [ ] 12.6 Configure log retention policies
- [ ] 12.7 Implement structured logging with JSON format
- [ ] 12.8 Test alarm notifications
- [ ] 12.9 Document monitoring and alerting procedures

**Dependencies:** Task 1, Task 2, Task 3, Task 4, Task 5, Task 6 or Task 7

**Estimated Effort:** 6 hours

---

### Phase 6: Documentation & Deployment

#### Task 13: Infrastructure as Code

**Description:** Create reusable Infrastructure as Code templates using AWS CDK or CloudFormation for reproducible deployments.

**Acceptance Criteria:**
- CDK or CloudFormation templates created for all infrastructure components
- Templates parameterized for different environments (dev, staging, prod)
- Templates include: DynamoDB table, S3 bucket, API Gateway, Lambda function, IAM roles, Amplify app or ECS service
- Deployment scripts created for automated provisioning
- Rollback procedures documented
- Templates validated and tested in isolated environment
- Version control applied to all IaC templates

**Sub-tasks:**
- [ ] 13.1 Create CDK/CloudFormation template for DynamoDB
- [ ] 13.2 Create CDK/CloudFormation template for S3
- [ ] 13.3 Create CDK/CloudFormation template for API Gateway
- [ ] 13.4 Create CDK/CloudFormation template for Lambda
- [ ] 13.5 Create CDK/CloudFormation template for IAM roles
- [ ] 13.6 Create CDK/CloudFormation template for Amplify or ECS
- [ ] 13.7 Parameterize templates for multiple environments
- [ ] 13.8 Create deployment scripts
- [ ] 13.9 Test templates in isolated environment
- [ ] 13.10 Document deployment and rollback procedures

**Dependencies:** Task 1, Task 2, Task 4, Task 5, Task 6 or Task 7

**Estimated Effort:** 10 hours

---

#### Task 14: Documentation

**Description:** Create comprehensive documentation for architecture, deployment, operations, and troubleshooting.

**Acceptance Criteria:**
- Architecture documentation includes: system diagrams, data flow diagrams, component descriptions
- Deployment documentation includes: step-by-step deployment guide, environment setup, configuration parameters
- Operations documentation includes: monitoring procedures, common issues and resolutions, scaling guidelines
- API documentation includes: endpoint specifications, request/response schemas, authentication requirements
- Troubleshooting guide includes: common errors, debugging procedures, log analysis
- Cost optimization guide includes: resource sizing recommendations, cost monitoring procedures
- All documentation reviewed and validated by team

**Sub-tasks:**
- [ ] 14.1 Create architecture documentation with diagrams
- [ ] 14.2 Create deployment guide
- [ ] 14.3 Create operations runbook
- [ ] 14.4 Create API documentation
- [ ] 14.5 Create troubleshooting guide
- [ ] 14.6 Create cost optimization guide
- [ ] 14.7 Review and validate all documentation
- [ ] 14.8 Publish documentation to team wiki or repository

**Dependencies:** All previous tasks

**Estimated Effort:** 8 hours

---

## Summary

**Total Tasks:** 14 main tasks with 150+ sub-tasks
**Total Estimated Effort:** ~118 hours
**Critical Path:** Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6/7 → Task 8 → Task 9 → Task 10 → Task 11 → Task 12 → Task 13 → Task 14

**Key Milestones:**
1. Data Layer Complete (Tasks 1-3): Foundation for sync operations
2. API Layer Complete (Tasks 4-5): Quiz generation workflow functional
3. Dashboard Deployed (Task 6 or 7): Teacher interface accessible
4. Testing Complete (Tasks 8-10): Quality and performance validated
5. Production Ready (Tasks 11-14): Security, monitoring, and documentation complete

**Risk Mitigation:**
- Parallel execution of independent tasks (e.g., Task 1 and Task 2 can run concurrently)
- Early integration testing to catch issues before final deployment
- Comprehensive property-based testing to validate correctness properties
- Infrastructure as Code for reproducible deployments and easy rollback
