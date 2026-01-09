"""
Mutation Event Types for Forge 3.0.

Concrete event types for entity and relationship mutations,
state changes, and correction/retcon operations.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import ConfigDict, Field

from forge.core.events.base import BaseEvent, EventType


# ============================================================================
# State Change Events
# ============================================================================


class StateChangeEvent(BaseEvent):
    """Generic state change for entity attributes.
    
    The "Swiss Army Knife" for attribute mutations.
    Captures old and new values for rollback support.
    """
    
    event_type: EventType = Field(default=EventType.STATE_CHANGE, frozen=True)
    field_name: str = Field(description="Attribute being changed")
    old_value: Optional[Any] = Field(default=None, description="Previous value")
    new_value: Any = Field(description="New value")
    
    model_config = ConfigDict(frozen=True)


class MovementEvent(BaseEvent):
    """Actor movement between locations."""
    
    event_type: EventType = Field(default=EventType.MOVEMENT, frozen=True)
    from_location_id: Optional[str] = Field(default=None, description="Source location")
    to_location_id: str = Field(description="Destination location")
    actor_id: str = Field(description="Moving entity")
    
    model_config = ConfigDict(frozen=True)


class TransferEvent(BaseEvent):
    """Transfer of resources between entities."""
    
    event_type: EventType = Field(default=EventType.TRANSFER, frozen=True)
    from_id: str = Field(description="Source entity")
    to_id: str = Field(description="Target entity")
    resource_type: str = Field(description="Type of resource")
    amount: float = Field(description="Amount transferred")
    
    model_config = ConfigDict(frozen=True)


# ============================================================================
# Relationship Events
# ============================================================================


class RelationshipMutationEvent(BaseEvent):
    """Change in relationship between entities."""
    
    event_type: EventType = Field(default=EventType.RELATIONSHIP_CREATED, frozen=True)
    relationship_id: str = Field(description="Affected relationship ID")
    old_type: Optional[str] = Field(default=None, description="Previous relationship type")
    new_type: Optional[str] = Field(default=None, description="New relationship type")
    old_strength: Optional[float] = Field(default=None)
    new_strength: Optional[float] = Field(default=None)
    
    model_config = ConfigDict(frozen=True)


# ============================================================================
# Correction Events
# ============================================================================


class RetconEvent(BaseEvent):
    """Correction that retroactively changes past state.
    
    Used when source material reveals that previous understanding
    was incorrect. Does not delete history, but records the correction.
    """
    
    event_type: EventType = Field(default=EventType.RETCON, frozen=True)
    original_event_id: str = Field(description="Event being corrected")
    reason: str = Field(description="Why correction is needed")
    compensating_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Data to apply as correction"
    )
    
    model_config = ConfigDict(frozen=True)


class CorrectionEvent(BaseEvent):
    """Minor correction to entity or relationship data.
    
    For small fixes like typos, without full retcon semantics.
    """
    
    event_type: EventType = Field(default=EventType.CORRECTION, frozen=True)
    original_event_id: Optional[str] = Field(
        default=None,
        description="Event being corrected (if applicable)"
    )
    field_name: str = Field(description="Field being corrected")
    old_value: Optional[Any] = Field(default=None)
    new_value: Any = Field(description="Corrected value")
    reason: str = Field(default="", description="Correction reason")
    
    model_config = ConfigDict(frozen=True)


# ============================================================================
# Extraction Events
# ============================================================================


class ExtractionEvent(BaseEvent):
    """Records an extraction operation from source documents."""
    
    event_type: EventType = Field(default=EventType.EXTRACTION, frozen=True)
    source_file: str = Field(description="Source document filename")
    entities_extracted: int = Field(default=0, description="Count of entities extracted")
    relationships_extracted: int = Field(default=0, description="Count of relationships extracted")
    chunk_index: Optional[int] = Field(default=None, description="Chunk number if chunked")
    
    model_config = ConfigDict(frozen=True)


class MergeApprovedEvent(BaseEvent):
    """Records approval of a Sentinel merge plan."""
    
    event_type: EventType = Field(default=EventType.MERGE_APPROVED, frozen=True)
    entities_added: int = Field(default=0)
    entities_updated: int = Field(default=0)
    entities_ignored: int = Field(default=0)
    relationships_added: int = Field(default=0)
    relationships_updated: int = Field(default=0)
    
    model_config = ConfigDict(frozen=True)


class MergeRejectedEvent(BaseEvent):
    """Records rejection of a Sentinel merge plan."""
    
    event_type: EventType = Field(default=EventType.MERGE_REJECTED, frozen=True)
    reason: Optional[str] = Field(default=None, description="Rejection reason")
    entities_rejected: int = Field(default=0)
    
    model_config = ConfigDict(frozen=True)


class RollbackEvent(BaseEvent):
    """Records a rollback operation."""
    
    event_type: EventType = Field(default=EventType.ROLLBACK, frozen=True)
    target_event_id: str = Field(description="Event being rolled back to")
    events_reverted: int = Field(default=0, description="Number of events undone")
    
    model_config = ConfigDict(frozen=True)


# ============================================================================
# Event Factory
# ============================================================================


def create_entity_created_event(
    entity_id: str,
    entity_type: str,
    name: str,
    source_document: str | None = None,
) -> BaseEvent:
    """Create an event for entity creation."""
    return BaseEvent(
        event_type=EventType.ENTITY_CREATED,
        target_id=entity_id,
        description=f"Created {entity_type} entity: {name}",
        data={"entity_type": entity_type, "name": name},
        source_document=source_document,
    )


def create_entity_updated_event(
    entity_id: str,
    changes: dict[str, Any],
    source_document: str | None = None,
) -> BaseEvent:
    """Create an event for entity update."""
    return BaseEvent(
        event_type=EventType.ENTITY_UPDATED,
        target_id=entity_id,
        description=f"Updated entity {entity_id}",
        data={"changes": changes},
        source_document=source_document,
    )


def create_entity_deleted_event(
    entity_id: str,
    name: str,
) -> BaseEvent:
    """Create an event for entity deletion."""
    return BaseEvent(
        event_type=EventType.ENTITY_DELETED,
        target_id=entity_id,
        description=f"Deleted entity: {name}",
        data={"name": name},
    )


def create_relationship_created_event(
    relationship_id: str,
    source_id: str,
    target_id: str,
    relationship_type: str,
    source_document: str | None = None,
) -> BaseEvent:
    """Create an event for relationship creation."""
    return BaseEvent(
        event_type=EventType.RELATIONSHIP_CREATED,
        source_id=source_id,
        target_id=target_id,
        description=f"Created {relationship_type} relationship",
        data={
            "relationship_id": relationship_id,
            "relationship_type": relationship_type,
        },
        source_document=source_document,
    )
