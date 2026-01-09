"""
Entity and Component Models for Forge 3.0.

This module defines the Entity model with dynamic attributes for flexible
schema support. Entities are the core data objects representing actors,
locations, organizations, and other world elements.

Key Changes from Legacy:
- Dynamic `attributes: dict` replaces fixed fields for prefab schema flexibility
- Added `embedding_row_id` for sqlite-vec vector table linking
- Simplified component structure while preserving ECS philosophy
"""

from __future__ import annotations

import json
import re
import threading
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# ID Generation (Thread-Safe)
# ============================================================================

_id_counters: dict[str, int] = {}
_id_lock = threading.Lock()
_id_counters_path: Path | None = None
_id_pattern = re.compile(r"^(?P<prefix>[A-Za-z]+)_(?P<num>\d+)$")


def generate_id(prefix: str) -> str:
    """Generate a human-readable ID like 'ACTOR_001'.
    
    Thread-safe and persistent across sessions when configured.
    """
    with _id_lock:
        if prefix not in _id_counters:
            _id_counters[prefix] = 1
        else:
            _id_counters[prefix] += 1
        
        if _id_counters_path:
            try:
                _id_counters_path.write_text(json.dumps(_id_counters), encoding="utf-8")
            except Exception:
                pass
        
        return f"{prefix}_{_id_counters[prefix]:03d}"


def set_id_counters_path(path: str | Path) -> None:
    """Configure persistence file for ID counters."""
    global _id_counters_path, _id_counters
    p = Path(path)
    _id_counters_path = p
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            _id_counters = {str(k): int(v) for k, v in data.items()}
        except Exception:
            _id_counters = {}


def reset_id_counters() -> None:
    """Reset all ID counters to 0."""
    global _id_counters
    _id_counters = {}
    if _id_counters_path:
        try:
            _id_counters_path.write_text(json.dumps(_id_counters), encoding="utf-8")
        except Exception:
            pass


def seed_id_counter(id_value: str) -> None:
    """Update counter based on existing ID value (e.g., 'ACTOR_005')."""
    if not id_value:
        return
    
    match = _id_pattern.match(id_value)
    if not match:
        return
    
    prefix = match.group("prefix").upper()
    try:
        num = int(match.group("num"))
    except ValueError:
        return
    
    with _id_lock:
        current = _id_counters.get(prefix, 0)
        if num > current:
            _id_counters[prefix] = num
            if _id_counters_path:
                try:
                    _id_counters_path.write_text(json.dumps(_id_counters), encoding="utf-8")
                except Exception:
                    pass


# ============================================================================
# Enums
# ============================================================================


class EntityType(str, Enum):
    """Classification for entities."""
    ACTOR = "actor"          # Individual person/agent
    POLITY = "polity"        # Organization/faction/group
    LOCATION = "location"    # Physical place
    REGION = "region"        # Container of locations
    RESOURCE = "resource"    # Asset/item
    EVENT = "event"          # Historical occurrence
    ABSTRACT = "abstract"    # Conceptual entity


class LocationLayer(str, Enum):
    """Spatial layer for location entities."""
    TERRESTRIAL = "terrestrial"
    ORBITAL = "orbital"
    SUBTERRANEAN = "subterranean"
    AQUATIC = "aquatic"
    VIRTUAL = "virtual"
    ABSTRACT = "abstract"


# ============================================================================
# Entity Model
# ============================================================================


class Entity(BaseModel):
    """Core entity model with dynamic attribute support.
    
    The `attributes` dict stores all entity-specific fields as defined
    by the project's prefab schema. This enables genre-agnostic flexibility.
    
    Attributes:
        id: Unique identifier (e.g., 'ACTOR_001')
        entity_type: Classification enum
        name: Human-readable name
        description: Biography or description text
        aliases: Alternative names for deduplication
        tags: Semantic classification tags
        attributes: Dynamic schema-driven fields (stats, traits, etc.)
        source_documents: List of source file names for provenance
        embedding_row_id: Row ID in sqlite-vec entity_embeddings table
        created_at: Creation timestamp
        updated_at: Last modification timestamp
    """
    
    id: str = Field(
        default_factory=lambda: generate_id("ENTITY"),
        description="Unique entity ID"
    )
    entity_type: EntityType = Field(
        default=EntityType.ABSTRACT,
        description="Type classification"
    )
    name: str = Field(
        default="",
        description="Human-readable name"
    )
    description: str = Field(
        default="",
        description="Biography or description text"
    )
    aliases: list[str] = Field(
        default_factory=list,
        description="Alternative names for matching"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Semantic classification tags"
    )
    
    # Dynamic attributes (the "Blank Canvas")
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Schema-driven dynamic fields"
    )
    
    # Spatial data (optional, for locations/actors)
    location_id: Optional[str] = Field(
        default=None,
        description="Current location entity ID (for actors)"
    )
    region_id: Optional[str] = Field(
        default=None,
        description="Parent region ID (for locations)"
    )
    coordinates: Optional[tuple[float, float]] = Field(
        default=None,
        description="X, Y coordinates for mapping"
    )
    layer: LocationLayer = Field(
        default=LocationLayer.TERRESTRIAL,
        description="Spatial layer"
    )
    
    # Provenance tracking
    source_documents: list[str] = Field(
        default_factory=list,
        description="Source files this entity was extracted from"
    )
    
    # Vector store linking
    embedding_row_id: Optional[int] = Field(
        default=None,
        description="Row ID in sqlite-vec entity_embeddings table"
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
        return f"Entity({self.name or self.id[:8]}, type={self.entity_type.value})"
    
    def __repr__(self) -> str:
        return f"<Entity id={self.id} name={self.name!r} type={self.entity_type.value}>"
    
    def get_attr(self, key: str, default: Any = None) -> Any:
        """Get a dynamic attribute value."""
        return self.attributes.get(key, default)
    
    def set_attr(self, key: str, value: Any) -> None:
        """Set a dynamic attribute value and update timestamp."""
        self.attributes[key] = value
        self.updated_at = datetime.now(UTC)
    
    def get_embedding_text(self) -> str:
        """Generate text representation for embedding.
        
        Combines name, description, aliases, and tags into a single
        string suitable for vectorization.
        """
        parts = [self.name, self.description]
        parts.extend(self.aliases)
        parts.extend(self.tags)
        return " ".join(filter(None, parts))
    
    def to_staging_dict(self) -> dict[str, Any]:
        """Convert to dictionary for staging JSON output."""
        return {
            "id": self.id,
            "entity_type": self.entity_type.value,
            "name": self.name,
            "description": self.description,
            "aliases": self.aliases,
            "tags": self.tags,
            "attributes": self.attributes,
            "location_id": self.location_id,
            "region_id": self.region_id,
            "coordinates": list(self.coordinates) if self.coordinates else None,
            "layer": self.layer.value,
            "source_documents": self.source_documents,
        }
    
    @classmethod
    def from_staging_dict(cls, data: dict[str, Any]) -> "Entity":
        """Create Entity from staging JSON data."""
        # Handle coordinates
        coords = data.get("coordinates")
        if coords and isinstance(coords, (list, tuple)) and len(coords) == 2:
            coords = tuple(coords)
        else:
            coords = None
        
        return cls(
            id=data.get("id", generate_id("ENTITY")),
            entity_type=EntityType(data.get("entity_type", "abstract")),
            name=data.get("name", ""),
            description=data.get("description", ""),
            aliases=data.get("aliases", []),
            tags=data.get("tags", []),
            attributes=data.get("attributes", {}),
            location_id=data.get("location_id"),
            region_id=data.get("region_id"),
            coordinates=coords,
            layer=LocationLayer(data.get("layer", "terrestrial")),
            source_documents=data.get("source_documents", []),
        )


# ============================================================================
# Type-Specific Entity Helpers
# ============================================================================


def create_actor(
    name: str,
    description: str = "",
    attributes: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Entity:
    """Create an Actor entity."""
    return Entity(
        id=generate_id("ACTOR"),
        entity_type=EntityType.ACTOR,
        name=name,
        description=description,
        attributes=attributes or {},
        **kwargs,
    )


def create_polity(
    name: str,
    description: str = "",
    attributes: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Entity:
    """Create a Polity (organization/faction) entity."""
    return Entity(
        id=generate_id("POLITY"),
        entity_type=EntityType.POLITY,
        name=name,
        description=description,
        attributes=attributes or {},
        **kwargs,
    )


def create_location(
    name: str,
    description: str = "",
    coordinates: tuple[float, float] | None = None,
    region_id: str | None = None,
    layer: LocationLayer = LocationLayer.TERRESTRIAL,
    attributes: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Entity:
    """Create a Location entity."""
    return Entity(
        id=generate_id("LOC"),
        entity_type=EntityType.LOCATION,
        name=name,
        description=description,
        coordinates=coordinates,
        region_id=region_id,
        layer=layer,
        attributes=attributes or {},
        **kwargs,
    )


def create_region(
    name: str,
    description: str = "",
    attributes: dict[str, Any] | None = None,
    **kwargs: Any,
) -> Entity:
    """Create a Region entity."""
    return Entity(
        id=generate_id("REGION"),
        entity_type=EntityType.REGION,
        name=name,
        description=description,
        attributes=attributes or {},
        **kwargs,
    )
