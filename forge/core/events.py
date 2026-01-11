"""Canonical event definitions for PyScrAI Forge."""

from __future__ import annotations

from typing import Any, Dict, Literal

from .event_bus import EventPayload

# Event Topics
TOPIC_TELEMETRY_UPDATE = "telemetry.update"
TOPIC_AGUI_EVENT = "agui.event"
TOPIC_WORKSPACE_SCHEMA = "workspace.schema"
TOPIC_STATUS_TEXT = "status.text"
TOPIC_NAV_SELECT = "nav.select"
TOPIC_USER_ACTION = "user.action"

# Domain Events (for future use)
TOPIC_DATA_INGESTED = "data.ingested"
TOPIC_ENTITY_EXTRACTED = "entity.extracted"
TOPIC_RELATIONSHIP_FOUND = "relationship.found"
TOPIC_GRAPH_UPDATED = "graph.updated"
TOPIC_INTELLIGENCE_SYNTHESIZED = "intelligence.synthesized"


def create_telemetry_event(gpu_util: float, vram_used_gb: float, vram_total_gb: float) -> EventPayload:
    """Create a telemetry update event."""
    return {
        "gpu_util": gpu_util,
        "vram_used_gb": vram_used_gb,
        "vram_total_gb": vram_total_gb,
    }


def create_agui_event(
    message: str,
    level: Literal["info", "warning", "error", "success"] = "info",
    topic: str | None = None,
) -> EventPayload:
    """Create an AG-UI feed event."""
    import time

    return {
        "message": message,
        "level": level,
        "topic": topic,
        "ts": time.time(),
    }


def create_workspace_schema_event(schema: Dict[str, Any]) -> EventPayload:
    """Create a workspace schema event."""
    return {
        "schema": schema,
    }


def create_status_text_event(text: str) -> EventPayload:
    """Create a status text update event."""
    return {
        "text": text,
    }


def create_nav_select_event(nav_id: str) -> EventPayload:
    """Create a navigation selection event."""
    return {
        "id": nav_id,
    }


def create_user_action_event(action: str, payload: Dict[str, Any] | None = None) -> EventPayload:
    """Create a user action event."""
    result: EventPayload = {"action": action}
    if payload:
        result.update(payload)
    return result
