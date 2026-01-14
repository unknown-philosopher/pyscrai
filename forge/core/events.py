"""Canonical event definitions for PyScrAI Forge."""

from __future__ import annotations

from typing import Any, Dict, Literal, List

from .event_bus import EventPayload

# Event Topics
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

# Embedding events
TOPIC_ENTITY_EMBEDDED = "entity.embedded"
TOPIC_RELATIONSHIP_EMBEDDED = "relationship.embedded"

# Intelligence events
TOPIC_ENTITY_MERGED = "entity.merged"
TOPIC_SEMANTIC_PROFILE = "semantic.profile"
TOPIC_NARRATIVE_GENERATED = "narrative.generated"
TOPIC_GRAPH_ANALYSIS = "graph.analysis"
TOPIC_INFERRED_RELATIONSHIP = "relationship.inferred"


def create_data_ingested_event(doc_id: str, content: str) -> EventPayload:
    """Create a data ingested event (document received for extraction)."""
    return {
        "doc_id": doc_id,
        "content": content,
    }


def create_entity_extracted_event(doc_id: str, entities: List[Dict[str, Any]]) -> EventPayload:
    """Create an entity extracted event."""
    return {
        "doc_id": doc_id,
        "entities": entities,
    }


def create_relationship_found_event(
    doc_id: str, 
    relationships: List[Dict[str, Any]],
    batch_index: int | None = None,
    is_complete: bool = True
) -> EventPayload:
    """Create a relationship found event.
    
    Args:
        doc_id: Document ID
        relationships: List of relationship dictionaries
        batch_index: Optional batch index for incremental publishing
        is_complete: Whether this is the final batch (default: True for backward compatibility)
    """
    event: EventPayload = {
        "doc_id": doc_id,
        "relationships": relationships,
        "is_complete": is_complete,
    }
    if batch_index is not None:
        event["batch_index"] = batch_index
    return event


def create_graph_updated_event(doc_id: str, graph_stats: Dict[str, Any]) -> EventPayload:
    """Create a graph updated event."""
    return {
        "doc_id": doc_id,
        "graph_stats": graph_stats,
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
