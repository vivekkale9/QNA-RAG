import logging
from typing import Dict, Any
from fastapi import HTTPException, status

from ..services.vector_rebuild_service import VectorRebuildService
from ..db.milvus_vector_store import MilvusVectorStore

logger = logging.getLogger(__name__)


class AdminVectorController:
    
    def __init__(self):
        self.rebuild_service = VectorRebuildService()
    
    async def get_vector_health(self) -> Dict[str, Any]:
        """
        Get comprehensive health information about the vector store.
        
        Returns:
            Dict containing health status, statistics, and diagnostics
        """
        try:
            # Initialize vector store
            vector_store = MilvusVectorStore()
            await vector_store.initialize()
            
            # Get health check
            health_info = await vector_store.health_check()
            
            # Get detailed statistics if healthy
            detailed_stats = {}
            if health_info["status"] in ["healthy", "degraded"]:
                try:
                    detailed_stats = await vector_store.get_detailed_statistics()
                except Exception as e:
                    health_info["errors"].append(f"Stats error: {str(e)}")
            
            # Get MongoDB backup information
            backup_stats = await self.rebuild_service.get_mongodb_backup_stats()
            
            return {
                "vector_store": health_info,
                "detailed_statistics": detailed_stats,
                "backup_availability": backup_stats
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Health check failed: {str(e)}"
            )
    
    async def rebuild_vector_store(
        self,
        user_filter: str = None,
        document_filter: str = None,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Rebuild vector store from MongoDB backup.
        
        Args:
            user_filter: Optional user ID to rebuild only specific user's data
            document_filter: Optional document ID to rebuild only specific document
            batch_size: Number of chunks to process in each batch
            
        Returns:
            Dict with rebuild results and statistics
        """
        try:
            result = await self.rebuild_service.rebuild_from_mongodb(
                user_filter=user_filter,
                document_filter=document_filter,
                batch_size=batch_size
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Rebuild failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Rebuild failed: {str(e)}"
            )
    
    async def get_backup_statistics(self) -> Dict[str, Any]:
        """
        Get detailed statistics about MongoDB backup data.
        
        Returns:
            Dict containing backup data statistics
        """
        try:
            backup_stats = await self.rebuild_service.get_mongodb_backup_stats()
            return backup_stats
            
        except Exception as e:
            logger.error(f"Backup stats failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get backup statistics: {str(e)}"
            ) 