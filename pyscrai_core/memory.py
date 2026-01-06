"""Memory models for PyScrAI.

This module defines semantic memory with domain classification.

Guardrail 2: StateComponent Is Authority
> StateComponent is the singular source of truth for all quantitative facts (in `resources_json`).
> MemoryChunk is perception, subjective, lossy, and contextual.

Guardrail 5: Memory Coherence as Gameplay Signal
> Divergence between StateComponent and MemoryChunk is information, not failure.
> Example: Agent believes 'gold' = 100, Reality 'gold' = 0.
"""

from .models import generate_intuitive_id
from datetime import UTC, datetime
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, Field


# ============================================================================
# Memory Domain Categories
# ============================================================================


class MemoryDomain(str, Enum):
    """Core memory categories. Non-removable."""
    IDENTITY = "self"
    ASSOCIATES = "actors"
    HISTORY = "timeline"
    MOTIVATION = "goals"
    BELIEFS = "ideology"
    KNOWLEDGE = "facts"
    SECRETS = "secrets"


# ============================================================================
# Memory Chunk (Perception, Subjective)
# ============================================================================


class MemoryChunk(BaseModel):
    """Semantic memory entry. Subjective, lossy, contextual.

    Never authoritative. Represents what an entity BELIEVES.
    Stored in ChromaDB.
    """

    id: str = Field(default_factory=lambda: generate_intuitive_id("MEM"), description="Unique memory ID")
    owner_id: str = Field(description="Actor/Polity who holds this memory")
    domain: MemoryDomain = Field(description="Memory category")
    tags: list[str] = Field(default_factory=list, description="Extensible semantic tags")
    content: str = Field(description="Text content to embed")
    embedding: list[float] = Field(
        default_factory=list, description="Vector embedding"
    )
    source_events: list[str] = Field(
        default_factory=list, description="Event IDs that generated this memory"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="When memory was formed"
    )
    last_recalled_at: Optional[datetime] = Field(
        default=None, description="Last time memory was retrieved"
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Certainty (0.0-1.0)"
    )
    importance: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Strategic significance"
    )
    access_count: int = Field(default=0, ge=0)
    decay_rate: float = Field(default=0.0, ge=0.0, le=1.0)

    class Config:
        frozen = False

    def recall(self) -> None:
        self.last_recalled_at = datetime.now(UTC)
        self.access_count += 1

    def decay(self, ticks_elapsed: int) -> None:
        if self.decay_rate > 0 and ticks_elapsed > 0:
            decay_factor = (1 - self.decay_rate) ** ticks_elapsed
            self.confidence = max(0.0, self.confidence * decay_factor)


# ============================================================================
# Memory Retrieval Result
# ============================================================================


class MemoryRetrieval(BaseModel):
    """Query result from semantic memory."""
    query: str
    domain: Optional[MemoryDomain] = None
    results: list[MemoryChunk] = Field(default_factory=list)
    note: str = Field(
        default="Perception may diverge from StateComponent resources",
        description="Reminder regarding subjective nature of memory"
    )

    class Config:
        frozen = False


# ============================================================================
# Memory Divergence Tracking
# ============================================================================


class DivergenceType(str, Enum):
    """Classification of perception vs reality mismatch."""
    FOG_OF_WAR = "fog_of_war"
    ESPIONAGE = "espionage"
    IDEOLOGICAL_DRIFT = "ideological_drift"
    PERCEPTION_ERROR = "perception_error"
    OUTDATED = "outdated"
    DECEPTION = "deception"


class MemoryDivergence(BaseModel):
    """Tracks perception vs reality mismatch.

    This maps a belief in `MemoryChunk` against the Project-Defined Schema in `StateComponent`.

    Example:
        divergence = MemoryDivergence(
            actor_id="actor_123",
            memory_id="mem_456",
            state_field="credits",  # Dynamic field from Project Schema
            believed_value=1000.0,
            actual_value=250.0,
            divergence_type=DivergenceType.ESPIONAGE
        )
    """

    id: str = Field(default_factory=lambda: generate_intuitive_id("DIV"))
    actor_id: str = Field(description="Entity with divergent perception")
    memory_id: str = Field(description="MemoryChunk containing false belief")
    state_field: str = Field(description="Key in resources_json that diverges")
    believed_value: str = Field(description="What actor believes (JSON serialized)")
    actual_value: str = Field(description="What resources_json contains (JSON serialized)")
    divergence_type: DivergenceType = Field(description="Classification")
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    severity: float = Field(default=0.5, ge=0.0, le=1.0)
    is_resolved: bool = Field(default=False)
    resolved_at: Optional[datetime] = None

    class Config:
        frozen = False

    def resolve(self) -> None:
        self.is_resolved = True
        self.resolved_at = datetime.now(UTC)


# ============================================================================
# Memory Context Builder
# ============================================================================


class MemoryContext(BaseModel):
    """Aggregated memory context for LLM prompting."""
    owner_id: str
    identity_memories: list[MemoryChunk] = Field(default_factory=list)
    relevant_memories: list[MemoryChunk] = Field(default_factory=list)
    relationship_memories: list[MemoryChunk] = Field(default_factory=list)
    goal_memories: list[MemoryChunk] = Field(default_factory=list)
    total_tokens_estimate: int = Field(default=0)

    class Config:
        frozen = False

    def to_prompt_text(self) -> str:
        sections = []
        if self.identity_memories:
            sections.append("## Who You Are")
            for mem in self.identity_memories:
                sections.append(f"- {mem.content}")
        if self.goal_memories:
            sections.append("\n## Your Goals")
            for mem in self.goal_memories:
                sections.append(f"- {mem.content}")
        if self.relationship_memories:
            sections.append("\n## People You Know")
            for mem in self.relationship_memories:
                sections.append(f"- {mem.content}")
        if self.relevant_memories:
            sections.append("\n## Relevant Information")
            for mem in self.relevant_memories:
                sections.append(f"- {mem.content}")
        return "\n".join(sections)