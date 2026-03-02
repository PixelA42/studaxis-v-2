"""
Studaxis — Content Downloader (Student-Side)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fetches assigned quizzes from the cloud and caches them locally for
offline use. Works through two paths:

  Path A (Online):
    Student App → AppSync → ContentDistribution Lambda → presigned URLs → S3
    
  Path B (Direct S3 — simpler for hackathon demo):
    Student App → S3 presigned URLs (via Lambda invoke or direct scan)

Offline-first: Downloaded quizzes are stored in data/quiz_cache/ and
available even without internet.
"""

import json
import os
import logging
import requests
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ContentDownloader:
    """Download and cache assigned quizzes for offline student use."""

    CACHE_DIR = "data/quiz_cache"
    MANIFEST_FILE = "data/quiz_cache/manifest.json"

    def __init__(
        self,
        appsync_endpoint: Optional[str] = None,
        appsync_api_key: Optional[str] = None,
        base_path: str = ".",
    ):
        self.appsync_endpoint = appsync_endpoint or os.getenv("APPSYNC_ENDPOINT", "")
        self.appsync_api_key = appsync_api_key or os.getenv("APPSYNC_API_KEY", "")
        self.base_path = Path(base_path)
        self.cache_dir = self.base_path / self.CACHE_DIR
        self.manifest_path = self.base_path / self.MANIFEST_FILE
        self.session = requests.Session()

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ── Online: Fetch manifest from AppSync/Lambda ──────────────────────────

    def fetch_content_manifest(
        self, user_id: str, subject: str = "All"
    ) -> Optional[Dict]:
        """
        Call AppSync → ContentDistribution Lambda to get a manifest
        with presigned S3 URLs for all assigned quizzes.

        Returns manifest dict or None on failure.
        """
        if not self.appsync_endpoint or "your-appsync" in self.appsync_endpoint:
            logger.warning("AppSync endpoint not configured, skipping manifest fetch")
            return None

        query = """
        query FetchOfflineContent($userId: String!, $subject: String) {
          fetchOfflineContent(userId: $userId, subject: $subject) {
            manifestId
            generatedAt
            totalItems
            presignedUrlExpirySeconds
            quizzes {
              quiz_id
              title
              subject
              difficulty
              s3_key
              offlineQuizUrl
              question_count
              assigned_to
              created_at
            }
          }
        }
        """

        try:
            response = self.session.post(
                self.appsync_endpoint,
                json={
                    "query": query,
                    "variables": {"userId": user_id, "subject": subject},
                },
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.appsync_api_key,
                },
                timeout=15,
            )

            if response.status_code == 200:
                result = response.json()
                if "errors" in result:
                    logger.error("AppSync error: %s", result["errors"])
                    return None
                manifest = result.get("data", {}).get("fetchOfflineContent")
                if manifest:
                    self._save_manifest(manifest)
                    logger.info(
                        "Fetched manifest: %d quizzes", manifest.get("totalItems", 0)
                    )
                return manifest

            logger.error("AppSync HTTP %d", response.status_code)
            return None

        except requests.exceptions.ConnectionError:
            logger.info("Offline — using cached quizzes")
            return None
        except requests.exceptions.Timeout:
            logger.warning("AppSync timeout — using cached quizzes")
            return None
        except Exception as e:
            logger.error("Manifest fetch error: %s", e)
            return None

    # ── Download individual quiz from presigned URL ─────────────────────────

    def download_quiz(self, quiz_meta: Dict) -> Optional[Dict]:
        """
        Download a single quiz JSON from its presigned S3 URL and cache locally.

        Args:
            quiz_meta: Dict with at least 'quiz_id' and 'offlineQuizUrl'

        Returns:
            Parsed quiz data dict, or None on failure.
        """
        quiz_id = quiz_meta.get("quiz_id", "unknown")
        url = quiz_meta.get("offlineQuizUrl", "")

        if not url:
            logger.warning("No download URL for quiz %s", quiz_id)
            return None

        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                quiz_data = response.json()
                self._cache_quiz(quiz_id, quiz_data)
                logger.info("Downloaded and cached quiz: %s", quiz_id)
                return quiz_data
            else:
                logger.error(
                    "Download failed for %s: HTTP %d", quiz_id, response.status_code
                )
                return None
        except requests.exceptions.ConnectionError:
            logger.info("Offline — cannot download %s", quiz_id)
            return self.load_cached_quiz(quiz_id)
        except Exception as e:
            logger.error("Download error for %s: %s", quiz_id, e)
            return None

    # ── Batch download all quizzes from manifest ────────────────────────────

    def sync_quizzes(self, user_id: str, subject: str = "All") -> Dict:
        """
        Full sync: fetch manifest → download each quiz → cache locally.

        Returns:
            { "downloaded": int, "cached": int, "failed": int, "quizzes": [...] }
        """
        result = {"downloaded": 0, "cached": 0, "failed": 0, "quizzes": []}

        manifest = self.fetch_content_manifest(user_id, subject)
        if not manifest:
            # Fall back to cached quizzes
            cached = self.list_cached_quizzes()
            result["cached"] = len(cached)
            result["quizzes"] = cached
            return result

        for quiz_meta in manifest.get("quizzes", []):
            quiz_id = quiz_meta.get("quiz_id", "")

            # Check if already cached and still valid
            if self._is_cached(quiz_id):
                cached_data = self.load_cached_quiz(quiz_id)
                if cached_data:
                    result["cached"] += 1
                    result["quizzes"].append(cached_data)
                    continue

            # Download fresh
            quiz_data = self.download_quiz(quiz_meta)
            if quiz_data:
                result["downloaded"] += 1
                result["quizzes"].append(quiz_data)
            else:
                result["failed"] += 1

        return result

    # ── Local cache management ──────────────────────────────────────────────

    def _cache_quiz(self, quiz_id: str, quiz_data: Dict):
        """Save quiz JSON to local cache."""
        cache_path = self.cache_dir / f"{quiz_id}.json"
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(quiz_data, f, indent=2, ensure_ascii=False)

    def load_cached_quiz(self, quiz_id: str) -> Optional[Dict]:
        """Load a quiz from local cache."""
        cache_path = self.cache_dir / f"{quiz_id}.json"
        if not cache_path.exists():
            return None
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error("Cache read error for %s: %s", quiz_id, e)
            return None

    def list_cached_quizzes(self) -> List[Dict]:
        """List all cached quiz files with basic metadata."""
        quizzes = []
        for path in self.cache_dir.glob("quiz_*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                quizzes.append(data)
            except Exception:
                continue
        return sorted(quizzes, key=lambda x: x.get("created_at", ""), reverse=True)

    def _is_cached(self, quiz_id: str) -> bool:
        """Check if a quiz is already in the local cache."""
        return (self.cache_dir / f"{quiz_id}.json").exists()

    def _save_manifest(self, manifest: Dict):
        """Persist the latest manifest for offline reference."""
        try:
            with open(self.manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error("Failed to save manifest: %s", e)

    def load_cached_manifest(self) -> Optional[Dict]:
        """Load the last saved manifest from disk."""
        if not self.manifest_path.exists():
            return None
        try:
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def get_cache_stats(self) -> Dict:
        """Return cache statistics."""
        cached_files = list(self.cache_dir.glob("quiz_*.json"))
        total_size = sum(f.stat().st_size for f in cached_files)
        return {
            "quiz_count": len(cached_files),
            "total_size_kb": round(total_size / 1024, 1),
            "cache_dir": str(self.cache_dir),
        }

    def clear_cache(self):
        """Remove all cached quizzes."""
        for path in self.cache_dir.glob("quiz_*.json"):
            path.unlink()
        if self.manifest_path.exists():
            self.manifest_path.unlink()
        logger.info("Quiz cache cleared")
