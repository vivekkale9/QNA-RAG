from typing import List, Optional
from fastapi import HTTPException, UploadFile, status

from ..services import DocumentService
from ..models import DocumentResponse
from ..dependencies import get_vector_store

class UploadController:
    
    def __init__(self):
        self.document_service = DocumentService()

    async def get_documents(
        self, 
        user_id: str, 
        skip: int = 0, 
        limit: int = 50, 
        db_session = None
    ) -> List[DocumentResponse]:
        """
        Get user documents.
        
        Args:
            user_id: Current user ID
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            db_session: Database session
            
        Returns:
            List[DocumentResponse]: User's documents
        """
        documents = await self.document_service.get_user_documents(
            user_id=user_id,
            skip=skip,
            limit=limit,
            db=db_session
        )
        return [DocumentResponse.model_validate(doc) for doc in documents]
    
    async def get_document(
        self, 
        document_id: str, 
        user_id: str, 
        db_session
    ) -> DocumentResponse:
        """
        Get specific document.
        
        Args:
            document_id: Document ID
            user_id: Current user ID
            db_session: Database session
            
        Returns:
            DocumentResponse: Document information
        """
        document = await self.document_service.get_document(
            document_id=document_id,
            user_id=user_id,
            db=db_session
        )
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        return DocumentResponse.model_validate(document)
    
    async def delete_document(
        self, 
        document_id: str, 
        user_id: str, 
        db_session
    ) -> dict:
        """
        Delete document.
        
        Args:
            document_id: Document ID
            user_id: Current user ID
            db_session: Database session
            
        Returns:
            dict: Deletion confirmation
        """
        # Get vector store with lazy initialization
        vector_manager = await get_vector_store()
        
        result = await self.document_service.delete_document(
            document_id=document_id,
            user_id=user_id,
            db=db_session,
            vector_store=vector_manager
        )
        
        return result 