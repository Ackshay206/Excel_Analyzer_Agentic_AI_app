from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    APP_NAME: str = "Billing AI Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # CORS Settings
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "https://excel-analyzer-agentic-ai-app.vercel.app", "*"]
    
    # OpenAI Settings - FIXED: Use underscore instead of hyphen
    OPENAI_API_KEY: Optional[str] =None
    OPENAI_MODEL: str = "gpt-4-turbo"
    
    # Optional fields that might be in your .env
    SECRET_KEY: str = "default-secret-key"
    
    # File Settings
    DATA_DIRECTORY: str = "data/excel_files"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: List[str] = [".xlsx", ".xls"]

    # AWS S3 Settings (REQUIRED for production)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "billing-analyzer-files-emerjence"
    
    # Agent Settings
    MAX_AGENT_ITERATIONS: int = 10
    AGENT_TIMEOUT: int = 60  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        # IMPORTANT: Allow extra fields to prevent validation errors
        extra = "allow"


settings = Settings()