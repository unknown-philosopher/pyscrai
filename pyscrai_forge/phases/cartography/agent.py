"""Phase 4: CARTOGRAPHY - CartographerAgent for Position Suggestions.

The CartographerAgent analyzes entity descriptions and relationships
to suggest spatial positions on a map grid.
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from pyscrai_core import Entity, Relationship
    from pyscrai_core.llm_interface.base import LLMProvider

logger = logging.getLogger(__name__)


@dataclass
class PositionSuggestion:
    """A suggested position for an entity."""
    entity_id: str
    x: float
    y: float
    confidence: float  # 0.0 to 1.0
    reasoning: str
    region: str = ""  # Suggested region name


@dataclass
class RegionSuggestion:
    """A suggested region on the map."""
    name: str
    x: float
    y: float
    width: float
    height: float
    description: str
    entity_ids: List[str]


POSITION_SUGGESTION_PROMPT = """You are analyzing entities for a worldbuilding project to suggest their positions on a 2D map grid.

The map grid is {grid_width} x {grid_height} units (0,0 is top-left).

## Entities

{entities_json}

## Relationships

{relationships_json}

## Task

For each LOCATION-type entity, suggest an (x, y) position on the map grid.
For CHARACTER/PERSON entities, place them near their associated locations.
For ORGANIZATION entities, suggest a headquarters location.

Consider:
1. Description hints (north, south, near, far, etc.)
2. Relationships (entities that are related should be near each other)
3. Entity type (locations as anchors, characters near locations)
4. Logical groupings (same faction members together)

## Response Format

Return a JSON array of position objects:
```json
[
  {{
    "entity_id": "ENTITY_001",
    "x": 250,
    "y": 150,
    "confidence": 0.8,
    "reasoning": "Description mentions 'northern capital'",
    "region": "Northern Kingdoms"
  }}
]
```

Only include entities you can reasonably position. Skip entities with no spatial hints.
"""


REGION_DETECTION_PROMPT = """You are analyzing entities to identify distinct regions or areas on a worldbuilding map.

## Entities

{entities_json}

## Current Positions

{positions_json}

## Task

Identify logical regions or areas that group related entities:
1. Political regions (kingdoms, territories)
2. Geographic areas (mountains, forests, coasts)
3. Cultural zones (faction territories)
4. Functional areas (trade routes, war zones)

For each region, provide:
- name: Region name
- x, y: Top-left corner of region bounding box
- width, height: Size of region
- description: Brief description
- entity_ids: List of entity IDs in this region

## Response Format

Return a JSON array of region objects:
```json
[
  {{
    "name": "Northern Kingdoms",
    "x": 0,
    "y": 0,
    "width": 300,
    "height": 200,
    "description": "The cold northern territories",
    "entity_ids": ["ENTITY_001", "ENTITY_003"]
  }}
]
```
"""


class CartographerAgent:
    """Agent for suggesting entity positions on a map."""
    
    def __init__(
        self,
        provider: "LLMProvider",
        model: Optional[str] = None,
        grid_width: int = 800,
        grid_height: int = 600
    ):
        """Initialize the CartographerAgent.
        
        Args:
            provider: LLM provider for suggestions
            model: Model name to use
            grid_width: Width of the map grid
            grid_height: Height of the map grid
        """
        self.provider = provider
        self.model = model or getattr(provider, 'default_model', None)
        self.grid_width = grid_width
        self.grid_height = grid_height
    
    async def suggest_positions(
        self,
        entities: List["Entity"],
        relationships: List["Relationship"],
        existing_positions: Optional[Dict[str, Tuple[float, float]]] = None
    ) -> List[PositionSuggestion]:
        """Suggest positions for entities on the map.
        
        Args:
            entities: List of entities to position
            relationships: Relationships between entities
            existing_positions: Already-placed entity positions
            
        Returns:
            List of position suggestions
        """
        if not entities:
            return []
        
        # Build entity summaries
        entity_summaries = []
        for e in entities[:30]:  # Limit for context
            summary = {
                "id": e.id,
                "name": e.descriptor.name if hasattr(e, "descriptor") else "",
                "type": e.descriptor.entity_type.value if hasattr(e.descriptor, "entity_type") else "",
                "description": getattr(e.descriptor, "description", "")[:200],
            }
            entity_summaries.append(summary)
        
        # Build relationship summaries
        relationship_summaries = []
        for r in relationships[:50]:
            summary = {
                "source": r.source_id,
                "target": r.target_id,
                "type": r.relationship_type.value if hasattr(r.relationship_type, "value") else str(r.relationship_type),
            }
            relationship_summaries.append(summary)
        
        prompt = POSITION_SUGGESTION_PROMPT.format(
            grid_width=self.grid_width,
            grid_height=self.grid_height,
            entities_json=json.dumps(entity_summaries, indent=2),
            relationships_json=json.dumps(relationship_summaries, indent=2)
        )
        
        try:
            response = await self.provider.complete(
                prompt=prompt,
                model=self.model,
                max_tokens=2000
            )
            
            content = response.content if hasattr(response, 'content') else str(response)
            
            suggestions = self._parse_position_response(content)
            logger.info(f"CartographerAgent suggested {len(suggestions)} positions")
            return suggestions
            
        except Exception as e:
            logger.error(f"CartographerAgent position suggestion failed: {e}")
            return []
    
    async def suggest_regions(
        self,
        entities: List["Entity"],
        positions: Dict[str, Tuple[float, float]]
    ) -> List[RegionSuggestion]:
        """Suggest regions to group entities.
        
        Args:
            entities: List of entities
            positions: Current entity positions
            
        Returns:
            List of region suggestions
        """
        if not entities or not positions:
            return []
        
        entity_summaries = []
        for e in entities[:30]:
            summary = {
                "id": e.id,
                "name": e.descriptor.name if hasattr(e, "descriptor") else "",
                "type": e.descriptor.entity_type.value if hasattr(e.descriptor, "entity_type") else "",
            }
            entity_summaries.append(summary)
        
        positions_json = {eid: {"x": x, "y": y} for eid, (x, y) in positions.items()}
        
        prompt = REGION_DETECTION_PROMPT.format(
            entities_json=json.dumps(entity_summaries, indent=2),
            positions_json=json.dumps(positions_json, indent=2)
        )
        
        try:
            response = await self.provider.complete(
                prompt=prompt,
                model=self.model,
                max_tokens=1500
            )
            
            content = response.content if hasattr(response, 'content') else str(response)
            
            regions = self._parse_regions_response(content)
            logger.info(f"CartographerAgent suggested {len(regions)} regions")
            return regions
            
        except Exception as e:
            logger.error(f"CartographerAgent region suggestion failed: {e}")
            return []
    
    def auto_layout(
        self,
        entities: List["Entity"],
        relationships: List["Relationship"]
    ) -> Dict[str, Tuple[float, float]]:
        """Generate automatic layout without LLM.
        
        Uses simple heuristics based on entity types and relationships.
        
        Args:
            entities: List of entities
            relationships: Relationships between entities
            
        Returns:
            Dict mapping entity ID to (x, y) position
        """
        positions = {}
        
        if not entities:
            return positions
        
        # Separate by type
        locations = []
        characters = []
        others = []
        
        for e in entities:
            entity_type = ""
            if hasattr(e, "descriptor") and hasattr(e.descriptor, "entity_type"):
                entity_type = e.descriptor.entity_type.value.lower()
            
            if entity_type in ("location", "place"):
                locations.append(e)
            elif entity_type in ("character", "person"):
                characters.append(e)
            else:
                others.append(e)
        
        # Place locations in a grid
        padding = 100
        loc_count = len(locations)
        if loc_count > 0:
            cols = max(1, int((loc_count ** 0.5) + 0.5))
            rows = (loc_count + cols - 1) // cols
            
            cell_w = (self.grid_width - 2 * padding) / max(cols, 1)
            cell_h = (self.grid_height - 2 * padding) / max(rows, 1)
            
            for i, loc in enumerate(locations):
                col = i % cols
                row = i // cols
                x = padding + col * cell_w + cell_w / 2 + random.uniform(-20, 20)
                y = padding + row * cell_h + cell_h / 2 + random.uniform(-20, 20)
                positions[loc.id] = (x, y)
        
        # Build location lookup from relationships
        entity_locations = {}
        for rel in relationships:
            rel_type = ""
            if hasattr(rel, "relationship_type"):
                rel_type = rel.relationship_type.value.lower() if hasattr(rel.relationship_type, "value") else str(rel.relationship_type).lower()
            
            if rel_type in ("located_in", "lives_in", "resides_in"):
                entity_locations[rel.source_id] = rel.target_id
        
        # Place characters near their locations
        for char in characters:
            if char.id in entity_locations:
                loc_id = entity_locations[char.id]
                if loc_id in positions:
                    loc_x, loc_y = positions[loc_id]
                    # Offset slightly
                    x = loc_x + random.uniform(-50, 50)
                    y = loc_y + random.uniform(-50, 50)
                    positions[char.id] = (x, y)
                    continue
            
            # Random position if no location
            x = random.uniform(padding, self.grid_width - padding)
            y = random.uniform(padding, self.grid_height - padding)
            positions[char.id] = (x, y)
        
        # Place others randomly
        for other in others:
            x = random.uniform(padding, self.grid_width - padding)
            y = random.uniform(padding, self.grid_height - padding)
            positions[other.id] = (x, y)
        
        return positions
    
    def _parse_position_response(self, content: str) -> List[PositionSuggestion]:
        """Parse LLM response into PositionSuggestion objects."""
        try:
            json_start = content.find('[')
            json_end = content.rfind(']') + 1
            
            if json_start == -1 or json_end <= json_start:
                return []
            
            json_str = content[json_start:json_end]
            data = json.loads(json_str)
            
            results = []
            for item in data:
                results.append(PositionSuggestion(
                    entity_id=item.get("entity_id", ""),
                    x=float(item.get("x", 0)),
                    y=float(item.get("y", 0)),
                    confidence=float(item.get("confidence", 0.5)),
                    reasoning=item.get("reasoning", ""),
                    region=item.get("region", "")
                ))
            
            return results
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse positions JSON: {e}")
            return []
    
    def _parse_regions_response(self, content: str) -> List[RegionSuggestion]:
        """Parse LLM response into RegionSuggestion objects."""
        try:
            json_start = content.find('[')
            json_end = content.rfind(']') + 1
            
            if json_start == -1 or json_end <= json_start:
                return []
            
            json_str = content[json_start:json_end]
            data = json.loads(json_str)
            
            results = []
            for item in data:
                results.append(RegionSuggestion(
                    name=item.get("name", ""),
                    x=float(item.get("x", 0)),
                    y=float(item.get("y", 0)),
                    width=float(item.get("width", 100)),
                    height=float(item.get("height", 100)),
                    description=item.get("description", ""),
                    entity_ids=item.get("entity_ids", [])
                ))
            
            return results
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse regions JSON: {e}")
            return []

