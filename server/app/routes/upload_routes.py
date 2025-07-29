
from typing import List
from fastapi import APIRouter, Depends, File, UploadFile, Query
from fastapi.responses import StreamingResponse
import asyncio

from ..utils import get_current_user
from ..db import MilvusVectorStore, get_postgres_database
from ..utils.sse import get_sse_headers, create_sse_generator, DocumentProcessingEventEmitter
from ..services import DocumentService
from ..models import DocumentResponse
from ..controllers import UploadController

router = APIRouter(prefix="/upload", tags=["Document Upload"])
document_service = DocumentService()
upload_controller = UploadController()

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

@router.get("/", response_model=List[DocumentResponse])
async def get_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user = Depends(get_current_user),
    db_session = Depends(get_postgres_database)
):
    return await upload_controller.get_documents(
        current_user.id, skip, limit, db_session
    )

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user = Depends(get_current_user),
    db_session = Depends(get_postgres_database)
):
    return await upload_controller.get_document(
        document_id, current_user.id, db_session
    )

@router.delete("/{document_id}", response_model=dict)
async def delete_document(
    document_id: str,
    current_user = Depends(get_current_user),
    db_session = Depends(get_postgres_database)
):
    return await upload_controller.delete_document(
        document_id, current_user.id, db_session
    ) 