"""
LLM Interface - Provider abstraction layer.

Supports multiple backends: OpenRouter, Cherry (local proxy), LM Studio.
"""

from forge.systems.llm.base import (
    LLMProvider,
    LLMError,
    AuthenticationError,
    RateLimitError,
)
from forge.systems.llm.models import (
    LLMMessage,
    LLMResponse,
    ModelInfo,
    MessageRole,
    Conversation,
)
from forge.systems.llm.provider_factory import (
    ProviderFactory,
    ProviderType,
    get_provider,
    complete_simple,
)
from forge.systems.llm.openrouter_provider import OpenRouterProvider

__all__ = [
    # Base
    "LLMProvider",
    "LLMError",
    "AuthenticationError",
    "RateLimitError",
    # Models
    "LLMMessage",
    "LLMResponse",
    "ModelInfo",
    "MessageRole",
    "Conversation",
    # Factory
    "ProviderFactory",
    "ProviderType",
    "get_provider",
    "complete_simple",
    # Providers
    "OpenRouterProvider",
]
