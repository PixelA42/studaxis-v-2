"""
AppSync-to-S3 Broker Pattern
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AppSync acts as a "broker" that generates presigned S3 URLs while staying 
under the 1MB payload limit. The Streamlit app then downloads the actual 
quiz JSON directly from S3 using the presigned URL.

Flow:
  1. Streamlit → AppSync: "Give me presigned URL for quiz_123"
  2. AppSync → ContentDistribution Lambda: "Get S3 URL"
  3. Lambda → S3: "Generate presigned URL for quiz_123.json"
  4. Lambda → AppSync: "Here's the presigned URL"
  5. AppSync → Streamlit: "https://studaxis-payloads.s3.../quiz_123.json?..."
  6. Streamlit → S3: "Download quiz JSON directly" ✅ BYPASSES AppSync limit!
"""

import streamlit as st
import requests
import json
import os
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# S3 DIRECT FETCH (Presigned URL Handler)
# ─────────────────────────────────────────────────────────────────────────────

class S3PresignedURLClient:
    """Handles direct S3 downloads using presigned URLs from AppSync/Lambda"""
    
    def __init__(self, region: str = "ap-south-1"):
        self.region = region
        self.session = requests.Session()
    
    def fetch_quiz_from_s3(self, presigned_url: str) -> Optional[Dict]:
        """
        Downloads live JSON file directly from S3 using presigned URL.
        
        This bypasses AppSync's 1MB payload limit by fetching large files
        directly from S3 after AppSync has brokered the presigned URL.
        
        Args:
            presigned_url: Full S3 presigned URL (from ContentDistribution Lambda)
        
        Returns:
            Parsed JSON dict, or None if download fails
        """
        try:
            logger.info(f"Fetching quiz from presigned S3 URL...")
            
            # Stream the download to handle large files
            response = self.session.get(presigned_url, timeout=30)
            
            if response.status_code == 200:
                quiz_data = response.json()
                logger.info(f"✅ Successfully fetched quiz: {quiz_data.get('quiz_id', 'unknown')}")
                return quiz_data
            
            elif response.status_code == 403:
                st.error("🔐 **Access Denied**: Presigned URL expired or invalid")
                logger.error(f"403 Forbidden: Presigned URL may have expired")
                return None
            
            elif response.status_code == 404:
                st.error("❌ **File Not Found**: Quiz not available in S3")
                logger.error(f"404 Not Found: Quiz missing from S3")
                return None
            
            else:
                st.error(f"❌ **Download Failed**: HTTP {response.status_code}")
                logger.error(f"S3 fetch failed: {response.status_code} - {response.text}")
                return None
        
        except requests.exceptions.Timeout:
            st.error("⏱️ **Timeout**: S3 request took too long (30s limit)")
            logger.error("S3 request timeout")
            return None
        
        except requests.exceptions.ConnectionError as e:
            st.error("🌐 **Connection Error**: Cannot reach S3 (offline or network issue)")
            logger.error(f"Connection error: {e}")
            return None
        
        except json.JSONDecodeError:
            st.error("❌ **Invalid JSON**: File downloaded but not valid JSON")
            logger.error("Downloaded file is not valid JSON")
            return None
        
        except Exception as e:
            st.error(f"❌ **Unexpected Error**: {e}")
            logger.error(f"Unexpected error fetching quiz: {e}")
            return None
    
    def validate_presigned_url(self, url: str) -> bool:
        """
        Quick validation that presigned URL is well-formed and accessible.
        (Doesn't download full payload, just HEAD request)
        """
        try:
            response = self.session.head(url, timeout=5)
            return response.status_code in [200, 403]  # 403 means expired, 200 means valid
        except Exception as e:
            logger.error(f"URL validation failed: {e}")
            return False

# ─────────────────────────────────────────────────────────────────────────────
# APPSYNC INTEGRATION (Fetches Presigned URLs)
# ─────────────────────────────────────────────────────────────────────────────

class AppSyncQLClient:
    """Queries AppSync GraphQL to get presigned S3 URLs via ContentDistribution Lambda"""
    
    def __init__(self, endpoint: str, api_key: str):
        """
        Args:
            endpoint: AppSync GraphQL endpoint URL
            api_key: AppSync API key (for dev) or JWT token (for prod)
        """
        self.endpoint = endpoint
        self.api_key = api_key
        self.session = requests.Session()
        
        # Set up AppSync headers
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }
    
    def get_quiz_presigned_url(self, quiz_id: str) -> Optional[str]:
        """
        Calls AppSync to get presigned URL for a quiz.
        This invokes ContentDistribution Lambda under the hood.
        
        GraphQL Query (AppSync resolves this to Lambda):
            query {
              getQuizPresignedUrl(quiz_id: "quiz_123") {
                presigned_url
                expires_at
              }
            }
        """
        query = """
        query GetQuizPresignedUrl($quizId: String!) {
          getQuizPresignedUrl(quiz_id: $quizId) {
            presigned_url
            expires_at
            quiz_id
          }
        }
        """
        
        variables = {"quizId": quiz_id}
        
        try:
            logger.info(f"Querying AppSync for presigned URL: {quiz_id}")
            
            response = self.session.post(
                self.endpoint,
                json={"query": query, "variables": variables},
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Check for GraphQL errors
                if "errors" in result:
                    error_msg = result["errors"][0].get("message", "Unknown error")
                    st.warning(f"⚠️ AppSync Error: {error_msg}")
                    logger.error(f"AppSync error: {error_msg}")
                    return None
                
                # Extract presigned URL
                presigned_url = result.get("data", {}).get("getQuizPresignedUrl", {}).get("presigned_url")
                expires_at = result.get("data", {}).get("getQuizPresignedUrl", {}).get("expires_at")
                
                if presigned_url:
                    logger.info(f"✅ Got presigned URL for {quiz_id}, expires: {expires_at}")
                    return presigned_url
                else:
                    st.error("❌ No presigned URL in AppSync response")
                    return None
            
            else:
                st.error(f"❌ AppSync returned {response.status_code}")
                logger.error(f"AppSync request failed: {response.status_code}")
                return None
        
        except requests.exceptions.Timeout:
            st.error("⏱️ AppSync request timed out")
            logger.error("AppSync timeout")
            return None
        
        except Exception as e:
            st.error(f"❌ Cannot reach AppSync: {e}")
            logger.error(f"AppSync connection error: {e}")
            return None
    
    def list_available_quizzes(self) -> Optional[list]:
        """
        List all available quizzes from Quiz Index DynamoDB table.
        Useful for building a quiz selector dropdown in the teacher dashboard.
        """
        query = """
        query ListQuizzes {
          listQuizzes {
            quiz_id
            title
            subject
            difficulty
            created_at
          }
        }
        """
        
        try:
            response = self.session.post(
                self.endpoint,
                json={"query": query},
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("data", {}).get("listQuizzes", [])
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to list quizzes: {e}")
            return None

# ─────────────────────────────────────────────────────────────────────────────
# STREAMLIT INTEGRATION (Dashboard Functions)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_quiz_with_presigned_url(presigned_url: str) -> Optional[Dict]:
    """
    Streamlit cached function to fetch + parse quiz JSON.
    Caches for 5 minutes to avoid re-downloading same quiz.
    """
    s3_client = S3PresignedURLClient()
    return s3_client.fetch_quiz_from_s3(presigned_url)

def display_quiz_content(quiz_data: Dict):
    """
    Renders a quiz in Streamlit UI (for teacher dashboard preview).
    """
    if not quiz_data:
        st.error("❌ No quiz data to display")
        return
    
    st.subheader(f"📖 {quiz_data.get('quiz_title', 'Untitled Quiz')}")
    
    # Quiz metadata
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Subject", quiz_data.get('subject', 'N/A'))
    with col2:
        st.metric("Questions", len(quiz_data.get('questions', [])))
    with col3:
        st.metric("Difficulty", quiz_data.get('difficulty', 'Medium'))
    
    st.divider()
    
    # Display each question
    for i, q in enumerate(quiz_data.get('questions', []), 1):
        with st.expander(f"**Q{i}:** {q.get('question', 'N/A')}"):
            st.write(f"**Options:**")
            for option in q.get('options', []):
                st.write(f"  • {option}")
            
            st.write(f"**Correct Answer:** {q.get('correct_answer', 'N/A')}")
            st.write(f"**Explanation:** {q.get('explanation', 'N/A')}")
