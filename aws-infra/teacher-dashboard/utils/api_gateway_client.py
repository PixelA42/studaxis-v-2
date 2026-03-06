"""
Studaxis — API Gateway Client for Teacher Dashboard
════════════════════════════════════════════════════
Calls the Teacher REST API (API Gateway → Lambda → Bedrock)
for quiz generation and lesson summary generation.

Uses AWS SigV4 signing when IAM auth is enabled, or falls back
to direct Bedrock calls when API Gateway is not configured.
"""

import json
import logging
import os
from typing import Dict, Optional

import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials

logger = logging.getLogger(__name__)


class TeacherApiClient:
    """
    Client for the Teacher API Gateway.
    Routes: POST /generateQuiz, POST /generateNotes
    Auth: AWS IAM (SigV4)
    """

    def __init__(
        self,
        endpoint: str = "",
        region: str = "ap-south-1",
    ):
        self.endpoint = endpoint or os.getenv("TEACHER_API_ENDPOINT", "")
        self.region = region
        self.session = requests.Session()

        # Get AWS credentials for SigV4 signing
        boto_session = boto3.Session()
        creds = boto_session.get_credentials()
        if creds:
            creds = creds.get_frozen_credentials()
            self._credentials = Credentials(
                creds.access_key, creds.secret_key, creds.token
            )
        else:
            self._credentials = None

    def _sign_request(self, method: str, url: str, body: str) -> Dict:
        """Sign a request with AWS SigV4 for IAM-authenticated API Gateway."""
        if not self._credentials:
            return {"Content-Type": "application/json"}

        request = AWSRequest(
            method=method,
            url=url,
            data=body,
            headers={"Content-Type": "application/json"},
        )
        SigV4Auth(self._credentials, "execute-api", self.region).add_auth(request)
        return dict(request.headers)

    def generate_quiz(
        self,
        topic: str,
        difficulty: str = "medium",
        num_questions: int = 3,
    ) -> Dict:
        """
        Call POST /generateQuiz on the Teacher API Gateway.

        Returns parsed quiz JSON dict.
        Raises RuntimeError on failure.
        """
        url = f"{self.endpoint.rstrip('/')}/generateQuiz"
        payload = json.dumps({
            "topic": topic,
            "difficulty": difficulty,
            "num_questions": num_questions,
        })

        headers = self._sign_request("POST", url, payload)

        try:
            resp = self.session.post(url, data=payload, headers=headers, timeout=35)

            if resp.status_code == 200:
                return resp.json()
            else:
                error_body = resp.text[:500]
                raise RuntimeError(
                    f"API Gateway returned {resp.status_code}: {error_body}"
                )
        except requests.exceptions.Timeout:
            raise RuntimeError("API Gateway request timed out (35s)")
        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(f"Cannot reach API Gateway: {e}")
        except json.JSONDecodeError:
            raise RuntimeError("API Gateway returned invalid JSON")

    def generate_notes(
        self,
        topic: str,
        grade_level: str = "Grade 10",
    ) -> Dict:
        """
        Call POST /generateNotes on the Teacher API Gateway.

        Returns parsed notes JSON dict.
        Raises RuntimeError on failure.
        """
        url = f"{self.endpoint.rstrip('/')}/generateNotes"
        payload = json.dumps({
            "topic": topic,
            "grade_level": grade_level,
        })

        headers = self._sign_request("POST", url, payload)

        try:
            resp = self.session.post(url, data=payload, headers=headers, timeout=35)

            if resp.status_code == 200:
                return resp.json()
            else:
                error_body = resp.text[:500]
                raise RuntimeError(
                    f"API Gateway returned {resp.status_code}: {error_body}"
                )
        except requests.exceptions.Timeout:
            raise RuntimeError("API Gateway request timed out (35s)")
        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(f"Cannot reach API Gateway: {e}")
        except json.JSONDecodeError:
            raise RuntimeError("API Gateway returned invalid JSON")

    def test_connection(self) -> Dict:
        """Test if the API Gateway endpoint is reachable."""
        if not self.endpoint or "your-api-id" in self.endpoint:
            return {
                "success": False,
                "message": "API Gateway endpoint not configured (set TEACHER_API_ENDPOINT)",
            }

        try:
            # Send a minimal request to test connectivity
            url = f"{self.endpoint.rstrip('/')}/generateQuiz"
            payload = json.dumps({"topic": ""})  # Will return 400, but proves connectivity
            headers = self._sign_request("POST", url, payload)
            resp = self.session.post(url, data=payload, headers=headers, timeout=10)

            if resp.status_code in (200, 400):
                return {
                    "success": True,
                    "message": f"API Gateway reachable (HTTP {resp.status_code})",
                }
            elif resp.status_code == 403:
                return {
                    "success": False,
                    "message": "API Gateway returned 403 — check IAM permissions",
                }
            else:
                return {
                    "success": False,
                    "message": f"API Gateway returned HTTP {resp.status_code}",
                }
        except requests.exceptions.Timeout:
            return {"success": False, "message": "API Gateway request timed out"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "message": "Cannot connect to API Gateway"}
        except Exception as e:
            return {"success": False, "message": str(e)}
