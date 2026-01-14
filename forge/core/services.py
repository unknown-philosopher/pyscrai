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
    max_tokens: int = 8000,
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
    # Get model if not provided - prefer default_model over first available
    if model is None:
        logger.debug(f"{service_name}: No model provided, checking default_model: '{llm_provider.default_model}'")
        model = llm_provider.default_model
        if not model:
            logger.warning(f"{service_name}: No default_model set, falling back to first available model")
            # Fallback to first available model if no default
            models = await llm_provider.list_models()
            model = models[0].id if models else None
            if model:
                logger.info(f"{service_name}: Selected first available model: '{model}'")
        if not model:
            raise ValueError(f"{service_name}: No model available for LLM call")
    
    # Log the model being used
    logger.info(f"{service_name}: Using model '{model}' for LLM call")
    if llm_provider.default_model and model != llm_provider.default_model:
        logger.warning(
            f"{service_name}: Model '{model}' differs from default_model '{llm_provider.default_model}'"
        )
    elif llm_provider.default_model:
        logger.debug(f"{service_name}: Using default_model '{model}' as expected")
    
    # Create LLM call function
    async def _make_llm_call():
        # Log the exact payload being sent
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        logger.debug(f"{service_name}: Sending LLM request with payload: {payload}")
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


def _add_json_format_reminder(prompt: str, attempt: int) -> str:
    """Add JSON format reminder to prompt on retries.
    
    Args:
        prompt: Original prompt
        attempt: Retry attempt number (1-based)
        
    Returns:
        Prompt with JSON format reminder appended
    """
    json_reminder = (
        "\n\nCRITICAL: Your previous response contained invalid JSON. "
        "You MUST respond with ONLY valid JSON - no markdown, no explanations, no code blocks. "
        "\n\nJSON Requirements:"
        "\n- All strings MUST use double quotes (\"), not single quotes (')"
        "\n- All property names MUST be in double quotes"
        "\n- Every string value MUST be properly closed with a matching quote"
        "\n- Every opening bracket [ must have a closing bracket ]"
        "\n- Every opening brace { must have a closing brace }"
        "\n- All items in arrays must be separated by commas"
        "\n- No trailing commas before closing brackets or braces"
        "\n- Escape special characters in strings with backslash (\\\" for quotes, \\\\ for backslash)"
        "\n\nYour response must be a valid JSON array that can be parsed by json.loads() with no errors."
    )
    return prompt + json_reminder


async def call_llm_and_parse_json(
    llm_provider: LLMProvider,
    prompt: str,
    model: Optional[str] = None,
    max_tokens: int = 2000,
    temperature: float = 0.3,
    service_name: str = "Service",
    doc_id: Optional[str] = None,
    max_retries: int = 2
) -> Optional[Any]:
    """Make an LLM call and parse the response as JSON with retry logic.
    
    Args:
        llm_provider: LLM provider instance
        prompt: Prompt text to send
        model: Model to use (if None, uses first available or default)
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        service_name: Service name for logging
        doc_id: Optional document ID for logging
        max_retries: Maximum number of retries on JSON parsing failure
        
    Returns:
        Parsed JSON object, or None if parsing fails after all retries
    """
    for attempt in range(max_retries + 1):  # Initial attempt + max_retries
        try:
            # Use original prompt on first attempt, add reminder on retries
            current_prompt = prompt if attempt == 0 else _add_json_format_reminder(prompt, attempt)
            
            # Lower temperature on retries for more deterministic output
            current_temperature = temperature if attempt == 0 else max(0.0, temperature - 0.1)
            
            if attempt > 0:
                log_msg = f"Retrying JSON parse (attempt {attempt + 1}/{max_retries + 1})"
                if doc_id:
                    log_msg += f" for document {doc_id}"
                logger.warning(f"{service_name}: {log_msg}")
            
            response = await call_llm_with_retry(
                llm_provider=llm_provider,
                prompt=current_prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=current_temperature,
                service_name=service_name
            )
            
            content = extract_content_from_response(response)
            if not content:
                log_msg = f"No content in LLM response"
                if doc_id:
                    log_msg += f" for document {doc_id}"
                if attempt < max_retries:
                    logger.warning(f"{service_name}: {log_msg}, will retry")
                    continue
                logger.warning(f"{service_name}: {log_msg}")
                return None
            
            # Clean markdown code blocks
            content = clean_markdown_code_blocks(content)
            
            # Parse JSON
            try:
                result = json.loads(content)
                if attempt > 0:
                    log_msg = f"Successfully parsed JSON on retry attempt {attempt + 1}"
                    if doc_id:
                        log_msg += f" for document {doc_id}"
                    logger.info(f"{service_name}: {log_msg}")
                return result
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse LLM response as JSON: {e}"
                if doc_id:
                    error_msg += f" (document {doc_id})"
                
                if attempt < max_retries:
                    logger.warning(f"{service_name}: {error_msg}, will retry")
                    # Log a snippet around the error location for debugging
                    error_pos = getattr(e, 'pos', None)
                    if error_pos:
                        start = max(0, error_pos - 100)
                        end = min(len(content), error_pos + 100)
                        logger.debug(f"{service_name}: Error context: ...{content[start:end]}...")
                    continue
                else:
                    logger.error(f"{service_name}: {error_msg} (all retries exhausted)")
                    logger.debug(f"{service_name}: Response content (first 1000 chars): {content[:1000]}")
                    
                    # Log error position if available
                    error_pos = getattr(e, 'pos', None)
                    if error_pos:
                        logger.debug(f"{service_name}: JSON parse error at position {error_pos} of {len(content)}")
                        # Show the problematic area
                        start = max(0, error_pos - 200)
                        end = min(len(content), error_pos + 200)
                        logger.debug(f"{service_name}: Error region: ...{content[start:end]}...")
                return None
                
        except Exception as e:
            log_msg = f"Error in LLM call"
            if doc_id:
                log_msg += f" for document {doc_id}"
            if attempt < max_retries:
                logger.warning(f"{service_name}: {log_msg}: {e}, will retry")
                continue
            logger.error(f"{service_name}: {log_msg}: {e} (all retries exhausted)", exc_info=True)
            return None
    
    # Should never reach here, but just in case
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
