import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from ..db.milvus_vector_store import MilvusVectorStore
from ..db.mongodb import Chunk, Document
from ..utils.document_processor import DocumentProcessor
from ..utils.sse import VectorRebuildEventEmitter, RebuildStatus

logger = logging.getLogger(__name__)


class VectorRebuildService:
    
    def __init__(self):
        self.processor = DocumentProcessor()
    
    async def rebuild_from_mongodb(
        self, 
        user_filter: Optional[str] = None,
        document_filter: Optional[str] = None,
        batch_size: int = 100,
        event_emitter: Optional[VectorRebuildEventEmitter] = None
    ) -> Dict[str, Any]:
        """
        Rebuild Milvus vector store from MongoDB backup data.
        
        Args:
            user_filter: Optional user ID to rebuild only specific user's data
            document_filter: Optional document ID to rebuild only specific document
            batch_size: Number of chunks to process in each batch
            event_emitter: Optional event emitter for progress updates
            
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
            "errors": [],
            "completed_at": None
        }
        
        try:
            logger.info("Starting vector store rebuild from MongoDB...")
            
            # Emit starting status
            if event_emitter:
                await event_emitter.emit_status(RebuildStatus.STARTED)
            
            # Initialize new Milvus vector store
            if event_emitter:
                await event_emitter.emit_status(RebuildStatus.INITIALIZING, "Initializing vector store...")
            
            vector_store = MilvusVectorStore()
            await vector_store.initialize()
            
            # Clear existing collection (rebuild from scratch)
            logger.info("Clearing existing vector store...")
            await self._clear_milvus_collection(vector_store)
            
            # Recreate collection with proper initialization
            vector_store._initialized = False  # Force re-initialization
            await vector_store.initialize()
                        
            # Test basic MongoDB connectivity
            try:
                test_count = await Chunk.count()
            except Exception as conn_error:
                error_msg = f"MongoDB connection test failed: {str(conn_error)}"
                rebuild_stats["errors"].append(error_msg)
                logger.error(error_msg, exc_info=True)
                if event_emitter:
                    await event_emitter.emit_status(RebuildStatus.FAILED, error_msg)
                raise
            
            # Build query filters
            if event_emitter:
                await event_emitter.emit_status(RebuildStatus.COUNTING, "Counting documents and chunks...")
            
            query_filter = {}
            if user_filter:
                # Filter by user via document relationship
                user_docs = await Document.find({"user_id": user_filter}).to_list()
                doc_ids = [str(doc.id) for doc in user_docs]
                query_filter["document_id"] = {"$in": doc_ids}
            elif document_filter:
                query_filter["document_id"] = document_filter
            else:
                logger.info("No filters applied - processing all chunks")
                
            
            # Count total chunks
            if query_filter:
                total_chunks = await Chunk.find(query_filter).count()
            else:
                total_chunks = await Chunk.count()
            rebuild_stats["total_chunks"] = total_chunks
            
            # Update event emitter with totals
            if event_emitter:
                event_emitter.update_totals(total_chunks, 0)  # Will update documents count later
                await event_emitter.emit_status(RebuildStatus.PROCESSING, f"Starting to process {total_chunks} chunks...")
            
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
            
            try:                
                chunk_query = Chunk.find(query_filter)
                try:
                    sorted_query = chunk_query.sort("document_id", 1)
                except Exception as sort_error:
                    logger.warning(f"Sort with integer failed: {sort_error}. Trying alternative...")
                    try:
                        # Try alternative sort format
                        sorted_query = chunk_query.sort([("document_id", 1)])
                    except Exception as sort_error2:
                        logger.warning(f"Sort with list also failed: {sort_error2}. Using unsorted query...")
                        sorted_query = chunk_query
                
                
                async for chunk in sorted_query:
                    try:
                        
                        # If we're starting a new document, process the previous batch
                        if current_doc_id and chunk.document_id != current_doc_id:
                            if doc_chunks_batch:
                                await self._process_document_batch(
                                    vector_store, 
                                    current_doc_id, 
                                    doc_chunks_batch, 
                                    rebuild_stats,
                                    event_emitter
                                )
                                doc_chunks_batch = []
                                rebuild_stats["processed_documents"] += 1
                                
                                # Update progress
                                if event_emitter:
                                    event_emitter.update_progress(rebuild_stats["processed_chunks"], rebuild_stats["processed_documents"])
                                    await event_emitter.emit_status(RebuildStatus.PROCESSING)
                        
                        current_doc_id = chunk.document_id
                        doc_chunks_batch.append(chunk)
                        
                        # Process batch if it reaches batch_size
                        if len(doc_chunks_batch) >= batch_size:
                            await self._process_document_batch(
                                vector_store, 
                                current_doc_id, 
                                doc_chunks_batch[:batch_size], 
                                rebuild_stats,
                                event_emitter
                            )
                            doc_chunks_batch = doc_chunks_batch[batch_size:]
                            processed += batch_size
                            
                            # Update progress
                            if event_emitter:
                                event_emitter.update_progress(rebuild_stats["processed_chunks"], rebuild_stats["processed_documents"])
                                await event_emitter.emit_status(RebuildStatus.PROCESSING)
                            
                            # Log progress
                            if processed % 100 == 0:  # More frequent logging
                                logger.info(f"Processed {processed}/{total_chunks} chunks...")
                    
                    except Exception as e:
                        error_msg = f"Error processing chunk {chunk.id}: {str(e)}"
                        rebuild_stats["errors"].append(error_msg)
                        logger.error(error_msg, exc_info=True)
            
            except Exception as query_error:
                error_msg = f"MongoDB query failed: {str(query_error)}"
                rebuild_stats["errors"].append(error_msg)
                logger.error(error_msg, exc_info=True)
                raise
                
            # Process remaining chunks
            if doc_chunks_batch:
                await self._process_document_batch(
                    vector_store, 
                    current_doc_id, 
                    doc_chunks_batch, 
                    rebuild_stats,
                    event_emitter
                )
                rebuild_stats["processed_documents"] += 1
            
            # Final statistics
            logger.info("Finalizing vector store rebuild...")
            if event_emitter:
                await event_emitter.emit_status(RebuildStatus.FINALIZING, "Getting final statistics...")
            
            # Get final stats
            final_stats = await vector_store.get_collection_stats()
            rebuild_stats.update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc),
                "final_entities": final_stats.get("total_entities", 0),
                "final_users": final_stats.get("unique_users", 0),
                "final_documents": final_stats.get("unique_documents", 0)
            })
            
            # Emit completion
            if event_emitter:
                event_emitter.update_progress(rebuild_stats["processed_chunks"], rebuild_stats["processed_documents"])
                completion_msg = f"Rebuild completed! Processed {rebuild_stats['processed_chunks']} chunks from {rebuild_stats['processed_documents']} documents."
                await event_emitter.emit_status(RebuildStatus.COMPLETED, completion_msg)
            
            logger.info(f"Rebuild completed! Processed {rebuild_stats['processed_chunks']} chunks from {rebuild_stats['processed_documents']} documents.")
                
        except Exception as e:
            error_msg = f"Rebuild failed: {str(e)}"
            rebuild_stats["errors"].append(error_msg)
            rebuild_stats["status"] = "failed"
            rebuild_stats["completed_at"] = datetime.now(timezone.utc)
            logger.error(error_msg)
            
            # Emit failure
            if event_emitter:
                await event_emitter.emit_status(RebuildStatus.FAILED, error_msg)
        
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
        rebuild_stats: Dict[str, Any],
        event_emitter: Optional[VectorRebuildEventEmitter] = None
    ):
        """Process a batch of chunks for a document."""
        try:
            
            # Get document metadata
            try:
                document = await Document.get(document_id)
                if not document:
                    rebuild_stats["errors"].append(f"Document {document_id} not found")
                    return
                logger.info(f"Found document: {document.filename} (user: {document.user_id})")
            except Exception as e:
                error_msg = f"Failed to get document {document_id}: {str(e)}"
                rebuild_stats["errors"].append(error_msg)
                logger.error(error_msg, exc_info=True)
                return
            
            # Prepare chunk data for vector store
            try:
                chunk_texts = []
                chunk_metadata = []
                
                for i, chunk in enumerate(chunks):
                    try:
                        # Validate chunk content
                        if not chunk.content or not isinstance(chunk.content, str):
                            logger.warning(f"Invalid chunk content for chunk {chunk.id}")
                            continue
                            
                        chunk_texts.append(chunk.content)
                        
                        # Prepare metadata - ensure all values are JSON-serializable
                        metadata = {
                            "mongo_chunk_id": str(chunk.id),
                            "file_type": str(document.file_type),
                            "char_count": len(chunk.content),
                            "word_count": len(chunk.content.split()),
                        }
                        
                        # Add chunk metadata if available (filter to ensure JSON compatibility)
                        if chunk.chunk_metadata:
                            for key, value in chunk.chunk_metadata.items():
                                # Only add serializable values to avoid type errors
                                if isinstance(value, (str, int, float, bool, list, dict)) and value is not None:
                                    metadata[key] = value
                        
                        chunk_metadata.append(metadata)
                        logger.debug(f"Prepared chunk {i+1}/{len(chunks)}: {len(chunk.content)} chars")
                        
                    except Exception as chunk_error:
                        logger.error(f"Error preparing chunk {chunk.id}: {str(chunk_error)}", exc_info=True)
                        continue
                
                if not chunk_texts:
                    logger.warning(f"No valid chunks found for document {document.filename}")
                    return
                    
                
            except Exception as e:
                error_msg = f"Failed to prepare chunk data: {str(e)}"
                rebuild_stats["errors"].append(error_msg)
                logger.error(error_msg, exc_info=True)
                return
            
            # Add chunks to vector store
            try:
                
                await vector_store.add_document_chunks(
                    user_id=str(document.user_id),
                    doc_id=str(document.id),
                    source=str(document.filename),
                    chunks=chunk_texts,
                    chunk_metadata=chunk_metadata
                )
                
                rebuild_stats["processed_chunks"] += len(chunk_texts)  # Use chunk_texts length, not chunks
                logger.info(f"Successfully processed {len(chunk_texts)} chunks for document {document.filename}")
                
            except Exception as vector_error:
                error_msg = f"Failed to add chunks to vector store for document {document.filename}: {str(vector_error)}"
                rebuild_stats["errors"].append(error_msg)
                logger.error(error_msg, exc_info=True)
                raise  # Re-raise to get caught by outer exception handler
            
        except Exception as e:
            error_msg = f"Failed to process document {document_id}: {str(e)}"
            rebuild_stats["errors"].append(error_msg)
            logger.error(error_msg, exc_info=True)  # Include full traceback
    
    async def get_mongodb_backup_stats(self) -> Dict[str, Any]:
        """Get statistics about available backup data in MongoDB."""
        try:
            total_documents = await Document.count()
            total_chunks = await Chunk.count()
            
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