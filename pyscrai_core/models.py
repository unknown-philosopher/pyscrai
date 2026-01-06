"""Core entity and component models for PyScrAI.

This module defines the Entity-Component-System (ECS) architecture.
All persistent state lives in Components. Entity classes are typed facades with behavior.

AUTHORITY: StateComponent is the singular source of truth.
MemoryChunk perception may diverge; conflicts indicate misinformation, espionage, or fog-of-war.

DESIGN PHILOSOPHY: "Blank Canvas" Architecture
==============================================
This module is genre-agnostic. It does NOT enforce specific simulation mechanics.
Instead, it provides the containers (`resources_json`) and infrastructure (`region_version`)
necessary for any simulation.

- **Project-Defined Schema**: The specific stats (treasury, mana, hull_integrity) are defined
  in the `ProjectManifest`, not here.
- **Dynamic State**: The `StateComponent` is a flexible container.
"""

import json
import re
import threading
from datetime import UTC, datetime
from pathlib import Path
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator
# ============================================================================
# Enums and Type Definitions
# ============================================================================

# Intuitive ID generator (thread-safe, per type)
_id_counters: dict[str, int] = {}
_id_lock = threading.Lock()
_id_counters_path: Path | None = None
_id_pattern = re.compile(r"^(?P<prefix>[A-Za-z]+)_0*(?P<num>\d+)$")
def generate_intuitive_id(prefix: str) -> str:
    with _id_lock:
        if prefix not in _id_counters:
            _id_counters[prefix] = 1
        else:
            _id_counters[prefix] += 1
        # Persist counters if path configured
        if _id_counters_path:
            try:
                _id_counters_path.write_text(json.dumps(_id_counters), encoding="utf-8")
            except Exception:
                pass
        return f"{prefix}_{_id_counters[prefix]:03d}"


def set_id_counters_path(path: str | Path) -> None:
    """Configure a JSON file path to persist ID counters across runs.

    When set, the file will be loaded if present and written each time a counter
    is incremented.
    """
    global _id_counters_path, _id_counters
    p = Path(path)
    _id_counters_path = p
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            # normalize to ints
            _id_counters = {str(k): int(v) for k, v in data.items()}
        except Exception:
            _id_counters = {}


def seed_id_counter_from_value(id_value: str) -> None:
    """Raise the counter for a prefix based on an existing ID value.

    Accepts IDs like REL_005 or rel_005; updates the counter so future
    generate_intuitive_id calls continue sequentially. No-op on parse failures.
    """
    match = _id_pattern.match(id_value)
    if not match:
        return

    prefix = match.group("prefix").upper()
    num = int(match.group("num"))

    with _id_lock:
        current = _id_counters.get(prefix, 0)
        if num > current:
            _id_counters[prefix] = num
            if _id_counters_path:
                try:
                    _id_counters_path.write_text(json.dumps(_id_counters), encoding="utf-8")
                except Exception:
                    pass


class EntityType(str, Enum):
    """Type classification for entities."""
    ACTOR = "actor"  # Individual
    POLITY = "polity"  # Collective
    LOCATION = "location"  # Place
    REGION = "region"  # Container
    RESOURCE = "resource"  # Asset
    EVENT = "event"  # Occurrence
    ABSTRACT = "abstract"  # Conceptual


class RelationshipType(str, Enum):
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
    CUSTOM = "custom"


class RelationshipVisibility(str, Enum):
    """Visibility level of a relationship."""
    PUBLIC = "public"
    PRIVATE = "private"
    SECRET = "secret"
    CLASSIFIED = "classified"


class LocationLayer(str, Enum):
    """Spatial layer for locations."""
    TERRESTRIAL = "terrestrial"
    ORBITAL = "orbital"
    SUBTERRANEAN = "subterranean"
    AQUATIC = "aquatic"
    VIRTUAL = "virtual"
    ABSTRACT = "abstract"


# ============================================================================
# Components (ECS Architecture)
# ============================================================================


class DescriptorComponent(BaseModel):
    """Semantic identity and classification metadata."""
    name: str = Field(default="", description="Human-readable name")
    bio: str = Field(default="", description="Biography or description text")
    tags: list[str] = Field(default_factory=list, description="Semantic tags")
    entity_type: EntityType = Field(default=EntityType.ABSTRACT, description="Type classification")

    class Config:
        frozen = False


class CognitiveComponent(BaseModel):
    """Decision-making and reasoning configuration."""
    model_id: str = Field(default="", description="LLM model identifier")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="AI temperature setting")
    system_prompt: str = Field(default="", description="System prompt for AI behavior")
    context_policy: str = Field(default="rolling_summary", description="Context window policy")
    max_context_tokens: Optional[int] = Field(default=None, description="Max context tokens")
    response_style: Optional[str] = Field(default=None, description="Output style hint")

    class Config:
        frozen = False


class SpatialComponent(BaseModel):
    """Physical or topological placement."""
    x: float = Field(default=0.0, description="X coordinate")
    y: float = Field(default=0.0, description="Y coordinate")
    region_id: Optional[str] = Field(default=None, description="Parent region identifier")
    current_location_id: Optional[str] = Field(default=None, description="Current location entity ID (for actors)")
    layer: LocationLayer = Field(default=LocationLayer.TERRESTRIAL, description="Spatial layer")
    capacity: Optional[int] = Field(default=None, description="Occupancy capacity")

    class Config:
        frozen = False


class StateComponent(BaseModel):
    """Mutable quantitative variables associated with an entity.

    AUTHORITY: This is the singular source of truth.

    Design: Project-Defined "Blank Canvas"
    ======================================
    This component does NOT enforce hardcoded stats like 'treasury' or 'health'.
    Instead, it uses `resources_json` as a flexible container.
    
    The structure of `resources_json` is defined by the `ProjectManifest` schema.
    
    Performance-Critical Fields:
    We keep Region optimization fields here as explicit properties because they are
    needed for the core pathfinding engine (O(1) access), regardless of genre.
    """

    resources_json: str = Field(
        default="{}",
        description="JSON string for project-specific dynamic stats (gold, mana, health, etc.)",
    )
    
    # Region-specific optimization (O(1) access required for engine)
    region_version: Optional[int] = Field(
        default=None, ge=1, description="Graph structural version"
    )
    adjacency_json: Optional[str] = Field(
        default=None, description="Serialized adjacency graph"
    )
    travel_times_json: Optional[str] = Field(
        default=None, description="Serialized precomputed travel times"
    )

    @property
    def resources(self) -> dict[str, Any]:
        """Get resources as dictionary."""
        try:
            return json.loads(self.resources_json) if self.resources_json else {}
        except json.JSONDecodeError:
            return {}

    @resources.setter
    def resources(self, value: dict[str, Any]) -> None:
        """Set resources from dictionary."""
        self.resources_json = json.dumps(value)

    class Config:
        frozen = False

    @field_validator("resources_json")
    @classmethod
    def validate_resources_json(cls, v: str) -> str:
        """Validate that resources_json is valid JSON."""
        if v:
            try:
                json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("resources_json must be valid JSON")
        return v


# ============================================================================
# Entity Base Class
# ============================================================================


class Entity(BaseModel):
    """Base entity class in the ECS architecture."""
    id: str = Field(default_factory=lambda: generate_intuitive_id("ENTITY"), description="Unique entity ID")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    descriptor: Optional[DescriptorComponent] = None
    cognitive: Optional[CognitiveComponent] = None
    spatial: Optional[SpatialComponent] = None
    state: Optional[StateComponent] = None

    class Config:
        frozen = False

    def __str__(self) -> str:
        name = self.descriptor.name if self.descriptor else self.id[:8]
        return f"Entity({name}, {self.id[:8]}...)"


# ============================================================================
# Entity Subclasses (Typed Facades)
# ============================================================================


class Actor(Entity):
    """Individual agent.
    
    Note: Facade properties (health, etc.) are removed to enforce dynamic schema.
    Access stats via `self.state.resources.get('health')` or helper methods.
    """
    
    def get_stat(self, key: str, default: Any = 0) -> Any:
        """Helper to access dynamic stats."""
        if not self.state:
            return default
        return self.state.resources.get(key, default)


class Polity(Entity):
    """Collective organization.
    
    Note: Facade properties (treasury, etc.) are removed to enforce dynamic schema.
    """
    
    def get_stat(self, key: str, default: Any = 0) -> Any:
        """Helper to access dynamic stats."""
        if not self.state:
            return default
        return self.state.resources.get(key, default)


class Region(Entity):
    """Logical container of Locations with versioned connectivity."""

    @property
    def region_version(self) -> int:
        if self.state is None:
            return 1
        return self.state.region_version if self.state.region_version is not None else 1

    @property
    def adjacency(self) -> str:
        if self.state is None:
            return "{}"
        return self.state.adjacency_json if self.state.adjacency_json is not None else "{}"

    @property
    def travel_times(self) -> str:
        if self.state is None:
            return "{}"
        return self.state.travel_times_json if self.state.travel_times_json is not None else "{}"


class Location(Entity):
    """Spatial anchor."""

    @property
    def region_id(self) -> Optional[str]:
        if self.spatial is None:
            return None
        return self.spatial.region_id

    @property
    def position(self) -> tuple[float, float]:
        if self.spatial is None:
            return (0.0, 0.0)
        return (self.spatial.x, self.spatial.y)

    @property
    def layer(self) -> LocationLayer:
        if self.spatial is None:
            return LocationLayer.TERRESTRIAL
        return self.spatial.layer


# ============================================================================
# Relationship Model
# ============================================================================


class Relationship(BaseModel):
    """Relationship between two entities."""
    id: str = Field(default_factory=lambda: generate_intuitive_id("REL"))
    source_id: str = Field(description="Source entity ID")
    target_id: str = Field(description="Target entity ID")
    relationship_type: RelationshipType = Field(description="Type of relationship")
    visibility: RelationshipVisibility = Field(default=RelationshipVisibility.PUBLIC)
    strength: float = Field(default=1.0, ge=-1.0, le=1.0)
    description: str = Field(default="", description="Human-readable description of the relationship")
    metadata: str = Field(default="{}")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        frozen = False

    @property
    def metadata_dict(self) -> dict[str, Any]:
        try:
            return json.loads(self.metadata) if self.metadata else {}
        except json.JSONDecodeError:
            return {}


def state_fields() -> set[str]:
    """List of authoritative state fields (now minimal)."""
    return {
        "resources_json",
        "region_version",
        "adjacency_json",
        "travel_times_json",
    }