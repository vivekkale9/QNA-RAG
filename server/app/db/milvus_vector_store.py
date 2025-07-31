import logging
import asyncio
from typing import List, Dict, Any, Optional
import numpy as np
from pymilvus import (
    connections, Collection, CollectionSchema, FieldSchema, DataType,
    utility
)
from transformers import AutoTokenizer, AutoModel
import torch

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class OptimizedEmbeddingModel:
    """
    Memory-optimized embedding model using transformers directly.
    Uses less memory than sentence-transformers library.
    """
    
    def __init__(self, model_name="sentence-transformers/paraphrase-MiniLM-L3-v2"):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.device = "cpu"  # Force CPU to save memory
        
    def _load_model(self):
        """Lazy load model only when needed"""
        if self.tokenizer is None:
            logger.info(f"🔄 Loading tokenizer: {self.model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
        if self.model is None:
            logger.info(f"🔄 Loading model: {self.model_name}")
            self.model = AutoModel.from_pretrained(
                self.model_name,
                torch_dtype=torch.float32,  # Use float32 for better compatibility
                device_map=None  # Force CPU
            )
            self.model.to(self.device)
            self.model.eval()  # Set to evaluation mode
            
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts"""
        self._load_model()
        
        # Tokenize inputs
        inputs = self.tokenizer(
            texts, 
            return_tensors='pt', 
            padding=True, 
            truncation=True, 
            max_length=512
        )
        
        # Move to device
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Generate embeddings
        with torch.no_grad():
            outputs = self.model(**inputs)
            # Use mean pooling instead of CLS token for better sentence representation
            embeddings = self._mean_pooling(outputs.last_hidden_state, inputs['attention_mask'])
            # Normalize embeddings
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            
        return embeddings.cpu().numpy()
    
    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text"""
        return self.embed_texts([text])[0]
    
    def _mean_pooling(self, hidden_states, attention_mask):
        """Apply mean pooling to get sentence embeddings"""
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(hidden_states.size()).float()
        return torch.sum(hidden_states * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    
    def get_sentence_embedding_dimension(self) -> int:
        """Get the embedding dimension"""
        self._load_model()
        return self.model.config.hidden_size


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
            # Configure connection parameters for Zilliz Cloud serverless
            if settings.milvus_token:
                # Zilliz Cloud serverless connection
                # Check if milvus_host already includes protocol scheme
                host = settings.milvus_host
                if not host.startswith(('http://', 'https://')):
                    host = f"https://{host}"
                
                connection_params = {
                    "alias": "default",
                    "uri": host,
                    "token": settings.milvus_token
                }
                logger.info(f"Connecting to Zilliz Cloud serverless at {host}")
            else:
                # Local Milvus connection
                connection_params = {
                    "alias": "default",
                    "host": settings.milvus_host,
                    "port": settings.milvus_port
                }
                logger.info(f"Connecting to local Milvus at {settings.milvus_host}:{settings.milvus_port}")
            
            connections.connect(**connection_params)
            logger.info("✅ Successfully connected to Milvus")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Milvus: {str(e)}")
            raise
            
    async def _load_embedding_model(self) -> None:
        try:
            # Use optimized embedding model
            self.embedding_model = OptimizedEmbeddingModel(self.model_name)
            
            # Load model in executor to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None, self.embedding_model._load_model
            )
            
            # Verify embedding dimension
            actual_dim = self.embedding_model.get_sentence_embedding_dimension()
            if actual_dim != self.embedding_dimension:
                logger.warning(f"Embedding dimension mismatch: expected {self.embedding_dimension}, got {actual_dim}")
                self.embedding_dimension = actual_dim
                
            logger.info(f"✅ Loaded optimized embedding model: {self.model_name} (dim: {self.embedding_dimension})")
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {str(e)}")
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
            # Generate embedding using optimized model
            embedding = await asyncio.get_event_loop().run_in_executor(
                None, self.embedding_model.embed_text, text
            )
            
            # Already normalized in the optimized model
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
            # Generate embeddings using optimized model
            embeddings = await asyncio.get_event_loop().run_in_executor(
                None, self.embedding_model.embed_texts, texts
            )
            
            # Already normalized in the optimized model
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
                # Create chunk_id and ensure it doesn't exceed VARCHAR limit (100 chars)
                chunk_id = f"{doc_id}_{i}"
                if len(chunk_id) > 100:
                    # Truncate doc_id if necessary to fit the limit
                    max_doc_id_len = 100 - len(f"_{i}") - 1
                    truncated_doc_id = doc_id[:max_doc_id_len] if len(doc_id) > max_doc_id_len else doc_id
                    chunk_id = f"{truncated_doc_id}_{i}"
                    
                chunk_ids.append(chunk_id)
                
                # Ensure text doesn't exceed VARCHAR limit (65535 chars)
                if len(chunk_text) > 65535:
                    truncated_text = chunk_text[:65532] + "..."
                    logger.warning(f"Truncated chunk text from {len(chunk_text)} to 65535 chars")
                    texts.append(truncated_text)
                else:
                    texts.append(chunk_text)
                user_ids.append(str(user_id))  # Ensure string type
                doc_ids.append(str(doc_id))    # Ensure string type
                sources.append(str(source))    # Ensure string type
                chunk_indices.append(int(i))   # Ensure INT64 type
                
                # Prepare metadata - ensure JSON serializable
                base_metadata = chunk_metadata[i] if chunk_metadata and i < len(chunk_metadata) else {}
                
                # Create clean metadata dict with only JSON-compatible values
                clean_metadata = {}
                if isinstance(base_metadata, dict):
                    for key, value in base_metadata.items():
                        if isinstance(value, (str, int, float, bool, list, dict)) and value is not None:
                            clean_metadata[key] = value
                
                # Add additional metadata
                clean_metadata.update({
                    "word_count": len(chunk_text.split()),
                    "char_count": len(chunk_text)
                })
                
                metadatas.append(clean_metadata)
                embedding_list.append(embedding.tolist())
                
            # Insert data into Milvus
            try:
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
                
                # Log data types for debugging
                logger.debug(f"Data types for insertion:")
                logger.debug(f"  chunk_ids: {type(chunk_ids[0]) if chunk_ids else 'empty'} (count: {len(chunk_ids)})")
                logger.debug(f"  embeddings: {type(embedding_list[0]) if embedding_list else 'empty'} (count: {len(embedding_list)})")
                logger.debug(f"  texts: {type(texts[0]) if texts else 'empty'} (count: {len(texts)})")
                logger.debug(f"  user_ids: {type(user_ids[0]) if user_ids else 'empty'} (count: {len(user_ids)})")
                logger.debug(f"  doc_ids: {type(doc_ids[0]) if doc_ids else 'empty'} (count: {len(doc_ids)})")
                logger.debug(f"  sources: {type(sources[0]) if sources else 'empty'} (count: {len(sources)})")
                logger.debug(f"  chunk_indices: {type(chunk_indices[0]) if chunk_indices else 'empty'} (count: {len(chunk_indices)})")
                logger.debug(f"  metadatas: {type(metadatas[0]) if metadatas else 'empty'} (count: {len(metadatas)})")
                
                # Validate all arrays have same length
                lengths = [len(chunk_ids), len(embedding_list), len(texts), len(user_ids), len(doc_ids), len(sources), len(chunk_indices), len(metadatas)]
                if len(set(lengths)) > 1:
                    raise ValueError(f"Array length mismatch: {lengths}")
                
                logger.info(f"Inserting {len(chunk_ids)} chunks into Milvus...")
                self.collection.insert(data)
                self.collection.flush()  # Ensure data is persisted
                logger.info("Successfully inserted and flushed data to Milvus")
                
            except Exception as insert_error:
                logger.error(f"Milvus insertion failed: {str(insert_error)}", exc_info=True)
                logger.error(f"Sample data for debugging:")
                if chunk_ids:
                    logger.error(f"  First chunk_id: {chunk_ids[0]} ({type(chunk_ids[0])})")
                if user_ids:
                    logger.error(f"  First user_id: {user_ids[0]} ({type(user_ids[0])})")
                if doc_ids:
                    logger.error(f"  First doc_id: {doc_ids[0]} ({type(doc_ids[0])})")
                if metadatas:
                    logger.error(f"  First metadata: {metadatas[0]} ({type(metadatas[0])})")
                raise
            
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
            # Use collection properties instead of deprecated get_stats()
            return {
                "collection_name": self.collection_name,
                "total_entities": self.collection.num_entities,
                "embedding_dimension": self.embedding_dimension,
                "model_name": self.model_name,
                "index_type": settings.milvus_index_type,
                "metric_type": settings.milvus_metric_type,
                "unique_users": 0,  # Placeholder - will be calculated elsewhere
                "unique_documents": 0,  # Placeholder - will be calculated elsewhere
                "is_empty": self.collection.is_empty,
                "primary_field_name": self.collection.primary_field.name if self.collection.primary_field else None
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {str(e)}")
            return {}
            

    
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
                "average_chunks_per_document": round(stats.get("total_entities", 0) / max(len(doc_stats), 1), 2) if len(doc_stats) > 0 else 0,
                "unique_users": len(user_stats),
                "unique_documents": len(doc_stats)
            }
            
        except Exception as e:
            logger.error(f"Failed to get detailed statistics: {str(e)}")
            return {"error": str(e)} 