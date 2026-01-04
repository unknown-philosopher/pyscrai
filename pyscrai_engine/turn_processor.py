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
        
        # Process each intention
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
                
            # Apply event to world state
            try:
                self.engine.event_applier.apply_event(event)
                intention.status = IntentionStatus.CONVERTED
                events.append(event)
                
                # Generate narrative entry
                narrative_entry = self._generate_narrative_entry(event, turn_number)
                if narrative_entry:
                    narrative_entries.append(narrative_entry)
                    
            except Exception as e:
                print(f"[TurnProcessor] Failed to apply event: {e}")
                intention.status = IntentionStatus.REJECTED
                intention.rejection_reason = f"Event application failed: {e}"
                rejected_count += 1
        
        # Commit changes to database
        self._commit_turn_changes()
        
        print(f"[TurnProcessor] Applied {len(events)} events, rejected {rejected_count} intentions")
        
        # Create Turn object
        turn = Turn(
            turn_number=turn_number,
            events=events,
            narrative=narrative_entries
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
                return MovementEvent(
                    source_id=intention.source_id,
                    actor_id=intention.source_id,
                    from_location_id=intention.from_location_id,
                    to_location_id=intention.target_location_id,
                    region_id=intention.region_id or "unknown",
                    region_version_at_time=0,  # TODO: Implement region versioning
                    description=f"Actor {intention.source_id} moves to {intention.target_location_id}"
                )
                
            elif isinstance(intention, ResourceTransferIntention):
                return ResourceTransferEvent(
                    source_id=intention.source_id,
                    from_id=intention.from_id,
                    to_id=intention.to_id,
                    resource_type=intention.resource_type,
                    amount=intention.amount,
                    description=f"Transfer {intention.amount} {intention.resource_type} from {intention.from_id} to {intention.to_id}"
                )
                
            elif isinstance(intention, ChangeRelationshipIntention):
                return RelationshipChangeEvent(
                    source_id=intention.source_id,
                    entity_a_id=intention.entity_a_id,
                    entity_b_id=intention.entity_b_id,
                    old_type=intention.old_type,
                    new_type=intention.new_type,
                    description=f"Relationship changed from {intention.old_type} to {intention.new_type}"
                )
                
            elif isinstance(intention, CustomIntention):
                return CustomEvent(
                    source_id=intention.source_id,
                    event_subtype=intention.action_type,
                    payload=intention.parameters,
                    description=intention.description or f"Custom action: {intention.action_type}"
                )
                
            else:
                print(f"[TurnProcessor] Unknown intention type: {type(intention)}")
                return None
                
        except Exception as e:
            print(f"[TurnProcessor] Error converting intention to event: {e}")
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
        entity_name = entity.descriptor.name if entity else event.source_id
        
        # Build narrative text based on event type
        if isinstance(event, MovementEvent):
            from_loc = self.engine.get_entity(event.from_location_id)
            to_loc = self.engine.get_entity(event.to_location_id)
            from_name = from_loc.descriptor.name if from_loc else event.from_location_id
            to_name = to_loc.descriptor.name if to_loc else event.to_location_id
            
            text = f"{entity_name} traveled from {from_name} to {to_name}."
            
        elif isinstance(event, ResourceTransferEvent):
            from_entity = self.engine.get_entity(event.from_id)
            to_entity = self.engine.get_entity(event.to_id)
            from_name = from_entity.descriptor.name if from_entity else event.from_id
            to_name = to_entity.descriptor.name if to_entity else event.to_id
            
            text = f"{from_name} transferred {event.amount} {event.resource_type} to {to_name}."
            
        elif isinstance(event, RelationshipChangeEvent):
            entity_a = self.engine.get_entity(event.entity_a_id)
            entity_b = self.engine.get_entity(event.entity_b_id)
            name_a = entity_a.descriptor.name if entity_a else event.entity_a_id
            name_b = entity_b.descriptor.name if entity_b else event.entity_b_id
            
            text = f"The relationship between {name_a} and {name_b} changed from {event.old_type} to {event.new_type}."
            
        else:
            text = event.description or f"Event: {event.event_type}"
            
        return NarrativeLogEntry(
            turn_number=turn_number,
            event_id=event.id,
            severity="info",
            text=text,
            entities_involved=[event.source_id]
        )
        
    def _commit_turn_changes(self) -> None:
        """Commit all entity state changes to the database."""
        try:
            # Update all modified entities
            for entity in self.engine.entities.values():
                self.engine.controller.update_entity(entity)
                
            # Update all relationships
            for relationship in self.engine.relationships:
                # TODO: Add update_relationship method to ProjectController
                pass
                
            print("[TurnProcessor] Changes committed to database")
            
        except Exception as e:
            print(f"[TurnProcessor] Failed to commit changes: {e}")
            raise
