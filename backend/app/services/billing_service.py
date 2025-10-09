from typing import Dict, Any, Optional
import logging
from pathlib import Path

from app.agents.billing_agent import BillingAgent
from app.config import settings
from app.utils.s3_storage import S3Storage

logger = logging.getLogger(__name__)


class BillingService:
    """Service layer for billing operations with S3-only storage"""
    
    def __init__(self):
        self.agent = BillingAgent()
        self.s3_storage = S3Storage()  # Initialize S3
        self._initialize_s3_files()
    
    def _initialize_s3_files(self):
        """Initialize with files from S3"""
        try:
            files = self.s3_storage.list_files()
            logger.info(f"Found {len(files)} files in S3")
            
            for file_info in files:
                filename = file_info['filename']
                if filename.endswith(('.xlsx', '.xls')):
                    try:
                        # Download file from S3 as stream
                        file_stream = self.s3_storage.download_file_to_stream(filename)
                        if file_stream:
                            self.agent.load_excel_file(file_stream, filename)
                            logger.info(f"Auto-loaded from S3: {filename}")
                    except Exception as e:
                        logger.warning(f"Could not auto-load {filename}: {e}")
        except Exception as e:
            logger.error(f"Error initializing S3 files: {e}")
    
    async def process_query(
        self, 
        query: str, 
        file_name: Optional[str] = None, 
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a billing query through the AI agent"""
        try:
            logger.info(f"Processing query: {query}")

            if api_key:
                logger.info("Using custom API key from session")
            else:
                logger.info("Using default API key from environment")
            
            # Ensure we have files loaded
            if not self.agent.loaded_files:
                # Try to load files from S3
                self._initialize_s3_files()
                
                if not self.agent.loaded_files:
                    return {
                        "answer": "No Excel files are currently available. Please upload a billing file first.",
                        "reasoning": "No files available for analysis",
                        "execution_time": 0,
                        "tools_used": 0
                    }
            
            # Process the query
            result = await self.agent.query(query, file_name, api_key=api_key)
            return result
            
        except Exception as e:
            logger.error(f"Error in billing service: {str(e)}")
            return {
                "answer": f"Service error: {str(e)}",
                "reasoning": "",
                "execution_time": 0,
                "tools_used": 0
            }
    
    def load_file(self, file_content: bytes, filename: str, sheet_name: str = "Billing Invoice (BI) Detail") -> str:
        """Upload file to S3 and load into agent"""
        try:
            # Upload to S3
            success = self.s3_storage.upload_file(file_content, filename)
            if not success:
                raise Exception("Failed to upload file to S3")
            
            # Download as stream and load into agent
            file_stream = self.s3_storage.download_file_to_stream(filename)
            if not file_stream:
                raise Exception("Failed to download file from S3")
            
            tool_name = self.agent.load_excel_file(file_stream, filename, sheet_name)
            logger.info(f"Successfully loaded file from S3: {filename}")
            return tool_name
        except Exception as e:
            logger.error(f"Error loading file {filename}: {e}")
            raise
    
    def get_loaded_files_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about currently loaded files"""
        return self.agent.get_loaded_files_info()
    
    def clear_files(self):
        """Clear all loaded files"""
        self.agent.clear_loaded_files()
        logger.info("Cleared all loaded files")