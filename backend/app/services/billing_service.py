from typing import Dict, Any, Optional
import logging
from pathlib import Path
import gc  
from app.agents.billing_agent import BillingAgent
from app.config import settings
from app.utils.s3_storage import S3Storage

logger = logging.getLogger(__name__)


class BillingService:
    """Service layer with aggressive memory optimization"""
    
    def __init__(self):
        self.agent = BillingAgent()
        self.s3_storage = S3Storage()
        logger.info("BillingService initialized (lazy loading enabled)")
    
    def _ensure_file_loaded(self, filename: str):
        """Load file only when needed"""
        tool_name = f"Excel Agent - {Path(filename).stem}"
        
        # Already loaded?
        if tool_name in self.agent.loaded_files:
            logger.info(f"File already in memory: {filename}")
            return
        
        try:
            logger.info(f"Loading file from S3: {filename}")
            file_stream = self.s3_storage.download_file_to_stream(filename)
            if file_stream:
                self.agent.load_excel_file(file_stream, filename)
                logger.info(f"Loaded: {filename}")
        except Exception as e:
            logger.error(f"Failed to load {filename}: {e}")
            raise
    
    def _unload_files(self):
        """Unload files from memory to free up RAM"""
        if self.agent.loaded_files:
            count = len(self.agent.loaded_files)
            self.agent.loaded_files.clear()
            self.agent._agent_cache.clear()
            gc.collect()  # Force garbage collection
            logger.info(f"Unloaded {count} files from memory")
    
    async def process_query(
        self, 
        query: str, 
        file_name: Optional[str] = None, 
        api_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process query with memory optimization"""
        try:
            logger.info(f"Processing query: {query[:50]}...")
            
            # Clear any previously loaded files to save memory
            self._unload_files()
            
            # Load only the specific file if requested
            if file_name:
                logger.info(f"Loading specific file: {file_name}")
                self._ensure_file_loaded(file_name)
            else:
                # Load all files (risky on 512MB)
                logger.warning("Loading all files - may use significant memory")
                files = self.s3_storage.list_files()
                for file_info in files:
                    if file_info['filename'].endswith(('.xlsx', '.xls')):
                        self._ensure_file_loaded(file_info['filename'])
            
            if not self.agent.loaded_files:
                return {
                    "answer": "No files available. Please upload a file first.",
                    "reasoning": "No files loaded",
                    "execution_time": 0,
                    "tools_used": 0
                }
            
            # Process query
            result = await self.agent.query(query, file_name, api_key=api_key)
            
            # Unload files after query to free memory for next request
            self._unload_files()
            
            return result
            
        except Exception as e:
            logger.error(f"Query error: {str(e)}")
            # Clean up on error
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
    
    def clear_files(self):
        """Clear all loaded files"""
        self._unload_files()