"""Rule-based agent for PyScrAI Engine.

A simple rule-based agent that generates intentions based on actor needs.
This is a reference implementation for basic agent behavior.
"""

from typing import Optional, TYPE_CHECKING

from pyscrai_core import Entity, EntityType
from pyscrai_core.intentions import (
    Intention,
    MoveIntention,
    ResourceTransferIntention
)
from pyscrai_core import RelationshipType

if TYPE_CHECKING:
    from ..world_state import WorldStateQuery


class BasicNeedsAgent:
    """Simple rule-based agent that responds to basic needs.
    
    Rules:
    1. If energy < 20, move to nearest rest location
    2. If wealth > threshold, distribute to allies
    """
    
    def __init__(self, energy_threshold: float = 20.0, wealth_threshold: float = 500.0):
        """Initialize basic needs agent.
        
        Args:
            energy_threshold: Energy level below which actor seeks rest
            wealth_threshold: Wealth level above which actor distributes to allies
        """
        self.energy_threshold = energy_threshold
        self.wealth_threshold = wealth_threshold
    
    def generate_intention(
        self, 
        actor: Entity, 
        world: "WorldStateQuery"
    ) -> Optional[Intention]:
        """Generate an intention based on actor's needs.
        
        Args:
            actor: Actor entity to generate intention for
            world: World state query utility
            
        Returns:
            Intention if one is generated, None otherwise
        """
        if actor.entity_type != EntityType.ACTOR:
            return None
            
        # Get actor stats
        stats = world.get_actor_stats(actor.id)
        
        # Rule 1: If energy < threshold, move to nearest rest location
        energy = stats.get('energy', 100)
        if energy < self.energy_threshold:
            rest_spots = world.get_locations_with_tag('rest')
            if not rest_spots:
                # Try alternative tags
                rest_spots = world.get_locations_with_tag('resting')
                if not rest_spots:
                    rest_spots = world.get_locations_with_tag('safe')
            
            if rest_spots:
                # Find nearest rest spot
                if actor.spatial:
                    actor_x = actor.spatial.x
                    actor_y = actor.spatial.y
                    
                    nearest = None
                    min_distance = float('inf')
                    
                    for spot in rest_spots:
                        if spot.spatial:
                            dx = spot.spatial.x - actor_x
                            dy = spot.spatial.y - actor_y
                            distance = (dx * dx + dy * dy) ** 0.5
                            
                            if distance < min_distance:
                                min_distance = distance
                                nearest = spot
                    
                    if nearest:
                        return MoveIntention(
                            source_id=actor.id,
                            target_location_id=nearest.id,
                            priority=10  # High priority for survival needs
                        )
        
        # Rule 2: If wealth > threshold, distribute to allies
        wealth = stats.get('wealth', 0)
        if wealth > self.wealth_threshold:
            # Get relationships
            relationships = world.get_relationships(actor.id)
            allies = [
                r for r in relationships 
                if r.relationship_type == RelationshipType.ALLIANCE
            ]
            
            if allies:
                # Pick first ally
                target_id = allies[0].target_id if allies[0].source_id == actor.id else allies[0].source_id
                transfer_amount = min(100, wealth / 2)
                
                # Check if transfer is feasible
                can_transfer, reason = world.can_transfer_resource(
                    actor.id, 
                    target_id, 
                    'wealth', 
                    transfer_amount
                )
                
                if can_transfer:
                    return ResourceTransferIntention(
                        source_id=actor.id,
                        target_id=target_id,
                        resource_type='wealth',
                        amount=transfer_amount,
                        priority=5  # Medium priority
                    )
        
        # No intention generated
        return None

