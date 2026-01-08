"""Semantic Conflict Resolver for Anvil Phase.

This module provides semantic conflict resolution that categorizes merge conflicts
as Corrections, Events, Branches, or Ambiguous based on semantic similarity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pyscrai_core import Entity
    from pyscrai_core.memory_service import MemoryService

logger = logging.getLogger(__name__)


class ConflictCategory(str, Enum):
    """Categories for merge conflicts."""
    CORRECTION = "correction"  # Same entity, fixing typo/error (distance < 0.2)
    EVENT = "event"  # Same entity, state changed over time (distance 0.2-0.5)
    BRANCH = "branch"  # Different entities with similar names (distance > 0.8)
    AMBIGUOUS = "ambiguous"  # User must decide (distance 0.5-0.8)


@dataclass
class ConflictAnalysis:
    """Analysis result for a merge conflict."""
    category: ConflictCategory
    similarity: float  # 0.0 to 1.0
    distance: float  # 1.0 - similarity
    attribute_changes: int
    reasoning: str
    suggested_action: str


class SemanticConflictResolver:
    """Resolves merge conflicts using semantic similarity analysis.
    
    Categorizes conflicts based on semantic distance and attribute changes
    to help users understand whether entities should be merged, updated, or
    kept separate.
    """
    
    def __init__(self, memory_service: Optional["MemoryService"] = None):
        """Initialize the SemanticConflictResolver.
        
        Args:
            memory_service: MemoryService instance for embedding calculations
        """
        self.memory_service = memory_service
    
    def categorize_conflict(
        self,
        staging: "Entity",
        canon: "Entity"
    ) -> ConflictAnalysis:
        """Categorize a merge conflict based on semantic similarity.
        
        Args:
            staging: Entity from staging
            canon: Entity from canonical database
            
        Returns:
            ConflictAnalysis with category, similarity, and reasoning
        """
        # Build full text representations
        staging_text = self._entity_to_full_text(staging)
        canon_text = self._entity_to_full_text(canon)
        
        # Calculate semantic similarity
        if self.memory_service:
            similarity = self.memory_service.calculate_similarity(staging_text, canon_text)
        else:
            # Fallback to simple text matching
            similarity = self._simple_similarity(staging_text, canon_text)
        
        distance = 1.0 - similarity
        
        # Count attribute changes
        attribute_changes = self._count_attribute_changes(staging, canon)
        
        # Categorize based on distance and changes
        if distance < 0.2:
            category = ConflictCategory.CORRECTION
            reasoning = f"Very high similarity ({similarity*100:.1f}%). Likely the same entity with minor corrections or typos."
            suggested_action = "UPDATE - Merge attributes, keeping canon as base"
        elif distance < 0.5:
            if attribute_changes > 0:
                category = ConflictCategory.EVENT
                reasoning = f"Moderate similarity ({similarity*100:.1f}%) with {attribute_changes} attribute changes. Likely state transition over time."
                suggested_action = "UPDATE - Apply state changes as time-based event"
            else:
                category = ConflictCategory.AMBIGUOUS
                reasoning = f"Moderate similarity ({similarity*100:.1f}%) but no clear attribute changes. Manual review needed."
                suggested_action = "REVIEW - User decision required"
        elif distance > 0.8:
            category = ConflictCategory.BRANCH
            reasoning = f"Low similarity ({similarity*100:.1f}%). Different entities with similar names."
            suggested_action = "CREATE - Keep as separate entities"
        else:
            category = ConflictCategory.AMBIGUOUS
            reasoning = f"Ambiguous similarity ({similarity*100:.1f}%). Could be same entity with major changes or different entities."
            suggested_action = "REVIEW - User decision required"
        
        return ConflictAnalysis(
            category=category,
            similarity=similarity,
            distance=distance,
            attribute_changes=attribute_changes,
            reasoning=reasoning,
            suggested_action=suggested_action
        )
    
    def _entity_to_full_text(self, entity: "Entity") -> str:
        """Convert entity to full text representation for comparison.
        
        Args:
            entity: Entity to convert
            
        Returns:
            Full text representation
        """
        parts = []
        
        # Add descriptor information
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
        
        # Add state information
        if hasattr(entity, "state") and entity.state:
            if hasattr(entity.state, "resources") and entity.state.resources:
                for key, value in entity.state.resources.items():
                    if isinstance(value, (str, int, float)):
                        parts.append(f"{key}: {value}")
        
        return " ".join(str(p) for p in parts if p)
    
    def _count_attribute_changes(self, staging: "Entity", canon: "Entity") -> int:
        """Count the number of attribute changes between entities.
        
        Args:
            staging: Staging entity
            canon: Canonical entity
            
        Returns:
            Number of changed attributes
        """
        changes = 0
        
        # Compare descriptors
        if hasattr(staging, "descriptor") and staging.descriptor and \
           hasattr(canon, "descriptor") and canon.descriptor:
            staging_desc = staging.descriptor
            canon_desc = canon.descriptor
            
            if hasattr(staging_desc, "description") and hasattr(canon_desc, "description"):
                if staging_desc.description != canon_desc.description:
                    changes += 1
            
            if hasattr(staging_desc, "bio") and hasattr(canon_desc, "bio"):
                if staging_desc.bio != canon_desc.bio:
                    changes += 1
        
        # Compare state resources
        staging_resources = {}
        canon_resources = {}
        
        if hasattr(staging, "state") and staging.state:
            if hasattr(staging.state, "resources") and staging.state.resources:
                staging_resources = staging.state.resources
        
        if hasattr(canon, "state") and canon.state:
            if hasattr(canon.state, "resources") and canon.state.resources:
                canon_resources = canon.state.resources
        
        # Count differences in resources
        all_keys = set(staging_resources.keys()) | set(canon_resources.keys())
        for key in all_keys:
            staging_val = staging_resources.get(key)
            canon_val = canon_resources.get(key)
            if staging_val != canon_val:
                changes += 1
        
        return changes
    
    def _simple_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple Jaccard similarity as fallback.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
