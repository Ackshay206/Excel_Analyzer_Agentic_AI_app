import boto3
from botocore.exceptions import ClientError
import logging
from pathlib import Path
from typing import Optional, List, Dict
import os
import io
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


class S3Storage:
    """Handle file storage operations with S3 only"""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.bucket_name = os.getenv('S3_BUCKET_NAME')
        
        # Validate configuration
        if not all([os.getenv('AWS_ACCESS_KEY_ID'), 
                   os.getenv('AWS_SECRET_ACCESS_KEY'), 
                   self.bucket_name]):
            raise ValueError("S3 credentials not configured. Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and S3_BUCKET_NAME")
        
        logger.info(f"S3Storage initialized with bucket: {self.bucket_name}")
    
    def upload_file(self, file_content: bytes, filename: str) -> bool:
        """Upload file content directly to S3"""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=filename,
                Body=file_content
            )
            logger.info(f"Uploaded {filename} to S3")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
            return False
    
    def download_file(self, filename: str) -> Optional[bytes]:
        """Download file content from S3"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=filename
            )
            content = response['Body'].read()
            logger.info(f"Downloaded {filename} from S3")
            return content
        except ClientError as e:
            logger.error(f"Failed to download from S3: {e}")
            return None
    
    def download_file_to_stream(self, filename: str) -> Optional[io.BytesIO]:
        """Download file as a stream for pandas to read"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=filename
            )
            content = response['Body'].read()
            logger.info(f"Downloaded {filename} from S3 as stream")
            return io.BytesIO(content)
        except ClientError as e:
            logger.error(f"Failed to download from S3: {e}")
            return None
    
    def delete_file(self, filename: str) -> bool:
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=filename
            )
            logger.info(f"Deleted {filename} from S3")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete from S3: {e}")
            return False
    
    def list_files(self) -> List[Dict]:
        """List all files in S3 bucket"""
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
            files = []
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'filename': obj['Key'],
                        'path': f"s3://{self.bucket_name}/{obj['Key']}",
                        'size': obj['Size'],
                        'modified': obj['LastModified'].timestamp()
                    })
                    
            logger.info(f"Listed {len(files)} files from S3")
            return files
        except ClientError as e:
            logger.error(f"Failed to list S3 files: {e}")
            return []
    
    def file_exists(self, filename: str) -> bool:
        """Check if file exists in S3"""
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=filename
            )
            return True
        except ClientError:
            return False