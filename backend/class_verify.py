"""
Class code verification — maps class_code to class_id via DynamoDB.

Queries the studaxis-classes table (same schema as Class Manager Lambda).
Used by complete_onboarding to resolve class codes before persisting profile.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

CLASSES_TABLE_NAME = os.environ.get("CLASSES_TABLE_NAME", "studaxis-classes")
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")


class ClassVerifyUnavailableError(Exception):
    """Raised when DynamoDB or boto3 is not configured/available."""


def verify_class_code(class_code: str) -> dict | None:
    """
    Verify class code against studaxis-classes DynamoDB table.
    Returns { class_id, class_name, class_code } or None if not found.

    - class_code: 4+ chars, normalized to uppercase
    - Uses scan with FilterExpression (same as Class Manager Lambda)
    - Returns None when code is invalid or not found in DynamoDB
    - Raises ClassVerifyUnavailableError when boto3/table not configured
    - Raises ClientError/Exception on DynamoDB failures (caller maps to 503)
    """
    code = (class_code or "").strip().upper()
    if len(code) < 4:
        return None

    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        logger.warning("boto3 not installed; class verification disabled")
        raise ClassVerifyUnavailableError("boto3 not installed") from None

    table_name = (os.environ.get("CLASSES_TABLE_NAME") or CLASSES_TABLE_NAME).strip()
    if not table_name:
        logger.debug("CLASSES_TABLE_NAME not set; class verification unavailable")
        raise ClassVerifyUnavailableError("CLASSES_TABLE_NAME not configured") from None

    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(table_name)
        res = table.scan(
            FilterExpression="class_code = :cc",
            ExpressionAttributeValues={":cc": code},
            Limit=1,
        )
        items = res.get("Items", [])
        if not items:
            return None
        item = items[0]
        return {
            "class_id": item.get("class_id"),
            "class_name": item.get("class_name"),
            "class_code": item.get("class_code"),
        }
    except ClientError as e:
        logger.error("verify_class_code DynamoDB error: %s", e)
        raise
