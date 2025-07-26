"""
FastAPI DocuChat Application

Main application entry point with middleware, routes, and configuration.
"""
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title='Q&A RAG',
    description="AI-powered document chat application with RAG capabilities",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else ["https://to-be-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
async def root():
    """
    Root endpoint with application information.
    
    Returns:
        dict: Application welcome message and status
    """
    return {
        "message": "Welcome to DocuChat AI",
        "description": "AI-powered document chat with RAG capabilities",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    ) 