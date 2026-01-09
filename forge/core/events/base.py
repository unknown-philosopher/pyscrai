"""
Base Event Classes for Forge 3.0.

Defines the immutable Event system for history tracking, logging,
and undo capabilities. All state changes flow through Events.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from forge.core.models.entity import generate_id


# ============================================================================
# Event Type Enum
# ============================================================================


class EventType(str, Enum):
    """Types of events in the system."""
    # Entity events
    ENTITY_CREATED = "entity_created"
    ENTITY_UPDATED = "entity_updated"
    ENTITY_DELETED = "entity_deleted"
    ENTITY_MERGED = "entity_merged"
    
    # Relationship events
    RELATIONSHIP_CREATED = "relationship_created"
    RELATIONSHIP_UPDATED = "relationship_updated"
    RELATIONSHIP_DELETED = "relationship_deleted"
    
    # State events
    STATE_CHANGE = "state_change"
    MOVEMENT = "movement"
    TRANSFER = "transfer"
    
    # Correction events
    RETCON = "retcon"
    CORRECTION = "correction"
    
    # System events
    EXTRACTION = "extraction"
    MERGE_APPROVED = "merge_approved"
    MERGE_REJECTED = "merge_rejected"
    ROLLBACK = "rollback"
    
    # Custom
    CUSTOM = "custom"


# ============================================================================
# Base Event
# ============================================================================


class BaseEvent(BaseModel):
    """Immutable atomic fact representing a state change.
    
    All mutations in Forge flow through events, enabling:
    - Complete history tracking
    - Provenance for each change
    - Rollback/undo capabilities
    - Audit logging
    
    Attributes:
        id: Unique event ID
        event_type: Classification of the event
        timestamp: When the event occurred
        source_id: Entity that triggered this event (or "system")
        target_id: Entity being affected (optional)
        description: Human-readable description
        data: Additional event-specific data
        source_document: Document this change came from
        is_rolled_back: Whether this event has been undone
    """
    
    id: str = Field(
        default_factory=lambda: generate_id("EVENT"),
        description="Unique event ID"
    )
    event_type: EventType = Field(
        description="Type classification"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When event occurred"
    )
    source_id: str = Field(
        default="system",
        description="Entity or system that triggered this event"
    )
    target_id: Optional[str] = Field(
        default=None,
        description="Entity being affected"
    )
    description: str = Field(
        default="",
        description="Human-readable description"
    )
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Event-specific data"
    )
    source_document: Optional[str] = Field(
        default=None,
        description="Source document for provenance"
    )
    is_rolled_back: bool = Field(
        default=False,
        description="Whether this event has been undone"
    )
    
    model_config = ConfigDict(frozen=True)  # Events are immutable
    
    def __str__(self) -> str:
        return f"Event({self.event_type.value}: {self.description[:50]})"
    
    def to_db_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "source_id": self.source_id,
            "target_id": self.target_id,
            "description": self.description,
            "data_json": self.data,
            "is_rolled_back": 1 if self.is_rolled_back else 0,
        }
