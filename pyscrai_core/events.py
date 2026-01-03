"""Event and temporal models for PyScrAI.

This module defines the immutable Event system, Turn container, and WorldSnapshot.

Guardrail 3: Event-First Mutation
> All state changes must flow through immutable Events, never direct StateComponent writes.

Design Philosophy: "Blank Canvas" Events
========================================
Events manipulate the **Project-Defined Schema**. 
Specifically, `ResourceTransferEvent` and `StateChangeEvent` target keys within the 
`resources_json` container, allowing them to work for 'gold', 'credits', 'mana', etc.
"""

import json
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Event Base Class (Immutable)
# ============================================================================


class Event(BaseModel):
    """Immutable atomic fact representing a state change.

    Lifecycle:
    1. Agent/User creates Intention.
    2. Engine validates and converts to Event.
    3. Event queued for Turn N.
    4. Turn N resolution applies event → mutates StateComponent.resources_json.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique event ID")
    event_type: str = Field(description="Type identifier for event dispatching")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="When event was created"
    )
    source_id: str = Field(description="Entity ID that triggered this event")
    description: str = Field(default="", description="Human-readable event description")

    class Config:
        frozen = True  # Immutable


# ============================================================================
# Concrete Event Types
# ============================================================================


class MovementEvent(Event):
    """Actor movement from one location to another.

    Uses `region_version` infrastructure fields (O(1) access) for validation.
    """

    event_type: str = Field(default="movement", frozen=True)
    from_location_id: str = Field(description="Source location ID")
    to_location_id: str = Field(description="Destination location ID")
    actor_id: str = Field(description="Moving entity ID")
    region_id: str = Field(description="Region this movement occurs in")
    region_version_at_time: int = Field(
        description="Region graph version when path was computed"
    )


class ResourceTransferEvent(Event):
    """Transfer of resources between entities.

    Operates on the dynamic Project Schema.
    `resource_type` must correspond to a key in the entity's `resources_json`.
    """

    event_type: str = Field(default="resource_transfer", frozen=True)
    from_id: str = Field(description="Source entity ID")
    to_id: str = Field(description="Target entity ID")
    resource_type: str = Field(description="Key in resources_json (e.g., 'gold', 'mana')")
    amount: float = Field(description="Amount transferred")


class RelationshipChangeType(str, Enum):
    """Types of relationship changes."""
    ALLIANCE_FORMED = "alliance_formed"
    ALLIANCE_BROKEN = "alliance_broken"
    WAR_DECLARED = "war_declared"
    PEACE_TREATY = "peace_treaty"
    TRADE_AGREEMENT = "trade_agreement"
    TRADE_EMBARGO = "trade_embargo"
    VASSALIZATION = "vassalization"
    INDEPENDENCE = "independence"
    HOSTILE_ACTION = "hostile_action"
    COOPERATION = "cooperation"
    CUSTOM = "custom"


class RelationshipChangeEvent(Event):
    """Change in relationship between entities."""

    event_type: str = Field(default="relationship_change", frozen=True)
    target_id: str = Field(description="Target entity ID")
    change_type: RelationshipChangeType = Field(description="Type of change")
    old_relationship: Optional[str] = Field(default=None)
    new_relationship: Optional[str] = Field(default=None)
    metadata_json: str = Field(default="{}")

    @property
    def metadata(self) -> dict[str, Any]:
        try:
            return json.loads(self.metadata_json) if self.metadata_json else {}
        except json.JSONDecodeError:
            return {}


# Alias for backwards compatibility
class DiplomaticShiftEvent(RelationshipChangeEvent):
    event_type: str = Field(default="diplomatic_shift", frozen=True)
    shift_type: Optional[RelationshipChangeType] = Field(default=None)


class CorrectionEvent(Event):
    """Corrects a previous event without deletion."""

    event_type: str = Field(default="correction", frozen=True)
    original_event_id: str = Field(description="ID of event being corrected")
    reason: str = Field(description="Why correction is needed")
    compensating_effect: str = Field(default="{}")

    @property
    def effect(self) -> dict[str, Any]:
        try:
            return json.loads(self.compensating_effect) if self.compensating_effect else {}
        except json.JSONDecodeError:
            return {}


class StateChangeEvent(Event):
    """Generic state change event for dynamic entity properties.

    The "Swiss Army Knife" for the Blank Canvas architecture.
    Used to mutate any field in `resources_json` or other StateComponent properties.
    
    Example:
        field_name="resources_json.mana", new_value="50"
    """

    event_type: str = Field(default="state_change", frozen=True)
    target_id: str = Field(description="Entity being modified")
    field_name: str = Field(description="Field being changed (supports dot notation for resources)")
    old_value: Optional[str] = Field(default=None, description="Previous value (JSON)")
    new_value: str = Field(description="New value (JSON)")


class CustomEvent(Event):
    """Fully custom event for domain-specific mechanics defined in Project."""

    event_type: str = Field(default="custom", frozen=True)
    action_type: str = Field(description="Domain-specific action identifier")
    target_id: Optional[str] = Field(default=None)
    parameters_json: str = Field(default="{}")

    @property
    def parameters(self) -> dict[str, Any]:
        try:
            return json.loads(self.parameters_json) if self.parameters_json else {}
        except json.JSONDecodeError:
            return {}


# ============================================================================
# Turn & Snapshot
# ============================================================================


class Turn(BaseModel):
    """Temporal container for a simulation tick."""
    tick: int = Field(description="Turn/tick number")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    applied_events: list[Event] = Field(default_factory=list)
    is_resolved: bool = Field(default=False)
    region_versions: str = Field(default="{}")

    class Config:
        frozen = False

    def add_event(self, event: Event) -> None:
        if self.is_resolved:
            raise RuntimeError(f"Cannot add events to resolved Turn {self.tick}")
        self.applied_events.append(event)

    def resolve(self) -> None:
        self.is_resolved = True

    @property
    def region_version_snapshot(self) -> dict[str, int]:
        try:
            return json.loads(self.region_versions) if self.region_versions else {}
        except json.JSONDecodeError:
            return {}


class NarrativeLogEntry(BaseModel):
    """Generated summary of a turn."""
    turn_id: int
    summary: str
    key_events: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        frozen = False


class WorldSnapshot(BaseModel):
    """Complete state freeze.
    
    Captures the full state, including the dynamic `resources_json` of all entities.
    """
    tick: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    entities_json: str = Field(description="JSON dict: {entity_id: serialized_entity_state}")
    relationships_json: str = Field(default="[]")
    schema_version: int = Field(default=1)

    class Config:
        frozen = True

    @property
    def entities(self) -> dict[str, dict]:
        try:
            return json.loads(self.entities_json) if self.entities_json else {}
        except json.JSONDecodeError:
            return {}

    @property
    def relationships(self) -> list[dict]:
        try:
            return json.loads(self.relationships_json) if self.relationships_json else []
        except json.JSONDecodeError:
            return []


# ============================================================================
# Event Registry
# ============================================================================


EVENT_TYPES: dict[str, type[Event]] = {
    "movement": MovementEvent,
    "resource_transfer": ResourceTransferEvent,
    "relationship_change": RelationshipChangeEvent,
    "diplomatic_shift": DiplomaticShiftEvent,
    "correction": CorrectionEvent,
    "state_change": StateChangeEvent,
    "custom": CustomEvent,
}


def get_event_class(event_type: str) -> type[Event]:
    """Get the Event subclass for a given event type."""
    if event_type not in EVENT_TYPES:
        raise KeyError(f"Unknown event type: {event_type}")
    return EVENT_TYPES[event_type]