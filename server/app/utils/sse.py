import json
import asyncio
from typing import Dict, Any, AsyncGenerator
from enum import Enum


class ProcessingStatus(str, Enum):
    STARTED = "started"
    VALIDATING = "validating"
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    STORING = "storing"
    COMPLETED = "completed"
    FAILED = "failed"


class RebuildStatus(str, Enum):
    STARTED = "started"
    INITIALIZING = "initializing"
    COUNTING = "counting"
    PROCESSING = "processing"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"


class SSEMessage:
    
    def __init__(self, event: str = None, data: Any = None, id: str = None, retry: int = None):
        self.event = event
        self.data = data
        self.id = id
        self.retry = retry
    
    def format(self) -> str:
        lines = []
        
        if self.id:
            lines.append(f"id: {self.id}")
        
        if self.event:
            lines.append(f"event: {self.event}")
        
        if self.retry:
            lines.append(f"retry: {self.retry}")
        
        if self.data is not None:
            if isinstance(self.data, (dict, list)):
                data_str = json.dumps(self.data)
            else:
                data_str = str(self.data)
            lines.append(f"data: {data_str}")
        
        return "\n".join(lines) + "\n\n"


class DocumentProcessingEventEmitter:
    
    def __init__(self):
        self.callbacks = []
        self.current_status = None
        self.progress = 0
        self.total_steps = 6  # validating, extracting, chunking, embedding, storing, completed
    
    def add_callback(self, callback):
        self.callbacks.append(callback)
    
    async def emit_status(self, status: ProcessingStatus, message: str = None, data: Dict[str, Any] = None):
        self.current_status = status
        
        # Calculate progress based on status
        status_progress = {
            ProcessingStatus.STARTED: 0,
            ProcessingStatus.VALIDATING: 10,
            ProcessingStatus.EXTRACTING: 25,
            ProcessingStatus.CHUNKING: 45,
            ProcessingStatus.EMBEDDING: 65,
            ProcessingStatus.STORING: 85,
            ProcessingStatus.COMPLETED: 100,
            ProcessingStatus.FAILED: self.progress  # Keep current progress on failure
        }
        
        self.progress = status_progress.get(status, self.progress)
        
        event_data = {
            "status": status.value,
            "progress": self.progress,
            "message": message or self._get_default_message(status),
            "timestamp": asyncio.get_event_loop().time(),
            **(data or {})
        }
        
        # Emit to all callbacks
        for callback in self.callbacks:
            try:
                await callback(event_data)
            except Exception as e:
                # Log error but don't stop processing
                pass
    
    def _get_default_message(self, status: ProcessingStatus) -> str:
        messages = {
            ProcessingStatus.STARTED: "Starting document processing...",
            ProcessingStatus.VALIDATING: "Validating file format and size...",
            ProcessingStatus.EXTRACTING: "Extracting text from document...",
            ProcessingStatus.CHUNKING: "Creating intelligent text chunks...",
            ProcessingStatus.EMBEDDING: "Generating embeddings...",
            ProcessingStatus.STORING: "Storing in vector database...",
            ProcessingStatus.COMPLETED: "Document processed successfully!",
            ProcessingStatus.FAILED: "Document processing failed."
        }
        return messages.get(status, "Processing...")


class VectorRebuildEventEmitter:
    """Event emitter for vector store rebuild progress."""
    
    def __init__(self):
        self.callbacks = []
        self.current_status = None
        self.progress = 0
        self.total_chunks = 0
        self.processed_chunks = 0
        self.total_documents = 0
        self.processed_documents = 0
    
    def add_callback(self, callback):
        self.callbacks.append(callback)
    
    async def emit_status(self, status: RebuildStatus, message: str = None, data: Dict[str, Any] = None):
        self.current_status = status
        
        # Calculate progress based on status and processed items
        if self.total_chunks > 0:
            chunk_progress = (self.processed_chunks / self.total_chunks) * 80  # 80% for processing
        else:
            chunk_progress = 0
            
        status_progress = {
            RebuildStatus.STARTED: 0,
            RebuildStatus.INITIALIZING: 5,
            RebuildStatus.COUNTING: 10,
            RebuildStatus.PROCESSING: 10 + chunk_progress,
            RebuildStatus.FINALIZING: 95,
            RebuildStatus.COMPLETED: 100,
            RebuildStatus.FAILED: self.progress
        }
        
        self.progress = min(100, status_progress.get(status, self.progress))
        
        event_data = {
            "status": status.value,
            "progress": round(self.progress, 1),
            "message": message or self._get_default_message(status),
            "timestamp": asyncio.get_event_loop().time(),
            "total_chunks": self.total_chunks,
            "processed_chunks": self.processed_chunks,
            "total_documents": self.total_documents,
            "processed_documents": self.processed_documents,
            **(data or {})
        }
        
        # Emit to all callbacks
        for callback in self.callbacks:
            try:
                await callback(event_data)
            except Exception as e:
                # Log error but don't stop processing
                pass
    
    def _get_default_message(self, status: RebuildStatus) -> str:
        messages = {
            RebuildStatus.STARTED: "Starting vector store rebuild...",
            RebuildStatus.INITIALIZING: "Initializing vector store...",
            RebuildStatus.COUNTING: "Counting documents and chunks...",
            RebuildStatus.PROCESSING: f"Processing chunks ({self.processed_chunks}/{self.total_chunks})...",
            RebuildStatus.FINALIZING: "Finalizing rebuild...",
            RebuildStatus.COMPLETED: "Rebuild completed successfully!",
            RebuildStatus.FAILED: "Rebuild failed."
        }
        return messages.get(status, "Processing...")

    def update_totals(self, total_chunks: int, total_documents: int):
        """Update total counts for progress calculation."""
        self.total_chunks = total_chunks
        self.total_documents = total_documents

    def update_progress(self, processed_chunks: int, processed_documents: int):
        """Update processed counts for progress calculation."""
        self.processed_chunks = processed_chunks
        self.processed_documents = processed_documents


async def create_sse_generator(
    emitter: DocumentProcessingEventEmitter,
    timeout: int = 300  # 5 minutes timeout
) -> AsyncGenerator[str, None]:
    """
    Create an SSE generator that yields formatted SSE messages.
    
    Args:
        emitter: Event emitter instance
        timeout: Maximum time to wait for completion (seconds)
        
    Yields:
        Formatted SSE message strings
    """
    start_time = asyncio.get_event_loop().time()
    events_queue = asyncio.Queue()
    
    # Add callback to emitter to put events in queue
    async def queue_callback(event_data):
        await events_queue.put(event_data)
    
    emitter.add_callback(queue_callback)
    
    try:
        while True:
            try:
                # Wait for next event with timeout
                remaining_time = timeout - (asyncio.get_event_loop().time() - start_time)
                if remaining_time <= 0:
                    # Send timeout message
                    timeout_msg = SSEMessage(
                        event="error",
                        data={"error": "Processing timeout", "status": "failed"}
                    )
                    yield timeout_msg.format()
                    break
                
                event_data = await asyncio.wait_for(events_queue.get(), timeout=remaining_time)
                
                # Format as SSE message
                sse_msg = SSEMessage(
                    event="processing_update",
                    data=event_data,
                    id=str(int(event_data["timestamp"]))
                )
                
                yield sse_msg.format()
                
                # Break if completed or failed
                if event_data["status"] in ["completed", "failed"]:
                    break
                    
            except asyncio.TimeoutError:
                # Send timeout message and break
                timeout_msg = SSEMessage(
                    event="error",
                    data={"error": "Processing timeout", "status": "failed"}
                )
                yield timeout_msg.format()
                break
                
    except Exception as e:
        # Send error message
        error_msg = SSEMessage(
            event="error",
            data={"error": str(e), "status": "failed"}
        )
        yield error_msg.format()


async def create_rebuild_sse_generator(
    emitter: VectorRebuildEventEmitter,
    timeout: int = 600  # 10 minutes timeout for rebuild
) -> AsyncGenerator[str, None]:
    """
    Create an SSE generator for vector rebuild progress.
    
    Args:
        emitter: Vector rebuild event emitter instance
        timeout: Maximum time to wait for completion (seconds)
        
    Yields:
        Formatted SSE message strings
    """
    start_time = asyncio.get_event_loop().time()
    events_queue = asyncio.Queue()
    
    # Add callback to emitter to put events in queue
    async def queue_callback(event_data):
        await events_queue.put(event_data)
    
    emitter.add_callback(queue_callback)
    
    try:
        while True:
            try:
                # Wait for next event with timeout
                remaining_time = timeout - (asyncio.get_event_loop().time() - start_time)
                if remaining_time <= 0:
                    # Send timeout message
                    timeout_msg = SSEMessage(
                        event="error",
                        data={"error": "Rebuild timeout", "status": "failed"}
                    )
                    yield timeout_msg.format()
                    break
                
                event_data = await asyncio.wait_for(events_queue.get(), timeout=remaining_time)
                
                # Format as SSE message
                sse_msg = SSEMessage(
                    event="rebuild_update",
                    data=event_data,
                    id=str(int(event_data["timestamp"]))
                )
                
                yield sse_msg.format()
                
                # Break if completed or failed
                if event_data["status"] in ["completed", "failed"]:
                    break
                    
            except asyncio.TimeoutError:
                # Send timeout message and break
                timeout_msg = SSEMessage(
                    event="error",
                    data={"error": "Rebuild timeout", "status": "failed"}
                )
                yield timeout_msg.format()
                break
                
    except Exception as e:
        # Send error message
        error_msg = SSEMessage(
            event="error",
            data={"error": str(e), "status": "failed"}
        )
        yield error_msg.format()


def create_heartbeat_generator(interval: int = 30) -> AsyncGenerator[str, None]:
    """
    Create a heartbeat generator for keeping SSE connection alive.
    
    Args:
        interval: Heartbeat interval in seconds
        
    Yields:
        Heartbeat SSE messages
    """
    async def heartbeat():
        while True:
            await asyncio.sleep(interval)
            heartbeat_msg = SSEMessage(
                event="heartbeat",
                data={"timestamp": asyncio.get_event_loop().time()}
            )
            yield heartbeat_msg.format()
    
    return heartbeat()


# Utility function to create SSE response headers
def get_sse_headers() -> Dict[str, str]:
    return {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",  # Configure based on your CORS policy
        "Access-Control-Allow-Headers": "Cache-Control"
    } 