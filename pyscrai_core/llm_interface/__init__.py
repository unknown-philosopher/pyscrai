"""LLM Provider abstraction layer for PyScrAI."""

from .base import (
    AuthenticationError,
    LLMClient,
    LLMError,
    LLMProvider,
    ModelRegistry,
    RateLimitError,
)
from .models import (
    ChatMessage,
    Conversation,
    Generation,
    MessageRole,
    ModelInfo,
    ModelPricing,
)
from .openrouter_provider import OpenRouterProvider
from .provider_factory import ProviderType, create_provider, get_provider_type_from_model_id

__all__ = [
    # Base protocols and errors
    "LLMProvider",
    "LLMClient",
    "ModelRegistry",
    "LLMError",
    "AuthenticationError",
    "RateLimitError",
    # Models
    "MessageRole",
    "ChatMessage",
    "Conversation",
    "ModelPricing",
    "ModelInfo",
    "Generation",
    # Providers
    "OpenRouterProvider",
    # Factory
    "create_provider",
    "ProviderType",
    "get_provider_type_from_model_id",
]
