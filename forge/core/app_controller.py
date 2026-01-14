from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from fletx.core import RxBool, RxDict, RxList, RxStr

from .event_bus import EventBus, EventPayload


class AppController:
    """Bridges the EventBus to reactive SDUI state for the application shell."""

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self._event_bus = event_bus or EventBus()

        # Reactive state exposed to the presentation layer
        self.nav_items: RxList[Dict[str, str]] = RxList(
            [
                {"id": "ingest", "label": "Ingest", "icon": "database"},
                {"id": "graph", "label": "Graph", "icon": "account_tree"},
                {"id": "intel", "label": "Intel", "icon": "psychology"},
                {"id": "project", "label": "Project", "icon": "settings_applications"},
            ]
        )
        self.nav_selected: RxStr = RxStr("ingest")
        self.status_text: RxStr = RxStr("System Initialized…")
        self.ag_feed: RxList[Dict[str, Any]] = RxList([])
        self.workspace_schemas: RxList[Dict[str, Any]] = RxList([])
        self.is_ready: RxBool = RxBool(False)

        # Internal flag to prevent duplicate subscriptions
        self._started = False

    @property
    def bus(self) -> EventBus:
        return self._event_bus

    async def start(self) -> None:
        """Wire bus subscriptions once."""
        if self._started:
            return

        await self._event_bus.subscribe("agui.event", self._handle_agui_event)
        await self._event_bus.subscribe("workspace.schema", self._handle_workspace_schema)
        await self._event_bus.subscribe("status.text", self._handle_status_text)
        await self._event_bus.subscribe("nav.select", self._handle_nav_select)

        self._started = True
        self.is_ready.value = True

    async def publish(self, topic: str, payload: EventPayload) -> None:
        """Publish through the shared bus."""
        await self._event_bus.publish(topic, payload)

    async def _handle_agui_event(self, payload: EventPayload) -> None:
        entry = {
            "ts": payload.get("ts", time.time()),
            "level": payload.get("level", "info"),
            "message": payload.get("message", ""),
            "topic": payload.get("topic"),
        }
        self.ag_feed.append(entry)
        # Keep the feed lightweight
        if len(self.ag_feed) > 200:
            self.ag_feed.value = self.ag_feed.value[-200:]

    async def _handle_workspace_schema(self, payload: EventPayload) -> None:
        schema = payload.get("schema")
        if schema:
            self.workspace_schemas.append(schema)

    async def _handle_status_text(self, payload: EventPayload) -> None:
        text = payload.get("text")
        if text:
            self.status_text.value = str(text)

    async def _handle_nav_select(self, payload: EventPayload) -> None:
        selection = payload.get("id")
        if selection:
            self.nav_selected.value = str(selection)

    async def raise_user_action(self, action: str, payload: Optional[EventPayload] = None) -> None:
        """Helper for UI to push user intent into the bus."""
        await self.publish("user.action", {"action": action, **(payload or {})})

    async def emit_schema(self, schema: Dict[str, Any]) -> None:
        """Convenience for domain services to add SDUI components."""
        await self.publish("workspace.schema", {"schema": schema})

    async def push_status(self, text: str) -> None:
        await self.publish("status.text", {"text": text})

    async def push_agui_log(self, message: str, level: str = "info") -> None:
        await self.publish(
            "agui.event",
            {"message": message, "level": level, "ts": time.time()},
        )

    def clear_workspace(self) -> None:
        """Synchronous helper to reset schemas."""
        self.workspace_schemas.clear()

    def clear_feed(self) -> None:
        self.ag_feed.clear()

    def set_nav_items(self, items: List[Dict[str, str]]) -> None:
        self.nav_items.value = items

    def set_nav_selected(self, nav_id: str) -> None:
        self.nav_selected.value = nav_id

    def ready(self) -> None:
        """Mark controller ready for the UI."""
        self.is_ready.value = True

    def close(self) -> None:
        """Teardown any local state if needed later."""
        self.clear_feed()
        self.workspace_schemas.clear()
