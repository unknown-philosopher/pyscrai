"""
Sentinel - Entity Reconciliation System for Forge 3.0.

The Sentinel aggregates extracted entities across chunks, detects
near-duplicates via embedding similarity, and manages the merge
approval workflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable
from datetime import UTC, datetime

from forge.core.events.mutations import MergeApprovedEvent, MergeRejectedEvent
from forge.core.models.entity import Entity
from forge.core.models.relationship import Relationship
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.phases.p0_extraction.extractor import ExtractionResult
    from forge.systems.memory.vector_memory import VectorMemory

logger = get_logger("p0_extraction.sentinel")


# ============================================================================
# Merge Candidate
# ============================================================================


class MergeDecision(str, Enum):
    """Possible decisions for a merge candidate."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_MERGED = "auto_merged"


@dataclass
class MergeCandidate:
    """A potential merge between two entities.
    
    Attributes:
        entity_a: First entity (typically earlier extraction)
        entity_b: Second entity (typically later extraction)
        similarity: Cosine similarity score (0.0-1.0)
        decision: Current merge decision
        merged_entity: Result of merge if approved
        reason: Reason for the decision
    """
    
    entity_a: Entity
    entity_b: Entity
    similarity: float
    decision: MergeDecision = MergeDecision.PENDING
    merged_entity: Entity | None = None
    reason: str = ""
    
    @property
    def id(self) -> str:
        """Unique identifier for this merge candidate."""
        return f"{self.entity_a.id}:{self.entity_b.id}"
    
    @property
    def is_pending(self) -> bool:
        return self.decision == MergeDecision.PENDING
    
    @property
    def is_resolved(self) -> bool:
        return self.decision != MergeDecision.PENDING


@dataclass
class SentinelStats:
    """Statistics about Sentinel operations."""
    
    total_entities: int = 0
    total_relationships: int = 0
    chunks_processed: int = 0
    merge_candidates: int = 0
    auto_merges: int = 0
    manual_merges: int = 0
    rejected_merges: int = 0
    pending_merges: int = 0


# ============================================================================
# Sentinel
# ============================================================================


class Sentinel:
    """Entity reconciliation and merge management system.
    
    The Sentinel:
    1. Aggregates entities from multiple extraction chunks
    2. Detects near-duplicates via embedding similarity
    3. Auto-merges entities above a high confidence threshold
    4. Queues lower-confidence candidates for human review
    5. Tracks merge decisions in the event log
    
    Usage:
        sentinel = Sentinel(vector_memory)
        
        # Process extraction results
        for result in extraction_results:
            sentinel.ingest_result(result)
        
        # Get merge candidates for review
        for candidate in sentinel.get_pending_merges():
            print(f"Possible duplicate: {candidate.entity_a.name} ~ {candidate.entity_b.name}")
            sentinel.approve_merge(candidate)
        
        # Get final entities and relationships
        entities = sentinel.get_resolved_entities()
        relationships = sentinel.get_resolved_relationships()
    """
    
    def __init__(
        self,
        vector_memory: "VectorMemory",
        similarity_threshold: float = 0.85,
        auto_merge_threshold: float = 0.95,
    ):
        """Initialize the Sentinel.
        
        Args:
            vector_memory: Vector memory for similarity search
            similarity_threshold: Minimum similarity to flag as potential duplicate
            auto_merge_threshold: Similarity above which to auto-merge
        """
        self.memory = vector_memory
        self.similarity_threshold = similarity_threshold
        self.auto_merge_threshold = auto_merge_threshold
        
        # Entity storage by ID
        self._entities: dict[str, Entity] = {}
        
        # Relationships storage by ID
        self._relationships: dict[str, Relationship] = {}
        
        # Merge candidates
        self._merge_candidates: dict[str, MergeCandidate] = {}
        
        # Tracking
        self._chunks_processed: int = 0
        self._auto_merges: int = 0
        self._events: list[Any] = []
    
    def ingest_result(self, result: "ExtractionResult") -> None:
        """Ingest an extraction result into the Sentinel.
        
        Args:
            result: Extraction result from a chunk
        """
        if not result.success:
            logger.warning(f"Skipping failed extraction from chunk {result.chunk_index}")
            return
        
        self._chunks_processed += 1
        
        # Process entities
        for entity in result.entities:
            self._ingest_entity(entity)
        
        # Process relationships (after entities so we can validate)
        for relationship in result.relationships:
            self._ingest_relationship(relationship)
        
        logger.debug(
            f"Ingested chunk {result.chunk_index}: "
            f"{len(result.entities)} entities, {len(result.relationships)} relationships"
        )
    
    def _ingest_entity(self, entity: Entity) -> None:
        """Ingest a single entity, checking for duplicates.
        
        Args:
            entity: Entity to ingest
        """
        # Check for near-duplicates using vector similarity
        # Create text representation of entity for similarity search
        entity_text = f"{entity.name} {entity.description}"
        duplicates = self.memory.find_near_duplicates(
            text=entity_text,
            threshold=self.similarity_threshold,
        )
        
        if duplicates:
            # Check highest similarity match
            best_match = duplicates[0]
            best_match_id = best_match.entity_id
            similarity = best_match.similarity
            
            if best_match_id in self._entities:
                existing = self._entities[best_match_id]
                
                if similarity >= self.auto_merge_threshold:
                    # Auto-merge
                    merged = self._merge_entities(existing, entity)
                    self._entities[existing.id] = merged
                    self._auto_merges += 1
                    
                    logger.debug(
                        f"Auto-merged '{entity.name}' into '{existing.name}' "
                        f"(similarity: {similarity:.3f})"
                    )
                    return
                else:
                    # Create merge candidate for review
                    candidate = MergeCandidate(
                        entity_a=existing,
                        entity_b=entity,
                        similarity=similarity,
                    )
                    
                    # Avoid duplicate candidates
                    if candidate.id not in self._merge_candidates:
                        self._merge_candidates[candidate.id] = candidate
                        logger.debug(
                            f"Created merge candidate: '{existing.name}' ~ '{entity.name}' "
                            f"(similarity: {similarity:.3f})"
                        )
        
        # Add entity to storage
        self._entities[entity.id] = entity
        
        # Add to vector memory
        self.memory.add_entity(entity)
    
    def _ingest_relationship(self, relationship: Relationship) -> None:
        """Ingest a relationship.
        
        Args:
            relationship: Relationship to ingest
        """
        # Validate that both entities exist
        if relationship.source_id not in self._entities:
            logger.debug(f"Skipping relationship: source {relationship.source_id} not found")
            return
        
        if relationship.target_id not in self._entities:
            logger.debug(f"Skipping relationship: target {relationship.target_id} not found")
            return
        
        # Check for duplicate relationships
        existing_key = f"{relationship.source_id}:{relationship.target_id}:{relationship.type.value}"
        for rel in self._relationships.values():
            key = f"{rel.source_id}:{rel.target_id}:{rel.type.value}"
            if key == existing_key:
                # Merge relationship descriptions
                if relationship.description and relationship.description not in rel.description:
                    rel.description = f"{rel.description}; {relationship.description}"
                return
        
        self._relationships[relationship.id] = relationship
    
    def _merge_entities(self, primary: Entity, secondary: Entity) -> Entity:
        """Merge two entities, preserving information from both.
        
        Args:
            primary: Entity to keep as base
            secondary: Entity to merge into primary
            
        Returns:
            Merged entity
        """
        # Combine aliases
        combined_aliases = list(set(primary.aliases + secondary.aliases + [secondary.name]))
        if primary.name in combined_aliases:
            combined_aliases.remove(primary.name)
        
        # Merge descriptions
        if secondary.description and secondary.description not in primary.description:
            merged_description = f"{primary.description}\n{secondary.description}".strip()
        else:
            merged_description = primary.description
        
        # Merge attributes
        merged_attributes = {**secondary.attributes, **primary.attributes}
        
        # Combine provenance
        merged_provenance = list(set(primary.provenance + secondary.provenance))
        
        return Entity(
            id=primary.id,
            name=primary.name,
            type=primary.type,
            description=merged_description,
            aliases=combined_aliases,
            attributes=merged_attributes,
            provenance=merged_provenance,
            created_at=primary.created_at,
            updated_at=datetime.now(UTC),
            embedding_row_id=primary.embedding_row_id,
        )
    
    # ========== Merge Workflow ==========
    
    def get_pending_merges(self) -> list[MergeCandidate]:
        """Get all pending merge candidates.
        
        Returns:
            List of pending merge candidates, sorted by similarity descending
        """
        pending = [c for c in self._merge_candidates.values() if c.is_pending]
        return sorted(pending, key=lambda c: c.similarity, reverse=True)
    
    def approve_merge(
        self,
        candidate: MergeCandidate,
        reason: str = "User approved",
    ) -> Entity:
        """Approve a merge candidate.
        
        Args:
            candidate: The merge candidate to approve
            reason: Reason for approval
            
        Returns:
            The merged entity
        """
        merged = self._merge_entities(candidate.entity_a, candidate.entity_b)
        
        # Update storage
        self._entities[candidate.entity_a.id] = merged
        if candidate.entity_b.id in self._entities:
            del self._entities[candidate.entity_b.id]
        
        # Update candidate
        candidate.decision = MergeDecision.APPROVED
        candidate.merged_entity = merged
        candidate.reason = reason
        
        # Log event
        event = MergeApprovedEvent(
            entity_id=merged.id,
            merged_ids=[candidate.entity_a.id, candidate.entity_b.id],
            details={"reason": reason, "similarity": candidate.similarity},
        )
        self._events.append(event)
        
        logger.info(
            f"Merge approved: '{candidate.entity_a.name}' + '{candidate.entity_b.name}'"
        )
        
        return merged
    
    def reject_merge(
        self,
        candidate: MergeCandidate,
        reason: str = "User rejected",
    ) -> None:
        """Reject a merge candidate.
        
        Args:
            candidate: The merge candidate to reject
            reason: Reason for rejection
        """
        candidate.decision = MergeDecision.REJECTED
        candidate.reason = reason
        
        # Log event
        event = MergeRejectedEvent(
            entity_id=candidate.entity_a.id,
            rejected_id=candidate.entity_b.id,
            details={"reason": reason, "similarity": candidate.similarity},
        )
        self._events.append(event)
        
        logger.info(
            f"Merge rejected: '{candidate.entity_a.name}' ≠ '{candidate.entity_b.name}'"
        )
    
    # ========== Output ==========
    
    def get_resolved_entities(self) -> list[Entity]:
        """Get all resolved entities.
        
        Returns:
            List of entities after merge resolution
        """
        return list(self._entities.values())
    
    def get_resolved_relationships(self) -> list[Relationship]:
        """Get all resolved relationships.
        
        Returns:
            List of relationships
        """
        return list(self._relationships.values())
    
    def get_events(self) -> list[Any]:
        """Get all recorded events."""
        return self._events.copy()
    
    def get_stats(self) -> SentinelStats:
        """Get Sentinel statistics.
        
        Returns:
            SentinelStats object
        """
        pending = sum(1 for c in self._merge_candidates.values() if c.is_pending)
        approved = sum(1 for c in self._merge_candidates.values() if c.decision == MergeDecision.APPROVED)
        rejected = sum(1 for c in self._merge_candidates.values() if c.decision == MergeDecision.REJECTED)
        
        return SentinelStats(
            total_entities=len(self._entities),
            total_relationships=len(self._relationships),
            chunks_processed=self._chunks_processed,
            merge_candidates=len(self._merge_candidates),
            auto_merges=self._auto_merges,
            manual_merges=approved,
            rejected_merges=rejected,
            pending_merges=pending,
        )
    
    # ========== Persistence ==========
    
    def to_staging_dict(self) -> dict:
        """Export Sentinel state to staging format.
        
        Returns:
            Dictionary suitable for JSON serialization
        """
        return {
            "entities": [e.to_staging_dict() for e in self._entities.values()],
            "relationships": [r.to_staging_dict() for r in self._relationships.values()],
            "merge_candidates": [
                {
                    "entity_a_id": c.entity_a.id,
                    "entity_b_id": c.entity_b.id,
                    "similarity": c.similarity,
                    "decision": c.decision.value,
                    "reason": c.reason,
                }
                for c in self._merge_candidates.values()
            ],
            "stats": {
                "chunks_processed": self._chunks_processed,
                "auto_merges": self._auto_merges,
            },
        }
    
    def clear(self) -> None:
        """Clear all Sentinel state."""
        self._entities.clear()
        self._relationships.clear()
        self._merge_candidates.clear()
        self._chunks_processed = 0
        self._auto_merges = 0
        self._events.clear()
        self.memory.clear()
