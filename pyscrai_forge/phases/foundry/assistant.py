"""Foundry Assistant - Alias Detection using Semantic Embeddings.

This module provides the FoundryAssistant class that uses Sentence Transformers
embeddings to detect when newly extracted entities are likely aliases of
existing entities, even when the words differ.
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
class AliasSuggestion:
    """A suggested alias relationship between two entities."""
    new_entity: "Entity"
    existing_entity: "Entity"
    similarity: float  # 0.0 to 1.0
    reasoning: str
    context_sentence: str = ""
    is_ocr_error: bool = False
    suggested_correction: Optional[str] = None


@dataclass
class OCRError:
    """A detected OCR error between two entities."""
    entity1: "Entity"
    entity2: "Entity"
    suggested_correction: str
    confidence: float


class FoundryAssistant:
    """Assistant for Foundry phase that detects aliases using semantic embeddings.
    
    Uses Sentence Transformers to compare contextual descriptions of entities
    and suggests ALIAS relationships when semantic similarity is high (>0.95).
    """
    
    def __init__(self, memory_service=None):
        """Initialize the FoundryAssistant.
        
        Args:
            memory_service: MemoryService instance for embedding calculations
        """
        self.memory_service = memory_service
    
    def detect_aliases(
        self,
        new_entity: "Entity",
        existing_entities: List["Entity"],
        context_sentence: str
    ) -> List[AliasSuggestion]:
        """Detect if new_entity is an alias of any existing entity.
        
        Args:
            new_entity: Newly extracted entity
            existing_entities: List of existing entities to compare against
            context_sentence: The sentence/paragraph where new_entity was mentioned
            
        Returns:
            List of AliasSuggestion objects (empty if no matches found)
        """
        if not self.memory_service or not self.memory_service.embedding:
            logger.warning("MemoryService or embedding model not available, skipping alias detection")
            return []
        
        if not context_sentence:
            context_sentence = self._entity_to_context_text(new_entity)
        
        suggestions = []
        
        # Embed the new entity's context
        new_embedding = self.memory_service.embedding.encode(context_sentence)
        if not new_embedding:
            return []
        
        # Compare against all existing entities
        for existing in existing_entities:
            existing_text = self._entity_to_context_text(existing)
            if not existing_text:
                continue
            
            existing_embedding = self.memory_service.embedding.encode(existing_text)
            if not existing_embedding:
                continue
            
            # Calculate cosine similarity
            similarity = self._cosine_similarity(new_embedding, existing_embedding)
            
            # Check for high similarity (alias candidate)
            if similarity > 0.95:
                # Check if this might be an OCR error instead
                ocr_error = self.detect_ocr_errors(new_entity, existing)
                
                suggestions.append(AliasSuggestion(
                    new_entity=new_entity,
                    existing_entity=existing,
                    similarity=similarity,
                    reasoning=f"Context descriptions are {similarity*100:.1f}% similar",
                    context_sentence=context_sentence,
                    is_ocr_error=ocr_error is not None,
                    suggested_correction=ocr_error.suggested_correction if ocr_error else None
                ))
        
        return suggestions
    
    def detect_ocr_errors(
        self,
        entity1: "Entity",
        entity2: "Entity"
    ) -> Optional[OCRError]:
        """Detect if two entities might be the same but with OCR errors.
        
        Args:
            entity1: First entity
            entity2: Second entity
            
        Returns:
            OCRError if OCR pattern detected, None otherwise
        """
        name1 = self._get_entity_name(entity1).lower()
        name2 = self._get_entity_name(entity2).lower()
        
        # Check for character substitution patterns (OCR errors)
        if self._has_ocr_pattern(name1, name2):
            # Calculate semantic similarity
            text1 = self._entity_to_text(entity1)
            text2 = self._entity_to_text(entity2)
            
            similarity = self.memory_service.calculate_similarity(text1, text2) if self.memory_service else 0.0
            
            if similarity > 0.90:
                suggested = self._suggest_correction(name1, name2)
                return OCRError(
                    entity1=entity1,
                    entity2=entity2,
                    suggested_correction=suggested,
                    confidence=similarity
                )
        
        return None
    
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
                # Add key attributes that help identify the entity
                for key, value in entity.state.resources.items():
                    if isinstance(value, (str, int, float)):
                        parts.append(f"{key}: {value}")
        
        return " ".join(str(p) for p in parts if p)
    
    def _entity_to_text(self, entity: "Entity") -> str:
        """Convert entity to simple text representation.
        
        Args:
            entity: Entity to convert
            
        Returns:
            Simple text representation
        """
        parts = []
        
        if hasattr(entity, "descriptor") and entity.descriptor:
            desc = entity.descriptor
            if hasattr(desc, "name") and desc.name:
                parts.append(desc.name)
            if hasattr(desc, "description") and desc.description:
                parts.append(desc.description)
        
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
    
    def _has_ocr_pattern(self, name1: str, name2: str) -> bool:
        """Check if two names have OCR error patterns.
        
        Common OCR errors:
        - Number/letter confusion: 0/O, 1/I/l, 5/S, 8/B
        - Similar characters: rn/m, cl/d, vv/w
        
        Args:
            name1: First name
            name2: Second name
            
        Returns:
            True if OCR pattern detected
        """
        if len(name1) != len(name2):
            return False
        
        # Check for character substitutions that are common OCR errors
        ocr_substitutions = {
            '0': 'o', 'o': '0',
            '1': 'i', 'i': '1', 'l': '1',
            '5': 's', 's': '5',
            '8': 'b', 'b': '8',
            'rn': 'm', 'm': 'rn',
            'cl': 'd', 'd': 'cl',
            'vv': 'w', 'w': 'vv'
        }
        
        differences = 0
        for c1, c2 in zip(name1, name2):
            if c1 != c2:
                # Check if it's a known OCR substitution
                if (c1 in ocr_substitutions and ocr_substitutions[c1] == c2) or \
                   (c2 in ocr_substitutions and ocr_substitutions[c2] == c1):
                    differences += 1
                else:
                    return False  # Not an OCR pattern
        
        # If all differences are OCR-like substitutions, it's a pattern
        return differences > 0 and differences <= len(name1) * 0.3  # Max 30% of characters
    
    def _suggest_correction(self, name1: str, name2: str) -> str:
        """Suggest a correction for OCR error.
        
        Args:
            name1: First name (potentially with OCR error)
            name2: Second name (potentially correct)
            
        Returns:
            Suggested correction
        """
        # Simple heuristic: prefer the name with fewer numbers (likely correct)
        num_digits1 = sum(1 for c in name1 if c.isdigit())
        num_digits2 = sum(1 for c in name2 if c.isdigit())
        
        if num_digits1 < num_digits2:
            return name1
        elif num_digits2 < num_digits1:
            return name2
        else:
            # Prefer the one with more common letters
            common_letters = set('aeiou')
            common1 = sum(1 for c in name1 if c in common_letters)
            common2 = sum(1 for c in name2 if c in common_letters)
            return name1 if common1 >= common2 else name2
