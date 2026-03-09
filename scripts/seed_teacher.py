#!/usr/bin/env python3
"""
Seed a teacher for testing JWT auth.
Uses the exact fields from the Login/Onboarding UI: classCode, name, email, etc.

Usage:
  # Via FastAPI backend (default) - creates teacher in data/teachers/
  python scripts/seed_teacher.py
  python scripts/seed_teacher.py --backend http://localhost:6782

  # Via DynamoDB (AWS) - for Lambda auth path
  python scripts/seed_teacher.py --dynamodb
  python scripts/seed_teacher.py --dynamodb --table studaxis-teachers-dev

After seeding, log in via the Teacher Dashboard with classCode=CS101 (or your chosen code).
"""

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_URL = os.environ.get("VITE_TEACHER_BACKEND_URL", "http://localhost:6782")

DEFAULT_TEACHER = {
    "name": "Dr. Priya Sharma",
    "email": "priya@school.edu.in",
    "subject": "Physics",
    "grade": "Grade 10",
    "school": "Kendriya Vidyalaya, Sector 12",
    "city": "Bengaluru",
    "board": "CBSE",
    "className": "Physics XI-A 2026",
    "classCode": "CS101",
    "numStudents": "35",
}


def seed_via_backend(backend_url: str, data: dict) -> bool:
    """POST to /api/teacher/onboard - creates teacher in FastAPI's data/teachers/."""
    import urllib.request

    url = f"{backend_url.rstrip('/')}/api/teacher/onboard"
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            if result.get("ok"):
                print(f"[OK] Teacher seeded via backend: classCode={data['classCode']}")
                return True
            print(f"[FAIL] Backend returned: {result}")
            return False
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else str(e)
        print(f"[FAIL] Backend error {e.code}: {body}")
        return False
    except Exception as e:
        print(f"[FAIL] Request failed: {e}")
        return False


def seed_via_dynamodb(table_name: str, data: dict) -> bool:
    """PutItem to DynamoDB - for Lambda auth path."""
    try:
        import boto3
    except ImportError:
        print("[FAIL] boto3 required for --dynamodb. pip install boto3")
        return False

    client = boto3.client("dynamodb")
    cc = (data.get("classCode") or "CS101").strip().upper()
    item = {
        "classCode": {"S": cc},
        "name": {"S": data.get("name", "")},
        "email": {"S": data.get("email", "")},
        "subject": {"S": data.get("subject", "")},
        "grade": {"S": data.get("grade", "")},
        "school": {"S": data.get("school", "")},
        "city": {"S": data.get("city", "")},
        "board": {"S": data.get("board", "")},
        "className": {"S": data.get("className", "")},
        "numStudents": {"S": data.get("numStudents", "")},
        "teacherId": {"S": data.get("teacherId", cc)},
    }
    try:
        client.put_item(TableName=table_name, Item=item)
        print(f"[OK] Teacher seeded to DynamoDB ({table_name}): classCode={cc}")
        return True
    except Exception as e:
        print(f"[FAIL] DynamoDB error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Seed a teacher for JWT auth testing")
    parser.add_argument("--backend", default=BACKEND_URL, help="FastAPI backend URL")
    parser.add_argument("--dynamodb", action="store_true", help="Use DynamoDB instead of backend")
    parser.add_argument("--table", default="studaxis-teachers-dev", help="DynamoDB table name")
    parser.add_argument("--class-code", default="CS101", help="Class code (e.g. CS101, PHYS11A)")
    parser.add_argument("--name", default=DEFAULT_TEACHER["name"], help="Teacher name")
    parser.add_argument("--email", default=DEFAULT_TEACHER["email"], help="Teacher email")
    args = parser.parse_args()

    cc = (args.class_code or "CS101").strip().upper()
    data = {
        **DEFAULT_TEACHER,
        "classCode": cc,
        "name": args.name,
        "email": args.email,
        "className": f"{args.name.split()[0]} Class {cc}",
    }

    if args.dynamodb:
        ok = seed_via_dynamodb(args.table, data)
    else:
        ok = seed_via_backend(args.backend, data)

    if ok:
        print(f"\n  Log in at the Teacher Dashboard with:")
        print(f"    Class Code: {cc}")
        print(f"    Teacher ID (optional): {args.email}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
