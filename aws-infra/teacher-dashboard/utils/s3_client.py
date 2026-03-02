import boto3
import json
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class S3StatsClient:
    """Helper to fetch student stats from S3"""
    
    def __init__(self, bucket_name: str):
        self.s3_client = boto3.client('s3')
        self.bucket_name = bucket_name
    
    def list_student_files(self) -> List[str]:
        """List all student_*.json files in bucket"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='student_'
            )
            return [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.json')]
        except Exception as e:
            logger.error(f"Error listing S3 files: {e}")
            return []
    
    def get_student_stats(self, student_id: str) -> Dict:
        """Fetch User_Stats.json for a specific student"""
        try:
            key = f"student_{student_id}_stats.json"
            obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return json.loads(obj['Body'].read().decode('utf-8'))
        except Exception as e:
            logger.error(f"Error fetching stats for {student_id}: {e}")
            return {}            