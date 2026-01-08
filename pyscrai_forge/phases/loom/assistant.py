"""Loom Assistant - Relationship Validation and Suggestions using Semantic Embeddings.

This module provides the LoomAssistant class that uses Sentence Transformers
embeddings to validate relationships, suggest missing relationships, and detect
potential relationship conflicts.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pyscrai_core import Entity, Relationship

# Import at runtime to avoid circular dependencies
try:
    from pyscrai_core.memory_service import MemoryService
except ImportError:
    MemoryService = None

logger = logging.getLogger(__name__)


@dataclass
class RelationshipSuggestion:
    """A suggested relationship between two entities."""
    source_id: str
    target_id: str
    relationship_type: str
    confidence: float  # 0.0 to 1.0
    reasoning: str
    evidence: str  # Quote or context from entity descriptions


@dataclass
class RelationshipConflict:
    """A detected conflict in relationships."""
    relationship1: "Relationship"
    relationship2: "Relationship"
    conflict_type: str  # "contradiction", "duplicate", "inconsistency"
    description: str
    suggestion: str


@dataclass
class MissingRelationship:
    """A potentially missing relationship detected by semantic analysis."""
    source_id: str
    target_id: str
    suggested_type: str
    confidence: float
    reasoning: str
    context_evidence: str


class LoomAssistant:
    """Assistant for Loom phase that validates and suggests relationships using semantic embeddings.
    
    Uses Sentence Transformers to:
    - Validate relationships against entity descriptions
    - Suggest missing relationships based on semantic context
    - Detect relationship conflicts and inconsistencies
    """
    
    def __init__(self, memory_service=None):
        """Initialize the LoomAssistant.
        
        Args:
            memory_service: MemoryService instance for embedding calculations
        """
        self.memory_service = memory_service
    
    def validate_relationship(
        self,
        relationship: "Relationship",
        source_entity: "Entity",
        target_entity: "Entity"
    ) -> tuple[bool, str]:
        """Validate a relationship against entity descriptions using semantic similarity.
        
        Args:
            relationship: Relationship to validate
            source_entity: Source entity
            target_entity: Target entity
            
        Returns:
            Tuple of (is_valid, reason)
        """
        if not self.memory_service or not self.memory_service.embedding:
            return True, ""  # Can't validate without embeddings
        
        # Build context for source and target
        source_context = self._entity_to_context_text(source_entity)
        target_context = self._entity_to_context_text(target_entity)
        
        # Check if relationship type makes semantic sense
        rel_type = relationship.relationship_type.value if hasattr(relationship.relationship_type, 'value') else str(relationship.relationship_type)
        
        # For MEMBER_OF relationships, verify target is mentioned in source's bio
        if rel_type.upper() == "MEMBER_OF":
            source_bio = self._get_entity_bio(source_entity).lower()
            target_name = self._get_entity_name(target_entity).lower()
            
            if target_name and target_name not in source_bio:
                return False, f"Target '{target_entity.descriptor.name if target_entity.descriptor else target_entity.id}' not mentioned in source entity's bio"
        
        # For KNOWS/WORKS_WITH relationships, check for explicit evidence
        if rel_type.upper() in ["KNOWS", "WORKS_WITH", "ALLIED_WITH"]:
            source_bio = self._get_entity_bio(source_entity).lower()
            target_name = self._get_entity_name(target_entity).lower()
            
            knows_keywords = ["knows", "works with", "colleague", "ally", "partner", "friend", "associate"]
            has_evidence = any(kw in source_bio for kw in knows_keywords) and target_name in source_bio
            
            if not has_evidence:
                return False, f"No explicit evidence of '{rel_type}' relationship in source entity's bio"
        
        # For LOCATED_IN relationships, verify location context
        if rel_type.upper() == "LOCATED_IN":
            source_bio = self._get_entity_bio(source_entity).lower()
            target_name = self._get_entity_name(target_entity).lower()
            
            location_keywords = ["located", "in", "at", "near", "within", "inside"]
            has_location_context = any(kw in source_bio for kw in location_keywords)
            
            if not has_location_context and target_name not in source_bio:
                return False, f"No location context found linking source to target"
        
        return True, ""
    
    def suggest_missing_relationships(
        self,
        entities: List["Entity"],
        existing_relationships: List["Relationship"],
        similarity_threshold: float = 0.85
    ) -> List[MissingRelationship]:
        """Suggest potentially missing relationships based on semantic context.
        
        Args:
            entities: List of all entities
            existing_relationships: List of existing relationships
            similarity_threshold: Minimum similarity to suggest relationship
            
        Returns:
            List of MissingRelationship suggestions
        """
        if not self.memory_service or not self.memory_service.embedding:
            return []
        
        if len(entities) < 2:
            return []
        
        suggestions = []
        
        # Build set of existing relationship pairs
        existing_pairs = set()
        for rel in existing_relationships:
            existing_pairs.add((rel.source_id, rel.target_id))
            existing_pairs.add((rel.target_id, rel.source_id))  # Bidirectional
        
        # Compare all entity pairs
        for i, source in enumerate(entities):
            source_context = self._entity_to_context_text(source)
            source_embedding = self.memory_service.embedding.encode(source_context)
            if not source_embedding:
                continue
            
            source_bio = self._get_entity_bio(source).lower()
            
            for j, target in enumerate(entities):
                if i >= j:  # Avoid duplicates
                    continue
                
                # Skip if relationship already exists
                if (source.id, target.id) in existing_pairs:
                    continue
                
                target_context = self._entity_to_context_text(target)
                target_embedding = self.memory_service.embedding.encode(target_context)
                if not target_embedding:
                    continue
                
                # Calculate semantic similarity
                similarity = self._cosine_similarity(source_embedding, target_embedding)
                
                if similarity >= similarity_threshold:
                    # Determine relationship type based on context
                    rel_type = self._infer_relationship_type(source, target, source_bio)
                    
                    if rel_type:
                        target_name = self._get_entity_name(target).lower()
                        evidence = self._extract_evidence(source_bio, target_name)
                        
                        suggestions.append(MissingRelationship(
                            source_id=source.id,
                            target_id=target.id,
                            suggested_type=rel_type,
                            confidence=similarity,
                            reasoning=f"High semantic similarity ({similarity*100:.1f}%) suggests {rel_type} relationship",
                            context_evidence=evidence
                        ))
        
        return suggestions
    
    def detect_relationship_conflicts(
        self,
        relationships: List["Relationship"],
        entities: List["Entity"]
    ) -> List[RelationshipConflict]:
        """Detect conflicts and inconsistencies in relationships.
        
        Args:
            relationships: List of relationships to check
            entities: List of entities
            
        Returns:
            List of RelationshipConflict objects
        """
        if not relationships or len(relationships) < 2:
            return []
        
        conflicts = []
        entity_map = {e.id: e for e in entities}
        
        # Check for duplicate relationships
        seen_pairs = {}
        for rel in relationships:
            pair = (rel.source_id, rel.target_id)
            if pair in seen_pairs:
                conflicts.append(RelationshipConflict(
                    relationship1=seen_pairs[pair],
                    relationship2=rel,
                    conflict_type="duplicate",
                    description=f"Duplicate relationship: {rel.source_id} -> {rel.target_id}",
                    suggestion="Remove one of the duplicate relationships"
                ))
            else:
                seen_pairs[pair] = rel
        
        # Check for contradictory relationships
        for i, rel1 in enumerate(relationships):
            for j, rel2 in enumerate(relationships[i+1:], start=i+1):
                # Check if same pair with different types
                if (rel1.source_id == rel2.source_id and rel1.target_id == rel2.target_id) or \
                   (rel1.source_id == rel2.target_id and rel1.target_id == rel2.source_id):
                    
                    rel1_type = rel1.relationship_type.value if hasattr(rel1.relationship_type, 'value') else str(rel1.relationship_type)
                    rel2_type = rel2.relationship_type.value if hasattr(rel2.relationship_type, 'value') else str(rel2.relationship_type)
                    
                    if rel1_type != rel2_type:
                        # Check if types are contradictory
                        if self._are_contradictory(rel1_type, rel2_type):
                            conflicts.append(RelationshipConflict(
                                relationship1=rel1,
                                relationship2=rel2,
                                conflict_type="contradiction",
                                description=f"Contradictory relationship types: {rel1_type} vs {rel2_type}",
                                suggestion="Review and resolve the contradiction"
                            ))
        
        # Check for relationships that don't match entity descriptions
        for rel in relationships:
            source = entity_map.get(rel.source_id)
            target = entity_map.get(rel.target_id)
            
            if source and target:
                is_valid, reason = self.validate_relationship(rel, source, target)
                if not is_valid:
                    conflicts.append(RelationshipConflict(
                        relationship1=rel,
                        relationship2=rel,  # Self-conflict
                        conflict_type="inconsistency",
                        description=reason,
                        suggestion="Review relationship against entity descriptions"
                    ))
        
        return conflicts
    
    def _infer_relationship_type(
        self,
        source: "Entity",
        target: "Entity",
        source_bio: str
    ) -> Optional[str]:
        """Infer relationship type from entity context.
        
        Args:
            source: Source entity
            target: Target entity
            source_bio: Source entity's bio text
            
        Returns:
            Suggested relationship type or None
        """
        target_name = self._get_entity_name(target).lower()
        source_type = self._get_entity_type(source)
        target_type = self._get_entity_type(target)
        
        # Check for MEMBER_OF patterns
        member_keywords = ["member of", "in the", "part of", "belongs to", "serves in"]
        if any(kw in source_bio for kw in member_keywords) and target_name in source_bio:
            if target_type == "polity" or "organization" in target_name or "faction" in target_name:
                return "MEMBER_OF"
        
        # Check for LOCATED_IN patterns
        location_keywords = ["located in", "in", "at", "near", "within"]
        if any(kw in source_bio for kw in location_keywords) and target_name in source_bio:
            if target_type == "location" or "outpost" in target_name or "base" in target_name:
                return "LOCATED_IN"
        
        # Check for KNOWS patterns
        knows_keywords = ["knows", "colleague", "friend", "associate"]
        if any(kw in source_bio for kw in knows_keywords) and target_name in source_bio:
            return "KNOWS"
        
        # Check for OWNS patterns
        owns_keywords = ["owns", "possesses", "controls"]
        if any(kw in source_bio for kw in owns_keywords) and target_name in source_bio:
            return "OWNS"
        
        return None
    
    def _are_contradictory(self, type1: str, type2: str) -> bool:
        """Check if two relationship types are contradictory.
        
        Args:
            type1: First relationship type
            type2: Second relationship type
            
        Returns:
            True if types are contradictory
        """
        contradictions = {
            "ENEMY_OF": {"ALLIED_WITH", "FRIEND"},
            "ALLIED_WITH": {"ENEMY_OF"},
            "OWNS": {"OWNS"},  # Can't own the same thing twice (usually)
        }
        
        type1_upper = type1.upper()
        type2_upper = type2.upper()
        
        return type1_upper in contradictions and type2_upper in contradictions[type1_upper]
    
    def _extract_evidence(self, bio: str, target_name: str) -> str:
        """Extract evidence sentence from bio.
        
        Args:
            bio: Entity bio text
            target_name: Target entity name
            
        Returns:
            Evidence sentence or empty string
        """
        if not target_name or target_name not in bio:
            return ""
        
        # Find sentence containing target name
        sentences = bio.split('.')
        for sentence in sentences:
            if target_name in sentence.lower():
                return sentence.strip() + "."
        
        return ""
    
    def _entity_to_context_text(self, entity: "Entity") -> str:
        """Convert entity to context text for embedding.
        
        Args:
            entity: Entity to convert
            
        Returns:
            Text representation of entity context
        """
        parts = []
        
        if hasattr(entity, "descriptor") and entity.descriptor:
            desc = entity.descriptor
            if hasattr(desc, "name") and desc.name:
                parts.append(desc.name)
            if hasattr(desc, "description") and desc.description:
                parts.append(desc.description)
            if hasattr(desc, "bio") and desc.bio:
                parts.append(desc.bio)
            if hasattr(desc, "aliases") and desc.aliases:
                parts.extend(desc.aliases)
        
        # Add state information if available
        if hasattr(entity, "state") and entity.state:
            if hasattr(entity.state, "resources") and entity.state.resources:
                for key, value in entity.state.resources.items():
                    if isinstance(value, (str, int, float)) and len(str(value)) < 100:
                        parts.append(f"{key}: {value}")
        
        return " ".join(str(p) for p in parts if p)
    
    def _get_entity_name(self, entity: "Entity") -> str:
        """Get entity name.
        
        Args:
            entity: Entity to get name from
            
        Returns:
            Entity name or empty string
        """
        if hasattr(entity, "descriptor") and entity.descriptor:
            if hasattr(entity.descriptor, "name") and entity.descriptor.name:
                return entity.descriptor.name
        return ""
    
    def _get_entity_bio(self, entity: "Entity") -> str:
        """Get entity bio/description.
        
        Args:
            entity: Entity to get bio from
            
        Returns:
            Entity bio or empty string
        """
        if hasattr(entity, "descriptor") and entity.descriptor:
            bio = getattr(entity.descriptor, "bio", "") or ""
            description = getattr(entity.descriptor, "description", "") or ""
            return (bio + " " + description).strip()
        return ""
    
    def _get_entity_type(self, entity: "Entity") -> str:
        """Get entity type as string.
        
        Args:
            entity: Entity to get type from
            
        Returns:
            Entity type or empty string
        """
        if hasattr(entity, "descriptor") and entity.descriptor:
            if hasattr(entity.descriptor, "entity_type"):
                et = entity.descriptor.entity_type
                return et.value if hasattr(et, 'value') else str(et)
        return ""
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity (0.0 to 1.0)
        """
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
