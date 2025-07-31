"""
Unit tests for DocumentService.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from fastapi import HTTPException, status, UploadFile
from io import BytesIO

from app.services.document_service import DocumentService
from app.models.document import DocumentResponse, UploadResponse, DocumentStatus, DocumentType
from app.db.postgres import User
from app.db.mongodb import Document, Chunk


@pytest.mark.unit
@pytest.mark.documents
class TestDocumentService:
    """Test cases for DocumentService."""

    async def test_upload_document_success(self, document_service, async_db_session, mock_vector_store, test_user, mock_file_upload):
        """Test successful document upload."""
        with patch.object(document_service, '_get_user_by_id', return_value=test_user):
            with patch.object(document_service, '_validate_file', return_value=True):
                with patch.object(document_service, '_save_file', return_value="/tmp/test_file.pdf"):
                    with patch('app.db.mongodb.Document') as mock_doc_class:
                        mock_document = Mock()
                        mock_document.id = "doc_123"
                        mock_document.save = AsyncMock()
                        mock_doc_class.return_value = mock_document
                        
                        with patch.object(document_service, '_process_document_async', new_callable=AsyncMock):
                            result = await document_service.upload_document(
                                mock_file_upload, test_user.id, async_db_session, mock_vector_store
                            )
                            
                            assert isinstance(result, UploadResponse)
                            assert result.document_id == "doc_123"
                            assert result.status == "processing"
                            assert result.message == "Document uploaded and processing started"

    async def test_upload_document_user_not_found(self, document_service, async_db_session, mock_vector_store, mock_file_upload):
        """Test document upload when user doesn't exist."""
        with patch.object(document_service, '_get_user_by_id', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await document_service.upload_document(
                    mock_file_upload, "nonexistent_user", async_db_session, mock_vector_store
                )
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert "User not found" in exc_info.value.detail

    async def test_upload_document_invalid_file(self, document_service, async_db_session, mock_vector_store, test_user, mock_file_upload):
        """Test document upload with invalid file."""
        with patch.object(document_service, '_get_user_by_id', return_value=test_user):
            with patch.object(document_service, '_validate_file', side_effect=HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type"
            )):
                with pytest.raises(HTTPException) as exc_info:
                    await document_service.upload_document(
                        mock_file_upload, test_user.id, async_db_session, mock_vector_store
                    )
                
                assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
                assert "Invalid file type" in exc_info.value.detail

    async def test_get_user_documents_success(self, document_service, async_db_session, test_user):
        """Test successful retrieval of user documents."""
        mock_documents = [
            Mock(
                id="doc_1", 
                name="test1.pdf", 
                status=DocumentStatus.COMPLETED,
                uploaded_at=datetime.now(timezone.utc)
            ),
            Mock(
                id="doc_2", 
                name="test2.pdf", 
                status=DocumentStatus.COMPLETED,
                uploaded_at=datetime.now(timezone.utc)
            )
        ]
        
        with patch.object(document_service, '_get_user_by_id', return_value=test_user):
            with patch('app.db.mongodb.Document.find') as mock_find:
                mock_find.return_value.sort.return_value.skip.return_value.limit.return_value.to_list = AsyncMock(
                    return_value=mock_documents
                )
                
                result = await document_service.get_user_documents(
                    test_user.id, async_db_session, skip=0, limit=10
                )
                
                assert len(result) == 2
                assert all(isinstance(doc, DocumentResponse) for doc in result)

    async def test_get_user_documents_user_not_found(self, document_service, async_db_session):
        """Test document retrieval when user doesn't exist."""
        with patch.object(document_service, '_get_user_by_id', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await document_service.get_user_documents(
                    "nonexistent_user", async_db_session
                )
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_document_success(self, document_service, async_db_session, test_user):
        """Test successful document retrieval."""
        mock_document = Mock()
        mock_document.id = "doc_123"
        mock_document.user_id = test_user.id
        mock_document.name = "test.pdf"
        mock_document.status = DocumentStatus.COMPLETED
        
        with patch.object(document_service, '_get_user_by_id', return_value=test_user):
            with patch('app.db.mongodb.Document.get', return_value=mock_document):
                result = await document_service.get_document(
                    "doc_123", test_user.id, async_db_session
                )
                
                assert isinstance(result, DocumentResponse)
                assert result.id == "doc_123"

    async def test_get_document_not_found(self, document_service, async_db_session, test_user):
        """Test document retrieval when document doesn't exist."""
        with patch.object(document_service, '_get_user_by_id', return_value=test_user):
            with patch('app.db.mongodb.Document.get', return_value=None):
                with pytest.raises(HTTPException) as exc_info:
                    await document_service.get_document(
                        "nonexistent_doc", test_user.id, async_db_session
                    )
                
                assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_document_access_denied(self, document_service, async_db_session, test_user):
        """Test document retrieval when user doesn't own the document."""
        mock_document = Mock()
        mock_document.user_id = "other_user_id"
        
        with patch.object(document_service, '_get_user_by_id', return_value=test_user):
            with patch('app.db.mongodb.Document.get', return_value=mock_document):
                with pytest.raises(HTTPException) as exc_info:
                    await document_service.get_document(
                        "doc_123", test_user.id, async_db_session
                    )
                
                assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    async def test_delete_document_success(self, document_service, async_db_session, mock_vector_store, test_user):
        """Test successful document deletion."""
        mock_document = Mock()
        mock_document.id = "doc_123"
        mock_document.user_id = test_user.id
        mock_document.file_path = "/tmp/test.pdf"
        mock_document.delete = AsyncMock()
        
        with patch.object(document_service, '_get_user_by_id', return_value=test_user):
            with patch('app.db.mongodb.Document.get', return_value=mock_document):
                with patch('app.db.mongodb.Chunk.find') as mock_find:
                    mock_find.return_value.delete_many = AsyncMock()
                    with patch('os.path.exists', return_value=True):
                        with patch('os.remove') as mock_remove:
                            result = await document_service.delete_document(
                                "doc_123", test_user.id, async_db_session, mock_vector_store
                            )
                            
                            assert result["message"] == "Document deleted successfully"
                            mock_vector_store.delete_document_vectors.assert_called_once_with("doc_123")
                            mock_remove.assert_called_once()

    async def test_validate_file_success(self, document_service):
        """Test successful file validation."""
        mock_file = Mock()
        mock_file.filename = "test.pdf"
        mock_file.size = 1024 * 1024  # 1MB
        mock_file.content_type = "application/pdf"
        
        # Should not raise exception
        document_service._validate_file(mock_file)

    async def test_validate_file_no_filename(self, document_service):
        """Test file validation with no filename."""
        mock_file = Mock()
        mock_file.filename = None
        
        with pytest.raises(HTTPException) as exc_info:
            document_service._validate_file(mock_file)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "No file provided" in exc_info.value.detail

    async def test_validate_file_unsupported_type(self, document_service):
        """Test file validation with unsupported file type."""
        mock_file = Mock()
        mock_file.filename = "test.exe"
        mock_file.size = 1024
        
        with pytest.raises(HTTPException) as exc_info:
            document_service._validate_file(mock_file)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unsupported file type" in exc_info.value.detail

    async def test_validate_file_too_large(self, document_service):
        """Test file validation with file too large."""
        mock_file = Mock()
        mock_file.filename = "test.pdf"
        mock_file.size = 100 * 1024 * 1024  # 100MB
        
        with pytest.raises(HTTPException) as exc_info:
            document_service._validate_file(mock_file)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "File too large" in exc_info.value.detail

    async def test_process_document_async_success(self, document_service, mock_vector_store):
        """Test successful document processing."""
        mock_document = Mock()
        mock_document.id = "doc_123"
        mock_document.file_path = "/tmp/test.pdf"
        mock_document.status = DocumentStatus.PROCESSING
        mock_document.save = AsyncMock()
        
        mock_chunks = [
            {"content": "Chunk 1", "metadata": {"page": 1}},
            {"content": "Chunk 2", "metadata": {"page": 2}}
        ]
        
        with patch.object(document_service.processor, 'process_document', return_value=mock_chunks):
            with patch('app.db.mongodb.Chunk') as mock_chunk_class:
                mock_chunk = Mock()
                mock_chunk.save = AsyncMock()
                mock_chunk_class.return_value = mock_chunk
                
                await document_service._process_document_async(
                    mock_document, mock_vector_store
                )
                
                # Verify document status was updated
                assert mock_document.status == DocumentStatus.COMPLETED
                mock_document.save.assert_called()

    async def test_process_document_async_failure(self, document_service, mock_vector_store):
        """Test document processing failure."""
        mock_document = Mock()
        mock_document.id = "doc_123"
        mock_document.file_path = "/tmp/test.pdf"
        mock_document.status = DocumentStatus.PROCESSING
        mock_document.save = AsyncMock()
        
        with patch.object(document_service.processor, 'process_document', side_effect=Exception("Processing failed")):
            await document_service._process_document_async(
                mock_document, mock_vector_store
            )
            
            # Verify document status was updated to failed
            assert mock_document.status == DocumentStatus.FAILED
            mock_document.save.assert_called()

    async def test_save_file_success(self, document_service, mock_file_upload):
        """Test successful file saving."""
        with patch('aiofiles.open') as mock_open:
            mock_file_handle = AsyncMock()
            mock_open.return_value.__aenter__.return_value = mock_file_handle
            
            with patch('os.makedirs') as mock_makedirs:
                with patch('os.path.exists', return_value=False):
                    result = await document_service._save_file(mock_file_upload, "test_user_123")
                    
                    assert "/uploads/test_user_123/" in result
                    assert result.endswith("test.pdf")
                    mock_makedirs.assert_called_once()

    async def test_get_user_by_id(self, document_service, async_db_session, test_user):
        """Test internal method to get user by ID."""
        with patch.object(async_db_session, 'get', return_value=test_user):
            result = await document_service._get_user_by_id(async_db_session, test_user.id)
            
            assert result == test_user
            async_db_session.get.assert_called_once_with(User, test_user.id)

    async def test_get_document_type_pdf(self, document_service):
        """Test document type detection for PDF."""
        result = document_service._get_document_type("test.pdf")
        assert result == DocumentType.PDF

    async def test_get_document_type_txt(self, document_service):
        """Test document type detection for TXT."""
        result = document_service._get_document_type("test.txt")
        assert result == DocumentType.TXT

    async def test_get_document_type_md(self, document_service):
        """Test document type detection for Markdown."""
        result = document_service._get_document_type("test.md")
        assert result == DocumentType.MD

    async def test_get_document_type_unknown(self, document_service):
        """Test document type detection for unknown extension."""
        with pytest.raises(HTTPException) as exc_info:
            document_service._get_document_type("test.exe")
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unsupported file type" in exc_info.value.detail 