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
    from pyscrai_core.memory_service import MemoryService

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

## Entity Analysis Guidelines

EXTRACT MEANINGFUL RELATIONSHIPS from the entity descriptions:

1. **MEMBER_OF**: For actors belonging to organizations/factions
   - "Captain in the Crimson Vanguard" → actor → Crimson Vanguard (MEMBER_OF)
   - "Senior Lieutenant in the Iron Syndicate" → actor → Iron Syndicate (MEMBER_OF)

2. **LOCATED_IN**: For locations containing or related to other entities
   - "Outpost Zeta under siege" → related to operation/actors present

3. **CREATED_BY / PART_OF**: For operations, events created by or involving entities
   - "Operation Silver Talon" → may involve actors or locations

4. **OPPOSES / ALLIED_WITH**: For opposing factions or allied groups
   - Only if explicitly stated or strongly implied (e.g., "enemy faction")

5. **KNOWS / WORKS_WITH**: ONLY if explicitly mentioned in bios
   - DO NOT fabricate relationships between unrelated characters
   - "knows" requires direct evidence

## CRITICAL RULES

- ONLY infer relationships DIRECTLY SUPPORTED by entity bios
- If an actor's bio says "in the X organization", infer MEMBER_OF
- If there's NO connection mentioned, do NOT invent one
- When in doubt, prefer fewer relationships over wrong ones
- For "knows" relationships, you MUST have explicit evidence

## Response Format

Return a JSON array of relationship objects:
```json
[
  {{
    "source_id": "ENTITY_001",
    "target_id": "ENTITY_002", 
    "relationship_type": "MEMBER_OF",
    "confidence": "high",
    "reasoning": "Elena Rossi's bio states she is 'A Captain in the Crimson Vanguard'",
    "evidence": "Bio quote: 'A Captain in the Crimson Vanguard'"
  }}
]
```

Return an empty array if no clear relationships are found.
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
        model: Optional[str] = None,
        memory_service: Optional["MemoryService"] = None
    ):
        """Initialize the LoomAgent.
        
        Args:
            provider: LLM provider for inference
            model: Model name to use (defaults to provider's default)
            memory_service: Optional MemoryService for semantic clustering
        """
        self.provider = provider
        self.model = model or getattr(provider, 'default_model', None)
        self.memory_service = memory_service
    
    async def infer_relationships(
        self,
        entities: List["Entity"],
        existing_relationships: Optional[List["Relationship"]] = None,
        max_entities: int = 20,
        use_clustering: bool = True
    ) -> List[InferredRelationship]:
        """Infer relationships between entities.
        
        Args:
            entities: List of entities to analyze
            existing_relationships: Existing relationships to avoid duplicates
            max_entities: Maximum entities to process at once (for context limits)
            use_clustering: Whether to use semantic clustering to reduce comparisons
            
        Returns:
            List of inferred relationships
        """
        if not entities:
            return []
        
        all_inferred = []
        
        # Use semantic clustering to group entities
        if use_clustering and self.memory_service and len(entities) > 10:
            try:
                from pyscrai_forge.phases.loom.clustering import SemanticClusterer
                clusterer = SemanticClusterer(self.memory_service)
                clusters = clusterer.cluster_entities(entities)
                
                logger.info(f"LoomAgent: Clustered {len(entities)} entities into {len(clusters)} clusters")
                
                # Process each cluster separately
                for cluster_id, cluster_entities in clusters.items():
                    if len(cluster_entities) < 2:
                        continue  # Need at least 2 entities for relationships
                    
                    # Process cluster (limit to max_entities per cluster)
                    cluster_entities_limited = cluster_entities[:max_entities]
                    cluster_inferred = await self._infer_relationships_for_cluster(
                        cluster_entities_limited,
                        existing_relationships,
                        cluster_id
                    )
                    all_inferred.extend(cluster_inferred)
                
                logger.info(f"LoomAgent inferred {len(all_inferred)} relationships (clustered)")
                return all_inferred
                
            except Exception as e:
                logger.warning(f"Clustering failed, falling back to non-clustered inference: {e}")
                # Fall through to non-clustered approach
        
        # Non-clustered approach (original behavior)
        entities_to_analyze = entities[:max_entities]
        inferred = await self._infer_relationships_for_cluster(
            entities_to_analyze,
            existing_relationships,
            "all"
        )
        
        logger.info(f"LoomAgent inferred {len(inferred)} relationships")
        return inferred
    
    async def _infer_relationships_for_cluster(
        self,
        entities: List["Entity"],
        existing_relationships: Optional[List["Relationship"]] = None,
        cluster_id: str = "all"
    ) -> List[InferredRelationship]:
        """Infer relationships for a cluster of entities.
        
        Args:
            entities: List of entities in the cluster
            existing_relationships: Existing relationships to avoid duplicates
            cluster_id: Identifier for the cluster (for logging)
            
        Returns:
            List of inferred relationships
        """
        if not entities:
            return []
        
        # Build entity summaries for the prompt
        entity_summaries = []
        for e in entities:
            summary = {
                "id": e.id,
                "name": e.descriptor.name if hasattr(e, "descriptor") and e.descriptor else "",
                "type": e.descriptor.entity_type.value if hasattr(e, "descriptor") and e.descriptor and hasattr(e.descriptor, "entity_type") else "",
                "description": getattr(e.descriptor, "description", "") if hasattr(e, "descriptor") and e.descriptor else "",
            }
            entity_summaries.append(summary)
        
        prompt = RELATIONSHIP_INFERENCE_PROMPT.format(
            entities_json=json.dumps(entity_summaries, indent=2)
        )
        
        try:
            content = await self.provider.complete_simple(
                prompt=prompt,
                model=self.model,
                temperature=0.3,
                max_tokens=2000
            )
            
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
            
            # Validate relationships against entity bios
            inferred = self._validate_relationships_against_entities(inferred, entities)
            
            return inferred
            
        except Exception as e:
            logger.error(f"LoomAgent relationship inference failed for cluster {cluster_id}: {e}")
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
            content = await self.provider.complete_simple(
                prompt=prompt,
                model=self.model,
                temperature=0.3,
                max_tokens=1500
            )
            
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
    
    def _validate_relationships_against_entities(
        self,
        relationships: List["InferredRelationship"],
        entities: List["Entity"]
    ) -> List["InferredRelationship"]:
        """Validate inferred relationships against entity bios for contradictions.
        
        This catches inferences bad like Marcus Thorne -> High Command when
        his bio says he's in the Iron Syndicate.
        
        Args:
            relationships: List of inferred relationships
            entities: List of entities with their bios
            
        Returns:
            Filtered list of valid relationships
        """
        if not relationships or not entities:
            return relationships
        
        # Build a map of entity_id -> bio text for quick lookup
        entity_bios = {}
        entity_names = {}
        for e in entities:
            if hasattr(e, "descriptor") and e.descriptor:
                entity_id = e.id
                entity_bios[entity_id] = getattr(e.descriptor, "bio", "") or ""
                entity_bios[entity_id] += " " + (getattr(e.descriptor, "description", "") or "")
                entity_names[entity_id] = getattr(e.descriptor, "name", "") or ""
        
        valid_relationships = []
        
        for rel in relationships:
            source_bio = entity_bios.get(rel.source_id, "").lower()
            target_bio = entity_bios.get(rel.target_id, "").lower()
            source_name = entity_names.get(rel.source_id, "")
            target_name = entity_names.get(rel.target_id, "")
            
            # Skip if either entity is unknown
            if not source_bio or not target_bio:
                logger.warning(f"Skipping relationship - missing entity data: {rel.source_id} or {rel.target_id}")
                continue
            
            # Check for MEMBER_OF contradictions
            if rel.relationship_type.upper() == "MEMBER_OF":
                # For actor -> polity relationships, verify the polity is mentioned in actor's bio
                # Don't create member_of from actor to a polity that doesn't appear in their bio
                if target_name.lower() not in source_bio:
                    # The target organization is NOT mentioned in source's bio
                    # This is a fabricated relationship - skip it
                    logger.debug(
                        f"Skipping fabricated MEMBER_OF: {source_name} -> {target_name} "
                        f"(target not in source bio)"
                    )
                    continue
            
            # Check for "knows" relationships - must have explicit evidence
            if rel.relationship_type.upper() in ["KNOWS", "WORKS_WITH", "ALLIED_WITH"]:
                # "knows" must be explicitly stated in the source entity's bio
                knows_keywords = ["knows", "works with", "colleague", "ally", "partner", "friend"]
                has_explicit_evidence = any(kw in source_bio for kw in knows_keywords)
                
                if not has_explicit_evidence:
                    logger.debug(
                        f"Skipping fabricated {rel.relationship_type}: {source_name} -> {target_name} "
                        f"(no explicit evidence in source bio)"
                    )
                    continue
            
            # Check for LOCATED_IN contradictions
            if rel.relationship_type.upper() == "LOCATED_IN":
                # Verify the location relationship makes sense
                pass  # Add additional checks if needed
            
            # If we passed all checks, keep the relationship
            valid_relationships.append(rel)
        
        filtered_count = len(relationships) - len(valid_relationships)
        if filtered_count > 0:
            logger.info(f"LoomAgent filtered {filtered_count} invalid relationship(s)")
        
        return valid_relationships

