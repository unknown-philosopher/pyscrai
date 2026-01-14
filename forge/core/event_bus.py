from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeAlias

EventPayload: TypeAlias = Dict[str, Any]
EventHandler: TypeAlias = Callable[[EventPayload], Awaitable[None]]


class EventBus:
    """Central Blackboard / PubSub hub."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[EventHandler]] = defaultdict(list)
        # Lazy initialization to avoid event loop binding issues
        self._lock: Optional[asyncio.Lock] = None
        self._loop_id: Optional[int] = None
        self._logger = logging.getLogger(__name__)
    
    def _ensure_lock(self) -> asyncio.Lock:
        """Get or create lock for current event loop."""
        try:
            loop = asyncio.get_running_loop()
            loop_id = id(loop)
            
            # If we have a lock but it's for a different loop, recreate it
            if self._loop_id is not None and self._loop_id != loop_id:
                self._lock = None
            
            # Create lock if needed
            if self._lock is None:
                self._lock = asyncio.Lock()
                self._loop_id = loop_id
        except RuntimeError:
            # No running event loop - create lock anyway (will be bound when used)
            if self._lock is None:
                self._lock = asyncio.Lock()
        
        return self._lock

    async def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Register an async handler for a topic."""
        async with self._ensure_lock():
            if handler not in self._subscribers[topic]:
                self._subscribers[topic].append(handler)

    async def unsubscribe(self, topic: str, handler: EventHandler) -> None:
        """Remove a handler from a topic."""
        async with self._ensure_lock():
            if handler in self._subscribers.get(topic, []):
                self._subscribers[topic].remove(handler)

    async def publish(self, topic: str, payload: EventPayload) -> None:
        """Publish an event to all subscribers."""
        async with self._ensure_lock():
            handlers = list(self._subscribers.get(topic, []))

        if not handlers:
            # Some topics are informational and may not have subscribers (e.g., relationship.inferred)
            # Log at debug level instead of warning to reduce noise
            self._logger.debug(f"No subscribers for topic '{topic}' (this is normal for informational topics)")
            return

        self._logger.debug(f"Publishing to topic '{topic}' with {len(handlers)} handler(s)")
        for handler in handlers:
            asyncio.create_task(self._safe_dispatch(topic, handler, payload))

    async def _safe_dispatch(
        self,
        topic: str,
        handler: EventHandler,
        payload: EventPayload,
    ) -> None:
        """Dispatch wrapper to keep one handler failure from stopping the bus."""
        handler_name = getattr(handler, "__name__", str(handler))
        self._logger.debug(f"Dispatching to handler '{handler_name}' for topic '{topic}'")
        try:
            await handler(payload)
            self._logger.debug(f"Handler '{handler_name}' completed successfully")
        except Exception as exc:
            self._logger.exception(
                f"EventBus handler error in '{handler_name}' for topic '{topic}'",
                exc_info=exc,
            )

    def clear(self) -> None:
        """Remove all subscriptions."""
        self._subscribers.clear()
