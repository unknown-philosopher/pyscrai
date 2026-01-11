from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict, List, TypeAlias

EventPayload: TypeAlias = Dict[str, Any]
EventHandler: TypeAlias = Callable[[EventPayload], Awaitable[None]]


class EventBus:
    """Central Blackboard / PubSub hub."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._logger = logging.getLogger(__name__)

    async def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Register an async handler for a topic."""
        async with self._lock:
            if handler not in self._subscribers[topic]:
                self._subscribers[topic].append(handler)

    async def unsubscribe(self, topic: str, handler: EventHandler) -> None:
        """Remove a handler from a topic."""
        async with self._lock:
            if handler in self._subscribers.get(topic, []):
                self._subscribers[topic].remove(handler)

    async def publish(self, topic: str, payload: EventPayload) -> None:
        """Publish an event to all subscribers."""
        async with self._lock:
            handlers = list(self._subscribers.get(topic, []))

        if not handlers:
            return

        for handler in handlers:
            asyncio.create_task(self._safe_dispatch(topic, handler, payload))

    async def _safe_dispatch(
        self,
        topic: str,
        handler: EventHandler,
        payload: EventPayload,
    ) -> None:
        """Dispatch wrapper to keep one handler failure from stopping the bus."""
        try:
            await handler(payload)
        except Exception as exc:  # pragma: no cover - placeholder logging
            self._logger.exception(
                "EventBus handler error",
                extra={"topic": topic, "handler": handler.__name__},
                exc_info=exc,
            )

    def clear(self) -> None:
        """Remove all subscriptions."""
        self._subscribers.clear()
