from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager  
import logging
import time
from collections import defaultdict

from app.api import billing          
from app.config import settings      

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Simple rate limiter
rate_limit_storage = defaultdict(list)


def check_rate_limit(client_ip: str, max_requests: int = 30, window: int = 60) -> bool:
    """
    Simple rate limiter: max_requests per window seconds per IP
    
    Args:
        client_ip: Client IP address
        max_requests: Maximum number of requests allowed in the window (default: 30)
        window: Time window in seconds (default: 60)
    
    Returns:
        True if request is allowed, False if rate limit exceeded
    """
    now = time.time()
    
    # Remove old requests outside the time window
    rate_limit_storage[client_ip] = [
        req_time for req_time in rate_limit_storage[client_ip] 
        if now - req_time < window
    ]
    
    # Check if under limit
    if len(rate_limit_storage[client_ip]) >= max_requests:
        return False
    
    # Add current request
    rate_limit_storage[client_ip].append(now)
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting up Billing AI Backend...")
    logger.info(f"Environment: {'Development' if settings.DEBUG else 'Production'}")
    yield
    logger.info("Shutting down Billing AI Backend...")


# Create FastAPI app
app = FastAPI(
    title="Billing AI Backend",
    description="AI-powered billing data analysis using LangChain agents",
    version="1.0.0",
    lifespan=lifespan
)


# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware to prevent abuse
    Skips rate limiting for health check endpoints
    """
    # Skip rate limit for health check and root
    if request.url.path in ["/health", "/"]:
        return await call_next(request)
    
    client_ip = request.client.host
    
    if not check_rate_limit(client_ip):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Too many requests. Please slow down and try again later."
            }
        )
    
    response = await call_next(request)
    return response


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(billing.router, prefix="/api/v1/billing", tags=["billing"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        status_code=200,
        content={"status": "healthy", "message": "Billing AI Backend is running"}
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to Billing AI Backend API"}


if __name__ == "__main__":
    import uvicorn
    # For production, set reload=False
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000, 
        reload=False  # Change to False for production
    )