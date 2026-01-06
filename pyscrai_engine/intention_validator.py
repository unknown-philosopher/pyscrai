"""Intention validation for PyScrAI Engine.

The IntentionValidator ensures that all intentions are valid before they
are converted to events. This prevents invalid state changes and provides
meaningful feedback to agents when their intentions are rejected.

Validation checks:
- Entity existence and accessibility
- Resource availability and schema compliance
- Spatial constraints (location, movement paths)
- Relationship constraints
- Project-specific rules from manifest
"""

import json
from typing import Tuple, TYPE_CHECKING

from pyscrai_core import EntityType
from pyscrai_core.intentions import (
    Intention,
    MoveIntention,
    AttackIntention,
    ResourceTransferIntention,
    ChangeRelationshipIntention,
    SpeakIntention,
    CustomIntention
)

if TYPE_CHECKING:
    from .engine import SimulationEngine


class IntentionValidator:
    """Validates intentions against current world state and project rules.
    
    Each intention type has its own validation logic. The validator checks:
    - Entity existence
    - Resource constraints
    - Spatial rules
    - Relationship rules
    - Project-specific constraints
    """
    
    def __init__(self, engine: "SimulationEngine"):
        """Initialize validator.
        
        Args:
            engine: Parent simulation engine
        """
        self.engine = engine
        
    def validate(self, intention: Intention) -> Tuple[bool, str]:
        """Validate an intention.
        
        Args:
            intention: Intention to validate
            
        Returns:
            Tuple of (is_valid, rejection_reason)
            If valid, rejection_reason will be empty string
        """
        # Route to appropriate validation method
        if isinstance(intention, MoveIntention):
            return self._validate_move(intention)
        elif isinstance(intention, ResourceTransferIntention):
            return self._validate_resource_transfer(intention)
        elif isinstance(intention, ChangeRelationshipIntention):
            return self._validate_relationship_change(intention)
        elif isinstance(intention, AttackIntention):
            return self._validate_attack(intention)
        elif isinstance(intention, SpeakIntention):
            return self._validate_speak(intention)
        elif isinstance(intention, CustomIntention):
            return self._validate_custom(intention)
        else:
            return False, f"Unknown intention type: {type(intention)}"
            
    def _validate_move(self, intention: MoveIntention) -> Tuple[bool, str]:
        """Validate a movement intention.
        
        Checks:
        - Actor exists and is an Actor type
        - Target location exists
        - Actor is currently in a location (has spatial component)
        - TODO: Path exists between locations
        """
        # Check actor exists
        actor = self.engine.get_entity(intention.source_id)
        if not actor:
            return False, f"Actor {intention.source_id} does not exist"
            
        if actor.entity_type != EntityType.ACTOR:
            return False, f"Entity {intention.source_id} is not an Actor"
            
        # Check target location exists
        target = self.engine.get_entity(intention.target_location_id)
        if not target:
            return False, f"Location {intention.target_location_id} does not exist"
            
        if target.entity_type != EntityType.LOCATION:
            return False, f"Target {intention.target_location_id} is not a Location"
            
        # Check actor has spatial component
        if not actor.spatial:
            return False, f"Actor {intention.source_id} has no spatial component"
            
        # Get current location
        current_location = actor.spatial.current_location_id
        if not current_location:
            return False, f"Actor {intention.source_id} is not in any location"
            
        # Check not already at target
        if current_location == intention.target_location_id:
            return False, f"Actor {intention.source_id} is already at {intention.target_location_id}"
            
        # TODO: Check path exists using region graph
        # For now, allow all movements
        
        return True, ""
        
    def _validate_resource_transfer(self, intention: ResourceTransferIntention) -> Tuple[bool, str]:
        """Validate a resource transfer intention.
        
        Checks:
        - Source and target entities exist
        - Resource type is in project schema
        - Source has enough of the resource
        - Amount is positive
        """
        # Check source entity exists
        source = self.engine.get_entity(intention.source_id)
        if not source:
            return False, f"Source entity {intention.source_id} does not exist"
            
        # Check target entity exists
        target = self.engine.get_entity(intention.target_id)
        if not target:
            return False, f"Target entity {intention.target_id} does not exist"
            
        # Check amount is positive
        if intention.amount <= 0:
            return False, "Transfer amount must be positive"
            
        # Get project schema for entity type
        entity_type_str = source.entity_type.value if source.entity_type else "abstract"
        schema = self.engine.manifest.entity_schemas.get(entity_type_str, {})
        
        # Check resource type exists in schema (if schema is defined, otherwise allow any)
        if schema and intention.resource_type not in schema:
            return False, f"Resource '{intention.resource_type}' not in schema for {entity_type_str}"
            
        # Check source has enough resources
        if not source.state:
            return False, f"Source entity {intention.source_id} has no state component"
            
        try:
            resources = json.loads(source.state.resources_json) if source.state.resources_json else {}
            current_amount = resources.get(intention.resource_type, 0)
            
            if current_amount < intention.amount:
                return False, f"Insufficient {intention.resource_type}: has {current_amount}, needs {intention.amount}"
                
        except json.JSONDecodeError:
            return False, f"Invalid resources_json for entity {intention.source_id}"
            
        return True, ""
        
    def _validate_relationship_change(self, intention: ChangeRelationshipIntention) -> Tuple[bool, str]:
        """Validate a relationship change intention.
        
        Checks:
        - Both entities exist
        - Relationship exists if updating
        - New relationship type is valid
        """
        # Check source entity exists
        source = self.engine.get_entity(intention.source_id)
        if not source:
            return False, f"Source entity {intention.source_id} does not exist"
            
        # Check target entity exists
        target = self.engine.get_entity(intention.target_id)
        if not target:
            return False, f"Target entity {intention.target_id} does not exist"
            
        # Check can't create relationship with self
        if intention.source_id == intention.target_id:
            return False, "Cannot create relationship with self"
            
        # Validate new relationship type (basic check - should be a valid string)
        if not intention.new_relationship_type or not intention.new_relationship_type.strip():
            return False, "New relationship type cannot be empty"
            
        # TODO: Check relationship exists if old_type is specified
        # TODO: Validate new relationship type against RelationshipChangeType enum
        
        return True, ""
        
    def _validate_attack(self, intention: AttackIntention) -> Tuple[bool, str]:
        """Validate an attack intention.
        
        Checks:
        - Attacker and target exist
        - Both are actors
        - Both are in same location
        - TODO: Check combat rules from project manifest
        """
        # Check attacker exists
        attacker = self.engine.get_entity(intention.source_id)
        if not attacker:
            return False, f"Attacker {intention.source_id} does not exist"
            
        if attacker.entity_type != EntityType.ACTOR:
            return False, f"Attacker {intention.source_id} is not an Actor"
            
        # Check target exists
        target = self.engine.get_entity(intention.target_id)
        if not target:
            return False, f"Target {intention.target_id} does not exist"
            
        if target.entity_type != EntityType.ACTOR:
            return False, f"Target {intention.target_id} is not an Actor"
            
        # Check both in same location
        if attacker.spatial and target.spatial:
            if attacker.spatial.current_location_id != target.spatial.current_location_id:
                return False, "Attacker and target must be in same location"
                
        # TODO: Check combat-specific rules from manifest
        
        return True, ""
        
    def _validate_speak(self, intention: SpeakIntention) -> Tuple[bool, str]:
        """Validate a speak intention.
        
        Checks:
        - Speaker exists
        - Target exists if specified
        - Message is not empty
        """
        # Check speaker exists
        speaker = self.engine.get_entity(intention.source_id)
        if not speaker:
            return False, f"Speaker {intention.source_id} does not exist"
            
        # Check message not empty
        if not intention.message or not intention.message.strip():
            return False, "Message cannot be empty"
            
        # Check target if specified
        if intention.target_id:
            target = self.engine.get_entity(intention.target_id)
            if not target:
                return False, f"Target {intention.target_id} does not exist"
                
        return True, ""
        
    def _validate_custom(self, intention: CustomIntention) -> Tuple[bool, str]:
        """Validate a custom intention.
        
        Custom intentions are project-specific, so validation is minimal.
        Project-specific validators can be added here.
        """
        # Check source entity exists
        source = self.engine.get_entity(intention.source_id)
        if not source:
            return False, f"Source entity {intention.source_id} does not exist"
            
        # TODO: Add hooks for project-specific custom validation
        
        return True, ""
