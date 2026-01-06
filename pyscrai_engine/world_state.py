"""World state query utility for PyScrAI Engine.

Provides convenient query methods for agents to inspect world state
before forming intentions.
"""

import json
import math
from typing import Optional, List, Tuple, TYPE_CHECKING

from pyscrai_core import Entity, EntityType, Relationship, RelationshipType

if TYPE_CHECKING:
    from .engine import SimulationEngine


class WorldStateQuery:
    """Utility class for querying world state.
    
    Used by agents to inspect entities, relationships, and resources
    before generating intentions.
    """
    
    def __init__(self, engine: "SimulationEngine"):
        """Initialize world state query.
        
        Args:
            engine: Parent simulation engine
        """
        self.engine = engine
    
    def get_actor_stats(self, actor_id: str) -> dict:
        """Get actor's stats from resources_json.
        
        Args:
            actor_id: Actor entity ID
            
        Returns:
            Dictionary of actor stats (parsed from resources_json)
        """
        actor = self.engine.get_entity(actor_id)
        if not actor:
            return {}
            
        if not actor.state:
            return {}
            
        try:
            return json.loads(actor.state.resources_json) if actor.state.resources_json else {}
        except json.JSONDecodeError:
            return {}
    
    def get_nearby_entities(self, actor_id: str, radius_km: float = 10.0) -> List[Entity]:
        """Get entities within spatial distance of an actor.
        
        Args:
            actor_id: Actor entity ID
            radius_km: Search radius in kilometers
            
        Returns:
            List of entities within radius
        """
        actor = self.engine.get_entity(actor_id)
        if not actor or not actor.spatial:
            return []
            
        actor_x = actor.spatial.x
        actor_y = actor.spatial.y
        
        nearby = []
        for entity in self.engine.entities.values():
            if entity.id == actor_id:
                continue
                
            if not entity.spatial:
                continue
                
            # Calculate distance (simple Euclidean)
            dx = entity.spatial.x - actor_x
            dy = entity.spatial.y - actor_y
            distance_km = math.sqrt(dx * dx + dy * dy)
            
            if distance_km <= radius_km:
                nearby.append(entity)
                
        return nearby
    
    def can_transfer_resource(
        self, 
        source_id: str, 
        target_id: str, 
        resource_type: str, 
        amount: float
    ) -> Tuple[bool, str]:
        """Validate if a resource transfer is feasible.
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            resource_type: Resource type to transfer
            amount: Amount to transfer
            
        Returns:
            Tuple of (can_transfer, reason)
        """
        source = self.engine.get_entity(source_id)
        if not source:
            return False, f"Source entity {source_id} not found"
            
        target = self.engine.get_entity(target_id)
        if not target:
            return False, f"Target entity {target_id} not found"
            
        if not source.state:
            return False, f"Source entity {source_id} has no state component"
            
        # Check source has enough resources
        try:
            resources = json.loads(source.state.resources_json) if source.state.resources_json else {}
            current_amount = resources.get(resource_type, 0)
            
            if current_amount < amount:
                return False, f"Insufficient {resource_type}: has {current_amount}, needs {amount}"
                
        except json.JSONDecodeError:
            return False, f"Invalid resources_json for source entity {source_id}"
            
        return True, ""
    
    def get_entity_by_name(self, name: str) -> Optional[Entity]:
        """Lookup entity by descriptor name.
        
        Args:
            name: Entity name to search for
            
        Returns:
            Entity if found, None otherwise
        """
        for entity in self.engine.entities.values():
            if entity.descriptor and entity.descriptor.name == name:
                return entity
        return None
    
    def get_relationships(self, entity_id: str) -> List[Relationship]:
        """Get all relationships involving an entity.
        
        Args:
            entity_id: Entity ID to lookup
            
        Returns:
            List of relationships where entity is source or target
        """
        return self.engine.get_relationships_for_entity(entity_id)
    
    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Get all entities of a specific type.
        
        Args:
            entity_type: Type to filter by
            
        Returns:
            List of entities matching the type
        """
        return self.engine.get_entities_by_type(entity_type)
    
    def get_locations_with_tag(self, tag: str) -> List[Entity]:
        """Get all locations with a specific tag.
        
        Args:
            tag: Tag to search for
            
        Returns:
            List of location entities with the tag
        """
        locations = []
        for entity in self.engine.entities.values():
            if entity.entity_type == EntityType.LOCATION:
                if entity.descriptor and tag in entity.descriptor.tags:
                    locations.append(entity)
        return locations

