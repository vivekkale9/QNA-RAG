from typing import Optional
from fastapi import APIRouter, Depends, Query

from ..controllers.admin_vector_controller import AdminVectorController
from ..utils.auth import require_role

router = APIRouter(prefix="/admin/vector", tags=["Admin Vector Store"])
admin_vector_controller = AdminVectorController()


@router.get("/health")
async def get_vector_store_health(
    _: dict = Depends(require_role("admin"))
):
    """
    Get comprehensive health information about the vector store.
    
    **Admin Only**
    
    Returns detailed information about:
    - Milvus connection status
    - Collection status and statistics  
    - Data consistency with MongoDB backup
    - Performance metrics
    - Error diagnostics
    """
    return await admin_vector_controller.get_vector_health()


@router.post("/rebuild")
async def rebuild_vector_store(
    user_filter: Optional[str] = Query(None, description="Filter by specific user ID"),
    document_filter: Optional[str] = Query(None, description="Filter by specific document ID"),
    batch_size: int = Query(100, ge=10, le=1000, description="Batch size for processing"),
    _: dict = Depends(require_role("admin"))
):
    """
    Rebuild vector store from MongoDB backup.
    
    **Admin Only - Disaster Recovery**
    
    This endpoint rebuilds the entire Milvus vector store from MongoDB backup data.
    
    **Use Cases:**
    - Milvus data corruption or loss
    - Migration to new Milvus instance
    - Data consistency restoration
    - Performance optimization (rebuild indexes)
    
    **Parameters:**
    - `user_filter`: Rebuild only specific user's data (optional)
    - `document_filter`: Rebuild only specific document (optional)  
    - `batch_size`: Number of chunks to process at once (10-1000)
    
    **Warning:** This endpoint may take a long time for large datasets.
    """
    return await admin_vector_controller.rebuild_vector_store(
        user_filter=user_filter,
        document_filter=document_filter,
        batch_size=batch_size
    )


@router.get("/backup/stats")
async def get_backup_statistics(
    _: dict = Depends(require_role("admin"))
):
    """
    Get detailed statistics about MongoDB backup data availability.
    
    **Admin Only**
    
    Returns information about:
    - Total documents and chunks in backup
    - User and document distribution
    - File type breakdown
    - Document status distribution
    - Data availability for rebuild operations
    
    Use this to assess backup data before initiating a rebuild.
    """
    return await admin_vector_controller.get_backup_statistics() 