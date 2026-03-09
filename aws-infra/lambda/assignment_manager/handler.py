"""
Studaxis — Assignment Manager Lambda (API Gateway → DynamoDB)
═══════════════════════════════════════════════════════════════
Purpose:
    Manage teacher assignments (quizzes, notes) to classes.
    Handles:
    - create_assignment: Teacher assigns content to a class
    - list_assignments: Get all assignments for a class
    - get_student_assignments: Get assignments for a specific student
    - mark_assignment_complete: Student marks assignment as done

DynamoDB Tables:
  - studaxis-assignments: Assignment records
    PK: assignment_id (UUID)
    GSI: class_code-created_at (for teacher queries)
    GSI: user_id-due_date (for student queries)

Trigger: API Gateway REST
IAM: dynamodb:PutItem, dynamodb:GetItem, dynamodb:Query
"""

import os
import json
import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
ASSIGNMENTS_TABLE = os.environ.get("ASSIGNMENTS_TABLE_NAME", "studaxis-assignments")
CLASSES_TABLE = os.environ.get("CLASSES_TABLE_NAME", "studaxis-classes")

logger = logging.getLogger("studaxis.assignment_manager")
logger.setLevel(LOG_LEVEL)

dynamodb = boto3.resource("dynamodb")
assignments_table = dynamodb.Table(ASSIGNMENTS_TABLE)
classes_table = dynamodb.Table(CLASSES_TABLE)


def _cors_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST,GET,PUT,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps(body, default=str),
    }


def _decimal(value) -> Decimal:
    """Convert to Decimal for DynamoDB."""
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    return value


def create_assignment(data: dict) -> dict:
    """
    Create a new assignment.
    
    Required fields:
    - teacher_id: Teacher who created it
    - class_code: Target class
    - content_type: "quiz" or "notes"
    - content_id: ID of the quiz/notes
    - title: Assignment title
    - due_date: ISO timestamp (optional)
    """
    teacher_id = (data.get("teacher_id") or "").strip()
    class_code = (data.get("class_code") or "").strip()
    content_type = (data.get("content_type") or "").strip()
    content_id = (data.get("content_id") or "").strip()
    title = (data.get("title") or "").strip()
    
    if not all([teacher_id, class_code, content_type, content_id, title]):
        raise ValueError("Missing required fields: teacher_id, class_code, content_type, content_id, title")
    
    if content_type not in ["quiz", "notes"]:
        raise ValueError("content_type must be 'quiz' or 'notes'")
    
    assignment_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    item = {
        "assignment_id": assignment_id,
        "teacher_id": teacher_id,
        "class_code": class_code,
        "content_type": content_type,
        "content_id": content_id,
        "title": title,
        "description": data.get("description", ""),
        "due_date": data.get("due_date"),
        "created_at": now,
        "status": "active",
    }
    
    # Add content metadata if provided
    if "content_data" in data:
        item["content_data"] = json.dumps(data["content_data"])
    
    assignments_table.put_item(Item=item)
    
    logger.info("Created assignment %s for class %s", assignment_id, class_code)
    return item


def list_assignments_for_class(class_code: str, teacher_id: str = None) -> list[dict]:
    """Get all assignments for a class."""
    class_code = (class_code or "").strip()
    if not class_code:
        return []
    
    try:
        # Scan with filter (GSI would be better for production)
        filter_expr = "class_code = :cc AND #status = :active"
        expr_values = {":cc": class_code, ":active": "active"}
        expr_names = {"#status": "status"}
        
        if teacher_id:
            filter_expr += " AND teacher_id = :tid"
            expr_values[":tid"] = teacher_id
        
        res = assignments_table.scan(
            FilterExpression=filter_expr,
            ExpressionAttributeValues=expr_values,
            ExpressionAttributeNames=expr_names,
        )
        
        items = res.get("Items", [])
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return items
    except ClientError as e:
        logger.error("list_assignments_for_class error: %s", e)
        raise


def get_student_assignments(user_id: str, class_code: str) -> list[dict]:
    """
    Get assignments for a student based on their class_code.
    Returns assignments with completion status.
    """
    user_id = (user_id or "").strip()
    class_code = (class_code or "").strip()
    
    if not user_id or not class_code or class_code == "SOLO":
        return []
    
    try:
        # Get all active assignments for the class
        assignments = list_assignments_for_class(class_code)
        
        # Check completion status for each
        for assignment in assignments:
            completion_id = f"{user_id}_{assignment['assignment_id']}"
            try:
                completion = assignments_table.get_item(
                    Key={"assignment_id": completion_id}
                )
                if "Item" in completion:
                    assignment["completed"] = True
                    assignment["completed_at"] = completion["Item"].get("completed_at")
                else:
                    assignment["completed"] = False
            except:
                assignment["completed"] = False
        
        return assignments
    except ClientError as e:
        logger.error("get_student_assignments error: %s", e)
        raise


def mark_assignment_complete(user_id: str, assignment_id: str, score: int = None) -> dict:
    """Mark an assignment as completed by a student."""
    user_id = (user_id or "").strip()
    assignment_id = (assignment_id or "").strip()
    
    if not user_id or not assignment_id:
        raise ValueError("user_id and assignment_id are required")
    
    now = datetime.now(timezone.utc).isoformat()
    completion_id = f"{user_id}_{assignment_id}"
    
    item = {
        "assignment_id": completion_id,
        "user_id": user_id,
        "original_assignment_id": assignment_id,
        "completed_at": now,
        "status": "completed",
    }
    
    if score is not None:
        item["score"] = _decimal(score)
    
    assignments_table.put_item(Item=item)
    
    logger.info("User %s completed assignment %s", user_id, assignment_id)
    return item


def delete_assignment(assignment_id: str, teacher_id: str) -> dict:
    """Soft delete an assignment (set status to deleted)."""
    assignment_id = (assignment_id or "").strip()
    teacher_id = (teacher_id or "").strip()
    
    if not assignment_id or not teacher_id:
        raise ValueError("assignment_id and teacher_id are required")
    
    try:
        # Verify teacher owns this assignment
        res = assignments_table.get_item(Key={"assignment_id": assignment_id})
        if "Item" not in res:
            raise ValueError("Assignment not found")
        
        if res["Item"].get("teacher_id") != teacher_id:
            raise ValueError("Unauthorized: You don't own this assignment")
        
        # Soft delete
        assignments_table.update_item(
            Key={"assignment_id": assignment_id},
            UpdateExpression="SET #status = :deleted",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":deleted": "deleted"},
        )
        
        logger.info("Deleted assignment %s", assignment_id)
        return {"assignment_id": assignment_id, "status": "deleted"}
    except ClientError as e:
        logger.error("delete_assignment error: %s", e)
        raise


def lambda_handler(event, context):
    """
    API Gateway REST handler.
    
    Routes:
      POST   /assignments                    → create_assignment
      GET    /assignments?class_code=X       → list_assignments_for_class
      GET    /assignments/student?user_id=X&class_code=Y → get_student_assignments
      POST   /assignments/complete           → mark_assignment_complete
      DELETE /assignments/{id}               → delete_assignment
      OPTIONS *                              → CORS
    """
    logger.info("Event: %s", json.dumps(event, default=str))
    
    if event.get("httpMethod") == "OPTIONS":
        return _cors_response(200, {"message": "CORS OK"})
    
    path = event.get("path", event.get("resource", ""))
    method = event.get("httpMethod", "GET")
    params = event.get("queryStringParameters") or {}
    
    try:
        # POST /assignments - create
        if method == "POST" and path.endswith("/assignments"):
            body = json.loads(event.get("body", "{}") or "{}")
            result = create_assignment(body)
            return _cors_response(200, result)
        
        # POST /assignments/complete
        if method == "POST" and "/complete" in path:
            body = json.loads(event.get("body", "{}") or "{}")
            user_id = body.get("user_id", "").strip()
            assignment_id = body.get("assignment_id", "").strip()
            score = body.get("score")
            result = mark_assignment_complete(user_id, assignment_id, score)
            return _cors_response(200, result)
        
        # GET /assignments/student
        if method == "GET" and "/student" in path:
            user_id = params.get("user_id", "").strip()
            class_code = params.get("class_code", "").strip()
            assignments = get_student_assignments(user_id, class_code)
            return _cors_response(200, {"assignments": assignments})
        
        # GET /assignments?class_code=X
        if method == "GET" and path.endswith("/assignments"):
            class_code = params.get("class_code", "").strip()
            teacher_id = params.get("teacher_id", "").strip() or None
            assignments = list_assignments_for_class(class_code, teacher_id)
            return _cors_response(200, {"assignments": assignments})
        
        # DELETE /assignments/{id}
        if method == "DELETE" and "/assignments/" in path:
            assignment_id = path.split("/")[-1]
            body = json.loads(event.get("body", "{}") or "{}")
            teacher_id = body.get("teacher_id", "").strip()
            result = delete_assignment(assignment_id, teacher_id)
            return _cors_response(200, result)
        
        return _cors_response(404, {"error": "Unknown route"})
    
    except ValueError as e:
        return _cors_response(400, {"error": str(e)})
    except ClientError as e:
        logger.error("DynamoDB error: %s", e)
        return _cors_response(500, {"error": "Database error"})
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return _cors_response(500, {"error": str(e)})
