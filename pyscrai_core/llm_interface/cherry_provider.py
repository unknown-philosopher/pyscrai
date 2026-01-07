"""Cherry API provider implementation.

Cherry is a local API proxy that routes requests to various LLM providers.
It uses OpenRouter-compatible API format but runs locally.

Model format: "<provider>:<model>" (e.g., "openrouter:xiaomi/mimo-v2-flash:free")
where <provider> is the upstream provider (openrouter, anthropic, openai, etc.)
and <model> is the model identifier for that provider.
"""

import asyncio
import json
import os
import time
from collections.abc import AsyncGenerator

import httpx
from dotenv import load_dotenv

from .base import AuthenticationError, LLMError, LLMProvider, RateLimitError
from .models import ModelInfo

# Load environment variables from .env file
load_dotenv()


class CherryProvider(LLMProvider):
    """Cherry API provider implementation.
    
    Cherry is a local API proxy that provides a unified interface to multiple
    LLM providers. It runs locally and uses an OpenRouter-compatible API format.
    """

    DEFAULT_BASE_URL = "http://127.0.0.1:23333/v1"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 60.0,
        app_name: str = "PyScrAI",
        default_model: str | None = None,
        cherry_provider: str | None = None,
    ):
        # Use provided api_key or load from environment variable
        if api_key is None:
            api_key = os.getenv("CHERRY_API_KEY")
            if not api_key:
                raise ValueError(
                    "CHERRY_API_KEY not provided and not found in environment variables"
                )
        
        # Use provided default_model or load from environment variable
        # Cherry model format is "<provider>:<model>"
        if default_model is None:
            cherry_provider = cherry_provider or os.getenv("CHERRY_PROVIDER", "openrouter")
            cherry_model = os.getenv("CHERRY_MODEL")
            if cherry_model:
                default_model = f"{cherry_provider}:{cherry_model}"
        self.default_model = default_model
        
        super().__init__(api_key, base_url, timeout, app_name)
        self._client: httpx.AsyncClient | None = None
        self._models_cache: list[ModelInfo] | None = None
        self._models_cache_time: float = 0
        self._cache_ttl: float = 300.0  # 5 minutes

    @property
    def provider_name(self) -> str:
        return "cherry"

    @property
    def headers(self) -> dict[str, str]:
        """Get default headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": self.app_name,
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None or self._client.is_closed:
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
                    keepalive_expiry=120.0
                ),
            )
        return self._client

    def _handle_error(self, response: httpx.Response) -> None:
        """Handle API error responses."""
        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", str(error_data))
        except (json.JSONDecodeError, KeyError):
            error_message = response.text or f"HTTP {response.status_code}"

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

    async def _post_stream(self, endpoint: str, data: dict) -> AsyncGenerator[str, None]:
        """Make a streaming POST request."""
        client = await self._get_client()

        try:
            async with client.stream("POST", endpoint, json=data) as response:
                if response.status_code >= 400:
                    await response.aread()
                    self._handle_error(response)

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        if data_str.strip() == "[DONE]":
                            break
                        yield data_str

        except (ConnectionResetError, asyncio.CancelledError):
            # Handle connection reset errors gracefully
            return

    # LLMClient implementation
    async def complete(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float = 1.0,
    ) -> dict:
        """Create a chat completion.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier (e.g., "openrouter:xiaomi/mimo-v2-flash:free")
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            
        Returns:
            API response dict with completion
        """
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
        }

        if max_tokens:
            data["max_tokens"] = max_tokens

        return await self._post("/chat/completions", data)

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

    async def complete_simple(
        self,
        prompt: str,
        model: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """Simple completion with just a prompt string.
        
        Args:
            prompt: User prompt
            model: Model identifier
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text content
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.complete(messages, model, temperature, max_tokens)
        
        if "choices" in response and len(response["choices"]) > 0:
            return response["choices"][0]["message"]["content"]
        return ""

    # ModelRegistry implementation
    async def list_models(self, force_refresh: bool = False) -> list[ModelInfo]:
        """List available models.
        
        Note: Cherry may not provide a models endpoint, so this returns a basic
        list based on configured providers. Override with actual endpoint if available.
        """
        current_time = time.time()

        # Return cached models if still valid
        if (
            not force_refresh
            and self._models_cache is not None
            and (current_time - self._models_cache_time) < self._cache_ttl
        ):
            return self._models_cache

        # Try to fetch models from API, or use defaults
        try:
            response = await self._get("/models")
            models_data = response.get("data", [])
            self._models_cache = [ModelInfo.from_api_response(m) for m in models_data]
        except Exception:
            # If API doesn't support models endpoint, return basic info
            cherry_provider = os.getenv("CHERRY_PROVIDER", "openrouter")
            default_model = os.getenv("CHERRY_MODEL", "xiaomi/mimo-v2-flash:free")
            
            self._models_cache = [
                ModelInfo(
                    id=f"{cherry_provider}:{default_model}",
                    name=f"Cherry ({cherry_provider})",
                    provider="cherry",
                    context_length=4096,
                    pricing={"prompt": "0", "completion": "0"},
                )
            ]
        
        self._models_cache_time = current_time
        return self._models_cache

    async def get_model(self, model_id: str) -> ModelInfo | None:
        """Get a specific model by ID."""
        models = await self.list_models()
        for model in models:
            if model.id == model_id:
                return model
        return None

    async def search_models(self, query: str) -> list[ModelInfo]:
        """Search models by name or description."""
        models = await self.list_models()
        query_lower = query.lower()
        return [
            m for m in models 
            if query_lower in m.name.lower() or query_lower in m.id.lower()
        ]

    async def get_free_models(self) -> list[ModelInfo]:
        """Get all free models."""
        models = await self.list_models()
        return [m for m in models if m.pricing.get("prompt") == "0"]

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
