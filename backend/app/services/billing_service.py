from typing import Dict, Any, Optional
import logging
from pathlib import Path

from app.agents.billing_agent import BillingAgent  
from app.config import settings                    # FIXED: Your structure has app/

logger = logging.getLogger(__name__)


class BillingService:
    """Service layer for billing operations"""
    
    def __init__(self):
        self.agent = BillingAgent()
        self._initialize_default_files()
    
    def _initialize_default_files(self):
        """Initialize with default files if available"""
        try:
            data_dir = Path(settings.DATA_DIRECTORY)
            if data_dir.exists():
                # Load any existing Excel files
                for excel_file in data_dir.glob("*.xlsx"):
                    try:
                        self.agent.load_excel_file(str(excel_file))
                        logger.info(f"Auto-loaded file: {excel_file.name}")
                    except Exception as e:
                        logger.warning(f"Could not auto-load {excel_file.name}: {e}")
        except Exception as e:
            logger.error(f"Error initializing default files: {e}")
    
    async def process_query(self, query: str, file_name: Optional[str] = None, api_key :Optional[str]= None) -> Dict[str, Any]:
        """Process a billing query through the AI agent"""
        try:
            logger.info(f"Processing query: {query}")

            if api_key:
                logger.info("Using custom API key from session")
            else:
                logger.info("Using default API key from environment")
            
            # Ensure we have files loaded
            if not self.agent.loaded_files:
                # Try to load default files
                self._initialize_default_files()
                
                if not self.agent.loaded_files:
                    return {
                        "answer": "No Excel files are currently loaded. Please upload a billing file first.",
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
    
    def load_file(self, file_path: str, sheet_name: str = "Billing Invoice (BI) Detail") -> str:
        """Load a new Excel file into the agent"""
        try:
            tool_name = self.agent.load_excel_file(file_path, sheet_name)
            logger.info(f"Successfully loaded file: {file_path}")
            return tool_name
        except Exception as e:
            logger.error(f"Error loading file {file_path}: {e}")
            raise
    
    def get_loaded_files_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about currently loaded files"""
        return self.agent.get_loaded_files_info()
    
    def clear_files(self):
        """Clear all loaded files"""
        self.agent.clear_loaded_files()
        logger.info("Cleared all loaded files")