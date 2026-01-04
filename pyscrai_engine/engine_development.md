## **PyScrAI Engine Implementation Plan**

### **Phase 0: Foundation (Week 1)**

**Goal**: Create the basic Engine structure and turn loop

**Files to create**:
```
pyscrai_engine/
├── __init__.py           # Package exports
├── engine.py             # Main SimulationEngine class
├── turn_processor.py     # Turn resolution logic
├── intention_validator.py # Validates intentions against state
└── event_applier.py      # Applies events to entities
```

**Core Functionality**:
1. **SimulationEngine** class that:
   - Loads a Forge project (reads `world.db`, `project.json`)
   - Maintains current world state (entities, relationships)
   - Runs a turn loop
   - Processes intentions → events → state changes

2. **Turn Processor**:
   - Collects all pending intentions for a turn
   - Sorts by priority
   - Validates each intention
   - Converts valid intentions to events
   - Applies events to mutate entity states

3. **Basic CLI**:
   - `pyscrai run <project_path>` - Start simulation
   - `pyscrai step <project_path>` - Execute one turn
   - `pyscrai status <project_path>` - Show current state

---

### **Phase 1: Intention Processing (Week 2)**

**Goal**: Implement the full intention → event → state pipeline

**What to build**:
1. **IntentionValidator** - Validates each intention type:
   - `MoveIntention`: Check actor exists, target location valid, path exists
   - `ResourceTransferIntention`: Check resources exist in schema, sufficient quantity
   - `AttackIntention`: Check both entities exist, combat rules
   - `ChangeRelationshipIntention`: Check relationship exists or can be created

2. **Event Applier** - Applies each event type to state:
   - `MovementEvent`: Update `SpatialComponent.current_location_id`
   - `ResourceTransferEvent`: Modify `StateComponent.resources_json`
   - `StateChangeEvent`: Generic resource updates
   - `RelationshipChangeEvent`: Create/update relationships

3. **Rejection Feedback**:
   - When intention fails validation, create meaningful error messages
   - Log rejected intentions for debugging

---

### **Phase 2: Basic AI Agents (Week 3)**

**Goal**: Let actors make autonomous decisions

**What to build**:
1. **Agent Interface**:
   ```python
   class ActorAgent:
       async def generate_intention(self, actor: Actor, world_state: WorldState) -> Intention
   ```

2. **Simple Rule-Based Agent**:
   - Check actor's resources
   - If low on critical resource, generate `ResourceTransferIntention` to seek it
   - Basic movement toward goals

3. **LLM-Powered Agent** (uses existing `pyscrai_core.llm_interface`):
   - Build prompt with actor's state, memories, nearby entities
   - LLM generates intention in JSON format
   - Parse and validate

4. **Agent Scheduler**:
   - Each turn, let active actors generate intentions
   - Respect `max_concurrent_agents` from project config

---

### **Phase 3: Memory Integration (Week 4)**

**Goal**: Connect the Memory system to agent decision-making

**What to build**:
1. **Memory Writer**:
   - After each turn, convert events to `MemoryChunk` objects
   - Store in ChromaDB (already configured in pyscrai_core)
   - Tag with domain (HISTORY, ASSOCIATES, etc.)

2. **Memory Retrieval**:
   - Before agent generates intention, query relevant memories
   - Use semantic search: "What do I know about [target]?"
   - Include in agent's context

3. **Perception vs Reality**:
   - Agents make decisions based on memories (perception)
   - Engine validates against `StateComponent` (reality)
   - Track divergence as gameplay signal

---

### **Phase 4: Scenario Execution (Week 5)**

**Goal**: Run complete scenarios from Forge

**What to build**:
1. **Scenario Loader**:
   - Read scenario files from `data/projects/<name>/scenarios/`
   - Parse initial conditions, goals, victory conditions

2. **Goal System**:
   - Entities can have goals (stored in `CognitiveComponent`)
   - Agents prioritize intentions that advance goals
   - Engine tracks goal completion

3. **Narrative Logging**:
   - Generate `NarrativeLogEntry` for significant events
   - Store in database
   - CLI command to read turn-by-turn narrative

---

### **Phase 5: Integration & Polish (Week 6)**

**Goal**: Complete the Forge → Engine → Forge loop

**What to build**:
1. **Export Results to Forge**:
   - Save final world state back to `world.db`
   - Mark which entities changed during simulation
   - Allow Forge to review and approve changes

2. **Snapshot System**:
   - Implement `WorldSnapshot` (already defined in events.py)
   - Save snapshots every N turns (configurable)
   - Allow loading from snapshot for replay/branching

3. **Visualization Hooks**:
   - Export turn data to JSON for external visualization
   - Basic CLI visualizations (entity status, relationship graph)

4. **Error Recovery**:
   - If simulation crashes, save emergency snapshot
   - Allow resume from last valid turn

---

## **Minimal Viable Engine (MVP) - Days 1-3**

If you want to see something working immediately, here's the **absolute minimum**:

```python
# pyscrai_engine/engine.py
class SimulationEngine:
    def __init__(self, project_path: Path):
        self.controller = ProjectController(project_path)
        self.current_turn = 0
        
    def step(self):
        """Execute one turn"""
        # 1. Load all entities
        entities = self.controller.get_all_entities()
        
        # 2. For each actor, generate a random intention
        intentions = [self.generate_random_intention(e) for e in entities if e.entity_type == EntityType.ACTOR]
        
        # 3. Convert intentions to events (no validation yet)
        events = [self.intention_to_event(i) for i in intentions]
        
        # 4. Apply events to entities
        for event in events:
            self.apply_event(event)
        
        # 5. Save changes
        self.controller.commit()
        self.current_turn += 1
        
    def run(self, max_turns: int = 100):
        for _ in range(max_turns):
            self.step()
            print(f"Turn {self.current_turn} complete")
```
