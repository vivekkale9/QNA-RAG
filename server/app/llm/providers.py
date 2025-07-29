"""
LLM Provider Implementations

Concrete implementations for different LLM providers with rate limiting and error handling.
"""

import asyncio
import time
import logging
import httpx
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, AsyncGenerator, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Standard response format for all LLM providers."""
    content: str
    provider: str
    model: str
    usage: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RateLimitTracker:
    """Tracks rate limiting for individual API keys."""
    requests_made: int = 0
    tokens_used: int = 0
    last_reset: datetime = field(default_factory=datetime.now)
    is_exhausted: bool = False
    exhausted_until: Optional[datetime] = None


class BaseLLMProvider(ABC):
    """Base class for all LLM providers."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the LLM provider.
        
        Args:
            config: Provider-specific configuration dictionary
        """
        self.config = config
        self.client = httpx.AsyncClient(timeout=60.0)
    
    @abstractmethod
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs: Any
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    async def stream_response(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """Stream a response from the LLM."""
        pass
    
    async def cleanup(self):
        """Clean up resources."""
        if self.client:
            await self.client.aclose()


class GroqProvider(BaseLLMProvider):
    """Groq LLM provider with round-robin API key management and rate limiting."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Groq provider.
        
        Args:
            config: Groq configuration containing api_keys, model, etc.
        """
        super().__init__(config)
        self.api_keys = config.get("api_keys", [])
        self.model = config.get("model", "llama-3.1-8b-instant")
        self.base_url = config.get("base_url", "https://api.groq.com")
        self.max_tokens = config.get("max_tokens", 2048)
        self.rate_limit_rpm = config.get("rate_limit_rpm", 30)
        self.rate_limit_tpm = config.get("rate_limit_tpm", 6000)
        
        # Track rate limits per API key
        self.rate_trackers: Dict[str, RateLimitTracker] = {
            key: RateLimitTracker() for key in self.api_keys
        }
        self.current_key_index = 0
        
        if not self.api_keys:
            raise ValueError("No Groq API keys provided")
    
    def _get_next_available_key(self) -> Optional[str]:
        """
        Get the next available API key using round-robin with rate limiting.
        
        Returns:
            Optional[str]: Available API key or None if all exhausted
        """
        now = datetime.now()
        
        # First, check if any exhausted keys can be reset
        for key, tracker in self.rate_trackers.items():
            if tracker.is_exhausted and tracker.exhausted_until and now > tracker.exhausted_until:
                tracker.is_exhausted = False
                tracker.exhausted_until = None
                logger.info(f"API key reset: {key[:10]}...")
        
        # Find next available key starting from current index
        for i in range(len(self.api_keys)):
            key_index = (self.current_key_index + i) % len(self.api_keys)
            key = self.api_keys[key_index]
            tracker = self.rate_trackers[key]
            
            # Check if key is not exhausted and within rate limits
            if not tracker.is_exhausted:
                # Reset counters if enough time has passed
                if now - tracker.last_reset > timedelta(minutes=1):
                    tracker.requests_made = 0
                    tracker.tokens_used = 0
                    tracker.last_reset = now
                
                # Check rate limits
                if (tracker.requests_made < self.rate_limit_rpm and 
                    tracker.tokens_used < self.rate_limit_tpm):
                    
                    self.current_key_index = (key_index + 1) % len(self.api_keys)
                    return key
        
        logger.warning("All API keys are exhausted")
        return None
    
    def _record_usage(self, api_key: str, tokens_used: int = 0):
        """
        Record usage for an API key.
        
        Args:
            api_key: The API key that was used
            tokens_used: Number of tokens consumed
        """
        if api_key in self.rate_trackers:
            tracker = self.rate_trackers[api_key]
            tracker.requests_made += 1
            tracker.tokens_used += tokens_used
    
    def _mark_key_exhausted(self, api_key: str, retry_after: int = 60):
        """
        Mark an API key as exhausted.
        
        Args:
            api_key: The API key to mark as exhausted
            retry_after: Seconds to wait before retrying
        """
        if api_key in self.rate_trackers:
            tracker = self.rate_trackers[api_key]
            tracker.is_exhausted = True
            tracker.exhausted_until = datetime.now() + timedelta(seconds=retry_after)
            logger.warning(f"API key exhausted until {tracker.exhausted_until}: {api_key[:10]}...")
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs: Any
    ) -> LLMResponse:
        """
        Generate a response using Groq API with round-robin key management.
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse: Generated response
        """
        api_key = self._get_next_available_key()
        if not api_key:
            raise Exception("No available Groq API keys")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", 0.7),
            "stream": False
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/openai/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 429:
                # Rate limit hit, mark key as exhausted
                retry_after = int(response.headers.get("retry-after", 60))
                self._mark_key_exhausted(api_key, retry_after)
                raise Exception(f"Rate limit exceeded for API key {api_key[:10]}...")
            
            response.raise_for_status()
            result = response.json()
            
            # Record successful usage
            usage = result.get("usage", {})
            tokens_used = usage.get("total_tokens", 0)
            self._record_usage(api_key, tokens_used)
            
            content = result["choices"][0]["message"]["content"]
            
            return LLMResponse(
                content=content,
                provider="groq",
                model=self.model,
                usage=usage,
                metadata={
                    "api_key_used": api_key[:10] + "...",
                    "response_id": result.get("id"),
                }
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Groq API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Groq API request failed: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Groq provider error: {e}")
            raise
    
    async def stream_response(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response using Groq API.
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters
            
        Yields:
            str: Response chunks
        """
        api_key = self._get_next_available_key()
        if not api_key:
            raise Exception("No available Groq API keys")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", 0.7),
            "stream": True
        }
        
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/openai/v1/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("retry-after", 60))
                    self._mark_key_exhausted(api_key, retry_after)
                    raise Exception(f"Rate limit exceeded for API key {api_key[:10]}...")
                
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        
                        if data == "[DONE]":
                            break
                        
                        try:
                            import json
                            chunk = json.loads(data)
                            
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                
                                if content:
                                    yield content
                                    
                        except json.JSONDecodeError:
                            continue
                
                # Record usage (approximate for streaming)
                self._record_usage(api_key, 100)  # Rough estimate
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Groq streaming error: {e.response.status_code}")
            raise Exception(f"Groq streaming failed: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Groq streaming error: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics for the Groq provider.
        
        Returns:
            Dict[str, Any]: Provider statistics
        """
        available_keys = sum(1 for tracker in self.rate_trackers.values() if not tracker.is_exhausted)
        total_requests = sum(tracker.requests_made for tracker in self.rate_trackers.values())
        total_tokens = sum(tracker.tokens_used for tracker in self.rate_trackers.values())
        
        return {
            "provider": "groq",
            "model": self.model,
            "total_api_keys": len(self.api_keys),
            "available_keys": available_keys,
            "exhausted_keys": len(self.api_keys) - available_keys,
            "total_requests": total_requests,
            "total_tokens_used": total_tokens,
            "rate_limit_rpm": self.rate_limit_rpm,
            "rate_limit_tpm": self.rate_limit_tpm,
        } 