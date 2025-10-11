from typing import Dict, Any, Optional
import logging
from pathlib import Path
import gc
import pandas as pd
from app.agents.billing_agent import BillingAgent
from app.config import settings
from app.utils.s3_storage import S3Storage

logger = logging.getLogger(__name__)


class BillingService:
    """Service layer with per-user file and cache management"""
    
    def __init__(self, username: str = None):
        self.agent = BillingAgent()
        self.s3_storage = S3Storage()
        self.username = username
        logger.info(f"BillingService initialized for user: {username}")
    
    def _ensure_file_loaded(self, filename: str):
        """Load specific file only when needed"""
        tool_name = f"Excel Agent - {Path(filename).stem}"
        
        # Check in agent's loaded_files (where agent expects them)
        if tool_name in self.agent.loaded_files:
            logger.info(f"File already in agent cache: {filename}")
            return tool_name
        
        try:
            logger.info(f"Loading file from S3 for user {self.username}: {filename}")
            file_stream = self.s3_storage.download_file_to_stream(filename)
            if file_stream:
                df = pd.read_excel(file_stream, sheet_name="Billing Invoice (BI) Detail")
                # Store in agent's loaded_files (not service's)
                self.agent.loaded_files[tool_name] = {
                    "file_path": filename,
                    "sheet_name": "Billing Invoice (BI) Detail",
                    "dataframe": df,
                    "tool_description": f"Use this tool to analyze the Excel file: {filename}"
                }
                logger.info(f"Loaded file for user {self.username}: {filename}")
                return tool_name
        except Exception as e:
            logger.error(f"Failed to load {filename}: {e}")
            raise
    
    def _unload_files(self):
        """Unload files from memory but keep agent cache"""
        if self.agent.loaded_files:
            count = len(self.agent.loaded_files)
            self.agent.loaded_files.clear()
            gc.collect()
            logger.info(f"Unloaded {count} files from memory for user {self.username}")
    
    async def process_query(
        self, 
        query: str, 
        file_name: Optional[str] = None, 
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process query with persistent cache (NOT cleared after query)"""
        try:
            logger.info(f"Processing query for user {self.username}: {query[:50]}...")
            
            # Must specify a file
            if not file_name:
                return {
                    "answer": "Please select a specific file to analyze.",
                    "reasoning": "No file specified",
                    "execution_time": 0,
                    "tools_used": 0
                }
            
            # Load the specific file
            logger.info(f"Loading specific file for user {self.username}: {file_name}")
            tool_name = self._ensure_file_loaded(file_name)
            
            if not tool_name:
                return {
                    "answer": "File not found or failed to load.",
                    "reasoning": "File loading failed",
                    "execution_time": 0,
                    "tools_used": 0
                }
            
            # Process query - agent cache will persist
            result = await self.agent.query(query, file_name, api_key=api_key)
            
            # Clear loaded files but keep agent cache
            self._unload_files()
            logger.info(f"Query completed for user {self.username}, files cleared, cache preserved")
            
            return result
            
        except Exception as e:
            logger.error(f"Query error: {str(e)}")
            self._unload_files()
            return {
                "answer": f"Error: {str(e)}",
                "reasoning": "",
                "execution_time": 0,
                "tools_used": 0
            }
    
    def load_file(self, file_content: bytes, filename: str, sheet_name: str = "Billing Invoice (BI) Detail") -> str:
        """Upload file to S3 and optionally load it"""
        try:
            # Upload to S3
            logger.info(f"Uploading {filename} to S3...")
            success = self.s3_storage.upload_file(file_content, filename)
            if not success:
                raise Exception("Failed to upload to S3")
            
            # Don't load immediately - will load on first query
            logger.info(f"Uploaded {filename} to S3 (will load on demand)")
            return f"Excel Agent - {Path(filename).stem}"
            
        except Exception as e:
            logger.error(f"Upload error: {e}")
            raise
    
    def get_loaded_files_info(self) -> Dict[str, Dict[str, Any]]:
        """Get info about loaded files"""
        return self.agent.get_loaded_files_info()
    
    def clear_cache(self):
        """Clear agent cache (called on logout/cleanup)"""
        self.agent._invalidate_cache()
        logger.info(f"Cleared agent cache for user {self.username}")