# Requirements Document

## Introduction

This document specifies requirements for elevating the StudAxis EdTech platform's AWS infrastructure from Phase 2 to MVP level for hackathon submission. The system implements a Dual-Brain Architecture where Amazon Bedrock serves as the Strategic Cloud Brain for content generation, while local Ollama provides edge AI for offline learning. The elevation focuses on integrating DynamoDB for sync metadata, Amplify for teacher dashboard hosting, API Gateway + Lambda for quiz generation workflows, and optional ECS/EC2 for containerized dashboard deployment.

## Glossary

- **StudAxis_Platform**: The EdTech application implementing Dual-Brain Architecture
- **Strategic_Cloud_Brain**: Amazon Bedrock service generating curriculum content from textbooks
- **Edge_AI**: Local Ollama instance providing offline tutoring capabilities
- **Teacher_Dashboard**: Streamlit-based web interface for educators to manage content and view analytics
- **Sync_Metadata**: Lightweight state information (User ID, Current Streak, Last Sync Timestamp)
- **Heavy_Payload**: Large files including PDFs and raw chat logs
- **Quiz_Generation_Workflow**: Process where teachers request AI-generated quizzes via Bedrock
- **DynamoDB_State_Store**: Amazon DynamoDB table storing sync metadata for global state
- **S3_Payload_Store**: Amazon S3 bucket storing heavy payloads
- **API_Gateway_Endpoint**: Amazon API Gateway REST endpoint fronting Lambda functions
- **Quiz_Lambda**: AWS Lambda function orchestrating Bedrock quiz generation
- **Dashboard_Host**: AWS Amplify or ECS/EC2 infrastructure hosting Teacher_Dashboard
- **Sync_Service**: Component managing synchronization between cloud and edge devices

## Requirements

### Requirement 1: DynamoDB Sync Metadata Storage

**User Story:** As a system architect, I want to store lightweight sync metadata in DynamoDB, so that teacher dashboards can query global state efficiently without processing heavy S3 payloads.

#### Acceptance Criteria

1. THE DynamoDB_State_Store SHALL store User ID as the partition key
2. THE DynamoDB_State_Store SHALL store Current Streak as a numeric attribute
3. THE DynamoDB_State_Store SHALL store Last Sync Timestamp as an ISO 8601 timestamp attribute
4. WHEN Sync_Service completes synchronization, THE Sync_Service SHALL update the corresponding record in DynamoDB_State_Store
5. THE S3_Payload_Store SHALL continue storing Heavy_Payload items
6. WHEN Teacher_Dashboard queries student state, THE Teacher_Dashboard SHALL read from DynamoDB_State_Store within 100ms
7. FOR ALL sync operations, writing metadata to DynamoDB_State_Store and payload to S3_Payload_Store SHALL complete atomically or provide retry logic

### Requirement 2: AWS Amplify Dashboard Hosting

**User Story:** As a teacher, I want to access the dashboard through a cloud-hosted URL, so that I can manage content and view analytics without running local infrastructure.

#### Acceptance Criteria

1. THE Dashboard_Host SHALL deploy Teacher_Dashboard using AWS Amplify Gen 2
2. WHERE Teacher_Dashboard requires containerization, THE Dashboard_Host SHALL support container-based deployment
3. WHERE Teacher_Dashboard uses static React wrapper, THE Dashboard_Host SHALL serve static assets via Amplify hosting
4. WHEN a teacher accesses the dashboard URL, THE Dashboard_Host SHALL serve the Teacher_Dashboard within 2 seconds
5. THE Dashboard_Host SHALL provide HTTPS endpoints for all dashboard access
6. THE Dashboard_Host SHALL integrate with DynamoDB_State_Store for reading sync metadata

### Requirement 3: API Gateway Quiz Generation Endpoint

**User Story:** As a teacher, I want to click "Generate Quiz" and receive AI-generated content, so that I can create assessments without manual authoring.

#### Acceptance Criteria

1. THE API_Gateway_Endpoint SHALL expose a POST endpoint for quiz generation requests
2. WHEN a teacher submits a quiz generation request, THE API_Gateway_Endpoint SHALL invoke Quiz_Lambda
3. THE Quiz_Lambda SHALL call Amazon Bedrock to generate quiz content
4. WHEN Amazon Bedrock returns quiz content, THE Quiz_Lambda SHALL save the result to S3_Payload_Store
5. THE Quiz_Lambda SHALL return a reference URL or object key to the requesting client within 30 seconds
6. IF Amazon Bedrock fails to generate content, THEN THE Quiz_Lambda SHALL return an error response with status code 500
7. THE API_Gateway_Endpoint SHALL implement authentication to restrict access to authorized teachers

### Requirement 4: S3 and DynamoDB Data Separation

**User Story:** As a system architect, I want to separate lightweight metadata from heavy payloads, so that dashboard queries remain fast and cost-efficient.

#### Acceptance Criteria

1. THE Sync_Service SHALL store sync metadata records smaller than 4KB in DynamoDB_State_Store
2. THE Sync_Service SHALL store Heavy_Payload items in S3_Payload_Store
3. WHEN storing a new sync record, THE Sync_Service SHALL write metadata to DynamoDB_State_Store and payload reference to S3_Payload_Store
4. THE Teacher_Dashboard SHALL retrieve sync metadata from DynamoDB_State_Store without accessing S3_Payload_Store
5. WHERE Teacher_Dashboard requires Heavy_Payload access, THE Teacher_Dashboard SHALL fetch from S3_Payload_Store using the stored reference

### Requirement 5: Optional ECS/EC2 Dashboard Deployment

**User Story:** As a system architect, I want the option to deploy Teacher_Dashboard on ECS or EC2, so that I can support containerized Streamlit applications that cannot run on Amplify static hosting.

#### Acceptance Criteria

1. WHERE Teacher_Dashboard requires container runtime, THE Dashboard_Host SHALL support deployment on AWS ECS Fargate
2. WHERE Teacher_Dashboard requires container runtime, THE Dashboard_Host SHALL support deployment on Amazon EC2 instances
3. WHERE ECS deployment is used, THE Dashboard_Host SHALL run on a small ECS cluster with Fargate launch type
4. WHERE EC2 deployment is used, THE Dashboard_Host SHALL use t3.small or t3.micro instance types
5. WHERE containerized deployment is used, THE Dashboard_Host SHALL sit behind an Application Load Balancer
6. THE containerized Teacher_Dashboard SHALL connect to DynamoDB_State_Store and S3_Payload_Store using IAM roles

### Requirement 6: AWS Generative AI Value Proposition Documentation

**User Story:** As a hackathon judge, I want to understand why AI is required, how AWS services are used, and what value the AI layer adds, so that I can evaluate the technical merit and innovation of the solution.

#### Acceptance Criteria

1. THE requirements document SHALL include a section titled "AWS Generative AI Value Proposition"
2. THE value proposition section SHALL answer "Why is AI required?" by explaining that rule-based systems cannot evaluate subjective free-form answers or provide contextual explanations
3. THE value proposition section SHALL explain that generative AI enables personalized 1-on-1 pedagogical feedback, semantic grading, and adaptive difficulty
4. THE value proposition section SHALL answer "How are AWS services used?" by describing the Dual-Brain Architecture with Amazon Bedrock as Strategic_Cloud_Brain
5. THE value proposition section SHALL explain the role of AWS AppSync, Lambda, API_Gateway_Endpoint, and DynamoDB_State_Store in managing intermittent sync state
6. THE value proposition section SHALL answer "What value does the AI layer add?" by explaining elimination of connectivity dependency
7. THE value proposition section SHALL explain that the AWS AI layer empowers a single educator to generate tailored curriculum for thousands of students simultaneously
8. THE value proposition section SHALL explain that Edge_AI delivers curriculum at 0 kbps, transforming low-cost government laptops into autonomous smart-tutors

### Requirement 7: Quiz Generation Workflow Integration

**User Story:** As a teacher, I want the quiz generation workflow to be reliable and traceable, so that I can trust the system to deliver content and debug issues when they occur.

#### Acceptance Criteria

1. WHEN a teacher clicks "Generate Quiz", THE Teacher_Dashboard SHALL send a request to API_Gateway_Endpoint
2. THE API_Gateway_Endpoint SHALL validate the request payload before invoking Quiz_Lambda
3. THE Quiz_Lambda SHALL log the request to Amazon CloudWatch Logs
4. WHEN Quiz_Lambda invokes Amazon Bedrock, THE Quiz_Lambda SHALL include the textbook context in the prompt
5. WHEN Amazon Bedrock returns quiz content, THE Quiz_Lambda SHALL validate the response format
6. THE Quiz_Lambda SHALL store the generated quiz in S3_Payload_Store with a unique object key
7. THE Quiz_Lambda SHALL return the S3 object key to Teacher_Dashboard via API_Gateway_Endpoint
8. IF any step fails, THEN THE Quiz_Lambda SHALL log the error and return a descriptive error message

### Requirement 8: Connectivity-Independent Architecture Preservation

**User Story:** As a student in a low-connectivity environment, I want to continue learning offline after initial sync, so that network availability does not block my education.

#### Acceptance Criteria

1. THE StudAxis_Platform SHALL support offline learning after initial content synchronization
2. THE Edge_AI SHALL provide tutoring capabilities without network connectivity
3. WHEN network connectivity is available, THE Sync_Service SHALL synchronize student progress to DynamoDB_State_Store
4. WHEN network connectivity is unavailable, THE Edge_AI SHALL continue operating using locally cached content
5. THE Strategic_Cloud_Brain SHALL generate new content only when network connectivity is available
6. WHEN connectivity is restored after offline period, THE Sync_Service SHALL upload accumulated progress data to DynamoDB_State_Store and S3_Payload_Store

---

## AWS Generative AI Value Proposition

### Why is AI Required?

Rule-based systems cannot evaluate subjective, free-form student answers or provide contextual explanations tailored to individual learning gaps. Traditional EdTech relies on multiple-choice questions and rigid scoring rubrics that fail to assess deeper understanding. Generative AI is the only technology capable of providing personalized, 1-on-1 pedagogical feedback, semantic grading of open-ended responses, and adaptive difficulty adjustment based on student performance patterns. Without AI, the system would be limited to static content delivery with no ability to understand or respond to student needs.

### How are AWS Services Used?

The StudAxis platform implements a Dual-Brain Architecture where Amazon Bedrock serves as the Strategic Cloud Brain, processing raw textbooks to auto-generate quizzes, micro-learning units, and adaptive assessments. Kiro enables spec-driven infrastructure deployment, ensuring consistent and reproducible AWS resource provisioning. AWS AppSync, Lambda, API Gateway, and DynamoDB manage intermittent sync state and content delivery to edge devices. When connectivity is available, the cloud brain generates personalized curriculum at scale; when offline, the edge brain (local Ollama) delivers that curriculum using cached models. This architecture separates content generation (cloud-intensive) from content delivery (edge-optimized).

### What Value Does the AI Layer Add?

The AI layer eliminates the connectivity dependency that plagues modern EdTech solutions, which typically require constant internet access. By leveraging AWS generative AI services, a single educator can generate tailored curriculum for thousands of students simultaneously—a task impossible with manual authoring. The Edge AI component delivers this curriculum at 0 kbps bandwidth, transforming $200 government-issued laptops into fully autonomous smart-tutors capable of providing Socratic dialogue, instant feedback, and adaptive learning paths. This combination of cloud-scale content generation and edge-based delivery democratizes access to high-quality, personalized education in low-resource environments where connectivity is unreliable or unavailable.
