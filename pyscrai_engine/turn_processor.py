"""Turn processing for PyScrAI Engine.

The TurnProcessor is responsible for:
1. Collecting all pending intentions for a turn
2. Sorting by priority
3. Validating each intention
4. Converting valid intentions to events
5. Applying events to world state
6. Generating narrative log entries

This is the core of the simulation loop.
"""

from typing import List, TYPE_CHECKING
from datetime import datetime, UTC

from pyscrai_core import Event, Turn, NarrativeLogEntry
from pyscrai_core.intentions import (
    Intention,
    IntentionStatus,
    MoveIntention,
    AttackIntention,
    ResourceTransferIntention,
    ChangeRelationshipIntention,
    SpeakIntention,
    CustomIntention
)
from pyscrai_core.events import (
    MovementEvent,
    ResourceTransferEvent,
    StateChangeEvent,
    RelationshipChangeEvent,
    CustomEvent
)

if TYPE_CHECKING:
    from .engine import SimulationEngine


class TurnProcessor:
    """Processes intentions and applies events for each simulation turn.
    
    The turn processing pipeline:
    1. Sort intentions by priority (highest first)
    2. For each intention:
       - Validate against current world state
       - Convert to event if valid
       - Apply event to world state
    3. Generate narrative summary
    4. Return Turn object with all events and narrative
    """
    
    def __init__(self, engine: "SimulationEngine"):
        """Initialize turn processor.
        
        Args:
            engine: Parent simulation engine
        """
        self.engine = engine
        
    def process_turn(self, intentions: List[Intention], turn_number: int) -> Turn:
        """Process all intentions for a single turn.
        
        Args:
            intentions: List of intentions to process
            turn_number: Current turn number
            
        Returns:
            Turn object containing events and narrative
        """
        # Sort by priority (highest first)
        sorted_intentions = sorted(intentions, key=lambda i: i.priority, reverse=True)
        
        events: List[Event] = []
        narrative_entries: List[NarrativeLogEntry] = []
        rejected_count = 0
        
        print(f"[TurnProcessor] Processing {len(sorted_intentions)} intentions")
        
        # Process each intention with transaction guard
        applied_events_in_turn = []
        try:
            for intention in sorted_intentions:
                # Validate intention
                is_valid, rejection_reason = self.engine.intention_validator.validate(intention)
                
                if not is_valid:
                    intention.status = IntentionStatus.REJECTED
                    intention.rejection_reason = rejection_reason
                    rejected_count += 1
                    print(f"[TurnProcessor] Rejected intention from {intention.source_id}: {rejection_reason}")
                    continue
                    
                # Convert to event
                event = self._convert_intention_to_event(intention)
                if event is None:
                    intention.status = IntentionStatus.REJECTED
                    intention.rejection_reason = "Failed to convert to event"
                    rejected_count += 1
                    continue
                    
                # Apply event to world state (within transaction)
                try:
                    self.engine.event_applier.apply_event(event)
                    intention.status = IntentionStatus.CONVERTED
                    events.append(event)
                    applied_events_in_turn.append(event)
                    
                    # Generate narrative entry
                    narrative_entry = self._generate_narrative_entry(event, turn_number)
                    if narrative_entry:
                        narrative_entries.append(narrative_entry)
                        
                except Exception as e:
                    print(f"[TurnProcessor] Failed to apply event: {e}")
                    # Rollback: revert all events applied in this turn
                    self._rollback_events(applied_events_in_turn)
                    raise RuntimeError(f"Event application failed, turn rolled back: {e}")
            
            # Commit changes to database (only if all events succeeded)
            self._commit_turn_changes()
            
        except Exception as e:
            # Transaction failed - rollback already done, but log it
            print(f"[TurnProcessor] Turn {turn_number} transaction failed: {e}")
            # Re-raise so turn is marked as failed
            raise
        
        print(f"[TurnProcessor] Applied {len(events)} events, rejected {rejected_count} intentions")
        
        # Create Turn object
        turn = Turn(
            tick=turn_number,
            applied_events=events,
            narrative=narrative_entries,
        )
        
        return turn
        
    def _convert_intention_to_event(self, intention: Intention) -> Event:
        """Convert a validated intention to an event.
        
        Args:
            intention: Validated intention
            
        Returns:
            Corresponding event, or None if conversion fails
        """
        try:
            if isinstance(intention, MoveIntention):
                # Get current location from actor's spatial component
                actor = self.engine.get_entity(intention.source_id)
                if not actor or not actor.spatial:
                    return None
                    
                # Try to get current_location_id, fallback to region_id or "unknown"
                from_location_id = getattr(actor.spatial, 'current_location_id', None)
                if not from_location_id:
                    # If no current_location_id, try to find it from relationships or use region_id
                    from_location_id = actor.spatial.region_id or "unknown"
                
                region_id = actor.spatial.region_id or "unknown"
                
                return MovementEvent(
                    source_id=intention.source_id,
                    actor_id=intention.source_id,
                    from_location_id=from_location_id,
                    to_location_id=intention.target_location_id,
                    region_id=region_id,
                    region_version_at_time=intention.path_region_version or 0,
                    description=f"Actor {intention.source_id} moves to {intention.target_location_id}"
                )
                
            elif isinstance(intention, ResourceTransferIntention):
                return ResourceTransferEvent(
                    source_id=intention.source_id,
                    from_id=intention.source_id,
                    to_id=intention.target_id,
                    resource_type=intention.resource_type,
                    amount=intention.amount,
                    description=f"Transfer {intention.amount} {intention.resource_type} from {intention.source_id} to {intention.target_id}"
                )
                
            elif isinstance(intention, ChangeRelationshipIntention):
                # Map new_relationship_type string to RelationshipChangeType enum
                from pyscrai_core.events import RelationshipChangeType
                change_type_map = {
                    "alliance": RelationshipChangeType.ALLIANCE_FORMED,
                    "war": RelationshipChangeType.WAR_DECLARED,
                    "peace": RelationshipChangeType.PEACE_TREATY,
                    "trade": RelationshipChangeType.TRADE_AGREEMENT,
                    "embargo": RelationshipChangeType.TRADE_EMBARGO,
                    "vassalization": RelationshipChangeType.VASSALIZATION,
                    "independence": RelationshipChangeType.INDEPENDENCE,
                    "hostile": RelationshipChangeType.HOSTILE_ACTION,
                    "cooperation": RelationshipChangeType.COOPERATION,
                }
                change_type = change_type_map.get(intention.new_relationship_type.lower(), RelationshipChangeType.CUSTOM)
                
                return RelationshipChangeEvent(
                    source_id=intention.source_id,
                    target_id=intention.target_id,
                    change_type=change_type,
                    old_relationship=None,  # TODO: Look up existing relationship
                    new_relationship=intention.new_relationship_type,
                    metadata_json=intention.metadata_json or "{}",
                    description=f"Relationship changed: {intention.new_relationship_type} between {intention.source_id} and {intention.target_id}"
                )
                
            elif isinstance(intention, CustomIntention):
                return CustomEvent(
                    source_id=intention.source_id,
                    action_type=intention.action_type,
                    target_id=None,  # CustomIntention doesn't have target_id
                    parameters_json=intention.parameters_json or "{}",
                    description=f"Custom action: {intention.action_type}"
                )
                
            else:
                print(f"[TurnProcessor] Unknown intention type: {type(intention)}")
                return None
                
        except Exception as e:
            print(f"[TurnProcessor] Error converting intention to event: {e}")
            import traceback
            traceback.print_exc()
            return None
            
    def _generate_narrative_entry(self, event: Event, turn_number: int) -> NarrativeLogEntry:
        """Generate a narrative log entry for an event.
        
        Args:
            event: Event to narrate
            turn_number: Current turn number
            
        Returns:
            NarrativeLogEntry describing the event
        """
        # Get entity name for better narrative
        entity = self.engine.get_entity(event.source_id)
        entity_name = entity.descriptor.name if entity and entity.descriptor else event.source_id
        
        # Build narrative text based on event type
        if isinstance(event, MovementEvent):
            from_loc = self.engine.get_entity(event.from_location_id)
            to_loc = self.engine.get_entity(event.to_location_id)
            from_name = from_loc.descriptor.name if from_loc and from_loc.descriptor else event.from_location_id
            to_name = to_loc.descriptor.name if to_loc and to_loc.descriptor else event.to_location_id
            
            summary = f"{entity_name} traveled from {from_name} to {to_name}."
            key_events = [f"Movement: {entity_name} → {to_name}"]
            
        elif isinstance(event, ResourceTransferEvent):
            from_entity = self.engine.get_entity(event.from_id)
            to_entity = self.engine.get_entity(event.to_id)
            from_name = from_entity.descriptor.name if from_entity and from_entity.descriptor else event.from_id
            to_name = to_entity.descriptor.name if to_entity and to_entity.descriptor else event.to_id
            
            summary = f"{from_name} transferred {event.amount} {event.resource_type} to {to_name}."
            key_events = [f"Transfer: {event.amount} {event.resource_type} from {from_name} to {to_name}"]
            
        elif isinstance(event, RelationshipChangeEvent):
            source_entity = self.engine.get_entity(event.source_id)
            target_entity = self.engine.get_entity(event.target_id)
            source_name = source_entity.descriptor.name if source_entity and source_entity.descriptor else event.source_id
            target_name = target_entity.descriptor.name if target_entity and target_entity.descriptor else event.target_id
            
            summary = f"The relationship between {source_name} and {target_name} changed: {event.change_type.value}."
            key_events = [f"Relationship: {source_name} ↔ {target_name} → {event.change_type.value}"]
            
        elif isinstance(event, StateChangeEvent):
            target_entity = self.engine.get_entity(event.target_id)
            target_name = target_entity.descriptor.name if target_entity and target_entity.descriptor else event.target_id
            
            summary = f"{target_name}'s {event.field_name} changed to {event.new_value}."
            key_events = [f"State change: {target_name}.{event.field_name}"]
            
        else:
            summary = event.description or f"Event: {event.event_type}"
            key_events = [event.event_type]
            
        return NarrativeLogEntry(
            turn_id=turn_number,
            summary=summary,
            key_events=key_events
        )
        
    def _commit_turn_changes(self) -> None:
        """Commit all entity state changes to the database.
        
        Note: Each update_entity/update_relationship call creates its own connection.
        For a true transaction, ProjectController would need to support transaction contexts.
        For now, we ensure all updates succeed before considering the turn committed.
        """
        if not self.engine.controller:
            return
            
        db_path = self.engine.controller.database_path
        if not db_path.exists():
            print("[TurnProcessor] Database not found, skipping commit")
            return
            
        try:
            # Update all modified entities
            for entity in self.engine.entities.values():
                self.engine.controller.update_entity(entity)
                
            # Update all relationships
            for relationship in self.engine.relationships:
                self.engine.controller.update_relationship(relationship)
            
            print("[TurnProcessor] Changes committed to database")
            
        except Exception as e:
            print(f"[TurnProcessor] Failed to commit changes: {e}")
            raise
    
    def _rollback_events(self, events: List[Event]) -> None:
        """Rollback events by reverting their effects.
        
        This is a simplified rollback - in a production system, you'd want
        to store state snapshots before applying events.
        """
        # For now, we'll just log the rollback
        # A full implementation would need to store pre-event state
        print(f"[TurnProcessor] Rolling back {len(events)} events")
        # TODO: Implement proper state snapshot/restore mechanism
