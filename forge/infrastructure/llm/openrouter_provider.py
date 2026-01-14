"""
OpenRouter LLM provider implementation for Forge 3.0.

Provides access to multiple LLM models through the OpenRouter API.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from collections.abc import AsyncGenerator

import httpx
from dotenv import load_dotenv

from forge.infrastructure.llm.base import (
    AuthenticationError,
    LLMError,
    LLMProvider,
    RateLimitError,
)
from forge.infrastructure.llm.models import ModelInfo

load_dotenv()


class OpenRouterProvider(LLMProvider):
    """OpenRouter API provider implementation.
    
    Provides access to multiple LLM models through the OpenRouter API.
    Supports both streaming and non-streaming completions.
    """
    
    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
    
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 60.0,
        app_name: str = "Forge",
        default_model: str | None = None,
    ):
        # Load from environment if not provided
        if api_key is None:
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENROUTER_API_KEY not provided and not found in environment"
                )
        
        if default_model is None:
            # Support both OPENROUTER_MODEL and OPENROUTER_DEFAULT_MODEL for compatibility
            default_model = os.getenv("OPENROUTER_MODEL") or os.getenv("OPENROUTER_DEFAULT_MODEL")
        
        super().__init__(api_key, base_url, timeout, app_name)
        self.default_model = default_model
        
        # Log the default model being set
        import logging
        logger = logging.getLogger(__name__)
        if self.default_model:
            logger.info(f"OpenRouterProvider initialized with default_model: '{self.default_model}'")
        else:
            logger.warning("OpenRouterProvider initialized without default_model - will use first available model")
        self._client: httpx.AsyncClient | None = None
        self._models_cache: list[ModelInfo] | None = None
        self._models_cache_time: float = 0
        self._cache_ttl: float = 300.0  # 5 minutes
    
    @property
    def provider_name(self) -> str:
        return "openrouter"
    
    @property
    def headers(self) -> dict[str, str]:
        """Get default headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/pyscrai",
            "X-Title": self.app_name,
            "Content-Type": "application/json",
        }
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None or self._client.is_closed:
            try:
                self._client = httpx.AsyncClient(
                    base_url=self.base_url,
                    headers=self.headers,
                    timeout=httpx.Timeout(
                        connect=self.timeout,
                        read=self.timeout,
                        write=self.timeout,
                        pool=self.timeout,
                    ),
                    limits=httpx.Limits(
                        max_connections=100,
                        max_keepalive_connections=20,
                        keepalive_expiry=120.0,
                    ),
                    http2=True,
                )
            except ImportError:
                # Fallback to HTTP/1.1
                self._client = httpx.AsyncClient(
                    base_url=self.base_url,
                    headers=self.headers,
                    timeout=httpx.Timeout(
                        connect=self.timeout,
                        read=self.timeout,
                        write=self.timeout,
                        pool=self.timeout,
                    ),
                    limits=httpx.Limits(
                        max_connections=100,
                        max_keepalive_connections=20,
                        keepalive_expiry=120.0,
                    ),
                )
        return self._client
    
    def _extract_error_message(self, response: httpx.Response) -> str:
        """Extract a meaningful error message from an HTTP response.
        
        Handles JSON errors, HTML error pages (e.g., Cloudflare), and plain text.
        """
        try:
            error_data = response.json()
            return error_data.get("error", {}).get("message", str(error_data))
        except (json.JSONDecodeError, KeyError):
            # Check if response is HTML (e.g., Cloudflare error page)
            text = response.text or ""
            content_type = response.headers.get("content-type", "").lower()
            
            if "text/html" in content_type or text.strip().startswith("<!DOCTYPE") or text.strip().startswith("<html"):
                # Extract meaningful error from HTML
                # Try to find error title or message in common HTML error pages
                title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
                h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.IGNORECASE | re.DOTALL)
                
                if title_match:
                    return title_match.group(1).strip()
                elif h1_match:
                    return h1_match.group(1).strip()
                else:
                    # Fallback: use status code with a generic message
                    return f"HTTP {response.status_code}: Server returned HTML error page"
            else:
                # Not HTML, use text but truncate if too long
                error_message = text[:500] if len(text) > 500 else text
                if not error_message:
                    error_message = f"HTTP {response.status_code}"
                return error_message
    
    def _handle_error(self, response: httpx.Response) -> None:
        """Handle API error responses."""
        error_message = self._extract_error_message(response)
        
        if response.status_code == 401:
            raise AuthenticationError(
                f"Authentication failed: {error_message}",
                status_code=response.status_code,
            )
        elif response.status_code == 429:
            raise RateLimitError(
                f"Rate limit exceeded: {error_message}",
                status_code=response.status_code,
            )
        else:
            raise LLMError(
                f"API error: {error_message}",
                status_code=response.status_code,
            )
    
    async def _get(self, endpoint: str, params: dict | None = None) -> dict:
        """Make a GET request."""
        client = await self._get_client()
        response = await client.get(endpoint, params=params)
        
        if response.status_code >= 400:
            self._handle_error(response)
        
        return response.json()
    
    async def _post(self, endpoint: str, data: dict) -> dict:
        """Make a POST request."""
        client = await self._get_client()
        response = await client.post(endpoint, json=data)
        
        if response.status_code >= 400:
            self._handle_error(response)
        
        return response.json()
    
    async def _post_stream(
        self, endpoint: str, data: dict
    ) -> AsyncGenerator[str, None]:
        """Make a streaming POST request."""
        client = await self._get_client()
        
        try:
            async with client.stream("POST", endpoint, json=data) as response:
                if response.status_code >= 400:
                    # Read the error response body before handling
                    await response.aread()
                    
                    # Use the same error extraction logic as non-streaming requests
                    error_message = self._extract_error_message(response)
                    
                    # Raise appropriate exception
                    if response.status_code == 401:
                        raise AuthenticationError(
                            f"Authentication failed: {error_message}",
                            status_code=response.status_code,
                        )
                    elif response.status_code == 429:
                        raise RateLimitError(
                            f"Rate limit exceeded: {error_message}",
                            status_code=response.status_code,
                        )
                    else:
                        raise LLMError(
                            f"API error: {error_message}",
                            status_code=response.status_code,
                        )
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        yield data_str
        except (ConnectionResetError, asyncio.CancelledError):
            return
    
    # ========== Chat Completion ==========
    
    async def complete(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float = 1.0,
    ) -> dict:
        """Create a chat completion."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Log the request payload BEFORE sending
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
        }
        if max_tokens:
            data["max_tokens"] = max_tokens
        
        logger.info(f"OpenRouterProvider.complete: Requesting model '{model}'")
        logger.debug(f"OpenRouterProvider.complete: Request payload: {data}")
        
        response = await self._post("/chat/completions", data)
        
        # Log the response model (may differ from requested if OpenRouter substitutes)
        response_model = response.get('model', 'N/A')
        logger.info(f"OpenRouterProvider.complete: Requested model '{model}', Response model '{response_model}'")
        if model != response_model:
            logger.warning(
                f"OpenRouterProvider.complete: Model mismatch! "
                f"Requested '{model}' but received '{response_model}'"
            )
        logger.debug(f"OpenRouterProvider.complete: Full LLM response: {response}")
        return response
    
    async def stream_complete(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float = 1.0,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion, yielding content chunks."""
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "stream": True,
        }
        
        if max_tokens:
            data["max_tokens"] = max_tokens
        
        async for chunk_str in self._post_stream("/chat/completions", data):
            try:
                chunk = json.loads(chunk_str)
                if "choices" in chunk and len(chunk["choices"]) > 0:
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
            except json.JSONDecodeError:
                continue
    
    # ========== Model Registry ==========
    
    async def list_models(self, force_refresh: bool = False) -> list[ModelInfo]:
        """List available models with caching."""
        current_time = time.time()
        
        if (
            not force_refresh
            and self._models_cache is not None
            and (current_time - self._models_cache_time) < self._cache_ttl
        ):
            return self._models_cache
        
        response = await self._get("/models")
        models_data = response.get("data", [])
        
        self._models_cache = [ModelInfo.from_api_response(m) for m in models_data]
        self._models_cache_time = current_time
        
        return self._models_cache
    
    async def get_model(self, model_id: str) -> ModelInfo | None:
        """Get a specific model by ID."""
        models = await self.list_models()
        for model in models:
            if model.id == model_id:
                return model
        return None
    
    # ========== Lifecycle ==========
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
