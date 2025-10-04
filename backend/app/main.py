from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager  
import logging

from app.api import billing          
from app.config import settings      

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting up Billing AI Backend...")
    yield
    logger.info("Shutting down Billing AI Backend...")


# Create FastAPI app
app = FastAPI(
    title="Billing AI Backend",
    description="AI-powered billing data analysis using LangChain agents",
    version="1.0.0",
    lifespan=lifespan
)

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
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)