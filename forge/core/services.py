"""Shared service utilities and base classes for PyScrAI Forge.

Provides common functionality for LLM-based services to reduce code duplication.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable

from forge.core.event_bus import EventBus
from forge.infrastructure.llm.base import LLMProvider, RateLimitError
from forge.infrastructure.llm.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


class BaseLLMService:
    """Base class for services that use LLM providers.
    
    Provides common initialization and LLM call utilities.
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        llm_provider: Optional[LLMProvider] = None,
        service_name: str = "Service"
    ):
        """Initialize the base service.
        
        Args:
            event_bus: Event bus for publishing/subscribing to events
            llm_provider: LLM provider (optional, will try to get from environment if None)
            service_name: Name of the service for logging
        """
        self.event_bus = event_bus
        self._llm_provider = llm_provider
        self.service_name = service_name
    
    @property
    def llm_provider(self) -> Optional[LLMProvider]:
        """Get the LLM provider, initializing from environment if needed."""
        if self._llm_provider is None:
            try:
                from forge.infrastructure.llm.provider_factory import ProviderFactory
                self._llm_provider, _ = ProviderFactory.create_from_env()
                logger.info(f"{self.service_name}: Using LLM provider from environment")
            except Exception as e:
                logger.warning(f"{self.service_name}: Could not initialize LLM provider: {e}")
                logger.warning(f"{self.service_name}: LLM operations will be disabled")
        return self._llm_provider
    
    async def ensure_llm_provider(self) -> bool:
        """Ensure LLM provider is available.
        
        Returns:
            True if LLM provider is available, False otherwise
        """
        if self.llm_provider is None:
            logger.error(f"{self.service_name}: No LLM provider available")
            return False
        return True


async def call_llm_with_retry(
    llm_provider: LLMProvider,
    prompt: str,
    model: Optional[str] = None,
    max_tokens: int = 2000,
    temperature: float = 0.3,
    service_name: str = "Service"
) -> Dict[str, Any]:
    """Make an LLM call with rate limiting and retry logic.
    
    Args:
        llm_provider: LLM provider instance
        prompt: Prompt text to send
        model: Model to use (if None, uses first available or default)
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        service_name: Service name for logging
        
    Returns:
        LLM response dictionary
        
    Raises:
        ValueError: If no model is available
        Exception: If LLM call fails after retries
    """
    # Get model if not provided
    if model is None:
        models = await llm_provider.list_models()
        model = models[0].id if models else llm_provider.default_model
        if not model:
            raise ValueError(f"{service_name}: No model available for LLM call")
    
    # Create LLM call function
    async def _make_llm_call():
        return await llm_provider.complete(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    
    # Use rate limiter for LLM call
    rate_limiter = get_rate_limiter()
    response = await rate_limiter.execute_with_retry(
        _make_llm_call,  # Pass function, not coroutine
        is_rate_limit_error=lambda e: isinstance(e, RateLimitError) or "rate limit" in str(e).lower()
    )
    
    return response


def extract_content_from_response(response: Dict[str, Any]) -> str:
    """Extract content text from LLM response.
    
    Args:
        response: LLM response dictionary
        
    Returns:
        Content text, or empty string if not found
    """
    if "choices" in response and response["choices"]:
        return response["choices"][0].get("message", {}).get("content", "")
    return ""


def clean_markdown_code_blocks(content: str) -> str:
    """Remove markdown code block markers from content.
    
    Args:
        content: Content text that may contain markdown code blocks
        
    Returns:
        Cleaned content text
    """
    content = content.strip()
    if content.startswith("```"):
        # Remove markdown code block markers
        lines = content.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()
    return content


async def call_llm_and_parse_json(
    llm_provider: LLMProvider,
    prompt: str,
    model: Optional[str] = None,
    max_tokens: int = 2000,
    temperature: float = 0.3,
    service_name: str = "Service",
    doc_id: Optional[str] = None
) -> Optional[Any]:
    """Make an LLM call and parse the response as JSON.
    
    Args:
        llm_provider: LLM provider instance
        prompt: Prompt text to send
        model: Model to use (if None, uses first available or default)
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        service_name: Service name for logging
        doc_id: Optional document ID for logging
        
    Returns:
        Parsed JSON object, or None if parsing fails
    """
    try:
        response = await call_llm_with_retry(
            llm_provider=llm_provider,
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            service_name=service_name
        )
        
        content = extract_content_from_response(response)
        if not content:
            log_msg = f"No content in LLM response"
            if doc_id:
                log_msg += f" for document {doc_id}"
            logger.warning(f"{service_name}: {log_msg}")
            return None
        
        # Clean markdown code blocks
        content = clean_markdown_code_blocks(content)
        
        # Parse JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            log_msg = f"Failed to parse LLM response as JSON: {e}"
            if doc_id:
                log_msg += f" (document {doc_id})"
            logger.error(f"{service_name}: {log_msg}")
            logger.debug(f"{service_name}: Response content: {content[:500]}")
            return None
            
    except Exception as e:
        log_msg = f"Error in LLM call"
        if doc_id:
            log_msg += f" for document {doc_id}"
        logger.error(f"{service_name}: {log_msg}: {e}", exc_info=True)
        return None


async def call_llm_and_get_text(
    llm_provider: LLMProvider,
    prompt: str,
    model: Optional[str] = None,
    max_tokens: int = 2000,
    temperature: float = 0.3,
    service_name: str = "Service",
    doc_id: Optional[str] = None
) -> Optional[str]:
    """Make an LLM call and return the text content.
    
    Args:
        llm_provider: LLM provider instance
        prompt: Prompt text to send
        model: Model to use (if None, uses first available or default)
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        service_name: Service name for logging
        doc_id: Optional document ID for logging
        
    Returns:
        Content text, or None if call fails
    """
    try:
        response = await call_llm_with_retry(
            llm_provider=llm_provider,
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            service_name=service_name
        )
        
        content = extract_content_from_response(response)
        if not content:
            log_msg = f"No content in LLM response"
            if doc_id:
                log_msg += f" for document {doc_id}"
            logger.warning(f"{service_name}: {log_msg}")
            return None
        
        # Clean markdown code blocks and return
        return clean_markdown_code_blocks(content)
        
    except Exception as e:
        log_msg = f"Error in LLM call"
        if doc_id:
            log_msg += f" for document {doc_id}"
        logger.error(f"{service_name}: {log_msg}: {e}", exc_info=True)
        return None
