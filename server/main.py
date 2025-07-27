import logging
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import api_router
from app.db import (
    init_postgres_db, connect_to_postgres, disconnect_from_postgres
)
from app.middlewares import (
    AuthenticationMiddleware
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    try:
        # Initialize PostgreSQL (User/Auth data)
        await connect_to_postgres()
        await init_postgres_db()
        logger.info("✅ PostgreSQL initialized successfully")
        logger.info("🚀 Application startup completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Error during startup: {e}")
        raise
    
    yield
    
    try:
        await disconnect_from_postgres()
        logger.info("✅ Application shutdown completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")

app = FastAPI(
    title='Q&A RAG',
    description="AI-powered document chat application with RAG capabilities",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else ["https://to-be-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.add_middleware(AuthenticationMiddleware)

app.include_router(api_router)

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
    ) 