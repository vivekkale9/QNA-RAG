import logging
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import api_router
from app.db import (
    init_postgres_db, connect_to_postgres, disconnect_from_postgres,
    init_mongodb_db, connect_to_mongodb, disconnect_from_mongodb,
    MilvusVectorStore
)
from app.middlewares import (
    AuthenticationMiddleware,
    ErrorHandlerMiddleware
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
settings = get_settings()

# Import dependencies for cleanup
from app.dependencies import cleanup_vector_store

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

        await connect_to_mongodb()
        await init_mongodb_db()
        logger.info("✅ MongoDB initialized successfully")

        # Vector store will be initialized lazily on first request
        logger.info("✅ Vector store will be initialized on first request")
        logger.info("🚀 Application startup completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Error during startup: {e}")
        raise
    
    yield
    
    try:
        # Cleanup resources
        await cleanup_vector_store()
        await disconnect_from_postgres()
        await disconnect_from_mongodb()
        logger.info("✅ Application shutdown completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")

app = FastAPI(
    title='Q&A RAG',
    description="AI-powered document chat application with RAG capabilities",
    version="1.0.0",
    lifespan=lifespan
)

origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
]

if settings.environment == "production":
    origins = [
        "https://qna-rag.vercel.app",
        "https://qna-rag.onrender.com"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(ErrorHandlerMiddleware)

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

@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and deployment.
    
    Returns:
        dict: Health status information
    """
    return {
        "status": "healthy",
        "environment": settings.environment,
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
    ) 