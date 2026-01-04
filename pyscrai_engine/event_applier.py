"""Event application for PyScrAI Engine.

The EventApplier mutates entity state based on events. This is the only
place where StateComponent should be modified during simulation.

Guardrail 3: Event-First Mutation
> All state changes must flow through immutable Events.
> This module is the sole authority on applying those events.
"""

import json
from typing import TYPE_CHECKING

from pyscrai_core.events import (
    Event,
    MovementEvent,
    ResourceTransferEvent,
    StateChangeEvent,
    RelationshipChangeEvent,
    CustomEvent
)
from pyscrai_core import Relationship, RelationshipType

if TYPE_CHECKING:
    from .engine import SimulationEngine


class EventApplier:
    """Applies events to entity state.
    
    This is the ONLY component that should mutate StateComponent during simulation.
    All state changes flow through Events to maintain determinism and replayability.
    """
    
    def __init__(self, engine: "SimulationEngine"):
        """Initialize event applier.
        
        Args:
            engine: Parent simulation engine
        """
        self.engine = engine
        
    def apply_event(self, event: Event) -> None:
        """Apply an event to world state.
        
        Args:
            event: Event to apply
            
        Raises:
            ValueError: If event cannot be applied
        """
        # Route to appropriate application method
        if isinstance(event, MovementEvent):
            self._apply_movement(event)
        elif isinstance(event, ResourceTransferEvent):
            self._apply_resource_transfer(event)
        elif isinstance(event, StateChangeEvent):
            self._apply_state_change(event)
        elif isinstance(event, RelationshipChangeEvent):
            self._apply_relationship_change(event)
        elif isinstance(event, CustomEvent):
            self._apply_custom(event)
        else:
            raise ValueError(f"Unknown event type: {type(event)}")
            
    def _apply_movement(self, event: MovementEvent) -> None:
        """Apply a movement event.
        
        Updates the actor's SpatialComponent.current_location_id
        """
        actor = self.engine.get_entity(event.actor_id)
        if not actor:
            raise ValueError(f"Actor {event.actor_id} not found")
            
        if not actor.spatial:
            raise ValueError(f"Actor {event.actor_id} has no spatial component")
            
        # Update location
        old_location = actor.spatial.current_location_id
        actor.spatial.current_location_id = event.to_location_id
        
        print(f"[EventApplier] {actor.descriptor.name} moved from {old_location} to {event.to_location_id}")
        
    def _apply_resource_transfer(self, event: ResourceTransferEvent) -> None:
        """Apply a resource transfer event.
        
        Modifies StateComponent.resources_json for both source and target.
        """
        # Get entities
        source = self.engine.get_entity(event.from_id)
        target = self.engine.get_entity(event.to_id)
        
        if not source:
            raise ValueError(f"Source entity {event.from_id} not found")
        if not target:
            raise ValueError(f"Target entity {event.to_id} not found")
            
        # Parse source resources
        source_resources = json.loads(source.state.resources_json) if source.state.resources_json else {}
        
        # Parse target resources
        target_resources = json.loads(target.state.resources_json) if target.state.resources_json else {}
        
        # Deduct from source
        current_amount = source_resources.get(event.resource_type, 0)
        new_source_amount = current_amount - event.amount
        
        if new_source_amount < 0:
            raise ValueError(f"Insufficient {event.resource_type} in source entity")
            
        source_resources[event.resource_type] = new_source_amount
        
        # Add to target
        target_current = target_resources.get(event.resource_type, 0)
        target_resources[event.resource_type] = target_current + event.amount
        
        # Save back to entities
        source.state.resources_json = json.dumps(source_resources)
        target.state.resources_json = json.dumps(target_resources)
        
        print(f"[EventApplier] Transferred {event.amount} {event.resource_type} from {source.descriptor.name} to {target.descriptor.name}")
        
    def _apply_state_change(self, event: StateChangeEvent) -> None:
        """Apply a generic state change event.
        
        Modifies StateComponent.resources_json based on event fields.
        """
        entity = self.engine.get_entity(event.entity_id)
        if not entity:
            raise ValueError(f"Entity {event.entity_id} not found")
            
        # Parse resources
        resources = json.loads(entity.state.resources_json) if entity.state.resources_json else {}
        
        # Apply changes
        for field, value in event.changes.items():
            resources[field] = value
            print(f"[EventApplier] Set {entity.descriptor.name}.{field} = {value}")
            
        # Save back
        entity.state.resources_json = json.dumps(resources)
        
    def _apply_relationship_change(self, event: RelationshipChangeEvent) -> None:
        """Apply a relationship change event.
        
        Creates, updates, or deletes relationships between entities.
        """
        # Find existing relationship
        existing = None
        for rel in self.engine.relationships:
            if (rel.source_id == event.entity_a_id and rel.target_id == event.entity_b_id) or \
               (rel.source_id == event.entity_b_id and rel.target_id == event.entity_a_id):
                existing = rel
                break
                
        if existing:
            # Update existing relationship
            old_type = existing.relationship_type
            existing.relationship_type = event.new_type
            print(f"[EventApplier] Updated relationship between {event.entity_a_id} and {event.entity_b_id}: {old_type} → {event.new_type}")
        else:
            # Create new relationship
            new_rel = Relationship(
                source_id=event.entity_a_id,
                target_id=event.entity_b_id,
                relationship_type=event.new_type,
                strength=0.5  # Default strength
            )
            self.engine.relationships.append(new_rel)
            print(f"[EventApplier] Created new relationship between {event.entity_a_id} and {event.entity_b_id}: {event.new_type}")
            
    def _apply_custom(self, event: CustomEvent) -> None:
        """Apply a custom event.
        
        Custom events are project-specific. This method provides a hook for
        extending the engine with custom event types.
        """
        print(f"[EventApplier] Applied custom event: {event.event_subtype}")
        
        # TODO: Add hooks for project-specific custom event handlers
        # For now, custom events are logged but don't modify state
        
        # Example: You could implement a registry of custom event handlers
        # handler = self.custom_handlers.get(event.event_subtype)
        # if handler:
        #     handler(event, self.engine)
