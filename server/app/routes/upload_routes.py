
from typing import List
from fastapi import APIRouter, Depends, File, UploadFile, Query
from fastapi.responses import StreamingResponse
import asyncio

from ..utils import get_current_user
from ..db import MilvusVectorStore, get_postgres_database
from ..utils.sse import get_sse_headers, create_sse_generator, DocumentProcessingEventEmitter
from ..services import DocumentService

router = APIRouter(prefix="/upload", tags=["Document Upload"])
document_service = DocumentService()

@router.post("/", response_class=StreamingResponse)
async def upload_document_stream(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db_session = Depends(get_postgres_database)
):
    """
    Document upload endpoint with real-time SSE progress updates.
    
    Returns a Server-Sent Events stream with processing status updates:
    - started: Processing begins
    - validating: File validation
    - extracting: Text extraction
    - chunking: Text chunking
    - embedding: Embedding generation
    - storing: Vector storage
    - processed: Processing complete
    - failed: Processing failed
    """
    
    # Create event emitter for progress updates
    event_emitter = DocumentProcessingEventEmitter()
    
    # Initialize vector store
    vector_store = MilvusVectorStore()
    await vector_store.initialize()
    
    async def process_document():
        try:
            await document_service.upload_document(
                file=file,
                user_id=current_user.id,
                db=db_session,
                vector_store=vector_store,
                event_emitter=event_emitter
            )
        except Exception as e:
            # Error will be emitted by the service
            pass
    
    # Start document processing in background
    asyncio.create_task(process_document())
    
    # Create SSE generator
    sse_generator = create_sse_generator(event_emitter, timeout=300)
    
    # Return streaming response
    return StreamingResponse(
        sse_generator,
        media_type="text/event-stream",
        headers=get_sse_headers()
    )