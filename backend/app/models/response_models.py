from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class BillingQueryResponse(BaseModel):
    """Response model for billing queries"""
    success: bool = Field(..., description="Whether the query was successful")
    answer: str = Field(..., description="The answer to the user's query")
    reasoning: Optional[str] = Field(None, description="Step-by-step reasoning (optional)")
    execution_time: float = Field(..., description="Time taken to process the query in seconds")
    using_custom_key: bool = Field(False, description="Whether a custom API key was used")


# New: API Key Response Model
class ApiKeyResponse(BaseModel):
    """Response model for API key operations"""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Status message")
    session_id: str = Field(..., description="Session identifier")
    using_custom_key: bool = Field(..., description="Whether using a custom key")

class FileUploadResponse(BaseModel):
    """Response model for file uploads"""
    success: bool = Field(..., description="Whether the upload was successful")
    message: str = Field(..., description="Upload status message")
    filename: str = Field(..., description="Name of the uploaded file")
    file_path: str = Field(..., description="Path where the file was saved")


class FileInfo(BaseModel):
    """Model for file information"""
    filename: str = Field(..., description="Name of the file")
    path: str = Field(..., description="Full path to the file")
    size: int = Field(..., description="File size in bytes")
    modified: float = Field(..., description="Last modified timestamp")


class FileListResponse(BaseModel):
    """Response model for listing files"""
    success: bool = Field(..., description="Whether the operation was successful")
    files: List[FileInfo] = Field(..., description="List of available files")
    message: str = Field(..., description="Status message")


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Health status")
    message: str = Field(..., description="Health status message")

