from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
import asyncio

from ..controllers.admin_vector_controller import AdminVectorController
from ..utils.auth import require_role
from ..utils.sse import VectorRebuildEventEmitter, create_rebuild_sse_generator, get_sse_headers

router = APIRouter(prefix="/admin/vector", tags=["Admin Vector Store"])
admin_vector_controller = AdminVectorController()



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


@router.post("/rebuild/stream", response_class=StreamingResponse)
async def rebuild_vector_store_stream(
    user_filter: Optional[str] = Query(None, description="Filter by specific user ID"),
    document_filter: Optional[str] = Query(None, description="Filter by specific document ID"),
    batch_size: int = Query(100, ge=10, le=1000, description="Batch size for processing"),
    _: dict = Depends(require_role("admin"))
):
    """
    Rebuild vector store from MongoDB backup with real-time SSE progress updates.
    
    **Admin Only - Disaster Recovery**
    
    Returns a Server-Sent Events stream with rebuild progress updates:
    - started: Rebuild begins
    - initializing: Vector store initialization
    - counting: Counting documents and chunks
    - processing: Processing chunks with progress
    - finalizing: Getting final statistics
    - completed: Rebuild complete
    - failed: Rebuild failed
    
    **Parameters:**
    - `user_filter`: Rebuild only specific user's data (optional)
    - `document_filter`: Rebuild only specific document (optional)  
    - `batch_size`: Number of chunks to process at once (10-1000)
    
    **Timeout:** 10 minutes for large datasets.
    """
    
    # Create event emitter for progress updates
    event_emitter = VectorRebuildEventEmitter()
    
    async def process_rebuild():
        try:
            await admin_vector_controller.rebuild_vector_store_with_events(
                user_filter=user_filter,
                document_filter=document_filter,
                batch_size=batch_size,
                event_emitter=event_emitter
            )
        except Exception as e:
            # Error will be emitted by the service
            pass
    
    # Start rebuild processing in background
    asyncio.create_task(process_rebuild())
    
    # Create SSE generator
    sse_generator = create_rebuild_sse_generator(event_emitter, timeout=600)
    
    return StreamingResponse(
        sse_generator,
        media_type="text/event-stream",
        headers=get_sse_headers()
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