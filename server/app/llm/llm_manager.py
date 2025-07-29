"""
LLM Manager

Manages multiple LLM providers with fallback mechanisms and tenant configuration.
"""

import asyncio
import logging
from typing import Dict, List, Optional, AsyncGenerator, Any
from .providers import GroqProvider, LLMResponse, BaseLLMProvider
from ..config import get_tenant_llm_config

logger = logging.getLogger(__name__)


class LLMManager:
    """
    Manages LLM providers with Groq as the primary provider.
    
    Supports tenant-specific configuration and round-robin API key usage.
    """
    
    def __init__(self, tenant_id: Optional[str] = None):
        """
        Initialize LLM manager with tenant-specific configuration.
        
        Args:
            tenant_id: Optional tenant identifier for custom configuration
        """
        self.tenant_id = tenant_id
        self.config = get_tenant_llm_config(tenant_id)
        self.providers: Dict[str, BaseLLMProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize available LLM providers based on configuration."""
        try:
            # Initialize Groq provider (primary and default)
            if "groq" in self.config and self.config["groq"]["api_keys"]:
                self.providers["groq"] = GroqProvider(self.config["groq"])
                logger.info(f"Initialized Groq provider with {len(self.config['groq']['api_keys'])} API keys")
            else:
                logger.warning("No valid Groq API keys found in configuration")
                
        except Exception as e:
            logger.error(f"Error initializing LLM providers: {e}")
    
    def _get_provider_order(self) -> List[str]:
        """
        Get the order of providers to try for requests.
        
        Returns:
            List[str]: Provider names in order of preference
        """
        # Since we only support Groq by default, return it if available
        available_providers = list(self.providers.keys())
        
        # Groq is our primary and only default provider
        if "groq" in available_providers:
            return ["groq"]
        
        logger.warning("No providers available")
        return []
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        **kwargs: Any
    ) -> LLMResponse:
        """
        Generate a response using available LLM providers.
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters for the LLM
            
        Returns:
            LLMResponse: Generated response
            
        Raises:
            Exception: If no providers are available or all fail
        """
        provider_order = self._get_provider_order()
        
        if not provider_order:
            raise Exception("No LLM providers available")
        
        last_error = None
        
        for provider_name in provider_order:
            try:
                provider = self.providers[provider_name]
                logger.info(f"Attempting to generate response using {provider_name}")
                
                response = await provider.generate_response(messages, **kwargs)
                logger.info(f"Successfully generated response using {provider_name}")
                return response
                
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                last_error = e
                continue
        
        # If we get here, all providers failed
        error_msg = f"All LLM providers failed. Last error: {last_error}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """
        Stream a response using available LLM providers.
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters for the LLM
            
        Yields:
            str: Response chunks
            
        Raises:
            Exception: If no providers are available or all fail
        """
        provider_order = self._get_provider_order()
        
        if not provider_order:
            raise Exception("No LLM providers available")
        
        last_error = None
        
        for provider_name in provider_order:
            try:
                provider = self.providers[provider_name]
                logger.info(f"Attempting to stream response using {provider_name}")
                
                async for chunk in provider.stream_response(messages, **kwargs):
                    yield chunk
                
                logger.info(f"Successfully streamed response using {provider_name}")
                return
                
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                last_error = e
                continue
        
        # If we get here, all providers failed
        error_msg = f"All LLM providers failed. Last error: {last_error}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    async def check_provider_health(self) -> Dict[str, bool]:
        """
        Check the health of all configured providers.
        
        Returns:
            Dict[str, bool]: Provider name to health status mapping
        """
        health_status = {}
        
        for provider_name, provider in self.providers.items():
            try:
                # Simple health check by generating a minimal response
                test_messages = [{"role": "user", "content": "Hello"}]
                await provider.generate_response(test_messages, max_tokens=10)
                health_status[provider_name] = True
                logger.info(f"Provider {provider_name} is healthy")
            except Exception as e:
                health_status[provider_name] = False
                logger.warning(f"Provider {provider_name} health check failed: {e}")
        
        return health_status
    
    def get_provider_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all configured providers.
        
        Returns:
            Dict[str, Dict[str, Any]]: Provider statistics
        """
        stats = {}
        
        for provider_name, provider in self.providers.items():
            try:
                if hasattr(provider, 'get_stats'):
                    stats[provider_name] = provider.get_stats()
                else:
                    stats[provider_name] = {"status": "available"}
            except Exception as e:
                logger.warning(f"Error getting stats for {provider_name}: {e}")
                stats[provider_name] = {"status": "error", "error": str(e)}
        
        return stats
    
    async def cleanup(self):
        """Clean up resources used by providers."""
        for provider_name, provider in self.providers.items():
            try:
                if hasattr(provider, 'cleanup'):
                    await provider.cleanup()
                logger.info(f"Cleaned up provider {provider_name}")
            except Exception as e:
                logger.warning(f"Error cleaning up provider {provider_name}: {e}") 