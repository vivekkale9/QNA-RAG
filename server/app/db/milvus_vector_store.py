import logging
import asyncio
from typing import List, Dict, Any, Optional
import numpy as np
from pymilvus import (
    connections, Collection, CollectionSchema, FieldSchema, DataType,
    utility
)
from sentence_transformers import SentenceTransformer

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MilvusVectorStore:

    def __init__(self):
        self.embedding_model = None
        self.collection = None
        self.collection_name = settings.milvus_collection_name
        self.embedding_dimension = settings.embedding_dimension
        self.model_name = settings.embedding_model
        self._initialized = False
        
    async def initialize(self) -> None:
        """
        Initialize Milvus connection, collection, and embedding model.
        
        Creates collection with proper schema if it doesn't exist.
        Loads embedding model and sets up indexes.
        """
        if self._initialized:
            return
            
        try:
            # Connect to Milvus
            await self._connect_to_milvus()
            
            # Load embedding model
            await self._load_embedding_model()
            
            # Create or load collection
            await self._setup_collection()
            
            # Load collection into memory
            self.collection.load()
            
            self._initialized = True
            logger.info(f"Milvus vector store initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Milvus vector store: {str(e)}")
            raise
            
    async def _connect_to_milvus(self) -> None:
        try:
            connections.connect(
                alias="default",
                host=settings.milvus_host,
                port=settings.milvus_port
            )
            logger.info(f"Connected to Milvus at {settings.milvus_host}:{settings.milvus_port}")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {str(e)}")
            raise
            
    async def _load_embedding_model(self) -> None:
        try:
            self.embedding_model = await asyncio.get_event_loop().run_in_executor(
                None, SentenceTransformer, self.model_name
            )
            # Verify embedding dimension
            actual_dim = self.embedding_model.get_sentence_embedding_dimension()
            if actual_dim != self.embedding_dimension:
                logger.warning(f"Embedding dimension mismatch: expected {self.embedding_dimension}, got {actual_dim}")
                self.embedding_dimension = actual_dim
                
            logger.info(f"Loaded embedding model: {self.model_name} (dim: {self.embedding_dimension})")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {str(e)}")
            raise
            
    async def _setup_collection(self) -> None:
        try:
            # Check if collection exists
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                logger.info(f"Loaded existing collection: {self.collection_name}")
            else:
                # Create new collection with schema
                await self._create_collection()
                
        except Exception as e:
            logger.error(f"Failed to setup collection: {str(e)}")
            raise
            
    async def _create_collection(self) -> None:
        try:
            # Define collection schema
            fields = [
                FieldSchema(
                    name="chunk_id", 
                    dtype=DataType.VARCHAR, 
                    is_primary=True, 
                    max_length=100
                ),
                FieldSchema(
                    name="embedding", 
                    dtype=DataType.FLOAT_VECTOR, 
                    dim=self.embedding_dimension
                ),
                FieldSchema(
                    name="text", 
                    dtype=DataType.VARCHAR, 
                    max_length=65535  # Support large text chunks
                ),
                FieldSchema(
                    name="user_id", 
                    dtype=DataType.VARCHAR, 
                    max_length=100
                ),
                FieldSchema(
                    name="doc_id", 
                    dtype=DataType.VARCHAR, 
                    max_length=100
                ),
                FieldSchema(
                    name="source", 
                    dtype=DataType.VARCHAR, 
                    max_length=500
                ),
                FieldSchema(
                    name="chunk_index", 
                    dtype=DataType.INT64
                ),
                FieldSchema(
                    name="metadata", 
                    dtype=DataType.JSON
                )
            ]
            
            schema = CollectionSchema(
                fields=fields, 
                description="Insurance document chunks with embeddings",
                enable_dynamic_field=True
            )
            
            # Create collection
            self.collection = Collection(
                name=self.collection_name,
                schema=schema,
                using='default'
            )
            
            # Create indexes for better performance
            await self._create_indexes()
            
            logger.info(f"Created new collection: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to create collection: {str(e)}")
            raise
            
    async def _create_indexes(self) -> None:
        try:
            # Vector index for similarity search
            vector_index_params = {
                "metric_type": settings.milvus_metric_type,
                "index_type": settings.milvus_index_type,
                "params": {"nlist": settings.milvus_nlist}
            }
            
            self.collection.create_index(
                field_name="embedding",
                index_params=vector_index_params
            )
            
            # Scalar indexes for filtering
            self.collection.create_index(field_name="user_id")
            self.collection.create_index(field_name="doc_id")
            
            logger.info("Created indexes successfully")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {str(e)}")
            raise
            
    async def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text (str): Text to embed
            
        Returns:
            np.ndarray: Normalized embedding vector
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            # Generate embedding
            embedding = await asyncio.get_event_loop().run_in_executor(
                None, self.embedding_model.encode, text
            )
            
            # Normalize for cosine similarity
            embedding = embedding / np.linalg.norm(embedding)
            return embedding.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise
            
    async def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts (List[str]): List of texts to embed
            
        Returns:
            np.ndarray: Array of normalized embedding vectors
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            # Generate embeddings in batches
            embeddings = await asyncio.get_event_loop().run_in_executor(
                None, self.embedding_model.encode, texts
            )
            
            # Normalize for cosine similarity
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / norms
            return embeddings.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            raise
            
    async def add_document_chunks(
        self,
        user_id: str,
        doc_id: str,
        source: str,
        chunks: List[str],
        chunk_metadata: List[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Add document chunks to Milvus with embeddings.
        
        Args:
            user_id (str): User ID for isolation
            doc_id (str): Document ID
            source (str): Original filename
            chunks (List[str]): List of text chunks
            chunk_metadata (List[Dict[str, Any]]): Optional metadata for each chunk
            
        Returns:
            List[str]: List of generated chunk IDs
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            if not chunks:
                return []
                
            # Generate embeddings for all chunks
            embeddings = await self.embed_texts(chunks)
            
            # Prepare data for insertion
            chunk_ids = []
            texts = []
            user_ids = []
            doc_ids = []
            sources = []
            chunk_indices = []
            metadatas = []
            embedding_list = []
            
            for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = f"{doc_id}_{i}"
                chunk_ids.append(chunk_id)
                texts.append(chunk_text)
                user_ids.append(user_id)
                doc_ids.append(doc_id)
                sources.append(source)
                chunk_indices.append(i)
                
                # Prepare metadata
                metadata = chunk_metadata[i] if chunk_metadata and i < len(chunk_metadata) else {}
                metadata.update({
                    "word_count": len(chunk_text.split()),
                    "char_count": len(chunk_text)
                })
                metadatas.append(metadata)
                embedding_list.append(embedding.tolist())
                
            # Insert data into Milvus
            data = [
                chunk_ids,      # chunk_id (primary key)
                embedding_list, # embedding (vector)
                texts,          # text
                user_ids,       # user_id
                doc_ids,        # doc_id
                sources,        # source
                chunk_indices,  # chunk_index
                metadatas       # metadata
            ]
            
            self.collection.insert(data)
            self.collection.flush()  # Ensure data is persisted
            
            logger.info(f"Inserted {len(chunks)} chunks for document {doc_id}")
            return chunk_ids
            
        except Exception as e:
            logger.error(f"Failed to add document chunks: {str(e)}")
            raise
            
    async def search_similar_chunks(
        self,
        query: str,
        user_id: str,
        k: int = 5,
        doc_ids: Optional[List[str]] = None,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks with user isolation.
        
        Args:
            query (str): Query text
            user_id (str): User ID for filtering
            k (int): Number of results to return
            doc_ids (Optional[List[str]]): Filter by specific document IDs
            similarity_threshold (float): Minimum similarity threshold
            
        Returns:
            List[Dict[str, Any]]: List of matching chunks with metadata and scores
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            # Generate query embedding
            query_embedding = await self.embed_text(query)
            
            # Build search expression for user isolation
            expr = f'user_id == "{user_id}"'
            if doc_ids:
                doc_id_filter = " or ".join([f'doc_id == "{doc_id}"' for doc_id in doc_ids])
                expr += f" and ({doc_id_filter})"
            
            # Debug logging for search parameters
            logger.info(f"Milvus search - Query: '{query[:50]}...', User: {user_id}, Expression: {expr}")
                
            # Search parameters
            search_params = {
                "metric_type": settings.milvus_metric_type,
                "params": {"nprobe": min(settings.milvus_nlist, 32)}
            }
            
            # Perform search
            results = self.collection.search(
                data=[query_embedding.tolist()],
                anns_field="embedding",
                param=search_params,
                limit=k * 2,  # Get more results to filter by threshold
                expr=expr,
                output_fields=["text", "user_id", "doc_id", "source", "chunk_index", "metadata"]
            )
            
            # Debug logging for search results
            logger.info(f"Milvus search returned {len(results[0]) if results and len(results) > 0 else 0} raw results")
            
            # Process results
            chunks = []
            if results and len(results) > 0:
                for hit in results[0]:
                    # Check similarity threshold
                    logger.debug(f"Hit score: {hit.score}, threshold: {similarity_threshold}")
                    if hit.score < similarity_threshold:
                        continue
                    
                    chunk_data = {
                        "chunk_id": hit.id,
                        "text": hit.entity.get("text"),
                        "user_id": hit.entity.get("user_id"),
                        "doc_id": hit.entity.get("doc_id"),
                        "source": hit.entity.get("source"),
                        "chunk_index": hit.entity.get("chunk_index"),
                        "metadata": hit.entity.get("metadata", {}),
                        "similarity_score": float(hit.score)
                    }
                    chunks.append(chunk_data)
                    
                    # Stop when we have enough results
                    if len(chunks) >= k:
                        break
                    
            logger.info(f"Found {len(chunks)} similar chunks for user {user_id}")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to search similar chunks: {str(e)}")
            raise
            
    async def delete_document_chunks(self, user_id: str, doc_id: str) -> bool:
        """
        Delete all chunks for a specific document.
        
        Args:
            user_id (str): User ID for verification
            doc_id (str): Document ID to delete
            
        Returns:
            bool: True if deletion was successful
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            # Delete chunks with user and document filtering
            expr = f'user_id == "{user_id}" and doc_id == "{doc_id}"'
            self.collection.delete(expr)
            self.collection.flush()
            
            logger.info(f"Deleted chunks for document {doc_id} (user: {user_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document chunks: {str(e)}")
            return False
            
    async def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics.
        
        Returns:
            Dict[str, Any]: Collection statistics
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            stats = self.collection.get_stats()
            return {
                "collection_name": self.collection_name,
                "total_entities": self.collection.num_entities,
                "embedding_dimension": self.embedding_dimension,
                "model_name": self.model_name,
                "index_type": settings.milvus_index_type,
                "metric_type": settings.milvus_metric_type,
                "raw_stats": stats
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {str(e)}")
            return {}
            
    async def health_check(self) -> Dict[str, Any]:
        """
        Comprehensive health check for Milvus vector store.
        
        Returns:
            Dict containing detailed health information
        """
        health_info = {
            "status": "unknown",
            "milvus_connection": False,
            "collection_exists": False,
            "collection_loaded": False,
            "total_entities": 0,
            "unique_users": 0,
            "unique_documents": 0,
            "index_status": "unknown",
            "disk_usage": "unknown",
            "last_insert": "unknown",
            "errors": []
        }
        
        try:
            # Check Milvus connection
            try:
                connections.get_connection(alias="default")
                health_info["milvus_connection"] = True
            except Exception as e:
                health_info["errors"].append(f"Connection error: {str(e)}")
                health_info["status"] = "critical"
                return health_info
            
            # Check collection existence
            try:
                health_info["collection_exists"] = utility.has_collection(self.collection_name)
                if not health_info["collection_exists"]:
                    health_info["errors"].append("Collection does not exist")
                    health_info["status"] = "critical"
                    return health_info
            except Exception as e:
                health_info["errors"].append(f"Collection check error: {str(e)}")
                health_info["status"] = "critical"
                return health_info
            
            # Get collection and check if loaded
            try:
                collection = Collection(self.collection_name)
                health_info["collection_loaded"] = collection.is_loaded
                
                if not health_info["collection_loaded"]:
                    health_info["errors"].append("Collection not loaded in memory")
                    health_info["status"] = "degraded"
            except Exception as e:
                health_info["errors"].append(f"Collection load check error: {str(e)}")
                health_info["status"] = "degraded"
            
            # Get entity statistics
            try:
                stats = await self.get_collection_stats()
                health_info.update(stats)
            except Exception as e:
                health_info["errors"].append(f"Stats error: {str(e)}")
            
            # Check index status
            try:
                collection = Collection(self.collection_name)
                indexes = collection.indexes
                if indexes:
                    index_info = collection.index()
                    health_info["index_status"] = "built"
                    health_info["index_type"] = index_info.params.get("index_type", "unknown")
                else:
                    health_info["index_status"] = "missing"
                    health_info["errors"].append("No indexes found")
            except Exception as e:
                health_info["errors"].append(f"Index check error: {str(e)}")
                health_info["index_status"] = "error"
            
            # Overall status determination
            if not health_info["errors"]:
                health_info["status"] = "healthy"
            elif health_info["status"] == "unknown":
                health_info["status"] = "degraded"
                
        except Exception as e:
            health_info["errors"].append(f"Health check error: {str(e)}")
            health_info["status"] = "critical"
        
        return health_info
    
    async def get_detailed_statistics(self) -> Dict[str, Any]:
        """
        Get detailed statistics about the vector store data.
        
        Returns:
            Dict containing comprehensive statistics
        """
        try:
            if not self.collection:
                await self.initialize()
            
            # Basic stats
            stats = await self.get_collection_stats()
            
            # Query for user distribution
            user_stats = {}
            doc_stats = {}
            
            try:
                # Get sample of data to analyze distribution
                search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
                
                # Create a dummy query vector for sampling
                dummy_vector = [0.0] * self.embedding_dimension
                results = self.collection.search(
                    data=[dummy_vector],
                    anns_field="embedding",
                    param=search_params,
                    limit=1000,  # Sample size
                    output_fields=["user_id", "doc_id", "chunk_index"]
                )
                
                if results and len(results) > 0:
                    for hit in results[0]:
                        user_id = hit.entity.get("user_id")
                        doc_id = hit.entity.get("doc_id")
                        
                        if user_id:
                            user_stats[user_id] = user_stats.get(user_id, 0) + 1
                        if doc_id:
                            doc_stats[doc_id] = doc_stats.get(doc_id, 0) + 1
                            
            except Exception as e:
                logger.warning(f"Could not get distribution stats: {str(e)}")
            
            return {
                **stats,
                "user_distribution": {
                    "sample_users": len(user_stats),
                    "top_users": sorted(user_stats.items(), key=lambda x: x[1], reverse=True)[:10]
                },
                "document_distribution": {
                    "sample_documents": len(doc_stats),
                    "top_documents": sorted(doc_stats.items(), key=lambda x: x[1], reverse=True)[:10]
                },
                "average_chunks_per_document": round(stats["total_entities"] / max(stats["unique_documents"], 1), 2) if stats["unique_documents"] > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get detailed statistics: {str(e)}")
            return {"error": str(e)} 