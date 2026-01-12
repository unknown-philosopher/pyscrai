"""Rate limiter for LLM API requests to prevent rate limit errors."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter using a semaphore and minimum delay between requests."""
    
    def __init__(
        self,
        max_concurrent: Optional[int] = None,
        min_delay: Optional[float] = None,
        max_retries: Optional[int] = None,
        initial_retry_delay: Optional[float] = None,
    ):
        """Initialize the rate limiter.
        
        Args:
            max_concurrent: Maximum number of concurrent requests (default: 2, or LLM_RATE_LIMIT_MAX_CONCURRENT env var)
            min_delay: Minimum delay between requests in seconds (default: 1.0, or LLM_RATE_LIMIT_MIN_DELAY env var)
            max_retries: Maximum number of retries for rate limit errors (default: 3, or LLM_RATE_LIMIT_MAX_RETRIES env var)
            initial_retry_delay: Initial delay before retrying in seconds (default: 2.0, or LLM_RATE_LIMIT_RETRY_DELAY env var)
        """
        # More conservative defaults for free tier APIs
        self.max_concurrent = max_concurrent or int(os.getenv("LLM_RATE_LIMIT_MAX_CONCURRENT", "2"))
        self.min_delay = min_delay or float(os.getenv("LLM_RATE_LIMIT_MIN_DELAY", "2.0"))
        self.max_retries = max_retries or int(os.getenv("LLM_RATE_LIMIT_MAX_RETRIES", "3"))
        self.initial_retry_delay = initial_retry_delay or float(os.getenv("LLM_RATE_LIMIT_RETRY_DELAY", "3.0"))
        
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        self._last_request_time: Optional[float] = None
        self._lock = asyncio.Lock()
        
        logger.info(
            f"RateLimiter initialized: max_concurrent={self.max_concurrent}, "
            f"min_delay={self.min_delay}s, max_retries={self.max_retries}"
        )
    
    async def acquire(self) -> None:
        """Acquire a permit for making a request (respects rate limits)."""
        async with self._lock:
            # Enforce minimum delay between requests
            if self._last_request_time is not None:
                elapsed = time.time() - self._last_request_time
                if elapsed < self.min_delay:
                    await asyncio.sleep(self.min_delay - elapsed)
            self._last_request_time = time.time()
        
        # Acquire semaphore to limit concurrency
        await self.semaphore.acquire()
    
    def release(self) -> None:
        """Release a permit after request completes."""
        self.semaphore.release()
    
    async def execute_with_retry(
        self,
        coro_factory,
        is_rate_limit_error = None,
    ):
        """Execute a coroutine with retry logic for rate limit errors.
        Args:
            coro_factory: Callable that returns a coroutine to execute (must be called on each retry)
            is_rate_limit_error: Function to check if an exception is a rate limit error.
                If None, uses default detection logic.
        Returns:
            Result of the coroutine
        Raises:
            Exception: If all retries are exhausted
        """
        import types
        def default_rate_limit_check(exc):
            error_str = str(exc).lower()
            return "rate limit" in error_str or "429" in error_str or "too many requests" in error_str
        check_func = is_rate_limit_error if is_rate_limit_error is not None else default_rate_limit_check
        retry_delay = self.initial_retry_delay
        for attempt in range(self.max_retries + 1):
            try:
                await self.acquire()
                try:
                    # Call the factory to create a new coroutine for each attempt
                    coro = coro_factory() if callable(coro_factory) else coro_factory
                    if not asyncio.iscoroutine(coro):
                        raise TypeError("coro_factory must return a coroutine object")
                    return await coro
                finally:
                    self.release()
            except Exception as e:
                if check_func(e) and attempt < self.max_retries:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Rate limit error (attempt {attempt + 1}/{self.max_retries + 1}), "
                        f"retrying in {wait_time:.1f}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                    retry_delay = wait_time
                    continue
                # Not a rate limit error or out of retries
                raise
        # Should never reach here, but just in case
        raise RuntimeError("Rate limiter retry logic failed")


# Global rate limiter instance
_default_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the default rate limiter instance."""
    global _default_limiter
    if _default_limiter is None:
        _default_limiter = RateLimiter()
    return _default_limiter
