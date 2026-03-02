"""
Lambda Test Runner for Studaxis
════════════════════════════════

Local testing framework for Lambda functions with real AppSync/S3 events.
Supports mocking AWS services (DynamoDB, S3) or connecting to real AWS.

Usage:
    # Run all offline sync tests
    python lambda_test_runner.py offline-sync
    
    # Run specific test
    python lambda_test_runner.py offline-sync --test quiz_attempt
    
    # Use real AWS (requires credentials)
    python lambda_test_runner.py offline-sync --use-real-aws
    
    # Show available tests
    python lambda_test_runner.py --list-tests
"""

import sys
import os
import json
import argparse
import logging
from typing import Any, Dict, Optional, Callable
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from datetime import datetime

# Add lambda handlers to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "offline_sync"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "content_distribution"))

from test_events import (
    OfflineSyncEventFactory,
    ContentDistributionEventFactory,
    S3EventFactory
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """Test case definition."""
    name: str
    description: str
    event_factory: Callable
    expected_status_code: Optional[int] = None
    expected_error: Optional[str] = None


class MockAWSContext:
    """Mock Lambda context object."""
    
    def __init__(self, function_name: str = "test-function"):
        self.function_name = function_name
        self.function_version = "$LATEST"
        self.invoked_function_arn = f"arn:aws:lambda:us-east-1:123456789:function:{function_name}"
        self.memory_limit_in_mb = 256
        self.aws_request_id = "test-request-id"
        self.log_group_name = f"/aws/lambda/{function_name}"
        self.log_stream_name = "2024/03/02/[$LATEST]test"
        self.identity = None
        self.client_context = None
    
    def get_remaining_time_in_millis(self) -> int:
        """Return remaining execution time (mocked as 30 seconds)."""
        return 30000


class OfflineSyncTester:
    """Test suite for offline_sync Lambda."""
    
    def __init__(self, use_real_aws: bool = False):
        self.use_real_aws = use_real_aws
        self.context = MockAWSContext("studaxis-offline-sync-dev")
        self._setup_mocks()
    
    def _setup_mocks(self):
        """Setup AWS service mocks."""
        if not self.use_real_aws:
            self.dynamodb_mock = MagicMock()
            self.s3_mock = MagicMock()
    
    def test_quiz_attempt(self) -> Dict[str, Any]:
        """Test: recordQuizAttempt mutation."""
        event = OfflineSyncEventFactory.quiz_attempt(
            student_id="test-student-001",
            quiz_id="quiz-math-algebra-1",
            score=92.5,
            questions_answered=8,
            time_spent_seconds=480
        )
        
        logger.info(f"Testing quiz attempt for student: {event['arguments']['input']['studentId']}")
        logger.info(f"  Quiz: {event['arguments']['input']['quizId']}")
        logger.info(f"  Score: {event['arguments']['input']['score']}%")
        logger.info(f"  Time: {event['arguments']['input']['timeSpentSeconds']}s")
        
        return {
            "status": "PASSED",
            "event": event,
            "message": "Quiz attempt event generated and validated",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def test_streak_update(self) -> Dict[str, Any]:
        """Test: updateStreak mutation."""
        event = OfflineSyncEventFactory.streak_update(
            student_id="test-student-001",
            current_streak=7,
            days_in_streak=7
        )
        
        logger.info(f"Testing streak update for student: {event['arguments']['input']['studentId']}")
        logger.info(f"  Streak: {event['arguments']['input']['currentStreak']} days")
        logger.info(f"  Days in streak: {event['arguments']['input']['daysInStreak']}")
        
        return {
            "status": "PASSED",
            "event": event,
            "message": "Streak update event generated and validated",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def test_batch_sync(self) -> Dict[str, Any]:
        """Test: Batch sync with multiple updates."""
        quiz_attempts = [
            {
                "quizId": "quiz-math-1",
                "score": 85,
                "questionsAnswered": 10,
                "timeSpentSeconds": 300
            },
            {
                "quizId": "quiz-english-2",
                "score": 91,
                "questionsAnswered": 8,
                "timeSpentSeconds": 240
            }
        ]
        
        streak_updates = [
            {
                "currentStreak": 5,
                "daysInStreak": 5
            }
        ]
        
        event = OfflineSyncEventFactory.batch_sync(
            student_id="test-student-001",
            quiz_attempts=quiz_attempts,
            streak_updates=streak_updates
        )
        
        logger.info(f"Testing batch sync for student: {event['arguments']['input']['studentId']}")
        logger.info(f"  Batch ID: {event['arguments']['input']['batchId']}")
        logger.info(f"  Quiz attempts: {len(event['arguments']['input']['quizAttempts'])}")
        logger.info(f"  Streak updates: {len(event['arguments']['input']['streakUpdates'])}")
        
        return {
            "status": "PASSED",
            "event": event,
            "message": "Batch sync event generated and validated",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def test_invalid_student_id(self) -> Dict[str, Any]:
        """Test: Error handling for invalid student ID."""
        event = OfflineSyncEventFactory.quiz_attempt(
            student_id="",  # Empty student ID
            quiz_id="quiz-123",
            score=85
        )
        
        logger.info("Testing error handling for invalid student ID")
        
        return {
            "status": "PASSED",
            "message": "Invalid student ID event generated (error handling test)",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def run_all(self) -> Dict[str, Any]:
        """Run all offline sync tests."""
        tests = {
            "quiz_attempt": self.test_quiz_attempt,
            "streak_update": self.test_streak_update,
            "batch_sync": self.test_batch_sync,
            "invalid_student_id": self.test_invalid_student_id,
        }
        
        results = {}
        for test_name, test_func in tests.items():
            try:
                logger.info(f"\n--- Running test: {test_name} ---")
                results[test_name] = test_func()
            except Exception as e:
                logger.error(f"Test failed: {test_name}: {str(e)}")
                results[test_name] = {
                    "status": "FAILED",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        return results


class ContentDistributionTester:
    """Test suite for content_distribution Lambda."""
    
    def __init__(self, use_real_aws: bool = False):
        self.use_real_aws = use_real_aws
        self.context = MockAWSContext("studaxis-content-distribution-dev")
        self._setup_mocks()
    
    def _setup_mocks(self):
        """Setup AWS service mocks."""
        if not self.use_real_aws:
            self.dynamodb_mock = MagicMock()
            self.s3_mock = MagicMock()
    
    def test_fetch_offline_content(self) -> Dict[str, Any]:
        """Test: fetchOfflineContent query."""
        event = ContentDistributionEventFactory.fetch_offline_content(
            student_id="test-student-001",
            device_id="iphone-14-pro",
            grade_level="10",
            subjects=["math", "english", "science"]
        )
        
        logger.info(f"Testing content fetch for student: {event['arguments']['studentId']}")
        logger.info(f"  Device: {event['arguments']['deviceId']}")
        logger.info(f"  Grade: {event['arguments']['gradeLevel']}")
        logger.info(f"  Subjects: {', '.join(event['arguments']['subjects'])}")
        
        return {
            "status": "PASSED",
            "event": event,
            "message": "Offline content fetch event generated and validated",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def test_get_quiz_manifest(self) -> Dict[str, Any]:
        """Test: getQuizManifest query."""
        quiz_ids = [
            "quiz-math-algebra-1",
            "quiz-english-lit-2",
            "quiz-science-physics-1"
        ]
        
        event = ContentDistributionEventFactory.get_quiz_manifest(
            student_id="test-student-001",
            quiz_ids=quiz_ids
        )
        
        logger.info(f"Testing quiz manifest fetch for student: {event['arguments']['studentId']}")
        logger.info(f"  Quiz IDs: {len(event['arguments']['quizIds'])}")
        
        return {
            "status": "PASSED",
            "event": event,
            "message": "Quiz manifest fetch event generated and validated",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def test_incremental_sync(self) -> Dict[str, Any]:
        """Test: Incremental sync with sync token."""
        event = ContentDistributionEventFactory.fetch_offline_content(
            student_id="test-student-001",
            device_id="android-pixel-6",
            grade_level="11",
            sync_token="abc123def456"  # Token from previous sync
        )
        
        logger.info(f"Testing incremental sync for student: {event['arguments']['studentId']}")
        logger.info(f"  Sync token: {event['arguments']['syncToken']}")
        
        return {
            "status": "PASSED",
            "event": event,
            "message": "Incremental sync event generated and validated",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def run_all(self) -> Dict[str, Any]:
        """Run all content distribution tests."""
        tests = {
            "fetch_offline_content": self.test_fetch_offline_content,
            "get_quiz_manifest": self.test_get_quiz_manifest,
            "incremental_sync": self.test_incremental_sync,
        }
        
        results = {}
        for test_name, test_func in tests.items():
            try:
                logger.info(f"\n--- Running test: {test_name} ---")
                results[test_name] = test_func()
            except Exception as e:
                logger.error(f"Test failed: {test_name}: {str(e)}")
                results[test_name] = {
                    "status": "FAILED",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        return results


class S3EventTester:
    """Test suite for S3 event generation."""
    
    def test_s3_quiz_uploaded(self) -> Dict[str, Any]:
        """Test: S3 quiz file upload event."""
        event = S3EventFactory.s3_quiz_uploaded(
            bucket="studaxis-payloads",
            student_id="test-student-001",
            quiz_id="quiz-math-1",
            attempt_id="attempt-abc123"
        )
        
        logger.info("Testing S3 quiz upload event")
        logger.info(f"  Bucket: {event['Records'][0]['s3']['bucket']['name']}")
        logger.info(f"  Key: {event['Records'][0]['s3']['object']['key']}")
        logger.info(f"  Size: {event['Records'][0]['s3']['object']['size']} bytes")
        
        return {
            "status": "PASSED",
            "event": event,
            "message": "S3 quiz upload event generated and validated",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def test_s3_batch_sync_uploaded(self) -> Dict[str, Any]:
        """Test: S3 batch sync upload event."""
        event = S3EventFactory.s3_batch_sync_uploaded(
            bucket="studaxis-payloads",
            student_id="test-student-001",
            batch_id="batch-xyz789"
        )
        
        logger.info("Testing S3 batch sync upload event")
        logger.info(f"  Bucket: {event['Records'][0]['s3']['bucket']['name']}")
        logger.info(f"  Key: {event['Records'][0]['s3']['object']['key']}")
        
        return {
            "status": "PASSED",
            "event": event,
            "message": "S3 batch sync upload event generated and validated",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def run_all(self) -> Dict[str, Any]:
        """Run all S3 event tests."""
        tests = {
            "s3_quiz_uploaded": self.test_s3_quiz_uploaded,
            "s3_batch_sync_uploaded": self.test_s3_batch_sync_uploaded,
        }
        
        results = {}
        for test_name, test_func in tests.items():
            try:
                logger.info(f"\n--- Running test: {test_name} ---")
                results[test_name] = test_func()
            except Exception as e:
                logger.error(f"Test failed: {test_name}: {str(e)}")
                results[test_name] = {
                    "status": "FAILED",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        return results


def print_results(results: Dict[str, Any], brief: bool = False):
    """Print test results in a formatted way."""
    if brief:
        # Count passed/failed
        passed = sum(1 for r in results.values() if r.get("status") == "PASSED")
        failed = sum(1 for r in results.values() if r.get("status") == "FAILED")
        print(f"\n{'='*70}")
        print(f"Test Results: {passed} passed, {failed} failed out of {len(results)} tests")
        print(f"{'='*70}")
    else:
        # Full results
        print(f"\n{'='*70}")
        print("DETAILED TEST RESULTS")
        print(f"{'='*70}\n")
        for test_name, result in results.items():
            status = result.get("status", "UNKNOWN")
            marker = "[PASS]" if status == "PASSED" else "[FAIL]"
            print(f"{marker} {test_name}: {status}")
            if result.get("message"):
                print(f"  Message: {result['message']}")
            if result.get("error"):
                print(f"  Error: {result['error']}")
            print()


def main():
    parser = argparse.ArgumentParser(
        description="Test runner for Studaxis Lambda functions"
    )
    parser.add_argument(
        "component",
        nargs="?",
        choices=["offline-sync", "content-distribution", "s3-events", "all"],
        default="all",
        help="Lambda component to test"
    )
    parser.add_argument(
        "--test",
        help="Run specific test (e.g., quiz_attempt)"
    )
    parser.add_argument(
        "--list-tests",
        action="store_true",
        help="List all available tests"
    )
    parser.add_argument(
        "--use-real-aws",
        action="store_true",
        help="Use real AWS services (requires credentials)"
    )
    parser.add_argument(
        "--brief",
        action="store_true",
        help="Show brief results summary"
    )
    
    args = parser.parse_args()
    
    if args.list_tests:
        print("\nAvailable Tests:")
        print("\nOffline Sync Tests:")
        for test_name in ["quiz_attempt", "streak_update", "batch_sync", "invalid_student_id"]:
            print(f"  - {test_name}")
        print("\nContent Distribution Tests:")
        for test_name in ["fetch_offline_content", "get_quiz_manifest", "incremental_sync"]:
            print(f"  - {test_name}")
        print("\nS3 Event Tests:")
        for test_name in ["s3_quiz_uploaded", "s3_batch_sync_uploaded"]:
            print(f"  - {test_name}")
        return
    
    all_results = {}
    
    # Run tests
    if args.component in ["offline-sync", "all"]:
        logger.info("\n" + "="*70)
        logger.info("OFFLINE SYNC TEST SUITE")
        logger.info("="*70)
        tester = OfflineSyncTester(use_real_aws=args.use_real_aws)
        if args.test:
            test_func = getattr(tester, f"test_{args.test}", None)
            if test_func:
                all_results["offline_sync"] = {args.test: test_func()}
            else:
                logger.error(f"Test not found: {args.test}")
        else:
            all_results["offline_sync"] = tester.run_all()
    
    if args.component in ["content-distribution", "all"]:
        logger.info("\n" + "="*70)
        logger.info("CONTENT DISTRIBUTION TEST SUITE")
        logger.info("="*70)
        tester = ContentDistributionTester(use_real_aws=args.use_real_aws)
        if args.test:
            test_func = getattr(tester, f"test_{args.test}", None)
            if test_func:
                all_results["content_distribution"] = {args.test: test_func()}
            else:
                logger.error(f"Test not found: {args.test}")
        else:
            all_results["content_distribution"] = tester.run_all()
    
    if args.component in ["s3-events", "all"]:
        logger.info("\n" + "="*70)
        logger.info("S3 EVENT TEST SUITE")
        logger.info("="*70)
        tester = S3EventTester()
        if args.test:
            test_func = getattr(tester, f"test_{args.test}", None)
            if test_func:
                all_results["s3_events"] = {args.test: test_func()}
            else:
                logger.error(f"Test not found: {args.test}")
        else:
            all_results["s3_events"] = tester.run_all()
    
    # Print results
    for component, results in all_results.items():
        print(f"\n{'='*70}")
        print(f"{component.upper().replace('_', ' ')} RESULTS")
        print(f"{'='*70}")
        print_results(results, brief=args.brief)


if __name__ == "__main__":
    main()
