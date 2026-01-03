"""The Architect Agent: Interactive Project Forge & Simulation Host.

This module implements the "Sorcerer" loop:
1. Architect Mode: Conversational project design and tool use.
2. Possession Mode: Direct roleplay/simulation of a specific entity.
"""

import json
import asyncio
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from pyscrai_core import (
    ProjectController, ProjectManifest, 
    Entity, Actor, Polity, Location, 
    DescriptorComponent, StateComponent, CognitiveComponent,
    EntityType
)
from pyscrai_core.llm_interface import LLMProvider, ChatMessage, MessageRole
from pyscrai_forge.src import storage
from pyscrai_forge.src.prompts.architect_prompts import (
    ARCHITECT_SYSTEM_PROMPT, 
    build_possession_system_prompt
)

console = Console()

class ArchitectAgent:
    """The interactive co-creator agent."""

    def __init__(self, provider: LLMProvider, project_path: Optional[Path] = None):
        self.provider = provider
        self.project_path = project_path
        
        # Initialize Controller if path exists
        self.controller = None
        if project_path:
            try:
                self.controller = ProjectController(project_path)
                if (project_path / "project.json").exists():
                    self.controller.load_project()
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load existing project: {e}[/yellow]")

        # State
        self.conversation_history: List[dict] = []
        self.possession_target: Optional[Entity] = None
        self.possession_history: List[dict] = []
        
        # Bootup
        self._init_history()

    def _init_history(self):
        """Set the initial system prompt."""
        self.conversation_history = [
            {"role": "system", "content": ARCHITECT_SYSTEM_PROMPT}
        ]

    async def chat_loop(self):
        """Main interactive loop."""
        console.print(Panel("The Architect is Online. (Type 'exit' to quit)", style="bold blue"))
        
        while True:
            try:
                user_input = console.input("[bold green]User > [/bold green]")
                if user_input.lower() in ["exit", "quit"]:
                    break
                
                # Check for client-side commands
                if user_input.lower() == "stop possession" and self.possession_target:
                    self._exit_possession()
                    continue

                if self.possession_target:
                    await self._handle_possession(user_input)
                else:
                    await self._handle_architect(user_input)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[red]Error in loop: {e}[/red]")

    async def _handle_architect(self, user_input: str):
        """Handle interaction in Project Design mode."""
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Call LLM
        response = await self.provider.complete(
            messages=self.conversation_history,
            model=self.provider.default_model
        )
        
        content = response["choices"][0]["message"]["content"]
        
        # Check for Tool Call (Naive JSON detection)
        # In a production version, we would use strict function calling APIs if available.
        tool_call = self._extract_json(content)
        
        if tool_call:
            console.print(f"[dim]Architect is using tool: {tool_call.get('tool')}[/dim]")
            result_msg = await self._execute_tool(tool_call)
            
            # Feed tool result back to LLM
            self.conversation_history.append({"role": "assistant", "content": content})
            self.conversation_history.append({"role": "system", "content": f"Tool Result: {result_msg}"})
            
            # Get final response after tool use
            response_2 = await self.provider.complete(
                messages=self.conversation_history,
                model=self.provider.default_model
            )
            final_content = response_2["choices"][0]["message"]["content"]
            self.conversation_history.append({"role": "assistant", "content": final_content})
            console.print(Markdown(final_content))
            
        else:
            # Just conversation
            self.conversation_history.append({"role": "assistant", "content": content})
            console.print(Markdown(content))

    async def _handle_possession(self, user_input: str):
        """Handle interaction in Possession/Simulation mode."""
        self.possession_history.append({"role": "user", "content": user_input})
        
        response = await self.provider.complete(
            messages=self.possession_history,
            model=self.provider.default_model,
            temperature=0.7 # Higher temp for creativity in roleplay
        )
        
        content = response["choices"][0]["message"]["content"]
        self.possession_history.append({"role": "assistant", "content": content})
        
        name = self.possession_target.descriptor.name
        console.print(Panel(Markdown(content), title=f"Possessing: {name}", style="purple"))

    def _extract_json(self, text: str) -> Optional[dict]:
        """Attempt to extract a JSON object from text."""
        try:
            # Try finding the first { and last }
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                json_str = text[start:end+1]
                return json.loads(json_str)
        except:
            pass
        return None

    # =========================================================================
    # TOOLS
    # =========================================================================

    async def _execute_tool(self, tool_call: dict) -> str:
        """Dispatcher for tool calls."""
        tool = tool_call.get("tool")
        params = tool_call.get("params", {})
        
        try:
            if tool == "create_project":
                return self._tool_create_project(params)
            elif tool == "define_schema":
                return self._tool_define_schema(params)
            elif tool == "create_entity":
                return self._tool_create_entity(params)
            elif tool == "list_entities":
                return self._tool_list_entities()
            elif tool == "possess_entity":
                return self._tool_possess_entity(params)
            else:
                return f"Unknown tool: {tool}"
        except Exception as e:
            return f"Tool Execution Error: {str(e)}"

    def _tool_create_project(self, params: dict) -> str:
        name = params.get("name", "New Project")
        desc = params.get("description", "")
        
        # If no path set, create one in current dir
        if not self.project_path:
            self.project_path = Path.cwd() / name.replace(" ", "_")
            
        self.controller = ProjectController(self.project_path)
        manifest = ProjectManifest(name=name, description=desc)
        
        try:
            self.controller.create_project(manifest)
            return f"Project '{name}' created successfully at {self.project_path}. Database initialized."
        except FileExistsError:
            self.controller.load_project()
            return f"Project '{name}' already exists. Loaded successfully."

    def _tool_define_schema(self, params: dict) -> str:
        if not self.controller or not self.controller.manifest:
            return "Error: No project loaded."
            
        e_type = params.get("entity_type")
        fields = params.get("fields", {})
        
        if e_type not in self.controller.manifest.entity_schemas:
            self.controller.manifest.entity_schemas[e_type] = {}
            
        self.controller.manifest.entity_schemas[e_type].update(fields)
        self.controller.save_manifest()
        
        return f"Schema updated for '{e_type}': {fields}"

    def _tool_create_entity(self, params: dict) -> str:
        if not self.controller:
            return "Error: No project loaded."
            
        name = params.get("name", "Unknown")
        e_type_str = params.get("entity_type", "actor").lower()
        stats = params.get("stats", {})
        bio = params.get("bio", "")
        
        # Factory logic
        try:
            e_type = EntityType(e_type_str)
        except ValueError:
            e_type = EntityType.ABSTRACT
            
        desc = DescriptorComponent(name=name, entity_type=e_type, bio=bio)
        state = StateComponent(resources_json=json.dumps(stats))
        
        # Create instance based on type
        if e_type == EntityType.ACTOR:
            ent = Actor(descriptor=desc, state=state)
        elif e_type == EntityType.POLITY:
            ent = Polity(descriptor=desc, state=state)
        elif e_type == EntityType.LOCATION:
            ent = Location(descriptor=desc, state=state)
        else:
            ent = Entity(descriptor=desc, state=state)
            
        storage.save_entity(self.controller.database_path, ent)
        
        return f"Entity Created: {name} (ID: {ent.id})"

    def _tool_list_entities(self) -> str:
        if not self.controller:
            return "Error: No project loaded."
            
        entities = storage.load_all_entities(self.controller.database_path)
        if not entities:
            return "No entities found in database."
            
        summary = "\n".join([
            f"- {e.descriptor.name} ({e.descriptor.entity_type.value}) [ID: {e.id}]" 
            for e in entities
        ])
        return f"Entities in Database:\n{summary}"

    def _tool_possess_entity(self, params: dict) -> str:
        if not self.controller:
            return "Error: No project loaded."
            
        ent_id = params.get("entity_id")
        
        # Try to find by ID, then by Name
        entities = storage.load_all_entities(self.controller.database_path)
        target = next((e for e in entities if e.id == ent_id), None)
        
        if not target:
            # Fuzzy match name
            target = next((e for e in entities if e.descriptor.name.lower() == ent_id.lower()), None)
            
        if not target:
            return f"Entity not found: {ent_id}"
            
        self._enter_possession(target)
        return f"ENTERING POSSESSION MODE: {target.descriptor.name}. All further user input will be directed to the entity."

    def _enter_possession(self, entity: Entity):
        """Switch context to possession."""
        self.possession_target = entity
        
        # Build the Persona System Prompt
        entity_data = json.loads(entity.model_dump_json())
        sys_prompt = build_possession_system_prompt(entity_data, context_summary="The user is interacting with you.")
        
        self.possession_history = [
            {"role": "system", "content": sys_prompt}
        ]
        
        console.print(Panel(
            f"You are now interacting directly with {entity.descriptor.name}.\n"
            f"Bio: {entity.descriptor.bio}\n"
            f"Type: 'stop possession' to return to Architect.",
            title="SIMULATION START", style="bold purple"
        ))

    def _exit_possession(self):
        """Return to Architect mode."""
        console.print(Panel("Leaving Simulation. Returning to Architect.", style="bold blue"))
        self.possession_target = None
        self.possession_history = []
        # Optional: Summarize what happened and add to Architect context?