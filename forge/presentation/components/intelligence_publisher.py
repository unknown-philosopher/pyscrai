"""Helper utilities for publishing intelligence visualizations to AG-UI feed."""

from typing import Dict, Any

from forge.core.event_bus import EventBus
from forge.core import events


async def publish_semantic_profile_ui(
    event_bus: EventBus,
    entity_id: str,
    summary: str,
    attributes: list[str],
    importance: int,
    key_relationships: list[str],
    confidence: float
):
    """Publish a semantic profile visualization to the AG-UI feed.
    
    Args:
        event_bus: Event bus instance
        entity_id: Entity identifier
        summary: Brief entity summary
        attributes: List of key attributes
        importance: 1-10 importance rating
        key_relationships: List of important relationship types
        confidence: 0-1 confidence score
    """
    await event_bus.publish(
        events.TOPIC_WORKSPACE_SCHEMA,
        events.create_workspace_schema_event({
            "type": "semantic_profile",
            "title": f"Profile: {entity_id}",
            "props": {
                "entity_id": entity_id,
                "summary": summary,
                "attributes": attributes,
                "importance": importance,
                "key_relationships": key_relationships,
                "confidence": confidence
            }
        })
    )


async def publish_narrative_ui(
    event_bus: EventBus,
    doc_id: str,
    narrative: str,
    entity_count: int,
    relationship_count: int
):
    """Publish a narrative visualization to the AG-UI feed.
    
    Args:
        event_bus: Event bus instance
        doc_id: Document identifier
        narrative: Markdown-formatted narrative text
        entity_count: Number of entities
        relationship_count: Number of relationships
    """
    await event_bus.publish(
        events.TOPIC_WORKSPACE_SCHEMA,
        events.create_workspace_schema_event({
            "type": "narrative",
            "title": "Document Narrative",
            "props": {
                "doc_id": doc_id,
                "narrative": narrative,
                "entity_count": entity_count,
                "relationship_count": relationship_count
            }
        })
    )


async def publish_graph_analytics_ui(
    event_bus: EventBus,
    analysis: Dict[str, Any]
):
    """Publish graph analytics visualization to the AG-UI feed.
    
    Args:
        event_bus: Event bus instance
        analysis: Analysis dict with centrality, communities, and statistics
    """
    await event_bus.publish(
        events.TOPIC_WORKSPACE_SCHEMA,
        events.create_workspace_schema_event({
            "type": "graph_analytics",
            "title": "Graph Analysis",
            "props": analysis
        })
    )


async def publish_entity_card_ui(
    event_bus: EventBus,
    entity_id: str,
    entity_type: str,
    label: str,
    relationship_count: int
):
    """Publish an entity card visualization to the AG-UI feed.
    
    Args:
        event_bus: Event bus instance
        entity_id: Entity identifier
        entity_type: Entity type (PERSON, ORG, etc.)
        label: Entity label/name
        relationship_count: Number of relationships
    """
    await event_bus.publish(
        events.TOPIC_WORKSPACE_SCHEMA,
        events.create_workspace_schema_event({
            "type": "entity_card",
            "title": f"{entity_type}: {label}",
            "props": {
                "entity_id": entity_id,
                "type": entity_type,
                "label": label,
                "relationship_count": relationship_count
            }
        })
    )
