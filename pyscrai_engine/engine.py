"""PyScrAI Engine - Core simulation engine.

The SimulationEngine is the heart of PyScrAI's runtime system. It:
1. Loads Forge projects (world.db, project.json)
2. Maintains current world state
3. Runs the turn-based simulation loop
4. Processes intentions → events → state changes
5. Manages agents, memory, and narrative logging

Architecture:
- Uses pyscrai_core models (Entity, Event, Intention, Memory)
- Delegates to TurnProcessor for turn resolution
- Maintains separation between async intentions and sync events
"""

from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, UTC

from pyscrai_core import (
    ProjectController,
    ProjectManifest,
    Entity,
    Relationship,
    EntityType,
    Event,
    Turn,
    WorldSnapshot
)
from pyscrai_core.intentions import Intention, IntentionStatus


class SimulationEngine:
    """Core simulation engine for PyScrAI.
    
    Responsibilities:
    - Project lifecycle (load, save, snapshot)
    - World state management (entities, relationships, turn counter)
    - Turn loop orchestration
    - Agent coordination
    
    Usage:
        engine = SimulationEngine(project_path)
        engine.initialize()
        engine.run(max_turns=100)
    """
    
    def __init__(self, project_path: Path):
        """Initialize engine with a Forge project.
        
        Args:
            project_path: Path to project directory containing world.db and project.json
        """
        self.project_path = Path(project_path)
        self.controller: Optional[ProjectController] = None
        self.manifest: Optional[ProjectManifest] = None
        
        # Simulation state
        self.current_turn: int = 0
        self.is_running: bool = False
        self.is_paused: bool = False
        
        # World state cache (loaded from DB)
        self.entities: Dict[str, Entity] = {}
        self.relationships: List[Relationship] = []
        
        # Turn data
        self.current_turn_intentions: List[Intention] = []
        self.current_turn_events: List[Event] = []
        self.turn_history: List[Turn] = []
        
        # Components (initialized in initialize())
        self.turn_processor = None
        self.intention_validator = None
        self.event_applier = None
        self.world_query = None
        self.narrator = None
        
        # Agent configuration
        self.enable_agents = False  # Set to True to enable rule-based agents
        
    def initialize(self) -> None:
        """Load project and initialize all subsystems.
        
        Raises:
            FileNotFoundError: If project files don't exist
            ValueError: If project configuration is invalid
        """
        if not self.project_path.exists():
            raise FileNotFoundError(f"Project path not found: {self.project_path}")
        
        # Load project
        self.controller = ProjectController(self.project_path)
        self.manifest = self.controller.load_project()
        
        print(f"[Engine] Loaded project: {self.manifest.name}")
        print(f"[Engine] Schema version: {self.manifest.schema_version}")
        
        # Load world state
        self._load_world_state()
        
        # Initialize subsystems (will be created in next steps)
        from .turn_processor import TurnProcessor
        from .intention_validator import IntentionValidator
        from .event_applier import EventApplier
        from .world_state import WorldStateQuery
        from .narrator import NarratorAgent
        
        self.intention_validator = IntentionValidator(self)
        self.event_applier = EventApplier(self)
        self.turn_processor = TurnProcessor(self)
        self.world_query = WorldStateQuery(self)
        self.narrator = NarratorAgent(self)
        
        print(f"[Engine] Initialized with {len(self.entities)} entities, {len(self.relationships)} relationships")
        
    def _load_world_state(self) -> None:
        """Load entities and relationships from database."""
        # Load all entities
        all_entities = self.controller.get_all_entities()
        # Index by entity ID (DescriptorComponent has no id field)
        self.entities = {e.id: e for e in all_entities}
        
        # Load all relationships
        self.relationships = self.controller.get_all_relationships()
        
    def submit_intention(self, intention: Intention) -> None:
        """Submit an intention for processing in the next turn.
        
        Args:
            intention: Intention to process
        """
        self.current_turn_intentions.append(intention)
        
    def step(self) -> Turn:
        """Execute one simulation turn.
        
        Returns:
            Turn object containing all events and narrative for this turn
        """
        turn_start = datetime.now(UTC)
        
        print(f"\n[Engine] === Turn {self.current_turn + 1} ===")
        
        # Generate agent intentions if enabled
        if self.enable_agents:
            self._generate_agent_intentions()
        
        # Process turn
        turn_result = self.turn_processor.process_turn(
            self.current_turn_intentions,
            self.current_turn
        )
        
        # Generate and save narrative
        if self.narrator:
            try:
                narrative_path = self.narrator.save_turn_narrative(turn_result, self.project_path)
                print(f"[Engine] Narrative saved to {narrative_path}")
            except Exception as e:
                print(f"[Engine] Failed to save narrative: {e}")
        
        # Store events
        self.current_turn_events = turn_result.events
        self.turn_history.append(turn_result)
        
        # Clear intentions for next turn
        self.current_turn_intentions.clear()
        
        # Increment turn counter
        self.current_turn += 1
        
        # Create snapshot if needed
        if self.current_turn % self.manifest.snapshot_interval == 0:
            self._create_snapshot()
        
        turn_end = datetime.now(UTC)
        duration = (turn_end - turn_start).total_seconds()
        
        print(f"[Engine] Turn {self.current_turn} completed in {duration:.2f}s")
        print(f"[Engine] Processed {len(turn_result.events)} events")
        
        return turn_result
    
    def _generate_agent_intentions(self) -> None:
        """Generate intentions from rule-based agents.
        
        Iterates through all actors and asks agents to generate intentions.
        """
        from .agents.rule_based import BasicNeedsAgent
        
        # Get all actors
        actors = self.get_entities_by_type(EntityType.ACTOR)
        
        if not actors:
            return
        
        # Create agent instance
        agent = BasicNeedsAgent()
        
        # Generate intentions for each actor
        for actor in actors:
            try:
                intention = agent.generate_intention(actor, self.world_query)
                if intention:
                    self.submit_intention(intention)
                    print(f"[Engine] Agent generated intention for {actor.descriptor.name if actor.descriptor else actor.id}")
            except Exception as e:
                print(f"[Engine] Agent failed to generate intention for {actor.id}: {e}")
        
    def run(self, max_turns: int = 100, stop_condition=None) -> None:
        """Run simulation for multiple turns.
        
        Args:
            max_turns: Maximum number of turns to execute
            stop_condition: Optional callable that returns True when simulation should stop
        """
        self.is_running = True
        
        print(f"[Engine] Starting simulation for up to {max_turns} turns")
        
        try:
            while self.is_running and self.current_turn < max_turns:
                # Check pause state
                if self.is_paused:
                    continue
                
                # Check stop condition
                if stop_condition and stop_condition(self):
                    print(f"[Engine] Stop condition met at turn {self.current_turn}")
                    break
                
                # Execute turn
                self.step()
                
        except KeyboardInterrupt:
            print(f"\n[Engine] Simulation interrupted by user at turn {self.current_turn}")
        except Exception as e:
            print(f"\n[Engine] Simulation error at turn {self.current_turn}: {e}")
            self._emergency_save()
            raise
        finally:
            self.is_running = False
            
        print(f"[Engine] Simulation ended at turn {self.current_turn}")
        
    def pause(self) -> None:
        """Pause the simulation."""
        self.is_paused = True
        print("[Engine] Simulation paused")
        
    def resume(self) -> None:
        """Resume the simulation."""
        self.is_paused = False
        print("[Engine] Simulation resumed")
        
    def stop(self) -> None:
        """Stop the simulation gracefully."""
        self.is_running = False
        print("[Engine] Stopping simulation...")
        
    def _create_snapshot(self) -> None:
        """Create a world snapshot for this turn."""
        import json
        entity_states = {}
        for eid, e in self.entities.items():
            if e.state:
                entity_states[eid] = {
                    "resources_json": e.state.resources_json,
                    "region_version": e.state.region_version,
                }
        
        snapshot = WorldSnapshot(
            tick=self.current_turn,
            entities_json=json.dumps(entity_states),
            relationships_json=json.dumps([r.model_dump() for r in self.relationships])
        )
        # TODO: Save to database (requires snapshot table in pyscrai_core)
        print(f"[Engine] Created snapshot at turn {self.current_turn}")
        
    def _emergency_save(self) -> None:
        """Emergency save when simulation crashes."""
        try:
            emergency_path = self.project_path / "logs" / f"emergency_save_turn_{self.current_turn}.json"
            emergency_path.parent.mkdir(exist_ok=True, parents=True)
            
            import json
            with open(emergency_path, 'w') as f:
                json.dump({
                    "turn": self.current_turn,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "entity_count": len(self.entities),
                    "relationship_count": len(self.relationships)
                }, f, indent=2)
                
            print(f"[Engine] Emergency save written to {emergency_path}")
        except Exception as e:
            print(f"[Engine] Emergency save failed: {e}")
            
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID.
        
        Args:
            entity_id: Entity ID to lookup
            
        Returns:
            Entity if found, None otherwise
        """
        return self.entities.get(entity_id)
        
    def get_entities_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Get all entities of a specific type.
        
        Args:
            entity_type: Type to filter by
            
        Returns:
            List of entities matching the type
        """
        return [e for e in self.entities.values() if e.entity_type == entity_type]
        
    def get_relationships_for_entity(self, entity_id: str) -> List[Relationship]:
        """Get all relationships involving an entity.
        
        Args:
            entity_id: Entity ID to lookup
            
        Returns:
            List of relationships where entity is source or target
        """
        return [
            r for r in self.relationships 
            if r.source_id == entity_id or r.target_id == entity_id
        ]
