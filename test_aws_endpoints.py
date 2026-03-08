#!/usr/bin/env python3
"""
Studaxis — AWS Endpoints E2E Test Script
══════════════════════════════════════════
Tests the Dual-Brain architecture end-to-end:
  1. Edge Brain → AppSync (student sync push)
  2. Teacher Dashboard → AppSync (roster pull)
  3. Strategic Cloud Brain → API Gateway (Bedrock quiz generation)

Run from repo root: python test_aws_endpoints.py
Loads credentials from backend/.env
"""

import json
import os
import sys
from pathlib import Path

# Load backend .env
_env_path = Path(__file__).resolve().parent / "backend" / ".env"
if _env_path.exists():
    with open(_env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")

try:
    import requests
except ImportError:
    print("ERROR: Install requests: pip install requests")
    sys.exit(1)

APPSYNC_ENDPOINT = os.getenv("APPSYNC_ENDPOINT", "")
APPSYNC_API_KEY = os.getenv("APPSYNC_API_KEY", "")
API_GATEWAY_URL = os.getenv("API_GATEWAY_QUIZ_URL", "") or os.getenv("VITE_API_GATEWAY_URL", "")

TEST_USER_ID = "test_student_99"
TEST_CLASS_CODE = "CS101"


def _appsync_post(query: str, variables: dict) -> dict:
    """Send GraphQL request to AppSync."""
    resp = requests.post(
        APPSYNC_ENDPOINT,
        json={"query": query, "variables": variables},
        headers={
            "Content-Type": "application/json",
            "x-api-key": APPSYNC_API_KEY,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def test_student_sync_push() -> bool:
    """
    Simulate the Edge Brain.
    Send updateStreak mutation to AppSync for test_student_99 (class_code CS101, streak 5).
    """
    print("\n" + "=" * 60)
    print("TEST 1: Student Sync Push (Edge Brain -> AppSync)")
    print("=" * 60)

    mutation = """
    mutation UpdateStreak($userId: String!, $currentStreak: Int!, $classCode: String) {
      updateStreak(userId: $userId, currentStreak: $currentStreak, classCode: $classCode) {
        userId
        currentStreak
        syncedAt
      }
    }
    """
    variables = {
        "userId": TEST_USER_ID,
        "currentStreak": 5,
        "classCode": TEST_CLASS_CODE,
    }

    try:
        data = _appsync_post(mutation, variables)
        if "errors" in data:
            print("FAIL: GraphQL errors:", json.dumps(data["errors"], indent=2))
            return False
        result = data.get("data", {}).get("updateStreak", {})
        print("SUCCESS: Streak synced to AppSync")
        print("  Response:", json.dumps(result, indent=2))
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_teacher_dashboard_pull() -> bool:
    """
    Simulate the Teacher Dashboard.
    Query listStudentProgresses filtered by class_code CS101.
    Assert test_student_99 appears in the roster.
    """
    print("\n" + "=" * 60)
    print("TEST 2: Teacher Dashboard Pull (AppSync -> Roster)")
    print("=" * 60)

    query = """
    query ListStudentProgresses($class_code: String, $limit: Int) {
      listStudentProgresses(class_code: $class_code, limit: $limit) {
        items {
          user_id
          class_code
          current_streak
          last_sync_timestamp
        }
        nextToken
      }
    }
    """
    variables = {"class_code": TEST_CLASS_CODE, "limit": 100}

    try:
        data = _appsync_post(query, variables)
        if "errors" in data:
            print("FAIL: GraphQL errors:", json.dumps(data["errors"], indent=2))
            return False

        items = data.get("data", {}).get("listStudentProgresses", {}).get("items") or []
        print(f"Roster for class {TEST_CLASS_CODE}: {len(items)} student(s)")
        for s in items:
            print(f"  - {s.get('user_id')}: streak={s.get('current_streak')}, last_sync={s.get('last_sync_timestamp', 'N/A')}")

        user_ids = [s.get("user_id") for s in items if s.get("user_id")]
        if TEST_USER_ID not in user_ids:
            print(f"FAIL: Expected {TEST_USER_ID} in roster, got: {user_ids}")
            return False

        print(f"SUCCESS: {TEST_USER_ID} found in roster")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def test_bedrock_quiz_generation() -> bool:
    """
    Simulate the Strategic Cloud Brain.
    POST to API Gateway with quiz generation payload.
    Print status code and s3_url (or quiz JSON if no s3_url).
    """
    print("\n" + "=" * 60)
    print("TEST 3: Bedrock Quiz Generation (API Gateway -> Lambda)")
    print("=" * 60)

    payload = {
        "textbook_id": "physics_101",
        "topic": "Gravity",
        "difficulty": "easy",
        "num_questions": 2,
    }

    try:
        resp = requests.post(
            API_GATEWAY_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )
        print(f"Status code: {resp.status_code}")

        body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        if "error" in body:
            print(f"FAIL: API returned error: {body['error']}")
            return False

        s3_url = body.get("s3_url")
        if s3_url:
            print(f"s3_url: {s3_url}")
        else:
            # Lambda returns quiz JSON directly (no S3 upload in current impl)
            quiz_title = body.get("quiz_title", body.get("topic", "N/A"))
            questions = body.get("questions", [])
            print(f"Quiz: {quiz_title} ({len(questions)} questions)")
            print("  (s3_url not in response - Lambda returns quiz JSON directly)")

        print("SUCCESS: Quiz generation completed")
        return resp.status_code == 200
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def main():
    print("\nStudaxis AWS E2E Test Suite")
    print("Loading credentials from backend/.env")

    if not APPSYNC_ENDPOINT or not APPSYNC_API_KEY:
        print("ERROR: APPSYNC_ENDPOINT and APPSYNC_API_KEY must be set in backend/.env")
        sys.exit(1)
    if not API_GATEWAY_URL:
        print("ERROR: API_GATEWAY_QUIZ_URL or VITE_API_GATEWAY_URL must be set in backend/.env")
        sys.exit(1)

    results = []
    results.append(("Student Sync Push", test_student_sync_push()))
    results.append(("Teacher Dashboard Pull", test_teacher_dashboard_pull()))
    results.append(("Bedrock Quiz Generation", test_bedrock_quiz_generation()))

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  {name}: {status}")
    passed = sum(1 for _, ok in results if ok)
    print(f"\nTotal: {passed}/{len(results)} passed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
