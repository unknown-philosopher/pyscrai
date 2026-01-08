"""Narrative generation for PyScrAI Engine.

Generates human-readable summaries of simulation turns.
"""

from pathlib import Path
from typing import List, TYPE_CHECKING
from datetime import datetime, UTC

from pyscrai_core import Event, Turn, NarrativeLogEntry

if TYPE_CHECKING:
    from .engine import SimulationEngine


class NarratorAgent:
    """Generates narrative summaries of simulation turns.
    
    Creates prose descriptions of events and saves them to markdown files.
    """
    
    def __init__(self, engine: "SimulationEngine"):
        """Initialize narrator agent.
        
        Args:
            engine: Parent simulation engine
        """
        self.engine = engine
    
    def summarize_turn(
        self, 
        events: List[Event], 
        turn_number: int,
        entities_dict: dict = None
    ) -> str:
        """Generate a prose summary of a turn.
        
        Args:
            events: List of events that occurred in the turn
            turn_number: Turn number
            entities_dict: Optional dictionary of entity_id -> Entity for lookups
            
        Returns:
            Markdown-formatted summary string
        """
        if entities_dict is None:
            entities_dict = self.engine.entities
        
        lines = [f"# Turn {turn_number} Summary", ""]
        
        if not events:
            lines.append("**No events occurred this turn.**")
            return "\n".join(lines)
        
        lines.append("**Events:**")
        lines.append("")
        
        for event in events:
            entity = entities_dict.get(event.source_id)
            entity_name = entity.descriptor.name if entity and entity.descriptor else event.source_id
            
            if event.event_type == "movement":
                from_loc = entities_dict.get(event.from_location_id) if hasattr(event, 'from_location_id') else None
                to_loc = entities_dict.get(event.to_location_id) if hasattr(event, 'to_location_id') else None
                from_name = from_loc.descriptor.name if from_loc and from_loc.descriptor else getattr(event, 'from_location_id', 'unknown')
                to_name = to_loc.descriptor.name if to_loc and to_loc.descriptor else getattr(event, 'to_location_id', 'unknown')
                lines.append(f"- {entity_name} moved from {from_name} to {to_name} (MovementEvent)")
                
            elif event.event_type == "resource_transfer":
                from_entity = entities_dict.get(event.from_id) if hasattr(event, 'from_id') else None
                to_entity = entities_dict.get(event.to_id) if hasattr(event, 'to_id') else None
                from_name = from_entity.descriptor.name if from_entity and from_entity.descriptor else getattr(event, 'from_id', 'unknown')
                to_name = to_entity.descriptor.name if to_entity and to_entity.descriptor else getattr(event, 'to_id', 'unknown')
                amount = getattr(event, 'amount', 0)
                resource_type = getattr(event, 'resource_type', 'resources')
                lines.append(f"- {from_name} transferred {amount} {resource_type} to {to_name} (ResourceTransferEvent)")
                
            elif event.event_type == "relationship_change":
                target_entity = entities_dict.get(event.target_id) if hasattr(event, 'target_id') else None
                target_name = target_entity.descriptor.name if target_entity and target_entity.descriptor else getattr(event, 'target_id', 'unknown')
                change_type = getattr(event, 'change_type', None)
                if change_type:
                    change_str = change_type.value if hasattr(change_type, 'value') else str(change_type)
                else:
                    change_str = "changed"
                lines.append(f"- {entity_name} and {target_name} relationship: {change_str} (RelationshipChangeEvent)")
                
            elif event.event_type == "state_change":
                target_entity = entities_dict.get(event.target_id) if hasattr(event, 'target_id') else None
                target_name = target_entity.descriptor.name if target_entity and target_entity.descriptor else getattr(event, 'target_id', 'unknown')
                field_name = getattr(event, 'field_name', 'state')
                new_value = getattr(event, 'new_value', 'unknown')
                lines.append(f"- {target_name}'s {field_name} changed to {new_value} (StateChangeEvent)")
                
            else:
                description = getattr(event, 'description', '')
                if description:
                    lines.append(f"- {description} ({event.event_type})")
                else:
                    lines.append(f"- Event: {event.event_type}")
        
        lines.append("")
        lines.append("**Key Outcomes:**")
        lines.append("")
        
        # Extract key outcomes from events
        outcomes = []
        for event in events:
            if event.event_type == "resource_transfer":
                from_entity = entities_dict.get(event.from_id) if hasattr(event, 'from_id') else None
                to_entity = entities_dict.get(event.to_id) if hasattr(event, 'to_id') else None
                from_name = from_entity.descriptor.name if from_entity and from_entity.descriptor else getattr(event, 'from_id', 'unknown')
                to_name = to_entity.descriptor.name if to_entity and to_entity.descriptor else getattr(event, 'to_id', 'unknown')
                amount = getattr(event, 'amount', 0)
                resource_type = getattr(event, 'resource_type', 'resources')
                outcomes.append(f"- {from_name}'s {resource_type} decreased by {amount}")
                outcomes.append(f"- {to_name}'s {resource_type} increased by {amount}")
            elif event.event_type == "relationship_change":
                target_entity = entities_dict.get(event.target_id) if hasattr(event, 'target_id') else None
                target_name = target_entity.descriptor.name if target_entity and target_entity.descriptor else getattr(event, 'target_id', 'unknown')
                source_entity = entities_dict.get(event.source_id)
                source_name = source_entity.descriptor.name if source_entity and source_entity.descriptor else event.source_id
                change_type = getattr(event, 'change_type', None)
                if change_type:
                    change_str = change_type.value if hasattr(change_type, 'value') else str(change_type)
                    outcomes.append(f"- A new relationship was formed: {source_name} ↔ {target_name} ({change_str})")
        
        if outcomes:
            lines.extend(outcomes)
        else:
            lines.append("- No significant state changes")
        
        lines.append("")
        lines.append(f"*Generated at {datetime.now(UTC).isoformat()}*")
        
        return "\n".join(lines)
    
    def save_turn_narrative(self, turn: Turn, project_path: Path) -> Path:
        """Save turn narrative to file.
        
        Args:
            turn: Turn object with events and narrative
            project_path: Project root path
            
        Returns:
            Path to saved narrative file
        """
        logs_dir = project_path / "logs"
        logs_dir.mkdir(exist_ok=True, parents=True)
        
        narrative_file = logs_dir / f"turn_{turn.tick}_summary.md"
        
        # Generate summary
        summary = self.summarize_turn(turn.applied_events, turn.tick)
        
        # Write to file
        narrative_file.write_text(summary, encoding="utf-8")
        
        return narrative_file

