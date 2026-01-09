"""
Relationship Model for Forge 3.0.

Defines graph edges between entities with type classification,
strength, visibility, and provenance tracking.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from forge.core.models.entity import generate_id


# ============================================================================
# Enums
# ============================================================================


class RelationType(str, Enum):
    """Types of relationships between entities."""
    ALLIANCE = "alliance"
    ENMITY = "enmity"
    TRADE = "trade"
    OWNS = "owns"
    OCCUPIES = "occupies"
    KNOWS = "knows"
    INFLUENCES = "influences"
    COMMANDS = "commands"
    MEMBER_OF = "member_of"
    PARENT_OF = "parent_of"
    SIBLING_OF = "sibling_of"
    WORKS_FOR = "works_for"
    LOCATED_IN = "located_in"
    CUSTOM = "custom"


class RelationshipVisibility(str, Enum):
    """Visibility level of a relationship."""
    PUBLIC = "public"       # Known to all
    PRIVATE = "private"     # Known to parties involved
    SECRET = "secret"       # Hidden from most
    CLASSIFIED = "classified"  # Highly restricted


# ============================================================================
# Relationship Model
# ============================================================================


class Relationship(BaseModel):
    """Graph edge representing a connection between two entities.
    
    Relationships are directional: source → target.
    Bidirectional relationships should be modeled as two separate edges
    or use a symmetric relationship type.
    
    Attributes:
        id: Unique identifier (e.g., 'REL_001')
        source_id: Origin entity ID
        target_id: Destination entity ID
        relationship_type: Classification of the relationship
        label: Human-readable edge label (e.g., "advises", "controls")
        description: Detailed description of the relationship
        strength: Relationship intensity (-1.0 to 1.0)
        visibility: Who knows about this relationship
        attributes: Dynamic schema-driven fields
        source_documents: Provenance tracking
        embedding_row_id: Row ID in sqlite-vec for relationship embeddings
        created_at: When the relationship was established
        updated_at: Last modification timestamp
    """
    
    id: str = Field(
        default_factory=lambda: generate_id("REL"),
        description="Unique relationship ID"
    )
    source_id: str = Field(
        description="Source entity ID"
    )
    target_id: str = Field(
        description="Target entity ID"
    )
    relationship_type: RelationType = Field(
        default=RelationType.CUSTOM,
        description="Type classification"
    )
    label: str = Field(
        default="",
        description="Human-readable edge label"
    )
    description: str = Field(
        default="",
        description="Detailed relationship description"
    )
    strength: float = Field(
        default=1.0,
        ge=-1.0,
        le=1.0,
        description="Relationship intensity"
    )
    visibility: RelationshipVisibility = Field(
        default=RelationshipVisibility.PUBLIC,
        description="Visibility level"
    )
    
    # Dynamic attributes
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Schema-driven dynamic fields"
    )
    
    # Provenance tracking
    source_documents: list[str] = Field(
        default_factory=list,
        description="Source files this relationship was extracted from"
    )
    
    # Vector store linking
    embedding_row_id: Optional[int] = Field(
        default=None,
        description="Row ID in sqlite-vec relationship_embeddings table"
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
    
    class Config:
        frozen = False
    
    def __str__(self) -> str:
        label = self.label or self.relationship_type.value
        return f"Relationship({self.source_id} --[{label}]--> {self.target_id})"
    
    def __repr__(self) -> str:
        return f"<Relationship id={self.id} {self.source_id}->{self.target_id} type={self.relationship_type.value}>"
    
    def get_attr(self, key: str, default: Any = None) -> Any:
        """Get a dynamic attribute value."""
        return self.attributes.get(key, default)
    
    def set_attr(self, key: str, value: Any) -> None:
        """Set a dynamic attribute value and update timestamp."""
        self.attributes[key] = value
        self.updated_at = datetime.now(UTC)
    
    def get_embedding_text(self) -> str:
        """Generate text representation for embedding.
        
        Combines relationship info for vectorization.
        """
        parts = [
            self.label,
            self.relationship_type.value,
            self.description,
        ]
        return " ".join(filter(None, parts))
    
    def to_staging_dict(self) -> dict[str, Any]:
        """Convert to dictionary for staging JSON output."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type.value,
            "label": self.label,
            "description": self.description,
            "strength": self.strength,
            "visibility": self.visibility.value,
            "attributes": self.attributes,
            "source_documents": self.source_documents,
        }
    
    @classmethod
    def from_staging_dict(cls, data: dict[str, Any]) -> "Relationship":
        """Create Relationship from staging JSON data."""
        return cls(
            id=data.get("id", generate_id("REL")),
            source_id=data["source_id"],
            target_id=data["target_id"],
            relationship_type=RelationType(data.get("relationship_type", "custom")),
            label=data.get("label", ""),
            description=data.get("description", ""),
            strength=data.get("strength", 1.0),
            visibility=RelationshipVisibility(data.get("visibility", "public")),
            attributes=data.get("attributes", {}),
            source_documents=data.get("source_documents", []),
        )


# ============================================================================
# Helper Functions
# ============================================================================


def create_relationship(
    source_id: str,
    target_id: str,
    relationship_type: RelationType = RelationType.CUSTOM,
    label: str = "",
    description: str = "",
    strength: float = 1.0,
    **kwargs: Any,
) -> Relationship:
    """Create a new relationship between entities."""
    return Relationship(
        source_id=source_id,
        target_id=target_id,
        relationship_type=relationship_type,
        label=label,
        description=description,
        strength=strength,
        **kwargs,
    )


def invert_relationship(rel: Relationship) -> Relationship:
    """Create an inverted copy of a relationship (swap source/target)."""
    return Relationship(
        id=generate_id("REL"),
        source_id=rel.target_id,
        target_id=rel.source_id,
        relationship_type=rel.relationship_type,
        label=f"inverse of {rel.label}" if rel.label else "",
        description=rel.description,
        strength=rel.strength,
        visibility=rel.visibility,
        attributes=rel.attributes.copy(),
        source_documents=rel.source_documents.copy(),
    )
