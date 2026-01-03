"""PyScrAI Core - Entity-Component-System Foundation.

This package provides the core foundation for PyScrAI simulations:

Models (Entity-Component-System):
- Entity, Polity, Region, Location, Actor - Typed facades
- DescriptorComponent, CognitiveComponent, SpatialComponent, StateComponent
- Relationship - Entity connections

Events (Immutable Facts):
- Event, MovementEvent, ResourceTransferEvent, RelationshipChangeEvent
- CustomEvent, CorrectionEvent, StateChangeEvent
- Turn, NarrativeLogEntry, WorldSnapshot

Intentions (Async Requests):
- Intention, MoveIntention, AttackIntention, ChangeRelationshipIntention
- ResourceTransferIntention, SpeakIntention, CustomIntention

Memory (Perception Cache):
- MemoryChunk, MemoryDomain, MemoryRetrieval, MemoryDivergence

Project Management:
- ProjectManifest, ProjectController, SchemaMigration

ARCHITECTURAL PRINCIPLES:
1. StateComponent is AUTHORITY (truth vs perception)
2. Events are immutable (replay determinism)
3. Intentions are async/fallible (simulation never waits for LLM)
4. Subclasses add behavior, never data (ECS purity)
5. Memory divergence is gameplay signal, not error
"""

# ============================================================================
# Models (Entity-Component-System)
# ============================================================================

from .models import (
    # Enums
    EntityType,
    RelationshipType,
    RelationshipVisibility,
    LocationLayer,
    # Components
    DescriptorComponent,
    CognitiveComponent,
    SpatialComponent,
    StateComponent,
    # Entity classes
    Entity,
    Actor,
    Polity,
    Region,
    Location,
    # Relationships
    Relationship,
    # Helpers
    state_fields,
)

# ============================================================================
# Events (Immutable Facts)
# ============================================================================

from .events import (
    # Base event
    Event,
    # Concrete events
    MovementEvent,
    ResourceTransferEvent,
    RelationshipChangeEvent,
    RelationshipChangeType,
    DiplomaticShiftEvent,  # Alias for backwards compatibility
    CorrectionEvent,
    StateChangeEvent,
    CustomEvent,
    # Temporal containers
    Turn,
    NarrativeLogEntry,
    WorldSnapshot,
    # Registry
    EVENT_TYPES,
    get_event_class,
)

# ============================================================================
# Intentions (Async Requests)
# ============================================================================

from .intentions import (
    # Status
    IntentionStatus,
    # Base intention
    Intention,
    # Concrete intentions
    MoveIntention,
    AttackIntention,
    ChangeRelationshipIntention,
    ResourceTransferIntention,
    SpeakIntention,
    CustomIntention,
    # Result
    IntentionResult,
    # Interface
    IntentionResolver,
    # Registry
    INTENTION_TYPES,
    get_intention_class,
)

# ============================================================================
# Memory (Perception Cache)
# ============================================================================

from .memory import (
    # Enums
    MemoryDomain,
    DivergenceType,
    # Memory models
    MemoryChunk,
    MemoryRetrieval,
    MemoryDivergence,
    MemoryContext,
)

# ============================================================================
# Project Management
# ============================================================================

from .project import (
    ProjectManifest,
    ProjectController,
    SchemaMigration,
)

# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # === Models ===
    # Enums
    "EntityType",
    "RelationshipType",
    "RelationshipVisibility",
    "LocationLayer",
    # Components
    "DescriptorComponent",
    "CognitiveComponent",
    "SpatialComponent",
    "StateComponent",
    # Entity classes
    "Entity",
    "Actor",
    "Polity",
    "Region",
    "Location",
    # Relationships
    "Relationship",
    # Helpers
    "state_fields",
    # === Events ===
    "Event",
    "MovementEvent",
    "ResourceTransferEvent",
    "RelationshipChangeEvent",
    "RelationshipChangeType",
    "DiplomaticShiftEvent",
    "CorrectionEvent",
    "StateChangeEvent",
    "CustomEvent",
    "Turn",
    "NarrativeLogEntry",
    "WorldSnapshot",
    "EVENT_TYPES",
    "get_event_class",
    # === Intentions ===
    "IntentionStatus",
    "Intention",
    "MoveIntention",
    "AttackIntention",
    "ChangeRelationshipIntention",
    "ResourceTransferIntention",
    "SpeakIntention",
    "CustomIntention",
    "IntentionResult",
    "IntentionResolver",
    "INTENTION_TYPES",
    "get_intention_class",
    # === Memory ===
    "MemoryDomain",
    "DivergenceType",
    "MemoryChunk",
    "MemoryRetrieval",
    "MemoryDivergence",
    "MemoryContext",
    # === Project ===
    "ProjectManifest",
    "ProjectController",
    "SchemaMigration",
]

# Version
__version__ = "0.1.0"
