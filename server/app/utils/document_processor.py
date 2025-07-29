import re
import logging
from typing import List, Dict, Any, Tuple
from fastapi import UploadFile
import fitz  # PyMuPDF

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentProcessor:
    
    def __init__(self):
        self.chunk_size = settings.chunk_size  # tokens
        self.chunk_overlap = settings.chunk_overlap  # tokens
        
    async def process_document_content(
        self, 
        content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Process document content directly (bytes) and extract text with metadata.
        
        Args:
            content (bytes): Document file content
            filename (str): Original filename for type detection
            
        Returns:
            Dict[str, Any]: Processing result with chunks and metadata
        """
        try:
            # Extract text based on file type
            file_extension = filename.split('.')[-1].lower() if '.' in filename else 'txt'
            
            if file_extension == "pdf":
                full_text, page_texts = await self._extract_from_pdf(content)
                page_texts = [full_text]
            elif file_extension in ["txt", "md"]:
                full_text = await self._extract_from_txt(content)
                page_texts = [full_text]
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
                
            # Clean the text
            full_text = self._clean_text(full_text)
            
            # Create chunks with metadata
            chunks = await self._create_logical_chunks(full_text, file_extension)
            
            return {
                "full_text": full_text,
                "chunks": chunks,
                "file_size": len(content),
                "file_type": file_extension,
                "page_count": len(page_texts) if isinstance(page_texts, list) else 1,
                "word_count": len(full_text.split()),
                "char_count": len(full_text)
            }
            
        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}")
            raise

    async def process_document(
        self, 
        file: UploadFile
    ) -> Dict[str, Any]:
        """
        Process an uploaded document and extract text with metadata.
        
        Args:
            file (UploadFile): Uploaded document file
            
        Returns:
            Dict[str, Any]: Processing result with chunks and metadata
        """
        try:
            # Read file content
            content = await file.read()
            
            # Use the content-based processing method
            return await self.process_document_content(content, file.filename)
            
        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}")
            raise
            
    async def _extract_from_pdf(self, content: bytes) -> Tuple[str, List[str]]:
        """Extract text from PDF using PyMuPDF."""
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            full_text = ""
            page_texts = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                page_texts.append(page_text)
                full_text += page_text + "\n"
                
            doc.close()
            return full_text.strip(), page_texts
            
        except Exception as e:
            logger.error(f"PDF extraction failed: {str(e)}")
            raise
            
    async def _extract_from_txt(self, content: bytes) -> str:
        try:
            # Try different encodings
            encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    return content.decode(encoding)
                except UnicodeDecodeError:
                    continue
                    
            raise ValueError("Could not decode text file with any supported encoding")
            
        except Exception as e:
            logger.error(f"TXT extraction failed: {str(e)}")
            raise
            
    def _clean_text(self, text: str) -> str:
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might interfere
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Normalize quotes and dashes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('–', '-').replace('—', '-')
        
        return text.strip()
        
    async def _create_logical_chunks(
        self, 
        text: str, 
        file_type: str
    ) -> List[Dict[str, Any]]:
        """
        Create logical chunks using sliding window with token-based overlap.
        
        Args:
            text (str): Full document text
            file_type (str): Document file type
            
        Returns:
            List[Dict[str, Any]]: List of chunks with metadata
        """
        if not text.strip():
            return []
            
        # Split into sentences for logical boundaries
        sentences = self._split_into_sentences(text)
        
        chunks = []
        current_chunk = ""
        current_tokens = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_tokens = len(sentence.split())
            
            # If adding this sentence exceeds chunk size and we have content
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append(self._create_chunk_metadata(
                    current_chunk.strip(), 
                    chunk_index, 
                    file_type
                ))
                
                # Start new chunk with overlap
                if self.chunk_overlap > 0:
                    overlap_text = self._get_overlap_text(current_chunk, self.chunk_overlap)
                    current_chunk = overlap_text + " " + sentence
                    current_tokens = len(current_chunk.split())
                else:
                    current_chunk = sentence
                    current_tokens = sentence_tokens
                    
                chunk_index += 1
            else:
                # Add sentence to current chunk
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
                current_tokens = len(current_chunk.split())
                
        # Add the last chunk if it has content
        if current_chunk.strip():
            chunks.append(self._create_chunk_metadata(
                current_chunk.strip(), 
                chunk_index, 
                file_type
            ))
            
        logger.info(f"Created {len(chunks)} logical chunks from {len(text)} characters")
        return chunks
        
    def _split_into_sentences(self, text: str) -> List[str]:
        # More sophisticated sentence splitting
        # Handle common abbreviations and edge cases
        abbreviations = {'Dr.', 'Mr.', 'Mrs.', 'Ms.', 'Prof.', 'Inc.', 'Corp.', 'Ltd.', 'etc.', 'vs.', 'e.g.', 'i.e.'}
        
        # Replace abbreviations temporarily
        temp_replacements = {}
        for i, abbr in enumerate(abbreviations):
            placeholder = f"__ABBR_{i}__"
            temp_replacements[placeholder] = abbr
            text = text.replace(abbr, placeholder)
            
        # Split on sentence endings
        sentences = re.split(r'[.!?]+\s+', text)
        
        # Restore abbreviations
        for placeholder, abbr in temp_replacements.items():
            for i, sentence in enumerate(sentences):
                sentences[i] = sentence.replace(placeholder, abbr)
                
        # Filter out very short sentences
        return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        
    def _get_overlap_text(self, text: str, overlap_tokens: int) -> str:
        """Get the last N tokens from text for overlap."""
        words = text.split()
        if len(words) <= overlap_tokens:
            return text
        return " ".join(words[-overlap_tokens:])
        
    def _create_chunk_metadata(
        self, 
        content: str, 
        chunk_index: int, 
        file_type: str
    ) -> Dict[str, Any]:
        """Create metadata for a text chunk."""
        return {
            "content": content,
            "chunk_index": chunk_index,
            "metadata": {
                "file_type": file_type,
                "word_count": len(content.split()),
                "char_count": len(content),
                "token_count": len(content.split()),  # Approximate token count
                "chunk_method": "sliding_window_logical"
            }
        }


# Legacy compatibility functions
async def extract_text_from_pdf(file_path: str) -> Tuple[str, List[str]]:
    processor = DocumentProcessor()
    with open(file_path, 'rb') as f:
        content = f.read()
    return await processor._extract_from_pdf(content)


async def extract_text_from_txt(file_path: str) -> str:
    processor = DocumentProcessor()
    with open(file_path, 'rb') as f:
        content = f.read()
    return await processor._extract_from_txt(content)


def clean_text(text: str) -> str:
    processor = DocumentProcessor()
    return processor._clean_text(text)


def chunk_text(text: str, chunk_size: int = 300, chunk_overlap: int = 50) -> List[str]:
    """
    Legacy function for text chunking.
    
    Args:
        text (str): Text to chunk
        chunk_size (int): Maximum chunk size in tokens
        chunk_overlap (int): Overlap between chunks in tokens
        
    Returns:
        List[str]: List of text chunks
    """
    processor = DocumentProcessor()
    processor.chunk_size = chunk_size
    processor.chunk_overlap = chunk_overlap
    
    sentences = processor._split_into_sentences(text)
    
    chunks = []
    current_chunk = ""
    current_tokens = 0
    
    for sentence in sentences:
        sentence_tokens = len(sentence.split())
        
        if current_tokens + sentence_tokens > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            
            # Start new chunk with overlap
            if chunk_overlap > 0:
                overlap_text = processor._get_overlap_text(current_chunk, chunk_overlap)
                current_chunk = overlap_text + " " + sentence
                current_tokens = len(current_chunk.split())
            else:
                current_chunk = sentence
                current_tokens = sentence_tokens
        else:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence
            current_tokens = len(current_chunk.split())
            
    # Add the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
        
    return chunks 