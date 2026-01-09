"""
Base classes and protocols for LLM providers in Forge 3.0.

Defines the abstract LLMProvider class and error types.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Protocol, runtime_checkable

from forge.systems.llm.models import ModelInfo


# ============================================================================
# Exceptions
# ============================================================================


class LLMError(Exception):
    """Base exception for LLM provider errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: dict | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class AuthenticationError(LLMError):
    """Authentication failed."""
    pass


class RateLimitError(LLMError):
    """Rate limit exceeded."""
    pass


class ModelNotFoundError(LLMError):
    """Requested model not found."""
    pass


# ============================================================================
# Protocols
# ============================================================================


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for LLM chat completion clients."""
    
    async def complete(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float = 1.0,
    ) -> dict:
        """Create a chat completion."""
        ...
    
    async def stream_complete(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float = 1.0,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion, yielding content chunks."""
        ...


@runtime_checkable
class ModelRegistry(Protocol):
    """Protocol for model listing and management."""
    
    async def list_models(self, force_refresh: bool = False) -> list[ModelInfo]:
        """List available models."""
        ...
    
    async def get_model(self, model_id: str) -> ModelInfo | None:
        """Get a specific model by ID."""
        ...


# ============================================================================
# Abstract Provider
# ============================================================================


class LLMProvider(ABC):
    """Abstract base class for LLM providers.
    
    Combines LLMClient and ModelRegistry functionality.
    Providers must implement the abstract methods for their specific API.
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: float = 60.0,
        app_name: str = "Forge",
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.app_name = app_name
        self.default_model: str | None = None
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'openrouter', 'openai')."""
        ...
    
    # ========== Chat Completion ==========
    
    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float = 1.0,
    ) -> dict:
        """Create a chat completion."""
        ...
    
    @abstractmethod
    async def stream_complete(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float = 1.0,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion, yielding content chunks."""
        ...
    
    async def complete_simple(
        self,
        prompt: str,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """Simple completion with just a prompt string.
        
        Args:
            prompt: User prompt
            model: Model identifier (uses default if not provided)
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text content
        """
        if model is None:
            model = self.default_model
            if model is None:
                raise ValueError("No model specified and no default model set")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await self.complete(messages, model, temperature, max_tokens)
        
        if "choices" in response and len(response["choices"]) > 0:
            return response["choices"][0]["message"]["content"]
        return ""
    
    # ========== Model Registry ==========
    
    @abstractmethod
    async def list_models(self, force_refresh: bool = False) -> list[ModelInfo]:
        """List available models."""
        ...
    
    @abstractmethod
    async def get_model(self, model_id: str) -> ModelInfo | None:
        """Get a specific model by ID."""
        ...
    
    async def search_models(self, query: str) -> list[ModelInfo]:
        """Search models by name or description."""
        models = await self.list_models()
        query_lower = query.lower()
        return [
            m for m in models
            if query_lower in m.name.lower() or query_lower in m.description.lower()
        ]
    
    async def get_free_models(self) -> list[ModelInfo]:
        """Get all free models."""
        models = await self.list_models()
        return [m for m in models if m.is_free]
    
    # ========== Lifecycle ==========
    
    @abstractmethod
    async def close(self) -> None:
        """Close the provider and release resources."""
        ...
    
    async def __aenter__(self) -> "LLMProvider":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
