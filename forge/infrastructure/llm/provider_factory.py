"""
Provider factory for LLM providers in Forge 3.0.

Centralizes provider creation and environment-driven configuration.
"""

from __future__ import annotations

import os
from enum import Enum

from dotenv import load_dotenv

from forge.infrastructure.llm.base import LLMProvider
from forge.infrastructure.llm.openrouter_provider import OpenRouterProvider

load_dotenv()


# ============================================================================
# Provider Types
# ============================================================================


class ProviderType(str, Enum):
    """Supported LLM provider types."""
    OPENROUTER = "openrouter"
    CHERRY = "cherry"
    LM_PROXY = "lm_proxy"
    LM_STUDIO = "lm_studio"


# Environment variable mapping per provider
PROVIDER_ENV_MAP: dict[str, dict[str, str]] = {
    ProviderType.OPENROUTER.value: {
        "api_key": "OPENROUTER_API_KEY",
        "base_url": "OPENROUTER_BASE_URL",
        "model": "OPENROUTER_MODEL",  # Also supports OPENROUTER_DEFAULT_MODEL for backwards compatibility
    },
    ProviderType.CHERRY.value: {
        "api_key": "CHERRY_API_KEY",
        "base_url": "CHERRY_API_URL",
        "model": "CHERRY_MODEL",
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


# ============================================================================
# Provider Factory
# ============================================================================


class ProviderFactory:
    """Factory for creating LLM provider instances."""
    
    @staticmethod
    def get_default_provider_name() -> str:
        """Get the default provider name from environment."""
        env_name = os.getenv("DEFAULT_PROVIDER")
        if not env_name:
            return ProviderType.OPENROUTER.value
        return env_name.strip().lower().replace("-", "_")
    
    @staticmethod
    def get_default_model() -> str | None:
        """Get the default model for the configured provider."""
        provider_name = ProviderFactory.get_default_provider_name()
        # Support both OPENROUTER_MODEL and OPENROUTER_DEFAULT_MODEL for backwards compatibility
        if provider_name == ProviderType.OPENROUTER.value:
            return os.getenv("OPENROUTER_MODEL") or os.getenv("OPENROUTER_DEFAULT_MODEL")
        env_map = PROVIDER_ENV_MAP.get(provider_name, {})
        model_var = env_map.get("model")
        return os.getenv(model_var) if model_var else None
    
    @staticmethod
    def create(
        provider_type: ProviderType | str,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
        app_name: str = "Forge",
    ) -> LLMProvider:
        """Create an LLM provider instance.
        
        Args:
            provider_type: Type of provider to create
            api_key: API key (loaded from env if not provided)
            base_url: Base URL (uses provider default if not provided)
            timeout: Request timeout in seconds
            app_name: Application name for API headers
            
        Returns:
            LLMProvider instance
            
        Raises:
            ValueError: If provider_type is not supported
        """
        # Normalize to enum
        if isinstance(provider_type, str):
            try:
                provider_type = ProviderType(provider_type.lower())
            except ValueError:
                raise ValueError(
                    f"Unsupported provider type: {provider_type}. "
                    f"Supported: {[p.value for p in ProviderType]}"
                ) from None
        
        if provider_type == ProviderType.OPENROUTER:
            return OpenRouterProvider(
                api_key=api_key,
                base_url=base_url or OpenRouterProvider.DEFAULT_BASE_URL,
                timeout=timeout,
                app_name=app_name,
            )
        
        elif provider_type in (ProviderType.CHERRY, ProviderType.LM_PROXY, ProviderType.LM_STUDIO):
            # These use OpenAI-compatible API via OpenRouter provider
            if not base_url:
                if provider_type == ProviderType.LM_STUDIO:
                    base_url = "http://localhost:1234/v1"
                elif provider_type == ProviderType.LM_PROXY:
                    base_url = "http://localhost:4000/openai/v1"
                elif provider_type == ProviderType.CHERRY:
                    base_url = os.getenv("CHERRY_API_URL", "http://localhost:8000/v1")
            
            return OpenRouterProvider(
                api_key=api_key or "not-needed",
                base_url=base_url,
                timeout=timeout,
                app_name=app_name,
            )
        
        raise ValueError(
            f"Provider type {provider_type} is not yet implemented. "
            f"Supported: {[p.value for p in ProviderType]}"
        )
    
    @staticmethod
    def create_from_env(
        timeout: float = 60.0,
        app_name: str = "Forge",
    ) -> tuple[LLMProvider, str | None]:
        """Create provider from environment configuration, with fallback to SECONDARY_PROVIDER and lm_proxy."""
        import logging
        logger = logging.getLogger(__name__)

        provider_name = ProviderFactory.get_default_provider_name()
        secondary_provider = os.getenv("SECONDARY_PROVIDER", None)
        tried_providers = []

        # Only use providers from .env, do not always fallback to lm_proxy unless set as secondary
        provider_candidates = [provider_name]
        if secondary_provider:
            secondary_provider = secondary_provider.strip().lower().replace("-", "_")
            if secondary_provider != provider_name:
                provider_candidates.append(secondary_provider)

        for prov in provider_candidates:
            if prov in tried_providers:
                continue
            tried_providers.append(prov)
            env_map = PROVIDER_ENV_MAP.get(prov)
            if env_map is None:
                continue
            api_key = os.getenv(env_map["api_key"]) if env_map.get("api_key") else None
            base_url = os.getenv(env_map["base_url"]) if env_map.get("base_url") else None
            if prov == ProviderType.OPENROUTER.value:
                model = os.getenv("OPENROUTER_MODEL") or os.getenv("OPENROUTER_DEFAULT_MODEL")
            else:
                model = os.getenv(env_map["model"]) if env_map.get("model") else None
            try:
                provider = ProviderFactory.create(
                    prov,
                    api_key=api_key,
                    base_url=base_url,
                    timeout=timeout,
                    app_name=app_name,
                )
                if model:
                    provider.default_model = model
                logger.info(f"ProviderFactory: Using provider '{prov}' with model '{model}'")
                return provider, model
            except Exception as e:
                logger.warning(f"ProviderFactory: Failed to initialize provider '{prov}': {e}")
                continue
        raise ValueError(
            f"No valid LLM provider could be initialized. Tried: {tried_providers}"
        )


# ============================================================================
# Convenience Functions
# ============================================================================


def get_provider(
    provider_type: ProviderType | str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout: float = 60.0,
) -> LLMProvider:
    """Get an LLM provider instance.
    
    If provider_type is None, uses the default from environment.
    """
    if provider_type is None:
        provider, _ = ProviderFactory.create_from_env(timeout=timeout)
        return provider
    
    return ProviderFactory.create(
        provider_type,
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
    )


async def complete_simple(
    prompt: str,
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int | None = None,
) -> str:
    """Quick completion using default provider.
    
    Creates a provider, makes the request, and closes it.
    For multiple requests, use get_provider() directly.
    """
    provider, default_model = ProviderFactory.create_from_env()
    
    if model is None:
        model = default_model
    if model is None:
        raise ValueError("No model specified and no default model configured")
    
    async with provider:
        return await provider.complete_simple(
            prompt,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
