"""Factory for creating LLM providers.

This module also centralizes environment-driven provider selection. The
`DEFAULT_PROVIDER` (or the common misspelling `DEAFULT_PROVIDE`) env var
determines which provider configuration to use. Only the env vars for the
selected provider are read so we don't accidentally mix configs.
"""

import os
from enum import Enum

from dotenv import load_dotenv

from .base import LLMProvider
from .openrouter_provider import OpenRouterProvider

# Load .env early so helpers work in CLI contexts
load_dotenv()


class ProviderType(str, Enum):
    """Supported LLM provider types."""

    OPENROUTER = "openrouter"
    LM_PROXY = "lm_proxy"
    LM_STUDIO = "lm_studio"
    # Future: OPENAI = "openai"
    # Future: ANTHROPIC = "anthropic"


# Mapping of provider -> env variable names
PROVIDER_ENV_MAP: dict[str, dict[str, str]] = {
    ProviderType.OPENROUTER.value: {
        "api_key": "OPENROUTER_API_KEY",
        "base_url": "OPENROUTER_BASE_URL",
        "model": "OPENROUTER_DEFAULT_MODEL",
    },
    ProviderType.LM_PROXY.value: {
        "api_key": "LM_PROXY_API_KEY",
        "base_url": "LM_PROXY_BASE_URL",
        "model": "LM_PROXY_MODEL",
    },
    ProviderType.LM_STUDIO.value: {
        "api_key": "LM_STUDIO_API_KEY",
        "base_url": "LM_STUDIO_BASE_URL",
        "model": "LM_STUDIO_MODEL",
    },
}


def _normalize_provider_name(name: str | None) -> str:
    """Normalize provider name with sensible defaults and typo fallback."""

    if not name:
        return ProviderType.OPENROUTER.value
    name = name.strip().lower().replace("-", "_")
    if name == "deafult_provide":
        # Direct typo mitigation
        return ProviderType.OPENROUTER.value
    return name


def get_default_provider_name() -> str:
    """Return the default provider name from env, with typo fallback."""

    env_name = os.getenv("DEFAULT_PROVIDER") or os.getenv("DEAFULT_PROVIDE")
    return _normalize_provider_name(env_name)


def get_default_model_from_env() -> str | None:
    """Return the default model for the selected provider (if any)."""

    provider_name = get_default_provider_name()
    env_map = PROVIDER_ENV_MAP.get(provider_name, {})
    model_var = env_map.get("model")
    return os.getenv(model_var) if model_var else None


def create_provider(
    provider_type: ProviderType | str,
    api_key: str,
    base_url: str | None = None,
    timeout: float = 60.0,
    app_name: str = "PyScrAI",
) -> LLMProvider:
    """Create an LLM provider instance.

    Args:
        provider_type: Type of provider to create (ProviderType enum or string)
        api_key: API key for the provider
        base_url: Optional base URL (uses provider default if not provided)
        timeout: Request timeout in seconds
        app_name: Application name for API headers

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If provider_type is not supported

    Example:
        >>> provider = create_provider(
        ...     ProviderType.OPENROUTER,
        ...     api_key="sk-or-...",
        ... )
        >>> async with provider:
        ...     models = await provider.list_models()
    """
    # Normalize provider_type to enum
    if isinstance(provider_type, str):
        try:
            provider_type = ProviderType(provider_type.lower())
        except ValueError:
            raise ValueError(
                f"Unsupported provider type: {provider_type}. "
                f"Supported types: {[p.value for p in ProviderType]}"
            ) from None

    if provider_type == ProviderType.OPENROUTER:
        base_url = base_url or OpenRouterProvider.DEFAULT_BASE_URL
        return OpenRouterProvider(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            app_name=app_name,
        )

    # Future providers would be added here
    # elif provider_type == ProviderType.OPENAI:
    #     return OpenAIProvider(...)
    # elif provider_type == ProviderType.ANTHROPIC:
    #     return AnthropicProvider(...)

    raise ValueError(
        f"Provider type {provider_type} is not yet implemented. "
        f"Supported types: {[p.value for p in ProviderType]}"
    )


def create_provider_from_env(
    timeout: float = 60.0,
    app_name: str = "PyScrAI",
) -> tuple[LLMProvider, str | None]:
    """Create provider based on env-configured DEFAULT_PROVIDER.

    Only env vars for the selected provider are read. Returns the provider
    instance and the configured default model (if present).
    """

    provider_name = get_default_provider_name()
    env_map = PROVIDER_ENV_MAP.get(provider_name)
    if env_map is None:
        raise ValueError(
            f"Unsupported provider type: {provider_name}. "
            f"Supported: {list(PROVIDER_ENV_MAP.keys())}"
        )

    api_key = os.getenv(env_map["api_key"]) if env_map.get("api_key") else None
    base_url = os.getenv(env_map["base_url"]) if env_map.get("base_url") else None
    model = os.getenv(env_map["model"]) if env_map.get("model") else None

    # For now we route all providers through the OpenRouter-compatible client
    provider = create_provider(
        ProviderType.OPENROUTER,
        api_key=api_key,  # Provider will validate presence when required
        base_url=base_url or OpenRouterProvider.DEFAULT_BASE_URL,
        timeout=timeout,
        app_name=app_name,
    )

    # Stash default model if provided (OpenRouterProvider already takes it)
    if isinstance(provider, OpenRouterProvider) and model:
        provider.default_model = model

    return provider, model


def get_provider_type_from_model_id(model_id: str) -> ProviderType | None:
    """Infer provider type from model ID.

    Args:
        model_id: Model identifier (e.g., "openai/gpt-4", "anthropic/claude-3")

    Returns:
        ProviderType if recognized, None otherwise

    Example:
        >>> get_provider_type_from_model_id("openai/gpt-4")
        ProviderType.OPENROUTER  # OpenRouter supports OpenAI models
    """
    # OpenRouter supports models from multiple providers
    # For now, all models go through OpenRouter
    # In the future, we might want to route directly to providers
    if "/" in model_id:
        # OpenRouter supports all these, so we default to OpenRouter
        # unless we want to route directly to the provider
        return ProviderType.OPENROUTER

    return None
