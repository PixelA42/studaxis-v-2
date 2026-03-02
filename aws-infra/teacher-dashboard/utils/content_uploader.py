"""
Studaxis — Content Upload & Assignment Module
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Handles:
  1. Uploading AI-generated quiz JSON to S3 (studaxis-payloads)
  2. Registering quiz metadata in DynamoDB (studaxis-quiz-index)
  3. Assigning quizzes to specific students or entire classes

Flow:
  Teacher generates quiz (Bedrock) → Publish → S3 + DynamoDB index
  Student app → ContentDistribution Lambda → presigned URL → S3 download
"""

import boto3
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class ContentUploader:
    """Upload quiz content to S3 and register in DynamoDB quiz index."""

    def __init__(
        self,
        s3_bucket: str = "studaxis-payloads",
        quiz_index_table: str = "studaxis-quiz-index",
        region: str = "ap-south-1",
    ):
        self.s3_bucket = s3_bucket
        self.quiz_index_table = quiz_index_table
        self.region = region

        self.s3_client = boto3.client("s3", region_name=region)
        self.dynamodb = boto3.resource("dynamodb", region_name=region)
        self.table = self.dynamodb.Table(quiz_index_table)

    # ── Public API ──────────────────────────────────────────────────────────

    def publish_quiz(
        self,
        quiz_data: Dict,
        subject: str,
        difficulty: str = "medium",
        assigned_to: Optional[List[str]] = None,
        time_limit_minutes: int = 0,
        total_marks: float = 0,
        created_by: str = "teacher",
    ) -> Dict:
        """
        Publish a quiz: upload JSON to S3 and register metadata in DynamoDB.

        Args:
            quiz_data:          Raw quiz dict from Bedrock (or manual creation).
            subject:            Subject tag (Mathematics, Science, etc.)
            difficulty:         easy / medium / hard
            assigned_to:        List of student_ids. Empty/None = all students.
            time_limit_minutes: 0 = no time limit.
            total_marks:        Total marks for the quiz. 0 = auto-calculated.
            created_by:         Teacher identifier.

        Returns:
            { "success": bool, "quiz_id": str, "s3_key": str, "message": str }
        """
        quiz_id = f"quiz_{uuid.uuid4().hex[:12]}"
        s3_key = f"quizzes/{subject.lower()}/{quiz_id}.json"
        now_iso = datetime.now(timezone.utc).isoformat()

        # ── Normalise the quiz payload to match quiz_content_schema ─────────
        normalised = self._normalise_quiz(
            quiz_data=quiz_data,
            quiz_id=quiz_id,
            subject=subject,
            difficulty=difficulty,
            assigned_to=assigned_to or [],
            time_limit_minutes=time_limit_minutes,
            total_marks=total_marks,
            created_by=created_by,
            created_at=now_iso,
        )

        # ── Step 1: Upload full quiz JSON to S3 ────────────────────────────
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=json.dumps(normalised, indent=2, ensure_ascii=False),
                ContentType="application/json",
                Metadata={
                    "quiz_id": quiz_id,
                    "subject": subject,
                    "difficulty": difficulty,
                    "created_by": created_by,
                },
            )
            logger.info("Uploaded quiz %s to s3://%s/%s", quiz_id, self.s3_bucket, s3_key)
        except ClientError as e:
            logger.error("S3 upload failed: %s", e)
            return {"success": False, "quiz_id": quiz_id, "s3_key": s3_key,
                    "message": f"S3 upload failed: {e}"}

        # ── Step 2: Register lightweight metadata in DynamoDB index ─────────
        try:
            index_item = {
                "quiz_id": quiz_id,
                "title": normalised.get("title", "Untitled Quiz"),
                "subject": subject,
                "difficulty": difficulty,
                "s3_key": s3_key,
                "created_by": created_by,
                "created_at": now_iso,
                "question_count": len(normalised.get("questions", [])),
                "total_marks": int(total_marks) if total_marks else len(normalised.get("questions", [])),
                "time_limit_minutes": time_limit_minutes,
                "assigned_to": assigned_to or [],
                "status": "published",
            }
            self.table.put_item(Item=index_item)
            logger.info("Registered quiz %s in DynamoDB index", quiz_id)
        except ClientError as e:
            logger.error("DynamoDB write failed: %s", e)
            return {"success": False, "quiz_id": quiz_id, "s3_key": s3_key,
                    "message": f"S3 upload OK but DynamoDB index failed: {e}"}

        return {
            "success": True,
            "quiz_id": quiz_id,
            "s3_key": s3_key,
            "message": f"Quiz published successfully! ID: {quiz_id}",
        }

    def list_published_quizzes(self, subject: Optional[str] = None) -> List[Dict]:
        """List quizzes from the DynamoDB index, optionally filtered by subject."""
        try:
            scan_kwargs = {}
            if subject and subject.lower() != "all":
                from boto3.dynamodb.conditions import Attr
                scan_kwargs["FilterExpression"] = Attr("subject").eq(subject)

            response = self.table.scan(**scan_kwargs)
            items = response.get("Items", [])

            while "LastEvaluatedKey" in response:
                scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                response = self.table.scan(**scan_kwargs)
                items.extend(response.get("Items", []))

            return sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)
        except ClientError as e:
            logger.error("Failed to list quizzes: %s", e)
            return []

    def delete_quiz(self, quiz_id: str, s3_key: str) -> Dict:
        """Remove a quiz from both S3 and DynamoDB."""
        errors = []
        try:
            self.s3_client.delete_object(Bucket=self.s3_bucket, Key=s3_key)
        except ClientError as e:
            errors.append(f"S3 delete failed: {e}")

        try:
            self.table.delete_item(Key={"quiz_id": quiz_id})
        except ClientError as e:
            errors.append(f"DynamoDB delete failed: {e}")

        if errors:
            return {"success": False, "message": "; ".join(errors)}
        return {"success": True, "message": f"Quiz {quiz_id} deleted from S3 and index."}

    def get_presigned_download_url(self, s3_key: str, expiry: int = 3600) -> Optional[str]:
        """Generate a presigned download URL for a quiz."""
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.s3_bucket, "Key": s3_key},
                ExpiresIn=expiry,
            )
            return url
        except ClientError as e:
            logger.error("Presign failed: %s", e)
            return None

    # ── Internal helpers ────────────────────────────────────────────────────

    def _normalise_quiz(
        self,
        quiz_data: Dict,
        quiz_id: str,
        subject: str,
        difficulty: str,
        assigned_to: List[str],
        time_limit_minutes: int,
        total_marks: float,
        created_by: str,
        created_at: str,
    ) -> Dict:
        """
        Transform the raw Bedrock quiz output into a payload that conforms
        to shared/schemas/quiz_content_schema.json.
        """
        raw_questions = quiz_data.get("questions", [])
        normalised_questions = []

        for i, q in enumerate(raw_questions, 1):
            nq = {
                "question_id": f"{quiz_id}_q{i:02d}",
                "question_text": q.get("question", q.get("question_text", "")),
                "question_type": q.get("question_type", "mcq"),
                "options": q.get("options", []),
                "correct_answer": q.get("answer", q.get("correct_answer", "")),
                "explanation": q.get("explanation", ""),
                "marks": q.get("marks", 1),
                "topic_tags": [subject],
            }
            normalised_questions.append(nq)

        if not total_marks:
            total_marks = sum(q.get("marks", 1) for q in normalised_questions)

        return {
            "quiz_id": quiz_id,
            "title": quiz_data.get("quiz_title", quiz_data.get("title", "Untitled Quiz")),
            "topic": subject,
            "difficulty": difficulty.capitalize(),
            "created_by": created_by,
            "created_at": created_at,
            "questions": normalised_questions,
            "total_marks": total_marks,
            "time_limit_minutes": time_limit_minutes,
            "assigned_to": assigned_to,
        }
