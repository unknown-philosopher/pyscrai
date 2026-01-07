"""Phase 2: LOOM - LoomAgent for Relationship Inference.

The LoomAgent analyzes entities and infers relationships between them
using LLM-powered reasoning. It can:
- Suggest relationships based on entity descriptions
- Detect potential conflicts or duplicates
- Validate existing relationships
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from pyscrai_core import Entity, Relationship
    from pyscrai_core.llm_interface.base import LLMProvider

logger = logging.getLogger(__name__)


class RelationshipConfidence(Enum):
    """Confidence level for inferred relationships."""
    HIGH = "high"       # Strong textual evidence
    MEDIUM = "medium"   # Reasonable inference
    LOW = "low"         # Weak/speculative connection


@dataclass
class InferredRelationship:
    """A relationship suggested by the LoomAgent."""
    source_id: str
    target_id: str
    relationship_type: str
    confidence: RelationshipConfidence
    reasoning: str
    evidence: str  # Quote or reference from entity data


@dataclass
class ConflictDetection:
    """A detected conflict or inconsistency."""
    entity_ids: List[str]
    conflict_type: str  # "duplicate", "contradiction", "missing_link"
    description: str
    suggestion: str


RELATIONSHIP_INFERENCE_PROMPT = """You are analyzing entities from a worldbuilding project to infer relationships between them.

## Entities

{entities_json}

## Task

Analyze these entities and identify relationships between them. Look for:
1. Explicit connections mentioned in descriptions
2. Implied relationships (same location, organization, family, etc.)
3. Hierarchical relationships (part-of, member-of, reports-to)
4. Social/interpersonal relationships (knows, allies, enemies)

For each relationship, provide:
- source_id: The ID of the source entity
- target_id: The ID of the target entity  
- relationship_type: One of [KNOWS, FAMILY, ALLIED_WITH, ENEMY_OF, MEMBER_OF, LOCATED_IN, OWNS, WORKS_FOR, CREATED_BY, PART_OF]
- confidence: "high", "medium", or "low"
- reasoning: Why this relationship exists
- evidence: Quote or reference from the entity data

## Response Format

Return a JSON array of relationship objects:
```json
[
  {{
    "source_id": "ENTITY_001",
    "target_id": "ENTITY_002", 
    "relationship_type": "KNOWS",
    "confidence": "high",
    "reasoning": "Both are described as working together",
    "evidence": "Source mentions 'colleague of John'"
  }}
]
```

Only include relationships you are reasonably confident about. Return an empty array if no relationships are found.
"""


CONFLICT_DETECTION_PROMPT = """You are analyzing entities and relationships for potential conflicts or inconsistencies.

## Entities

{entities_json}

## Existing Relationships

{relationships_json}

## Task

Identify any conflicts, inconsistencies, or issues:

1. **Duplicates**: Entities that might be the same person/place/thing with different names
2. **Contradictions**: Information that conflicts (e.g., character in two places at once)
3. **Missing Links**: Obviously related entities without explicit relationships
4. **Orphans**: Entities that seem disconnected from the world

For each issue, provide:
- entity_ids: List of entity IDs involved
- conflict_type: "duplicate", "contradiction", "missing_link", or "orphan"
- description: What the issue is
- suggestion: How to resolve it

## Response Format

Return a JSON array of conflict objects:
```json
[
  {{
    "entity_ids": ["ENTITY_001", "ENTITY_005"],
    "conflict_type": "duplicate",
    "description": "Both appear to be the same character 'John Smith'",
    "suggestion": "Merge ENTITY_005 into ENTITY_001"
  }}
]
```

Return an empty array if no issues are found.
"""


class LoomAgent:
    """Agent for inferring and validating relationships between entities."""
    
    def __init__(
        self,
        provider: "LLMProvider",
        model: Optional[str] = None
    ):
        """Initialize the LoomAgent.
        
        Args:
            provider: LLM provider for inference
            model: Model name to use (defaults to provider's default)
        """
        self.provider = provider
        self.model = model or getattr(provider, 'default_model', None)
    
    async def infer_relationships(
        self,
        entities: List["Entity"],
        existing_relationships: Optional[List["Relationship"]] = None,
        max_entities: int = 20
    ) -> List[InferredRelationship]:
        """Infer relationships between entities.
        
        Args:
            entities: List of entities to analyze
            existing_relationships: Existing relationships to avoid duplicates
            max_entities: Maximum entities to process at once (for context limits)
            
        Returns:
            List of inferred relationships
        """
        if not entities:
            return []
        
        # Limit entities to avoid context overflow
        entities_to_analyze = entities[:max_entities]
        
        # Build entity summaries for the prompt
        entity_summaries = []
        for e in entities_to_analyze:
            summary = {
                "id": e.id,
                "name": e.descriptor.name if hasattr(e, "descriptor") else "",
                "type": e.descriptor.entity_type.value if hasattr(e.descriptor, "entity_type") else "",
                "description": getattr(e.descriptor, "description", ""),
            }
            entity_summaries.append(summary)
        
        prompt = RELATIONSHIP_INFERENCE_PROMPT.format(
            entities_json=json.dumps(entity_summaries, indent=2)
        )
        
        try:
            response = await self.provider.complete(
                prompt=prompt,
                model=self.model,
                max_tokens=2000
            )
            
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parse the JSON response
            inferred = self._parse_relationships_response(content)
            
            # Filter out existing relationships
            if existing_relationships:
                existing_pairs = {
                    (r.source_id, r.target_id) for r in existing_relationships
                }
                inferred = [
                    r for r in inferred
                    if (r.source_id, r.target_id) not in existing_pairs
                    and (r.target_id, r.source_id) not in existing_pairs
                ]
            
            logger.info(f"LoomAgent inferred {len(inferred)} relationships")
            return inferred
            
        except Exception as e:
            logger.error(f"LoomAgent relationship inference failed: {e}")
            return []
    
    async def detect_conflicts(
        self,
        entities: List["Entity"],
        relationships: List["Relationship"]
    ) -> List[ConflictDetection]:
        """Detect conflicts and inconsistencies.
        
        Args:
            entities: List of entities
            relationships: List of relationships
            
        Returns:
            List of detected conflicts
        """
        if not entities:
            return []
        
        # Build summaries
        entity_summaries = []
        for e in entities[:30]:  # Limit for context
            summary = {
                "id": e.id,
                "name": e.descriptor.name if hasattr(e, "descriptor") else "",
                "type": e.descriptor.entity_type.value if hasattr(e.descriptor, "entity_type") else "",
                "description": getattr(e.descriptor, "description", ""),
            }
            entity_summaries.append(summary)
        
        relationship_summaries = []
        for r in relationships[:50]:  # Limit for context
            summary = {
                "source": r.source_id,
                "target": r.target_id,
                "type": r.relationship_type.value if hasattr(r.relationship_type, "value") else str(r.relationship_type),
            }
            relationship_summaries.append(summary)
        
        prompt = CONFLICT_DETECTION_PROMPT.format(
            entities_json=json.dumps(entity_summaries, indent=2),
            relationships_json=json.dumps(relationship_summaries, indent=2)
        )
        
        try:
            response = await self.provider.complete(
                prompt=prompt,
                model=self.model,
                max_tokens=1500
            )
            
            content = response.content if hasattr(response, 'content') else str(response)
            
            conflicts = self._parse_conflicts_response(content)
            logger.info(f"LoomAgent detected {len(conflicts)} conflicts")
            return conflicts
            
        except Exception as e:
            logger.error(f"LoomAgent conflict detection failed: {e}")
            return []
    
    def _parse_relationships_response(self, content: str) -> List[InferredRelationship]:
        """Parse LLM response into InferredRelationship objects."""
        try:
            # Try to extract JSON from the response
            json_start = content.find('[')
            json_end = content.rfind(']') + 1
            
            if json_start == -1 or json_end <= json_start:
                return []
            
            json_str = content[json_start:json_end]
            data = json.loads(json_str)
            
            results = []
            for item in data:
                try:
                    confidence = RelationshipConfidence(item.get("confidence", "medium").lower())
                except ValueError:
                    confidence = RelationshipConfidence.MEDIUM
                
                results.append(InferredRelationship(
                    source_id=item.get("source_id", ""),
                    target_id=item.get("target_id", ""),
                    relationship_type=item.get("relationship_type", "KNOWS"),
                    confidence=confidence,
                    reasoning=item.get("reasoning", ""),
                    evidence=item.get("evidence", "")
                ))
            
            return results
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse relationships JSON: {e}")
            return []
    
    def _parse_conflicts_response(self, content: str) -> List[ConflictDetection]:
        """Parse LLM response into ConflictDetection objects."""
        try:
            json_start = content.find('[')
            json_end = content.rfind(']') + 1
            
            if json_start == -1 or json_end <= json_start:
                return []
            
            json_str = content[json_start:json_end]
            data = json.loads(json_str)
            
            results = []
            for item in data:
                results.append(ConflictDetection(
                    entity_ids=item.get("entity_ids", []),
                    conflict_type=item.get("conflict_type", "unknown"),
                    description=item.get("description", ""),
                    suggestion=item.get("suggestion", "")
                ))
            
            return results
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse conflicts JSON: {e}")
            return []
    
    def validate_relationship(
        self,
        relationship: "Relationship",
        entities: List["Entity"]
    ) -> Tuple[bool, str]:
        """Validate a single relationship.
        
        Args:
            relationship: The relationship to validate
            entities: Available entities
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        entity_ids = {e.id for e in entities}
        
        if relationship.source_id not in entity_ids:
            return False, f"Source entity {relationship.source_id} not found"
        
        if relationship.target_id not in entity_ids:
            return False, f"Target entity {relationship.target_id} not found"
        
        if relationship.source_id == relationship.target_id:
            return False, "Self-referential relationship"
        
        return True, ""

