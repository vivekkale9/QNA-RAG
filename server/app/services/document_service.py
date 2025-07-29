"""
Document Service

Business logic for document upload, processing, and management.
"""

import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, UploadFile
from bson import ObjectId

from ..db.postgres import User
from ..db.mongodb import Document, Chunk
from ..models.document import (
    DocumentResponse, UploadResponse, ProcessingStatus, DocumentStatus, DocumentType
)
from ..utils.document_processor import DocumentProcessor
from ..db.milvus_vector_store import MilvusVectorStore
from ..utils.sse import DocumentProcessingEventEmitter, ProcessingStatus

logger = logging.getLogger(__name__)


class DocumentService:
    """Service class for document operations."""
    
    def __init__(self):
        self.processor = DocumentProcessor()
    
    async def upload_document(
        self, 
        file: UploadFile, 
        user_id: str, 
        db: AsyncSession,
        vector_store: MilvusVectorStore,
        event_emitter: DocumentProcessingEventEmitter = None
    ) -> UploadResponse:
        """
        Upload and process a document.
        
        Args:
            file: Uploaded file
            user_id: User ID
            db: PostgreSQL database session
            vector_store: Milvus vector store instance
            event_emitter: Optional event emitter for progress updates
            
        Returns:
            UploadResponse: Upload result
        """
        try:
            # Emit starting status
            if event_emitter:
                await event_emitter.emit_status(ProcessingStatus.STARTED)
            
            # Validate user exists
            if event_emitter:
                await event_emitter.emit_status(ProcessingStatus.VALIDATING, "Validating user and file...")
                
            user = await self._get_user_by_id(db, user_id)
            if not user:
                error_msg = "User not found"
                if event_emitter:
                    await event_emitter.emit_status(ProcessingStatus.FAILED, error_msg)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=error_msg
                )
            
            # Validate file
            if not file or not file.filename:
                error_msg = "No file provided or filename is empty"
                if event_emitter:
                    await event_emitter.emit_status(ProcessingStatus.FAILED, error_msg)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
            
            # Read file content once and store it
            try:
                file_content = await file.read()
                file_size = len(file_content)
                
                # Validate file size
                if file_size == 0:
                    error_msg = "File is empty"
                    if event_emitter:
                        await event_emitter.emit_status(ProcessingStatus.FAILED, error_msg)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=error_msg
                    )
                    
            except Exception as e:
                error_msg = f"Failed to read file content: {str(e)}"
                if event_emitter:
                    await event_emitter.emit_status(ProcessingStatus.FAILED, error_msg)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
            
            # Determine file type
            file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else 'txt'
            if file_extension == 'pdf':
                file_type = DocumentType.PDF
            elif file_extension == 'md':
                file_type = DocumentType.MD
            else:
                file_type = DocumentType.TXT
            
            # Create safe filename
            safe_filename = file.filename.replace(' ', '_').replace('/', '_')
            
            # Create document record (MongoDB) with all required fields
            try:
                document = Document(
                    filename=safe_filename,
                    original_filename=file.filename,
                    file_path=f"/uploads/{user_id}/{safe_filename}",
                    file_type=file_type,
                    file_size=file_size,
                    user_id=user_id,
                    status=DocumentStatus.PROCESSING,
                    record_status=1  # Set as active document
                )
                
                # Save document to MongoDB
                await document.save()
                
            except Exception as e:
                error_msg = f"Failed to create document record: {str(e)}"
                logger.error(error_msg)
                if event_emitter:
                    await event_emitter.emit_status(ProcessingStatus.FAILED, error_msg)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_msg
                )
            
            # Process document with progress updates (pass file content directly)
            await self._process_document(file_content, file.filename, document, vector_store, event_emitter)
            
            logger.info(f"Document uploaded: {file.filename} by user {user_id}")
            
            return UploadResponse(
                document_id=str(document.id),
                filename=file.filename,
                status=DocumentStatus.PROCESSING,
                message="Document upload initiated. Processing in background."
            )
            
        except HTTPException:
            # Re-raise HTTP exceptions (they already have proper status codes)
            raise
        except Exception as e:
            error_msg = f"Document upload failed: {str(e)}" if str(e) else "Document upload failed: Unknown error"
            logger.error(error_msg)
            
            # Emit failure status for SSE
            if event_emitter:
                await event_emitter.emit_status(ProcessingStatus.FAILED, error_msg)
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
    
    async def get_document(
        self, 
        document_id: str, 
        user_id: str, 
        db: AsyncSession
    ) -> DocumentResponse:
        """
        Get a specific document.
        
        Args:
            document_id: Document ID
            user_id: User ID
            db: PostgreSQL database session (for user verification)
            
        Returns:
            DocumentResponse: Document information
            
        Raises:
            HTTPException: If document not found
        """
        try:
            # Verify user exists
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Get document from MongoDB (only active documents)
            try:
                obj_id = ObjectId(document_id)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid document ID format"
                )
            
            document = await Document.find_one(
                Document.id == obj_id,
                Document.user_id == user_id,
                Document.record_status == 1
            )
            
            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document not found"
                )
            
            return DocumentResponse(
                id=str(document.id),
                name=document.original_filename,
                file_size=document.file_size,
                file_type=document.file_type,
                status=document.status,
                chunk_count=document.total_chunks,
                query_count=0,  # Default value, can be enhanced later
                uploaded_at=document.uploaded_at,
                processed_at=document.processed_at,
                user_id=document.user_id,
                file_path=document.file_path
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get document failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve document"
            )
    
    async def get_user_documents(
        self, 
        user_id: str, 
        skip: int, 
        limit: int, 
        db: AsyncSession
    ) -> List[DocumentResponse]:
        """
        Get user's documents with pagination.
        
        Args:
            user_id: User ID
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            db: PostgreSQL database session (for user verification)
            
        Returns:
            List[DocumentResponse]: List of user documents
            
        Raises:
            HTTPException: If user not found
        """
        try:
            # Verify user exists
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Get documents from MongoDB (only active documents)
            documents = await Document.find(
                Document.user_id == user_id,
                Document.record_status == 1
            ).skip(skip).limit(limit).to_list()
            
            return [
                DocumentResponse(
                    id=str(doc.id),
                    name=doc.original_filename,
                    file_size=doc.file_size,
                    file_type=doc.file_type,
                    status=doc.status,
                    chunk_count=doc.total_chunks,
                    query_count=0,  # Default value, can be enhanced later
                    uploaded_at=doc.uploaded_at,
                    processed_at=doc.processed_at,
                    user_id=doc.user_id,
                    file_path=doc.file_path
                )
                for doc in documents
            ]
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get user documents failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve documents"
            )
    
    async def delete_document(
        self, 
        document_id: str, 
        user_id: str, 
        db: AsyncSession,
        vector_store: MilvusVectorStore
    ) -> Dict[str, Any]:
        """
        Soft delete a document by updating its record_status to -1.
        
        Args:
            document_id: Document ID
            user_id: User ID
            db: PostgreSQL database session (for user verification)
            vector_store: Vector store manager
            
        Returns:
            Dict[str, Any]: Success message
            
        Raises:
            HTTPException: If deletion fails
        """
        try:
            # Verify user exists
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Get document from MongoDB (only active documents)
            try:
                obj_id = ObjectId(document_id)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid document ID format"
                )
            
            document = await Document.find_one(
                Document.id == obj_id,
                Document.user_id == user_id,
                Document.record_status == 1
            )
            
            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document not found"
                )
            
            # Soft delete: update record_status to -1
            document.record_status = -1
            document.updated_at = datetime.now(timezone.utc)
            await document.save()
            
            # Remove from vector store
            await vector_store.delete_document_chunks(user_id, document_id)
            
            logger.info(f"Document soft deleted: {document.filename} by user {user_id}")
            
            return {"message": "Document deleted successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Document deletion failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Document deletion failed"
            )
    
    async def get_processing_status(
        self, 
        document_id: str, 
        user_id: str, 
        db: AsyncSession
    ) -> ProcessingStatus:
        """
        Get document processing status.
        
        Args:
            document_id: Document ID
            user_id: User ID
            db: PostgreSQL database session (for user verification)
            
        Returns:
            ProcessingStatus: Processing status information
            
        Raises:
            HTTPException: If document not found
        """
        try:
            # Verify user exists
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Get document from MongoDB (only active documents)
            try:
                obj_id = ObjectId(document_id)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid document ID format"
                )
            
            document = await Document.find_one(
                Document.id == obj_id,
                Document.user_id == user_id,
                Document.record_status == 1
            )
            
            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document not found"
                )
            
            return ProcessingStatus(
                document_id=str(document.id),
                status=document.status,
                progress=100 if document.status == DocumentStatus.COMPLETED else 0,
                chunks_processed=document.chunk_count or 0,
                error_message=getattr(document, 'error_message', None)
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get processing status failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve processing status"
            )
    
    # Private helper methods
    
    async def _get_user_by_id(self, db: AsyncSession, user_id: str) -> Optional[User]:
        """Get user by ID from PostgreSQL."""
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    async def _process_document(
        self, 
        file_content: bytes,
        filename: str, 
        document: Document, 
        vector_store: MilvusVectorStore,
        event_emitter: DocumentProcessingEventEmitter = None
    ):
        """Process document: extract text, chunk, embed, and store."""
        try:
            # Extract text from document
            if event_emitter:
                await event_emitter.emit_status(ProcessingStatus.EXTRACTING, "Extracting text from document...")
            
            result = await self.processor.process_document_content(file_content, filename)
            
            # Update progress - chunking
            if event_emitter:
                await event_emitter.emit_status(
                    ProcessingStatus.CHUNKING, 
                    f"Created {len(result['chunks'])} text chunks",
                    {"chunk_count": len(result["chunks"]), "word_count": result["word_count"]}
                )
            
            # Update document record
            document.text_content = result["full_text"][:5000]  # Store first 5000 chars as preview
            document.total_chunks = len(result["chunks"])
            document.processing_metadata = {
                "word_count": result["word_count"],
                "char_count": result["char_count"],
                "page_count": result.get("page_count", 1)
            }
            document.processed_at = datetime.now(timezone.utc)
            document.status = DocumentStatus.COMPLETED
            await document.save()

            # Save chunks to MongoDB
            for i, chunk_data in enumerate(result["chunks"]):
                chunk = Chunk(
                    document_id=str(document.id),
                    content=chunk_data["content"],
                    chunk_index=i,
                    chunk_metadata=chunk_data["metadata"],
                    created_at=datetime.now(timezone.utc)
                )
                await chunk.save()

            # Generate embeddings and store in vector database
            if event_emitter:
                await event_emitter.emit_status(ProcessingStatus.EMBEDDING, "Generating embeddings...")
            
            chunk_metadata = [chunk["metadata"] for chunk in result["chunks"]]
            await vector_store.add_document_chunks(
                user_id=document.user_id,
                doc_id=str(document.id),
                source=document.filename,
                chunks=[chunk["content"] for chunk in result["chunks"]],
                chunk_metadata=chunk_metadata
            )
            
            # Final storage step
            if event_emitter:
                await event_emitter.emit_status(ProcessingStatus.STORING, "Finalizing document storage...")
            
            # Emit completion status
            if event_emitter:
                await event_emitter.emit_status(
                    ProcessingStatus.COMPLETED, 
                    "Document processing completed successfully!",
                    {
                        "document_id": str(document.id),
                        "chunk_count": len(result["chunks"]),
                        "file_size": result["file_size"],
                        "word_count": result["word_count"]
                    }
                )
            
        except Exception as e:
            # Update document with error status
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)
            document.processed_at = datetime.now(timezone.utc)
            await document.save()
            
            # Emit failure status
            if event_emitter:
                await event_emitter.emit_status(ProcessingStatus.FAILED, f"Processing failed: {str(e)}")
            
            logger.error(f"Document processing failed: {str(e)}")
            raise 