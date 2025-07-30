import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from ..db.milvus_vector_store import MilvusVectorStore
from ..db.mongodb import Chunk, Document
from ..utils.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)


class VectorRebuildService:
    
    def __init__(self):
        self.processor = DocumentProcessor()
    
    async def rebuild_from_mongodb(
        self, 
        user_filter: Optional[str] = None,
        document_filter: Optional[str] = None,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Rebuild Milvus vector store from MongoDB backup data.
        
        Args:
            user_filter: Optional user ID to rebuild only specific user's data
            document_filter: Optional document ID to rebuild only specific document
            batch_size: Number of chunks to process in each batch
            
        Returns:
            Dict with rebuild statistics and results
        """
        rebuild_stats = {
            "started_at": datetime.now(timezone.utc),
            "status": "in_progress",
            "total_chunks": 0,
            "processed_chunks": 0,
            "total_documents": 0,
            "processed_documents": 0,
            "total_users": 0,
            "errors": [],
            "completed_at": None
        }
        
        try:
            logger.info("Starting vector store rebuild from MongoDB...")
            
            # Initialize new Milvus vector store
            vector_store = MilvusVectorStore()
            await vector_store.initialize()
            
            # Clear existing collection (rebuild from scratch)
            logger.info("Clearing existing vector store...")
            await self._clear_milvus_collection(vector_store)
            await vector_store.initialize()  # Recreate collection
            
            # Get chunks from MongoDB
            logger.info("Fetching chunks from MongoDB backup...")
            
            # Build query filters
            query_filter = {}
            if user_filter:
                # Filter by user via document relationship
                user_docs = await Document.find({"user_id": user_filter}).to_list()
                doc_ids = [str(doc.id) for doc in user_docs]
                query_filter["document_id"] = {"$in": doc_ids}
            elif document_filter:
                query_filter["document_id"] = document_filter
            
            # Count total chunks
            total_chunks = await Chunk.count_documents(query_filter)
            rebuild_stats["total_chunks"] = total_chunks
            
            if total_chunks == 0:
                rebuild_stats["status"] = "completed"
                rebuild_stats["completed_at"] = datetime.now(timezone.utc)
                logger.info("No chunks found to rebuild.")
                return rebuild_stats
            
            # Process chunks in batches
            logger.info(f"Processing {total_chunks} chunks in batches of {batch_size}...")
            
            processed = 0
            current_doc_id = None
            doc_chunks_batch = []
            
            # Stream chunks and group by document
            async for chunk in Chunk.find(query_filter).sort("document_id", 1):
                try:
                    # If we're starting a new document, process the previous batch
                    if current_doc_id and chunk.document_id != current_doc_id:
                        if doc_chunks_batch:
                            await self._process_document_batch(
                                vector_store, 
                                current_doc_id, 
                                doc_chunks_batch, 
                                rebuild_stats
                            )
                            doc_chunks_batch = []
                            rebuild_stats["processed_documents"] += 1
                    
                    current_doc_id = chunk.document_id
                    doc_chunks_batch.append(chunk)
                    
                    # Process batch if it reaches batch_size
                    if len(doc_chunks_batch) >= batch_size:
                        await self._process_document_batch(
                            vector_store, 
                            current_doc_id, 
                            doc_chunks_batch[:batch_size], 
                            rebuild_stats
                        )
                        doc_chunks_batch = doc_chunks_batch[batch_size:]
                        processed += batch_size
                        
                        # Log progress
                        if processed % 1000 == 0:
                            logger.info(f"Processed {processed}/{total_chunks} chunks...")
                
                except Exception as e:
                    error_msg = f"Error processing chunk {chunk.id}: {str(e)}"
                    rebuild_stats["errors"].append(error_msg)
                    logger.error(error_msg)
            
            # Process remaining chunks
            if doc_chunks_batch:
                await self._process_document_batch(
                    vector_store, 
                    current_doc_id, 
                    doc_chunks_batch, 
                    rebuild_stats
                )
                rebuild_stats["processed_documents"] += 1
            
            # Final statistics
            logger.info("Finalizing vector store rebuild...")
            
            # Get final stats
            final_stats = await vector_store.get_collection_stats()
            rebuild_stats.update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc),
                "final_entities": final_stats.get("total_entities", 0),
                "final_users": final_stats.get("unique_users", 0),
                "final_documents": final_stats.get("unique_documents", 0)
            })
            
            logger.info(f"Rebuild completed! Processed {rebuild_stats['processed_chunks']} chunks from {rebuild_stats['processed_documents']} documents.")
                
        except Exception as e:
            error_msg = f"Rebuild failed: {str(e)}"
            rebuild_stats["errors"].append(error_msg)
            rebuild_stats["status"] = "failed"
            rebuild_stats["completed_at"] = datetime.now(timezone.utc)
            logger.error(error_msg)
        
        return rebuild_stats
    
    async def _clear_milvus_collection(self, vector_store: MilvusVectorStore):
        """Clear the existing Milvus collection."""
        try:
            from pymilvus import utility, connections
            
            # Check if collection exists and drop it
            if utility.has_collection(vector_store.collection_name):
                collection = vector_store.collection
                collection.release()
                utility.drop_collection(vector_store.collection_name)
                logger.info(f"Dropped existing collection: {vector_store.collection_name}")
                
        except Exception as e:
            logger.warning(f"Could not clear collection: {str(e)}")
    
    async def _process_document_batch(
        self, 
        vector_store: MilvusVectorStore, 
        document_id: str, 
        chunks: list, 
        rebuild_stats: Dict[str, Any]
    ):
        """Process a batch of chunks for a document."""
        try:
            # Get document metadata
            document = await Document.get(document_id)
            if not document:
                rebuild_stats["errors"].append(f"Document {document_id} not found")
                return
            
            # Prepare chunk data for vector store
            chunk_texts = []
            chunk_metadata = []
            
            for chunk in chunks:
                chunk_texts.append(chunk.content)
                
                # Prepare metadata
                metadata = {
                    "chunk_index": chunk.chunk_index,
                    "mongo_chunk_id": str(chunk.id),
                    "file_type": document.file_type,
                    "char_count": len(chunk.content),
                    "word_count": len(chunk.content.split()),
                }
                
                # Add chunk metadata if available
                if chunk.chunk_metadata:
                    metadata.update(chunk.chunk_metadata)
                
                chunk_metadata.append(metadata)
            
            # Add chunks to vector store
            await vector_store.add_document_chunks(
                user_id=document.user_id,
                doc_id=str(document.id),
                source=document.filename,
                chunks=chunk_texts,
                chunk_metadata=chunk_metadata
            )
            
            rebuild_stats["processed_chunks"] += len(chunks)
            
        except Exception as e:
            error_msg = f"Failed to process document {document_id}: {str(e)}"
            rebuild_stats["errors"].append(error_msg)
            logger.error(error_msg)
    
    async def get_mongodb_backup_stats(self) -> Dict[str, Any]:
        """Get statistics about available backup data in MongoDB."""
        try:
            total_documents = await Document.count_documents({})
            total_chunks = await Chunk.count_documents({})
            
            # Get user distribution
            user_pipeline = [
                {"$group": {"_id": "$user_id", "document_count": {"$sum": 1}}},
                {"$sort": {"document_count": -1}}
            ]
            user_distribution = await Document.aggregate(user_pipeline).to_list()
            
            # Get document types
            type_pipeline = [
                {"$group": {"_id": "$file_type", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            type_distribution = await Document.aggregate(type_pipeline).to_list()
            
            # Get status distribution
            status_pipeline = [
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ]
            status_distribution = await Document.aggregate(status_pipeline).to_list()
            
            return {
                "total_documents": total_documents,
                "total_chunks": total_chunks,
                "average_chunks_per_document": round(total_chunks / max(total_documents, 1), 2),
                "user_distribution": user_distribution[:10],  # Top 10 users
                "file_type_distribution": type_distribution,
                "status_distribution": status_distribution,
                "total_users": len(user_distribution)
            }
            
        except Exception as e:
            logger.error(f"Failed to get MongoDB backup stats: {str(e)}")
            return {"error": str(e)} 