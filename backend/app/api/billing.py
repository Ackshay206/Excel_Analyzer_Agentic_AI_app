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
    """Session storage with username-based sessions"""
    def __init__(self):
        self._store = {}
    
    def set(self, username: str, api_key: str = None):
        """Store username and optional API key"""
        if username not in self._store:
            self._store[username] = {'api_key': api_key, 'is_new_user': True}
        else:
            # Preserve is_new_user status for existing users
            is_new = self._store[username].get('is_new_user', False)
            self._store[username]['api_key'] = api_key
            self._store[username]['is_new_user'] = is_new
    
    def get(self, username: str):
        """Get session data for username"""
        return self._store.get(username, {}).get('api_key')
    
    def delete(self, username: str):
        """Remove user API key but keep session"""
        if username in self._store:
            self._store[username]['api_key'] = None
    
    def has_user(self, username: str):
        """Check if username exists"""
        return username in self._store
    
    def has_api_key(self, username: str):
        """Check if username has an API key set"""
        return username in self._store and self._store[username].get('api_key') is not None
    
    def get_user_status(self, username: str):
        """Get detailed user status"""
        if not self.has_user(username):
            return {'exists': False, 'has_api_key': False, 'is_new_user': True}
        
        session = self._store[username]
        return {
            'exists': True,
            'has_api_key': session.get('api_key') is not None,
            'is_new_user': session.get('is_new_user', False)
        }


user_api_keys = SessionStore()

# Dictionary to store billing service instances per user
_billing_service_instances = {}


def get_billing_service(username: str = None) -> BillingService:
    """Get or create a billing service instance for a specific user"""
    global _billing_service_instances
    
    if username is None:
        # For backwards compatibility and initialization
        return BillingService()
    
    if username not in _billing_service_instances:
        _billing_service_instances[username] = BillingService(username=username)
        logger.info(f"Created new billing service instance for user: {username}")
    
    return _billing_service_instances[username]


def cleanup_user_session(username: str):
    """Clean up user's billing service instance when they leave"""
    global _billing_service_instances
    if username in _billing_service_instances:
        del _billing_service_instances[username]
        logger.info(f"Cleaned up billing service instance for user: {username}")


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
        
        username = request.username
        if not username:
            raise HTTPException(
                status_code=400,
                detail="Username is required"
            )
        
        # Get current user status
        user_status = user_api_keys.get_user_status(username)
        
        # If there was a previous key for this user, invalidate its cache
        old_key = user_api_keys.get(username)
        if old_key:
            service = get_billing_service(username)
            service.agent.invalidate_session_cache(old_key)
            logger.info(f"Invalidated cache for old API key for user: {username}")
        
        # Store the new API key
        user_api_keys.set(username, request.api_key)
        
        # Create response message based on user status
        message = "Signed up and API key set successfully" if user_status['is_new_user'] else "Signed in and API key updated successfully"
        
        logger.info(f"API key set for user: {username} (ends with: ...{request.api_key[-4:]})")
        
        return ApiKeyResponse(
            success=True,
            message=message,
            username=username,
            using_custom_key=True,
            is_new_user=user_status['is_new_user']
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
async def remove_api_key(username: str):
    """Remove the stored API key and invalidate its cache"""
    try:
        if not username:
            raise HTTPException(
                status_code=400,
                detail="Username is required"
            )
            
        if user_api_keys.has_api_key(username):
            # Get the key before deleting to invalidate its cache
            api_key = user_api_keys.get(username)
            
            # Invalidate cache for this API key
            service = get_billing_service(username)
            service.agent.invalidate_session_cache(api_key)
            
            # Remove the key
            user_api_keys.delete(username)
            
            logger.info(f"API key removed for user: {username}")
            return {
                "success": True,
                "message": "API key removed. Using default key from environment."
            }
        else:
            return {
                "success": True,
                "message": "No custom API key was set for this user."
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing API key: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error removing API key: {str(e)}"
        )


@router.get("/api-key-status")
async def get_api_key_status(username: str):
    """Check status of a user session and their API key"""
    if not username:
        raise HTTPException(
            status_code=400,
            detail="Username is required"
        )
    
    user_status = user_api_keys.get_user_status(username)
    has_env_key = bool(settings.OPENAI_API_KEY)
    
    # Get cache info for debugging
    service = get_billing_service()
    cache_info = service.agent.get_cache_info()
    
    return {
        "exists": user_status['exists'],
        "has_api_key": user_status['has_api_key'],
        "is_new_user": user_status['is_new_user'],
        "has_env_key": has_env_key,
        "using_custom_key": user_status['has_api_key'],
        "username": username,
        "cache_info": cache_info
    }


@router.post("/query", response_model=BillingQueryResponse)
async def query_billing_data(request: BillingQueryRequest):
    """Query billing data using AI agent"""
    try:
        logger.info(f"Received billing query from user {request.username}: {request.query}")

        # Verify user exists and has API key
        if not user_api_keys.has_user(request.username):
            raise HTTPException(
                status_code=401,
                detail="User not found. Please set up your session first."
            )
        
        # Get API key and service for this user
        api_key = user_api_keys.get(request.username)
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="No API key set for this user. Please set your API key first."
            )
        
        # Get user-specific billing service
        service = get_billing_service(request.username)
        
        # Process query through the billing service
        result = await service.process_query(request.query, request.file_name, api_key=api_key)
        
        return BillingQueryResponse(
            success=True,
            answer=result["answer"],
            reasoning=result.get("reasoning", ""),
            execution_time=result.get("execution_time", 0),
            using_custom_key=True,
            username=request.username
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing billing query: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )


@router.post("/upload", response_model=FileUploadResponse)
async def upload_excel_file(
    file: UploadFile = File(...),
    username: str = None
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
        
        # Upload to S3
        service = get_billing_service()
        try:
            service.load_file(content, file.filename)
            logger.info(f"File uploaded to S3 and loaded: {file.filename}")
        except Exception as e:
            logger.error(f"Failed to process file: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process file: {str(e)}"
            )
        
        # Clear agent cache for the user who uploaded (if username provided)
        if username:
            user_service = get_billing_service(username)
            user_service.agent._invalidate_cache()
            logger.info(f"Cleared agent cache for user {username} after file upload")
        
        return FileUploadResponse(
            success=True,
            message="File uploaded to S3 successfully",
            filename=file.filename,
            file_path=f"s3://{settings.S3_BUCKET_NAME}/{file.filename}"
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


@router.post("/cleanup-session")
async def cleanup_session(username: str):
    """Cleanup user session when they leave the app"""
    try:
        if not username:
            raise HTTPException(
                status_code=400,
                detail="Username is required"
            )
        
        # Get user's service and clear agent cache before cleanup
        if username in _billing_service_instances:
            service = _billing_service_instances[username]
            service.agent._invalidate_cache()
            logger.info(f"Cleared agent cache for user: {username}")
        
        cleanup_user_session(username)
        return {
            "success": True,
            "message": f"Session cleaned up for user: {username}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up session: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error cleaning up session: {str(e)}"
        )