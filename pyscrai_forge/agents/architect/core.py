"""The Architect Agent: Interactive Project Forge & Simulation Host.

Refined for V1.0.0 prototype with improved path handling and tool-use feedback.
"""

import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from pyscrai_core import (
    ProjectController as CoreController, 
    ProjectManifest, 
    Entity, Actor, Polity, Location, 
    DescriptorComponent, StateComponent,
    EntityType
)
from pyscrai_core.llm_interface import LLMProvider
from pyscrai_forge.src import storage
from pyscrai_forge.prompts.architect_prompts import (
    ARCHITECT_SYSTEM_PROMPT, 
    build_possession_system_prompt
)

console = Console()

class ArchitectAgent:
    """The interactive co-creator agent."""

    def __init__(self, provider: LLMProvider, project_path: Optional[Path] = None):
        self.provider = provider
        
        # Robust path resolution
        self.project_path = Path(project_path).resolve() if project_path else None
        
        # State
        self.controller: Optional[CoreController] = None
        self.conversation_history: List[dict] = []
        self.possession_target: Optional[Entity] = None
        self.possession_history: List[dict] = []
        
        # Load project immediately if path provided
        if self.project_path:
            self._attempt_load_project(self.project_path)
        
        self._init_history()

    def _attempt_load_project(self, path: Path):
        """Helper to initialize the controller and manifest."""
        try:
            # Note: We use the core controller for data-level project management
            self.controller = CoreController(path)
            if (path / "project.json").exists():
                self.controller.load_project()
                console.print(f"[green]Architect connected to project: {self.controller.manifest.name}[/green]")
            else:
                console.print(f"[yellow]Path exists but no project.json found at: {path}[/yellow]")
        except Exception as e:
            console.print(f"[red]Failed to load project at {path}: {e}[/red]")
            self.controller = None

    def _init_history(self):
        """Set the initial system prompt."""
        self.conversation_history = [
            {"role": "system", "content": ARCHITECT_SYSTEM_PROMPT}
        ]
        # If project is already loaded, tell the Architect in the context
        if self.controller and self.controller.manifest:
            self.conversation_history.append({
                "role": "system", 
                "content": f"CONTEXT: You are currently working on project '{self.controller.manifest.name}' located at {self.project_path}."
            })

    async def chat_loop(self):
        """Main interactive loop."""
        console.print(Panel("The Architect is Online. (Type 'exit' to quit)", style="bold blue"))
        
        while True:
            try:
                user_input = console.input("[bold green]User > [/bold green]")
                if not user_input.strip():
                    continue
                if user_input.lower() in ["exit", "quit"]:
                    break
                
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
        
        response = await self.provider.complete(
            messages=self.conversation_history,
            model=self.provider.default_model
        )
        
        content = response["choices"][0]["message"]["content"]
        tool_call = self._extract_json(content)
        
        if tool_call:
            console.print(f"[dim]Executing {tool_call.get('tool')}...[/dim]")
            result_msg = await self._execute_tool(tool_call)
            
            # Feed tool result back
            self.conversation_history.append({"role": "assistant", "content": content})
            self.conversation_history.append({"role": "system", "content": f"Tool Result: {result_msg}"})
            
            # Get narrative follow-up
            response_2 = await self.provider.complete(
                messages=self.conversation_history,
                model=self.provider.default_model
            )
            final_content = response_2["choices"][0]["message"]["content"]
            self.conversation_history.append({"role": "assistant", "content": final_content})
            console.print(Markdown(final_content))
        else:
            self.conversation_history.append({"role": "assistant", "content": content})
            console.print(Markdown(content))

    async def _handle_possession(self, user_input: str):
        """Handle interaction in Possession mode."""
        self.possession_history.append({"role": "user", "content": user_input})
        response = await self.provider.complete(
            messages=self.possession_history,
            model=self.provider.default_model,
            temperature=0.8
        )
        content = response["choices"][0]["message"]["content"]
        self.possession_history.append({"role": "assistant", "content": content})
        console.print(Panel(Markdown(content), title=f"{self.possession_target.descriptor.name}", style="purple"))

    def _extract_json(self, text: str) -> Optional[dict]:
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                return json.loads(text[start:end+1])
        except: pass
        return None

    # =========================================================================
    # TOOLS
    # =========================================================================

    async def _execute_tool(self, tool_call: dict) -> str:
        tool = tool_call.get("tool")
        params = tool_call.get("params", {})
        
        try:
            if tool == "create_project": return self._tool_create_project(params)
            if tool == "define_schema": return self._tool_define_schema(params)
            if tool == "create_entity": return self._tool_create_entity(params)
            if tool == "list_entities": return self._tool_list_entities(params)
            if tool == "possess_entity": return self._tool_possess_entity(params)
            return f"Unknown tool: {tool}"
        except Exception as e:
            return f"Technical Error: {str(e)}"

    def _tool_create_project(self, params: dict) -> str:
        name = params.get("name", "New Project")
        desc = params.get("description", "")
        path = Path.cwd() / name.replace(" ", "_")
        
        self.controller = CoreController(path)
        manifest = ProjectManifest(name=name, description=desc)
        try:
            self.controller.create_project(manifest)
            self.project_path = path
            return f"Success: Project created at {path}."
        except FileExistsError:
            self.controller.load_project()
            self.project_path = path
            return f"Loaded existing project at {path}."

    def _tool_define_schema(self, params: dict) -> str:
        if not self.controller or not self.controller.manifest: return "Error: No project loaded."
        e_type = params.get("entity_type")
        fields = params.get("fields", {})
        if e_type not in self.controller.manifest.entity_schemas:
            self.controller.manifest.entity_schemas[e_type] = {}
        self.controller.manifest.entity_schemas[e_type].update(fields)
        self.controller.save_manifest()
        return f"Schema updated for {e_type}."

    def _tool_create_entity(self, params: dict) -> str:
        if not self.controller: return "Error: No project loaded."
        name = params.get("name")
        e_type_str = params.get("entity_type", "actor").lower()
        
        try:
            e_type = EntityType(e_type_str)
        except:
            e_type = EntityType.ABSTRACT
            
        desc = DescriptorComponent(name=name, entity_type=e_type, bio=params.get("bio", ""))
        state = StateComponent(resources_json=json.dumps(params.get("stats", {})))
        
        ent = Actor(descriptor=desc, state=state) if e_type == EntityType.ACTOR else Entity(descriptor=desc, state=state)
        storage.save_entity(self.controller.database_path, ent)
        return f"Created entity {name} (ID: {ent.id})"

    def _tool_list_entities(self, params: dict) -> str:
        if not self.controller or not self.controller.database_path.exists():
            return "Error: No project or database file found."
        
        entities = storage.load_all_entities(self.controller.database_path)
        if not entities: 
            return "The database is currently empty."
            
        # Optional type filtering
        filter_type = params.get("entity_type")
        if filter_type:
            entities = [e for e in entities if e.descriptor.entity_type.value.lower() == filter_type.lower()]
            if not entities: 
                return f"No entities of type '{filter_type}' found in the database."

        # Return name, type, and ID to ensure the Architect knows exactly what it's seeing
        return "\n".join([f"- {e.descriptor.name} ({e.descriptor.entity_type.value}) [ID: {e.id}]" for e in entities])

    def _tool_possess_entity(self, params: dict) -> str:
        if not self.controller: return "Error: No project loaded."
        target_id = params.get("entity_id")
        entities = storage.load_all_entities(self.controller.database_path)
        target = next((e for e in entities if e.id == target_id or e.descriptor.name.lower() == target_id.lower()), None)
        
        if not target: return f"Could not find entity: {target_id}"
        
        self.possession_target = target
        entity_data = json.loads(target.model_dump_json())
        sys_prompt = build_possession_system_prompt(entity_data)
        self.possession_history = [{"role": "system", "content": sys_prompt}]
        return f"POSSESSION_STARTED:{target.descriptor.name}"

    def _exit_possession(self):
        self.possession_target = None
        self.possession_history = []
        console.print("[blue]Returned to Architect mode.[/blue]")