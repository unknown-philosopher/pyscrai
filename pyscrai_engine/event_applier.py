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
        entity = self.engine.get_entity(event.target_id)
        if not entity:
            raise ValueError(f"Entity {event.target_id} not found")
            
        if not entity.state:
            raise ValueError(f"Entity {event.target_id} has no state component")
            
        # Parse resources
        resources = json.loads(entity.state.resources_json) if entity.state.resources_json else {}
        
        # Parse new value (it's a JSON string)
        try:
            new_value = json.loads(event.new_value) if event.new_value else None
        except json.JSONDecodeError:
            # If not JSON, treat as string
            new_value = event.new_value
        
        # Apply change to field (supports dot notation for nested resources)
        if "." in event.field_name:
            # Handle nested paths like "resources_json.mana"
            parts = event.field_name.split(".")
            if parts[0] == "resources_json" and len(parts) == 2:
                resources[parts[1]] = new_value
            else:
                raise ValueError(f"Unsupported field path: {event.field_name}")
        else:
            # Direct field in resources_json
            resources[event.field_name] = new_value
            
        entity_name = entity.descriptor.name if entity.descriptor else event.target_id
        print(f"[EventApplier] Set {entity_name}.{event.field_name} = {new_value}")
            
        # Save back
        entity.state.resources_json = json.dumps(resources)
        
    def _apply_relationship_change(self, event: RelationshipChangeEvent) -> None:
        """Apply a relationship change event.
        
        Creates, updates, or deletes relationships between entities.
        """
        # Find existing relationship (check both directions)
        existing = None
        for rel in self.engine.relationships:
            if (rel.source_id == event.source_id and rel.target_id == event.target_id) or \
               (rel.source_id == event.target_id and rel.target_id == event.source_id):
                existing = rel
                break
                
        # Map RelationshipChangeType to RelationshipType
        from pyscrai_core import RelationshipType
        type_mapping = {
            "alliance_formed": RelationshipType.ALLIANCE,
            "alliance_broken": RelationshipType.ENMITY,  # Broken alliance becomes enmity
            "war_declared": RelationshipType.ENMITY,
            "peace_treaty": RelationshipType.ALLIANCE,
            "trade_agreement": RelationshipType.TRADE,
            "trade_embargo": RelationshipType.ENMITY,
            "vassalization": RelationshipType.COMMANDS,
            "independence": RelationshipType.CUSTOM,
            "hostile_action": RelationshipType.ENMITY,
            "cooperation": RelationshipType.ALLIANCE,
            "custom": RelationshipType.CUSTOM,
        }
        
        new_relationship_type = type_mapping.get(event.change_type.value, RelationshipType.CUSTOM)
        
        if existing:
            # Update existing relationship
            old_type = existing.relationship_type
            existing.relationship_type = new_relationship_type
            # Update metadata if provided
            if event.metadata_json:
                try:
                    metadata = json.loads(event.metadata_json)
                    existing.metadata = json.dumps({**existing.metadata_dict, **metadata})
                except json.JSONDecodeError:
                    pass
                    
            source_entity = self.engine.get_entity(event.source_id)
            target_entity = self.engine.get_entity(event.target_id)
            source_name = source_entity.descriptor.name if source_entity and source_entity.descriptor else event.source_id
            target_name = target_entity.descriptor.name if target_entity and target_entity.descriptor else event.target_id
            print(f"[EventApplier] Updated relationship between {source_name} and {target_name}: {old_type} → {new_relationship_type}")
        else:
            # Create new relationship
            new_rel = Relationship(
                source_id=event.source_id,
                target_id=event.target_id,
                relationship_type=new_relationship_type,
                strength=0.5,  # Default strength
                metadata=event.metadata_json if event.metadata_json else "{}"
            )
            self.engine.relationships.append(new_rel)
            source_entity = self.engine.get_entity(event.source_id)
            target_entity = self.engine.get_entity(event.target_id)
            source_name = source_entity.descriptor.name if source_entity and source_entity.descriptor else event.source_id
            target_name = target_entity.descriptor.name if target_entity and target_entity.descriptor else event.target_id
            print(f"[EventApplier] Created new relationship between {source_name} and {target_name}: {new_relationship_type}")
            
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
