"""
Dependency injection for FastAPI routes and controllers.
Handles shared resources like vector store to avoid circular imports.
"""

import logging
from typing import Optional
from .db.milvus_vector_store import MilvusVectorStore

logger = logging.getLogger(__name__)

# Global vector store instance
_vector_store_manager: Optional[MilvusVectorStore] = None

async def get_vector_store() -> MilvusVectorStore:
    """
    Get vector store instance with lazy initialization.
    This saves memory during startup by only initializing when needed.
    """
    global _vector_store_manager
    if _vector_store_manager is None:
        logger.info("🔄 Initializing vector store on first use...")
        _vector_store_manager = MilvusVectorStore()
        await _vector_store_manager.initialize()
        logger.info("✅ Vector store initialized successfully")
    return _vector_store_manager

def set_vector_store(vector_store: MilvusVectorStore) -> None:
    """Set the global vector store instance (for testing)"""
    global _vector_store_manager
    _vector_store_manager = vector_store

async def cleanup_vector_store() -> None:
    """Cleanup vector store resources"""
    global _vector_store_manager
    if _vector_store_manager:
        try:
            await _vector_store_manager.cleanup()
            logger.info("✅ Vector store cleanup completed")
        except Exception as e:
            logger.error(f"❌ Error during vector store cleanup: {e}")
        finally:
            _vector_store_manager = None 