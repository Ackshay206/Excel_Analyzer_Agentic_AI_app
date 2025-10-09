from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager  
import logging
import time
from collections import defaultdict
import os
import psutil  # Add this import

from app.api import billing          
from app.config import settings      

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def log_memory_usage():
    """Log current memory usage"""
    try:
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        logger.info(f"Memory usage: {memory_mb:.1f} MB")
        return memory_mb
    except:
        return 0


# Simple rate limiter
rate_limit_storage = defaultdict(list)


def check_rate_limit(client_ip: str, max_requests: int = 30, window: int = 60) -> bool:
    """Simple rate limiter"""
    now = time.time()
    rate_limit_storage[client_ip] = [
        req_time for req_time in rate_limit_storage[client_ip] 
        if now - req_time < window
    ]
    
    if len(rate_limit_storage[client_ip]) >= max_requests:
        return False
    
    rate_limit_storage[client_ip].append(now)
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting up Billing AI Backend...")
    logger.info(f"Environment: {'Development' if settings.DEBUG else 'Production'}")
    log_memory_usage()
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
    """Rate limiting middleware"""
    if request.url.path in ["/health", "/"]:
        response = await call_next(request)
        return response
    
    client_ip = request.client.host
    
    if not check_rate_limit(client_ip):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please slow down."}
        )
    
    response = await call_next(request)
    return response


# CORS
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
    memory = log_memory_usage()
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy", 
            "message": "Billing AI Backend is running",
            "memory_mb": round(memory, 1)
        }
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to Billing AI Backend API"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)