"""
Test Event Generators for Studaxis Lambda Functions
═════════════════════════════════════════════════════

Generates realistic AppSync and S3 events for local Lambda testing.
Use with SAM local start-api or by invoking handlers directly.

Examples:
    # Generate offline sync event
    event = OfflineSyncEventFactory.quiz_attempt(
        student_id="student-123",
        quiz_id="quiz-456",
        score=92.5
    )
    
    # Generate content distribution event
    event = ContentDistributionEventFactory.fetch_offline_content(
        student_id="student-123",
        device_id="iphone-xyz"
    )
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from decimal import Decimal


class OfflineSyncEventFactory:
    """Generate AppSync events for offline_sync Lambda."""
    
    @staticmethod
    def quiz_attempt(
        student_id: str,
        quiz_id: str,
        score: float,
        questions_answered: int = 10,
        time_spent_seconds: int = 300,
        attempt_timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate recordQuizAttempt mutation event.
        
        Args:
            student_id: Unique student identifier
            quiz_id: Quiz being attempted
            score: Percentage score (0-100)
            questions_answered: Number of questions answered
            time_spent_seconds: Time spent on quiz
            attempt_timestamp: ISO timestamp (defaults to now)
        
        Returns:
            AppSync mutation event dict
        """
        timestamp = attempt_timestamp or datetime.now(timezone.utc).isoformat()
        
        return {
            "identity": {
                "claims": {
                    "sub": student_id,
                    "cognito:username": f"user#{student_id}"
                }
            },
            "arguments": {
                "input": {
                    "studentId": student_id,
                    "quizId": quiz_id,
                    "score": score,
                    "questionsAnswered": questions_answered,
                    "timeSpentSeconds": time_spent_seconds,
                    "attemptedAt": timestamp,
                    "deviceId": f"device-{uuid.uuid4().hex[:8]}",
                    "offlineAttempt": True
                }
            },
            "request": {
                "headers": {
                    "x-amzn-appsync-operation": "Mutation",
                    "x-appsync-request-id": uuid.uuid4().hex
                }
            },
            "prev": None
        }
    
    @staticmethod
    def streak_update(
        student_id: str,
        current_streak: int,
        days_in_streak: int,
        last_activity: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate updateStreak mutation event.
        
        Args:
            student_id: Unique student identifier
            current_streak: Current streak count
            days_in_streak: Days in current streak
            last_activity: ISO timestamp of last activity
        
        Returns:
            AppSync mutation event dict
        """
        last_activity = last_activity or datetime.now(timezone.utc).isoformat()
        
        return {
            "identity": {
                "claims": {
                    "sub": student_id,
                    "cognito:username": f"user#{student_id}"
                }
            },
            "arguments": {
                "input": {
                    "studentId": student_id,
                    "currentStreak": current_streak,
                    "daysInStreak": days_in_streak,
                    "lastActivity": last_activity,
                    "offlineUpdate": True
                }
            },
            "request": {
                "headers": {
                    "x-amzn-appsync-operation": "Mutation",
                    "x-appsync-request-id": uuid.uuid4().hex
                }
            },
            "prev": None
        }
    
    @staticmethod
    def batch_sync(
        student_id: str,
        quiz_attempts: List[Dict[str, Any]],
        streak_updates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate batch sync event (multiple updates at once).
        
        Args:
            student_id: Student ID
            quiz_attempts: List of quiz attempts
            streak_updates: List of streak updates
        
        Returns:
            AppSync batch mutation event
        """
        return {
            "identity": {
                "claims": {
                    "sub": student_id,
                    "cognito:username": f"user#{student_id}"
                }
            },
            "arguments": {
                "input": {
                    "studentId": student_id,
                    "batchId": uuid.uuid4().hex,
                    "quizAttempts": quiz_attempts,
                    "streakUpdates": streak_updates,
                    "syncedAt": datetime.now(timezone.utc).isoformat()
                }
            },
            "request": {
                "headers": {
                    "x-amzn-appsync-operation": "Mutation",
                    "x-appsync-request-id": uuid.uuid4().hex
                }
            },
            "prev": None
        }


class ContentDistributionEventFactory:
    """Generate AppSync events for content_distribution Lambda."""
    
    @staticmethod
    def fetch_offline_content(
        student_id: str,
        device_id: str,
        grade_level: str = "10",
        subjects: Optional[List[str]] = None,
        sync_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate fetchOfflineContent query event.
        
        Args:
            student_id: Student requesting content
            device_id: Device identifier
            grade_level: Student grade level
            subjects: List of subjects to fetch
            sync_token: Optional sync token for incremental updates
        
        Returns:
            AppSync query event dict
        """
        subjects = subjects or ["math", "english", "science"]
        sync_token = sync_token or ""
        
        return {
            "identity": {
                "claims": {
                    "sub": student_id,
                    "cognito:username": f"user#{student_id}"
                }
            },
            "arguments": {
                "studentId": student_id,
                "deviceId": device_id,
                "gradeLevel": grade_level,
                "subjects": subjects,
                "syncToken": sync_token,
                "requestedAt": datetime.now(timezone.utc).isoformat()
            },
            "request": {
                "headers": {
                    "x-amzn-appsync-operation": "Query",
                    "x-appsync-request-id": uuid.uuid4().hex,
                    "user-agent": "studaxis-mobile/1.0"
                }
            },
            "prev": None
        }
    
    @staticmethod
    def get_quiz_manifest(
        student_id: str,
        quiz_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Generate getQuizManifest query event.
        
        Args:
            student_id: Student requesting manifest
            quiz_ids: List of quiz IDs to get manifest for
        
        Returns:
            AppSync query event dict
        """
        return {
            "identity": {
                "claims": {
                    "sub": student_id,
                    "cognito:username": f"user#{student_id}"
                }
            },
            "arguments": {
                "studentId": student_id,
                "quizIds": quiz_ids
            },
            "request": {
                "headers": {
                    "x-amzn-appsync-operation": "Query",
                    "x-appsync-request-id": uuid.uuid4().hex
                }
            },
            "prev": None
        }


class S3EventFactory:
    """Generate S3 events for Lambda testing."""
    
    @staticmethod
    def s3_put_object(
        bucket: str,
        key: str,
        size: int = 1024,
        etag: Optional[str] = None,
        version_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate S3:ObjectCreated:Put event.
        
        Args:
            bucket: S3 bucket name
            key: Object key
            size: Object size in bytes
            etag: Object ETag
            version_id: Version ID if versioning enabled
        
        Returns:
            S3 event dict
        """
        etag = etag or uuid.uuid4().hex
        version_id = version_id or uuid.uuid4().hex
        
        return {
            "Records": [
                {
                    "eventVersion": "2.1",
                    "eventSource": "aws:s3",
                    "awsRegion": "us-east-1",
                    "eventTime": datetime.now(timezone.utc).isoformat() + "Z",
                    "eventName": "ObjectCreated:Put",
                    "userIdentity": {
                        "principalId": "AIDACKCEVSQ6C2EXAMPLE"
                    },
                    "requestParameters": {
                        "sourceIPAddress": "192.0.2.1"
                    },
                    "responseElements": {
                        "x-amz-request-id": uuid.uuid4().hex,
                        "x-amz-id-2": uuid.uuid4().hex
                    },
                    "s3": {
                        "s3SchemaVersion": "1.0",
                        "configurationId": "studaxis-lambda-trigger",
                        "bucket": {
                            "name": bucket,
                            "ownerIdentity": {
                                "principalId": "AIDACKCEVSQ6C2EXAMPLE"
                            },
                            "arn": f"arn:aws:s3:::{bucket}"
                        },
                        "object": {
                            "key": key,
                            "size": size,
                            "eTag": etag,
                            "sequencer": uuid.uuid4().hex,
                            "versionId": version_id
                        }
                    }
                }
            ]
        }
    
    @staticmethod
    def s3_quiz_uploaded(
        bucket: str,
        student_id: str,
        quiz_id: str,
        attempt_id: str
    ) -> Dict[str, Any]:
        """
        Generate S3 event for quiz JSON upload.
        
        Object key: `payloads/students/{student_id}/quizzes/{quiz_id}/{attempt_id}.json`
        """
        key = f"payloads/students/{student_id}/quizzes/{quiz_id}/{attempt_id}.json"
        return S3EventFactory.s3_put_object(
            bucket=bucket,
            key=key,
            size=2048
        )
    
    @staticmethod
    def s3_batch_sync_uploaded(
        bucket: str,
        student_id: str,
        batch_id: str
    ) -> Dict[str, Any]:
        """
        Generate S3 event for batch sync JSON upload.
        
        Object key: `payloads/students/{student_id}/syncs/{batch_id}.json`
        """
        key = f"payloads/students/{student_id}/syncs/{batch_id}.json"
        return S3EventFactory.s3_put_object(
            bucket=bucket,
            key=key,
            size=4096
        )


if __name__ == "__main__":
    # Test event generation
    import json
    
    print("=" * 70)
    print("OFFLINE SYNC EVENT - Quiz Attempt")
    print("=" * 70)
    event = OfflineSyncEventFactory.quiz_attempt(
        student_id="student-123",
        quiz_id="quiz-45-math-1",
        score=87.5,
        questions_answered=8,
        time_spent_seconds=450
    )
    print(json.dumps(event, indent=2))
    
    print("\n" + "=" * 70)
    print("CONTENT DISTRIBUTION EVENT - Fetch Offline Content")
    print("=" * 70)
    event = ContentDistributionEventFactory.fetch_offline_content(
        student_id="student-123",
        device_id="iphone-14-xyz",
        grade_level="10",
        subjects=["math", "physics"]
    )
    print(json.dumps(event, indent=2))
    
    print("\n" + "=" * 70)
    print("S3 EVENT - Quiz Uploaded")
    print("=" * 70)
    event = S3EventFactory.s3_quiz_uploaded(
        bucket="studaxis-payloads",
        student_id="student-123",
        quiz_id="quiz-45",
        attempt_id=uuid.uuid4().hex
    )
    print(json.dumps(event, indent=2, default=str))
