from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from typing import List
import logging
import os
from pathlib import Path

from app.models.request_models import BillingQueryRequest, SetApiKeyRequest     
from app.models.response_models import BillingQueryResponse, FileUploadResponse, FileListResponse, ApiKeyResponse
from app.services.billing_service import BillingService      
from app.config import settings                               

logger = logging.getLogger(__name__)
router = APIRouter()


class SessionStore:
    """Simple in-memory session storage"""
    def __init__(self):
        self._store = {}
    
    def set(self, session_id: str, api_key: str):
        self._store[session_id] = api_key
    
    def get(self, session_id: str):
        return self._store.get(session_id)
    
    def delete(self, session_id: str):
        self._store.pop(session_id, None)
    
    def has(self, session_id: str):
        return session_id in self._store


user_api_keys = SessionStore()

# Single shared billing service instance to maintain cache
_billing_service_instance = None


def get_billing_service() -> BillingService:
    """Get or create a single shared billing service instance"""
    global _billing_service_instance
    if _billing_service_instance is None:
        _billing_service_instance = BillingService()
    return _billing_service_instance


@router.post("/set-api-key", response_model=ApiKeyResponse)
async def set_api_key(request: SetApiKeyRequest):
    """
    Allow users to set their OpenAI API key for the session.
    This is stored temporarily in memory and used for all subsequent queries.
    """
    try:
        # Basic validation - check if key looks like an OpenAI key
        if not request.api_key.startswith('sk-'):
            raise HTTPException(
                status_code=400,
                detail="Invalid API key format. OpenAI keys start with 'sk-'"
            )
        
        # Generate a simple session ID
        session_id = request.session_id or "default"
        
        # If there was a previous key for this session, invalidate its cache
        old_key = user_api_keys.get(session_id)
        if old_key:
            service = get_billing_service()
            service.agent.invalidate_session_cache(old_key)
            logger.info(f"Invalidated cache for old API key in session: {session_id}")
        
        # Store the new API key
        user_api_keys.set(session_id, request.api_key)
        
        logger.info(f"API key set for session: {session_id} (ends with: ...{request.api_key[-4:]})")
        
        return ApiKeyResponse(
            success=True,
            message="API key set successfully",
            session_id=session_id,
            using_custom_key=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting API key: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error setting API key: {str(e)}"
        )


@router.delete("/remove-api-key")
async def remove_api_key(session_id: str = "default"):
    """Remove the stored API key and invalidate its cache"""
    try:
        if user_api_keys.has(session_id):
            # Get the key before deleting to invalidate its cache
            api_key = user_api_keys.get(session_id)
            
            # Invalidate cache for this API key
            service = get_billing_service()
            service.agent.invalidate_session_cache(api_key)
            
            # Remove the key
            user_api_keys.delete(session_id)
            
            logger.info(f"API key removed for session: {session_id}")
            return {
                "success": True,
                "message": "API key removed. Using default key from environment."
            }
        else:
            return {
                "success": True,
                "message": "No custom API key was set for this session."
            }
    except Exception as e:
        logger.error(f"Error removing API key: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error removing API key: {str(e)}"
        )


@router.get("/api-key-status")
async def get_api_key_status(session_id: str = "default"):
    """Check if a custom API key is set for this session"""
    has_custom_key = user_api_keys.has(session_id)
    has_env_key = bool(settings.OPENAI_API_KEY)
    
    # Get cache info for debugging
    service = get_billing_service()
    cache_info = service.agent.get_cache_info()
    
    return {
        "has_custom_key": has_custom_key,
        "has_env_key": has_env_key,
        "using_custom_key": has_custom_key,
        "session_id": session_id,
        "cache_info": cache_info
    }


@router.post("/query", response_model=BillingQueryResponse)
async def query_billing_data(
    request: BillingQueryRequest,
    service: BillingService = Depends(get_billing_service)
):
    """Query billing data using AI agent"""
    try:
        logger.info(f"Received billing query: {request.query}")

        # Get API KEY from the session storage
        session_id = request.session_id or "default"
        api_key = user_api_keys.get(session_id)
        
        # Process query through the billing service
        result = await service.process_query(request.query, request.file_name, api_key=api_key)
        
        return BillingQueryResponse(
            success=True,
            answer=result["answer"],
            reasoning=result.get("reasoning", ""),
            execution_time=result.get("execution_time", 0),
            using_custom_key=api_key is not None
        )
        
    except Exception as e:
        logger.error(f"Error processing billing query: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )


@router.post("/upload", response_model=FileUploadResponse)
async def upload_excel_file(
    file: UploadFile = File(...),
    service: BillingService = Depends(get_billing_service)
):
    """Upload Excel file directly to S3"""
    try:
        # Validate file type
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="Only Excel files (.xlsx, .xls) are supported"
            )
        
        # Read file content
        content = await file.read()
        
        # Check file size
        if len(content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {settings.MAX_FILE_SIZE / 1024 / 1024}MB"
            )
        
        # Upload to S3 and load into agent
        try:
            service.load_file(content, file.filename)
            logger.info(f"File uploaded to S3 and loaded: {file.filename}")
        except Exception as e:
            logger.error(f"Failed to process file: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process file: {str(e)}"
            )
        
        return FileUploadResponse(
            success=True,
            message="File uploaded to S3 successfully",
            filename=file.filename,
            file_path=f"s3://{os.getenv('S3_BUCKET_NAME')}/{file.filename}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading file: {str(e)}"
        )


@router.get("/files", response_model=FileListResponse)
async def list_available_files(
    service: BillingService = Depends(get_billing_service)
):
    """List all available Excel files from S3"""
    try:
        files = service.s3_storage.list_files()
        
        return FileListResponse(
            success=True,
            files=files,
            message=f"Found {len(files)} files in S3"
        )
        
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing files: {str(e)}"
        )


@router.delete("/files/{filename}")
async def delete_file(
    filename: str,
    service: BillingService = Depends(get_billing_service)
):
    """Delete an Excel file from S3"""
    try:
        # Delete from S3
        success = service.s3_storage.delete_file(filename)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="File not found or failed to delete"
            )
        
        # Reload remaining files
        service.agent.clear_loaded_files()
        service._initialize_s3_files()
        
        logger.info(f"File deleted from S3: {filename}")
        
        return {
            "success": True, 
            "message": f"File {filename} deleted from S3"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting file: {str(e)}"
        )