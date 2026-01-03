PyScrAI|Forge V1.0.0 Architecture: The Unified Manager1. Executive SummaryThe V1.0.0 release of PyScrAI|Forge unifies the disparate "Harvester" and "Architect" agent pipelines into a single, cohesive system governed by the Forge Manager. This eliminates redundancy, centralizes state management, and provides a streamlined "Sorcerer Loop" for user interaction.The new architecture flattens the agent hierarchy: The ForgeManager acts as the single point of contact (the "Brain") which delegates specialized tasks to worker agents (Analyst, Narrator) who share a centralized prompt repository.2. Directory Structure RestructuringThe pyscrai_forge package will be reorganized to reflect this unified vision.pyscrai_forge/
├── agents/                  <-- [MODIFIED] Flat agent directory
│   ├── manager.py           # The "ForgeManager" (formerly HarvesterOrchestrator)
│   ├── analyst.py           # The "Left Brain" (Extraction, Refining, Validation)
│   ├── narrator.py          # The "Right Brain" (Scenario Gen, Possession)
│   ├── scout.py             # The "Eyes" (File discovery - Future)
│   └── models.py            # Shared Pydantic models for agent communication
│
├── prompts/                 <-- [NEW] Centralized Prompt Repository
│   ├── core.py              # Base system prompts & shared definitions
│   ├── analysis.py          # Prompts for Analyst (Extraction & Refining)
│   └── narrative.py         # Prompts for Narrator (Scenarios & Possession)
3. The Forge Manager (manager.py)Role: The Orchestrator. It holds the ProjectController (Database Access) and LLMProvider (API Access). It routes high-level user intents to specific agent workflows.Key Responsibilities:Session Management: Maintains the conversation history and project state.Intent Routing: Decides if a request is for "Data Extraction" (routes to Analyst) or "Creative Writing" (routes to Narrator).Human-In-The-Loop (HITL): Pauses execution to ask the user for clarification or approval (e.g., confirming a schema change).Class Specification:class ForgeManager:
    def __init__(self, provider, project_path=None):
        self.provider = provider
        self.analyst = AnalystAgent(provider)
        self.narrator = NarratorAgent(provider)
        # ... logic to load project ...

    async def interactive_chat(self):
        # Main "Sorcerer" CLI Loop
        pass

    async def run_extraction_pipeline(self, text):
        # Calls self.analyst.extract() -> self.analyst.refine()
        pass

    async def run_scenario_generation(self, focus):
        # Calls storage.load_all() -> self.narrator.generate_scenario()
        pass
4. The Unified Agent RosterA. The Analyst (analyst.py)Role: The Data Scientist.Prompt Source: pyscrai_forge.prompts.analysisCapabilities:extract_from_text(text, schema): Turns raw text into JSON.refine_data(raw_json, schema): Cleans, deduplicates, and validates JSON. Formerly the "JSON Agent".B. The Narrator (narrator.py)Role: The Creative Writer.Prompt Source: pyscrai_forge.prompts.narrativeCapabilities:generate_scenario(corpus, focus): Writes a SitRep based on database entities. Formerly the "Chronicler".possess_entity(entity, user_input): Handles roleplay turns for a specific node.5. Prompt Engineering StrategyWe move away from hardcoded strings in agent classes. All prompts live in pyscrai_forge/prompts/.prompts/core.py: Defines the BASE_SYSTEM_PROMPT ensuring all agents respect the "Agnostic" and "Data-Driven" core principles.prompts/analysis.py: Contains ANALYST_SYSTEM_PROMPT and template functions like build_refinement_prompt(raw_data, schema).prompts/narrative.py: Contains NARRATOR_SYSTEM_PROMPT and build_possession_prompt(entity).6. Implementation RoadmapRefactor Prompts: Move all prompt strings from src/prompts.py and agents/*.py into the new prompts/ modules.Consolidate Analyst: Merge the logic from harvester/analyst.py and the proposed JSONRefiner into a single AnalystAgent class in agents/analyst.py.Create Narrator: Implement agents/narrator.py to handle the creative tasks.Build Manager: Rewrite agents/manager.py to implement the ForgeManager class as specified above.Update CLI: Modify src/cli.py to instantiate ForgeManager and launch interactive_chat() for the forge architect command.7. Migration NoteDelete pyscrai_forge/agents/architect/ (The old separation is obsolete).Delete pyscrai_forge/agents/harvester/ (Move useful files to root agents/).