"""The ForgeManager: Unified orchestrator for PyScrAI|Forge.

This manager coordinates all workflows, replacing both ArchitectAgent and
HarvesterOrchestrator with a single unified interface.
"""

import json
import asyncio
import logging
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

logger = logging.getLogger(__name__)

from pyscrai_core import (
    ProjectController as CoreController,
    ProjectManifest,
    Entity, Actor, Polity, Location,
    DescriptorComponent, StateComponent,
    EntityType
)
from pyscrai_core.llm_interface import LLMProvider

from pyscrai_forge.src import storage
from pyscrai_forge.agents.analyst import AnalystAgent
from pyscrai_forge.agents.narrator import NarratorAgent
from pyscrai_forge.agents.scout import ScoutAgent
from pyscrai_forge.agents.models import EntityStub
from pyscrai_forge.prompts.core import Genre
from pyscrai_forge.prompts.narrative import ARCHITECT_SYSTEM_PROMPT, build_possession_system_prompt, get_scout_prompt
from pyscrai_forge.prompts.analysis import get_relationship_prompt
from pyscrai_core import Relationship, RelationshipType

console = Console()


class ForgeManager:
    """The unified orchestrator for PyScrAI|Forge workflows.
    
    Responsibilities:
    - Session management (conversation history, project state)
    - Intent routing (extraction vs creative writing)
    - Human-in-the-Loop (HITL) coordination
    - Tool execution (project management, entity creation, etc.)
    """

    def __init__(self, provider: LLMProvider, project_path: Optional[Path] = None, hil_callback: Optional[callable] = None):
        self.provider = provider
        self.hil_callback = hil_callback
        
        # Robust path resolution
        self.project_path = Path(project_path).resolve() if project_path else None
        
        # Initialize agents with shared template manager
        # Scout has its own template_manager, we'll share it with Analyst
        self.scout = ScoutAgent(provider)
        self.analyst = AnalystAgent(provider, template_manager=self.scout.template_manager)
        self.narrator = NarratorAgent(provider)
        
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
            self.controller = CoreController(path)
            if (path / "project.json").exists():
                self.controller.load_project()
                console.print(f"[green]ForgeManager connected to project: {self.controller.manifest.name}[/green]")
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
        # If project is already loaded, tell the Manager in the context
        if self.controller and self.controller.manifest:
            self.conversation_history.append({
                "role": "system",
                "content": f"CONTEXT: You are currently working on project '{self.controller.manifest.name}' located at {self.project_path}."
            })

    async def interactive_chat(self):
        """Main interactive "Sorcerer" CLI loop."""
        console.print(Panel("The ForgeManager is Online. (Type 'exit' to quit)", style="bold blue"))
        
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
        response = await self.narrator.possess_entity(
            self.possession_target,
            user_input
        )
        self.possession_history.append({"role": "assistant", "content": response})
        console.print(Panel(Markdown(response), title=f"{self.possession_target.descriptor.name}", style="purple"))

    def _extract_json(self, text: str) -> Optional[dict]:
        """Extract JSON tool call from text."""
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                return json.loads(text[start:end+1])
        except:
            pass
        return None

    # =========================================================================
    # PIPELINE METHODS
    # =========================================================================

    async def run_extraction_pipeline(
        self,
        text: str,
        genre: Genre = Genre.GENERIC,
        output_path: Optional[Path] = None,
        template_name: Optional[str] = None,
        interactive: bool = False,
        verbose: bool = False,
        extract_relationships: bool = True
    ) -> str:
        """Run the extraction pipeline: Scout → Analyst → (Relationships) → Save.
        
        Can run automated (non-interactive) or with pauses for human review (interactive).
        
        Args:
            text: Raw text to extract entities from
            genre: Document genre for context
            output_path: Optional path to save review packet JSON
            template_name: Optional custom template directory name to use
            interactive: If True and hil_callback is available, pauses for human review
            verbose: If True, enables DEBUG level logging to show prompts and responses
            extract_relationships: If False, skip relationship extraction (for Foundry phase)
            
        Returns:
            Path to the generated review packet JSON file
        """
        if not self.controller:
            raise ValueError("No project loaded. Cannot run extraction pipeline.")
        
        # Enable verbose logging if requested or if DEBUG is already enabled
        import logging
        root_logger = logging.getLogger()
        is_debug = root_logger.level <= logging.DEBUG
        
        if verbose or is_debug:
            root_logger.setLevel(logging.DEBUG)
            for handler in root_logger.handlers:
                handler.setLevel(logging.DEBUG)
            if verbose:
                logger.info("Verbose mode enabled - showing prompts and responses")
            elif is_debug:
                logger.debug("DEBUG logging detected - verbose output enabled")
        
        # For now, treat both interactive and non-interactive the same
        # The hil_callback is stored and can be used by _run_extraction_pipeline_impl if needed
        return await self._run_extraction_pipeline_impl(text, genre, output_path, template_name, extract_relationships)
    
    async def _run_extraction_pipeline_impl(
        self,
        text: str,
        genre: Genre,
        output_path: Optional[Path],
        template_name: Optional[str] = None,
        extract_relationships: bool = True
    ) -> str:
        """Internal extraction pipeline - automated, no pauses."""
        import asyncio
        import json
        from datetime import datetime

        manifest = self.controller.manifest

        # =================================================================
        # PHASE 1: SCOUT (Entity Discovery)
        # =================================================================
        console.print(f"[dim]--- [Phase 1] Scouting ({len(text)} chars) ---[/dim]")
        if template_name:
            logger.info(f"ForgeManager: Running extraction with template_name='{template_name}'")
            console.print(f"[dim]Using template: {template_name}[/dim]")
        else:
            logger.info(f"ForgeManager: Running extraction without explicit template_name (using genre-based selection)")
        system_prompt, user_prompt = get_scout_prompt(text, genre)
        stubs = await self.scout.discover_entities(text, genre, template_name=template_name)

        if not stubs:
            console.print("[yellow]Scout phase found no entities[/yellow]")
            stubs = []
        else:
            console.print(f"Found {len(stubs)} potential entities.")

        # Dedup stubs (simple by ID)
        seen_ids = set()
        unique_stubs = []
        for stub in stubs:
            if stub.id not in seen_ids:
                unique_stubs.append(stub)
                seen_ids.add(stub.id)

        # =================================================================
        # PHASE 2: ANALYST (Entity Extraction & Refinement)
        # =================================================================
        console.print(f"[dim]--- [Phase 2] Analyzing {len(unique_stubs)} entities ---[/dim]")
        enriched_entities = []
        for stub in unique_stubs:
            schema = manifest.entity_schemas.get(stub.entity_type.value, {})
            # Pass genre and template_name to Analyst so it can use the correct template
            entity = await self.analyst.extract_from_text(stub, text, schema, genre=genre, template_name=template_name)
            enriched_entities.append(entity)
        console.print("Analysis complete.")

        # =================================================================
        # PHASE 3: RELATIONSHIPS (Mapping connections between entities)
        # =================================================================
        relationships = []
        if extract_relationships:
            console.print("[dim]--- [Phase 3] Mapping Relationships ---[/dim]")
            
            # Use TemplateManager to load relationships.yaml template instead of hardcoded prompt
            template = None
            try:
                # Determine template genre (same logic as Scout and Analyst)
                if template_name:
                    template_genre = template_name
                    logger.info(f"ForgeManager: Using explicit template_name='{template_name}' for relationships")
                    allow_fallback = False
                else:
                    genre_map = {
                        Genre.GENERIC.value: "default",
                        Genre.HISTORICAL.value: "historical",
                        "historical": "historical",
                        "espionage": "espionage",
                        "fictional": "fictional",
                    }
                    template_genre = genre_map.get(genre.value if hasattr(genre, 'value') else genre, "default")
                    logger.info(f"ForgeManager: Using genre-based template selection for relationships: genre={genre} -> template_genre='{template_genre}'")
                    allow_fallback = True
                
                try:
                    template = self.scout.template_manager.get_template(
                        "relationships",
                        genre=template_genre,
                        allow_fallback=allow_fallback
                    )
                    logger.info(f"ForgeManager: Successfully loaded relationships template from genre='{template_genre}'")
                except (FileNotFoundError, ValueError) as e:
                    if not allow_fallback:
                        error_type = "not found" if isinstance(e, FileNotFoundError) else "empty or malformed"
                        logger.error(f"ForgeManager: Relationships template '{template_genre}' {error_type}, but template_name was explicitly provided. Falling back to hardcoded prompt.")
                        template = None  # Will use fallback below
                    else:
                        logger.warning(f"ForgeManager: Relationships template '{template_genre}' not found or invalid, falling back to 'default'")
                        try:
                            template = self.scout.template_manager.get_template("relationships", genre="default", allow_fallback=True)
                        except Exception:
                            template = None  # Will use fallback below
                
                # Render template with variables if successfully loaded (full descriptions, no truncation)
                if template is not None:
                    # Format entities list for template (full descriptions, no truncation)
                    # The template expects {entities_list} variable
                    entities_list = []
                    for e in enriched_entities:
                        entities_list.append({
                            "id": e.id,
                            "name": e.descriptor.name,
                            "type": e.descriptor.entity_type.value,
                            "description": e.descriptor.bio or ""  # Full description, no truncation
                        })
                    
                    # Convert to JSON string for template
                    import json as _json
                    entities_list_json = _json.dumps(entities_list, indent=2)
                    
                    # Render template with variables
                    rel_system_prompt, rel_user_prompt = template.render(
                        text=text,
                        entities_list=entities_list_json,
                        genre=genre.value if hasattr(genre, 'value') else str(genre)
                    )
                else:
                    # Fallback to hardcoded prompt if template loading failed
                    logger.warning(f"ForgeManager: Using hardcoded relationship prompt as fallback")
                    ent_dicts = [
                        {
                            "id": e.id,
                            "name": e.descriptor.name,
                            "entity_type": e.descriptor.entity_type.value,
                            "description": e.descriptor.bio  # Full description, no truncation
                        }
                        for e in enriched_entities
                    ]
                    rel_system_prompt, rel_user_prompt = get_relationship_prompt(text, ent_dicts, genre)
            except Exception as e:
                # Fallback to hardcoded prompt if template loading fails
                logger.warning(f"ForgeManager: Failed to load relationships template, falling back to hardcoded prompt: {e}")
                ent_dicts = [
                    {
                        "id": e.id,
                        "name": e.descriptor.name,
                        "entity_type": e.descriptor.entity_type.value,
                        "description": e.descriptor.bio  # Full description, no truncation
                    }
                    for e in enriched_entities
                ]
                rel_system_prompt, rel_user_prompt = get_relationship_prompt(text, ent_dicts, genre)

            # Verbose logging: Show relationship prompts
            logger.debug("=" * 80)
            logger.debug("RELATIONSHIP EXTRACTION")
            logger.debug("=" * 80)
            logger.debug(f"Model: {self.provider.default_model}")
            logger.debug(f"Temperature: 0.1")
            logger.debug(f"Entities: {len(enriched_entities)}")
            logger.debug("\n--- SYSTEM PROMPT ---")
            logger.debug(rel_system_prompt)
            logger.debug("\n--- USER PROMPT ---")
            logger.debug(rel_user_prompt)
            logger.debug("\n--- Sending request to LLM ---")

            relationships = await self._extract_relationships_with_prompts(
                rel_system_prompt,
                rel_user_prompt
            )

            # Verbose logging: Show relationship results
            logger.debug(f"\n--- Found {len(relationships)} relationships ---")
            for rel in relationships:
                logger.debug(f"  {rel.source_id} --[{rel.relationship_type.value}]--> {rel.target_id}")
            logger.debug("=" * 80)

            console.print(f"Found {len(relationships)} relationships.")

            # =================================================================
            # NEW PHASE: ALIAS RESOLUTION (Merging Duplicates)
            # =================================================================
            console.print("[dim]--- [Phase 3.5] Resolving Aliases ---[/dim]")
            enriched_entities = self._resolve_aliases(enriched_entities, relationships)
        else:
            console.print("[dim]--- [Phase 3] Skipping Relationships (Foundry mode) ---[/dim]")
            
            # =================================================================
            # NEW PHASE: ALIAS RESOLUTION (Merging Duplicates) - Also run in Foundry mode
            # =================================================================
            console.print("[dim]--- [Phase 3.5] Resolving Aliases (Foundry mode) ---[/dim]")
            enriched_entities = self._resolve_aliases(enriched_entities, [])

        # Validate
        console.print("[dim]--- [Phase 4] Validation ---[/dim]")
        from pyscrai_forge.agents.validator import ValidatorAgent
        validator = ValidatorAgent()
        report = validator.validate(enriched_entities, relationships, manifest)
        if not report.is_valid:
            console.print(f"[yellow]Validation Errors: {len(report.critical_errors)}[/yellow]")
            for idx, err in enumerate(report.critical_errors, 1):
                console.print(f"    [red]Error {idx}:[/red] {err}")
        else:
            console.print("Validation Passed.")

        # Create review packet
        console.print("[dim]--- [Phase 5] Creating Review Packet ---[/dim]")
        from pyscrai_forge.agents.reviewer import ReviewerAgent
        reviewer = ReviewerAgent()
        packet = reviewer.create_review_packet(
            enriched_entities,
            relationships,
            report,
            text
        )

        if output_path is None:
            output_path = Path("review_packet.json")
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        reviewer.save_packet(packet, output_path)
        console.print(f"Review Packet saved to: {output_path}")

        return str(output_path)
    def _resolve_aliases(self, entities: List[Entity], relationships: List[Relationship]) -> List[Entity]:
        """Merges entities that are identified as the same person/object.
        
        Detects aliases through:
        1. Relationships with alias indicators (when relationships exist)
        2. Entity descriptions/bios that mention other entity names (always available)
        """
        alias_map = {} # source_id -> target_id (The 'Master' entity)

        # 1. Identify "Alias" relationships (if relationships were extracted)
        # Check for various terms that indicate entity identity/alias relationships
        alias_keywords = [
            "alias", "same as", "same person", "same entity", "same object",
            "call sign", "callsign", "call-sign",
            "code name", "codename", "code-name",
            "also known as", "aka", "a.k.a.",
            "nickname", "handle", "pseudonym",
            "identified as",  # e.g., "Viper is identified as Captain Elena Rossi"
            "operating under", "operating under the",  # e.g., "operating under the codename"
            "codename for", "alias for"  # e.g., "alias for Marcus Thorne"
        ]
        
        # Track alias relationships to remove them after merging (they've served their purpose)
        alias_relationships_to_remove = []
        
        for rel in relationships:
            desc = rel.description.lower()
            # Check if relationship type is explicitly same_as
            if rel.relationship_type.value == "same_as":
                alias_map[rel.source_id] = rel.target_id
                alias_relationships_to_remove.append(rel)
                logger.info(f"ForgeManager: Found alias relationship (same_as type) {rel.source_id} -> {rel.target_id}")
                continue
            
            # Check description for alias-indicating keywords
            is_alias_relationship = False
            for keyword in alias_keywords:
                if keyword in desc:
                    is_alias_relationship = True
                    break
            
            # Additional pattern: "X is the Y for Z" or "X is Y for Z" patterns
            # These often indicate aliases (e.g., "Viper is the call sign for Captain Elena Rossi")
            if not is_alias_relationship:
                # Pattern: "X is [the] Y for Z" where Y could be alias/call sign/etc
                pattern = r"(\w+)\s+is\s+(?:the\s+)?(?:call\s+sign|callsign|alias|codename|code\s+name|nickname|handle)\s+for\s+(.+)"
                if re.search(pattern, desc):
                    is_alias_relationship = True
            
            # Additional pattern: "X is identified as Y" (common identity pattern)
            if not is_alias_relationship:
                # Pattern: "X is identified as Y" - indicates identity relationship
                pattern = r"(\w+)\s+is\s+identified\s+as\s+(.+)"
                if re.search(pattern, desc):
                    is_alias_relationship = True
                    logger.debug(f"ForgeManager: Matched 'identified as' pattern: {rel.description}")
            
            if is_alias_relationship:
                # Assume the target is the canonical one if mentioned in description
                alias_map[rel.source_id] = rel.target_id
                alias_relationships_to_remove.append(rel)
                logger.info(f"ForgeManager: Found alias relationship {rel.source_id} -> {rel.target_id} (description: '{rel.description}')")

        # 1b. Detect aliases from entity descriptions/bios (works even without relationships)
        # This is especially useful for Foundry mode where relationships aren't extracted
        entity_by_name = {e.descriptor.name.lower(): e for e in entities}
        
        for entity in entities:
            if entity.id in alias_map:  # Already mapped via relationship
                continue
                
            bio_lower = (entity.descriptor.bio or "").lower()
            name_lower = entity.descriptor.name.lower()
            
            # Check if bio mentions another entity name (indicating alias/identity)
            # Patterns like: "identified as X", "alias for X", "codename for X", "operating under the alias/codename X"
            for other_name, other_entity in entity_by_name.items():
                if other_entity.id == entity.id:  # Skip self
                    continue
                if other_entity.id in alias_map:  # Skip if already mapped
                    continue
                
                # Check if this entity's bio mentions the other entity name
                # and contains alias keywords
                if other_name in bio_lower:
                    # Escape name but allow flexible whitespace (handle multi-word names)
                    # Replace escaped spaces with \s+ pattern
                    escaped_name = re.escape(other_name).replace('\\ ', '\\s+')
                    
                    # Check for alias patterns in bio
                    patterns = [
                        rf"identified\s+as\s+{escaped_name}",
                        rf"alias\s+for\s+{escaped_name}",
                        rf"alias\s+used\s+by\s+{escaped_name}",
                        rf"alias\s+of\s+{escaped_name}",
                        rf"codename\s+for\s+{escaped_name}",
                        rf"codename\s+used\s+by\s+{escaped_name}",
                        rf"codename\s+of\s+{escaped_name}",
                        rf"codename[:\s]+{escaped_name}",
                        rf"operating\s+under\s+(?:the\s+)?(?:alias|codename|callsign)\s+{escaped_name}",
                        rf"call(?:s|-)?sign[:\s]+{escaped_name}",
                        rf"also\s+known\s+as\s+{escaped_name}",
                        rf"aka\s+{escaped_name}",
                        rf"a\.k\.a\.\s+{escaped_name}",
                    ]
                    
                    for pattern in patterns:
                        if re.search(pattern, bio_lower, re.IGNORECASE):
                            # The mentioned entity is the canonical one
                            alias_map[entity.id] = other_entity.id
                            logger.info(f"ForgeManager: Found alias from bio: '{entity.descriptor.name}' -> '{other_entity.descriptor.name}' (pattern: '{pattern}')")
                            break
                
                # Also check reverse: if other entity's bio mentions this entity name
                other_bio_lower = (other_entity.descriptor.bio or "").lower()
                if name_lower in other_bio_lower and entity.id not in alias_map:
                    # Escape name but allow flexible whitespace (handle multi-word names)
                    # Replace escaped spaces with \s+ pattern
                    escaped_name = re.escape(name_lower).replace('\\ ', '\\s+')
                    
                    # Check if other entity's bio indicates this entity is an alias
                    reverse_patterns = [
                        rf"identified\s+as\s+{escaped_name}",
                        rf"alias\s+for\s+{escaped_name}",
                        rf"alias\s+used\s+by\s+{escaped_name}",
                        rf"alias\s+of\s+{escaped_name}",
                        rf"codename\s+for\s+{escaped_name}",
                        rf"codename\s+used\s+by\s+{escaped_name}",
                        rf"codename\s+of\s+{escaped_name}",
                        rf"codename[:\s]+{escaped_name}",
                        rf"operating\s+under\s+(?:the\s+)?(?:alias|codename|callsign)\s+{escaped_name}",
                        rf"call(?:s|-)?sign[:\s]+{escaped_name}",
                        rf"also\s+known\s+as\s+{escaped_name}",
                        rf"aka\s+{escaped_name}",
                        rf"a\.k\.a\.\s+{escaped_name}",
                    ]
                    
                    for pattern in reverse_patterns:
                        if re.search(pattern, other_bio_lower, re.IGNORECASE):
                            # This entity is the alias, other is canonical
                            alias_map[entity.id] = other_entity.id
                            logger.info(f"ForgeManager: Found alias from reverse bio: '{entity.descriptor.name}' -> '{other_entity.descriptor.name}'")
                            break

        if not alias_map:
            console.print("[dim]No aliases detected.[/dim]")
            return entities

        # 2. Perform the Merge
        resolved_entities = {e.id: e for e in entities}
        to_delete = []


        for alias_id, master_id in alias_map.items():
            if alias_id in resolved_entities and master_id in resolved_entities:
                master = resolved_entities[master_id]
                alias = resolved_entities[alias_id]

                console.print(f"[yellow]Merging alias '{alias.descriptor.name}' into canonical '{master.descriptor.name}'[/yellow]")

                # Merge Tags and Aliases
                # Ensure tags are sets for merging, then restore original type
                master_tags = master.descriptor.tags
                alias_tags = alias.descriptor.tags
                # Convert to set if not already
                master_tags_set = set(master_tags) if isinstance(master_tags, list) else master_tags
                alias_tags_set = set(alias_tags) if isinstance(alias_tags, list) else alias_tags
                master_tags_set.update(alias_tags_set)
                master_tags_set.add(alias.descriptor.name)
                # Restore to original type (list or set)
                if isinstance(master_tags, list):
                    master.descriptor.tags = list(master_tags_set)
                else:
                    master.descriptor.tags = master_tags_set

                # Merge Resources (Master wins if both have data)
                m_res = json.loads(master.state.resources_json or "{}")
                a_res = json.loads(alias.state.resources_json or "{}")

                # Fill master gaps with alias data
                for key, val in a_res.items():
                    if val and not m_res.get(key):
                        m_res[key] = val

                master.state.resources_json = json.dumps(m_res)
                to_delete.append(alias_id)

        # 3. Update relationships to point to master entities instead of deleted aliases
        # Build a mapping that includes transitive aliases (if A->B and B->C, then A->C)
        final_alias_map = {}
        for alias_id, master_id in alias_map.items():
            # Follow the chain to find the ultimate master
            current = master_id
            while current in alias_map:
                current = alias_map[current]
            final_alias_map[alias_id] = current
        
        # Update relationships that reference deleted alias entities
        # Also filter out self-referential relationships (entity pointing to itself)
        relationships_updated = 0
        relationships_to_remove = []
        
        for rel in relationships:
            updated = False
            # Check if source_id is an alias that was deleted
            if rel.source_id in final_alias_map:
                rel.source_id = final_alias_map[rel.source_id]
                updated = True
            # Check if target_id is an alias that was deleted
            if rel.target_id in final_alias_map:
                rel.target_id = final_alias_map[rel.target_id]
                updated = True
            
            # Check for self-referential relationships (entity pointing to itself)
            if rel.source_id == rel.target_id:
                relationships_to_remove.append(rel)
                logger.info(f"ForgeManager: Removing self-referential relationship {rel.id} ({rel.description})")
            elif updated:
                relationships_updated += 1
                logger.info(f"ForgeManager: Updated relationship {rel.id} to reference master entities")
        
        # Remove self-referential relationships
        for rel in relationships_to_remove:
            relationships.remove(rel)
        
        # Remove alias relationships themselves (they've served their purpose after merging)
        for rel in alias_relationships_to_remove:
            if rel in relationships:  # Check if not already removed
                relationships.remove(rel)
                logger.info(f"ForgeManager: Removed alias relationship {rel.id} after merge ({rel.description})")
        
        if relationships_updated > 0:
            console.print(f"[dim]Updated {relationships_updated} relationships to point to master entities[/dim]")
        if relationships_to_remove:
            console.print(f"[dim]Removed {len(relationships_to_remove)} self-referential relationship(s)[/dim]")
        if alias_relationships_to_remove:
            console.print(f"[dim]Removed {len(alias_relationships_to_remove)} alias relationship(s) after merge[/dim]")

        # 4. Clean up the entities list
        return [e for e in entities if e.id not in to_delete]

    async def _extract_relationships(self, text: str, entities: list, genre: Genre) -> List[Relationship]:
        """Helper to extract relationships using the prompt system."""
        # Convert entities to dicts for prompt
        ent_dicts = []
        for e in entities:
            ent_dicts.append({
                "id": e.id,
                "name": e.descriptor.name,
                "entity_type": e.descriptor.entity_type.value,
                "description": e.descriptor.bio
            })
            
        system_prompt, user_prompt = get_relationship_prompt(text, ent_dicts, genre)
        return await self._extract_relationships_with_prompts(system_prompt, user_prompt)
    
    async def _extract_relationships_with_prompts(self, system_prompt: str, user_prompt: str) -> List[Relationship]:
        """Helper to extract relationships using custom prompts."""
        try:
            response = await self.provider.complete_simple(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                model=self.provider.default_model
            )
            
            # Verbose logging: Show raw response
            logger.debug("\n--- LLM RESPONSE ---")
            logger.debug(response)
            
            # Parse response
            import re
            cleaned = response.strip()
            if "```json" in cleaned:
                match = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL)
                if match:
                    cleaned = match.group(1)
            elif "```" in cleaned:
                match = re.search(r"```\s*(.*?)\s*```", cleaned, re.DOTALL)
                if match:
                    cleaned = match.group(1)
            
            logger.debug("\n--- Parsed JSON ---")
            logger.debug(cleaned)
                
            data = json.loads(cleaned)
            rels_raw = data.get("relationships", [])
            
            rels = []
            for r in rels_raw:
                try:
                    rel_type_str = r.get("relationship_type", "custom").lower()
                    try:
                        rt = RelationshipType(rel_type_str)
                    except ValueError:
                        rt = RelationshipType.CUSTOM
                        
                    rels.append(Relationship(
                        id=r.get("id"),
                        source_id=r.get("source_id"),
                        target_id=r.get("target_id"),
                        relationship_type=rt,
                        strength=float(r.get("strength", 0.0)),
                        description=r.get("description", "")
                    ))
                except Exception:
                    continue
            return rels

        except Exception as e:
            console.print(f"[yellow]Relationship extraction failed: {e}[/yellow]")
            return []

    async def run_scenario_generation(
        self,
        focus: Optional[str] = None,
        project_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Run scenario generation: load entities → Narrator.generate_scenario.
        
        Args:
            focus: Optional focus area for scenario
            project_config: Project configuration (uses current project if not provided)
            
        Returns:
            Generated scenario text
        """
        if not self.controller:
            return "Error: No project loaded."
        
        # Load entities from database
        entities = storage.load_all_entities(self.controller.database_path)
        corpus_data = [json.loads(e.model_dump_json()) for e in entities]
        
        # Get project config
        if project_config is None:
            manifest = self.controller.manifest
            project_config = {
                "name": manifest.name,
                "description": manifest.description,
                "entity_schemas": manifest.entity_schemas,
            }
        
        return await self.narrator.generate_scenario(corpus_data, project_config, focus)

    async def generate_project_narrative(
        self,
        mode: Optional[str] = None,
        focus: Optional[str] = None,
        entity_filter: Optional[str] = None
    ) -> str:
        """Generate a narrative from project entities using the fact-checking loop.
        
        Args:
            mode: Narrative mode (sitrep, story, dossier, summary). Auto-detected if None.
            focus: Focus area for the narrative  
            entity_filter: Optional entity type filter (actor, polity, location)
            
        Returns:
            Generated narrative text
        """
        if not self.controller:
            raise ValueError("No project loaded. Cannot generate narrative.")
        
        # Load entities from database
        entities = storage.load_all_entities(self.controller.database_path)
        
        # Apply entity filter if specified
        if entity_filter:
            entities = [e for e in entities if e.descriptor.entity_type.value == entity_filter.lower()]
        
        if not entities:
            return "No entities found to generate narrative from."
        
        # Convert entities to lightweight dicts
        entity_dicts = []
        for e in entities:
            entity_dicts.append({
                "id": e.id,
                "name": e.descriptor.name,
                "type": e.descriptor.entity_type.value,
                "resources": json.loads(e.state.resources_json or "{}")
            })
        
        # Load relationships (simplified for now)
        relationships = []  # TODO: Load from database when relationship storage is implemented
        
        # Determine narrative mode with intelligent fallback
        from pyscrai_forge.prompts.narrative import NarrativeMode
        if mode:
            mode_map = {
                "sitrep": NarrativeMode.SITREP,
                "story": NarrativeMode.STORY,
                "dossier": NarrativeMode.DOSSIER,
                "summary": NarrativeMode.SUMMARY
            }
            narrative_mode = mode_map.get(mode.lower(), NarrativeMode.SUMMARY)
        else:
            # Auto-detect based on entity count and types
            actor_count = len([e for e in entities if e.descriptor.entity_type.value == "actor"])
            polity_count = len([e for e in entities if e.descriptor.entity_type.value == "polity"])
            
            if actor_count > polity_count and actor_count <= 3:
                narrative_mode = NarrativeMode.STORY  # Character-focused
            elif polity_count > 0 or len(entities) > 5:
                narrative_mode = NarrativeMode.SITREP  # Strategic overview
            else:
                narrative_mode = NarrativeMode.SUMMARY  # General summary
        
        focus_text = focus or "General Overview"
        context = f"Project: {self.controller.manifest.name}\nEntities: {len(entities)}"
        
        return await self.narrator.generate_narrative(
            entity_dicts, relationships, narrative_mode, focus_text, context
        )

    async def handle_possession(self, entity_id: str, user_input: str) -> str:
        """Handle entity possession interaction.
        
        Args:
            entity_id: ID or name of entity to possess
            user_input: User's input/query
            
        Returns:
            Response from entity's perspective
        """
        if not self.controller:
            return "Error: No project loaded."
        
        entities = storage.load_all_entities(self.controller.database_path)
        target = next(
            (e for e in entities if e.id == entity_id or e.descriptor.name.lower() == entity_id.lower()),
            None
        )
        
        if not target:
            return f"Could not find entity: {entity_id}"
        
        return await self.narrator.possess_entity(target, user_input)

    # =========================================================================
    # TOOLS
    # =========================================================================

    async def _execute_tool(self, tool_call: dict) -> str:
        """Execute a tool call."""
        tool = tool_call.get("tool")
        params = tool_call.get("params", {})
        
        try:
            if tool == "create_project":
                return self._tool_create_project(params)
            if tool == "define_schema":
                return self._tool_define_schema(params)
            if tool == "create_entity":
                return self._tool_create_entity(params)
            if tool == "list_entities":
                return self._tool_list_entities(params)
            if tool == "possess_entity":
                return self._tool_possess_entity(params)
            if tool == "generate_narrative":
                return await self._tool_generate_narrative(params)
            return f"Unknown tool: {tool}"
        except Exception as e:
            return f"Technical Error: {str(e)}"

    def _tool_create_project(self, params: dict) -> str:
        """Create a new project."""
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
        """Define entity schema."""
        if not self.controller or not self.controller.manifest:
            return "Error: No project loaded."
        e_type = params.get("entity_type")
        fields = params.get("fields", {})
        if e_type not in self.controller.manifest.entity_schemas:
            self.controller.manifest.entity_schemas[e_type] = {}
        self.controller.manifest.entity_schemas[e_type].update(fields)
        self.controller.save_manifest()
        return f"Schema updated for {e_type}."

    def _tool_create_entity(self, params: dict) -> str:
        """Create an entity."""
        if not self.controller:
            return "Error: No project loaded."
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
        """List entities in database."""
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

        return "\n".join([f"- {e.descriptor.name} ({e.descriptor.entity_type.value}) [ID: {e.id}]" for e in entities])

    def _tool_possess_entity(self, params: dict) -> str:
        """Enter possession mode for an entity."""
        if not self.controller:
            return "Error: No project loaded."
        target_id = params.get("entity_id")
        entities = storage.load_all_entities(self.controller.database_path)
        target = next(
            (e for e in entities if e.id == target_id or e.descriptor.name.lower() == target_id.lower()),
            None
        )
        
        if not target:
            return f"Could not find entity: {target_id}"
        
        self.possession_target = target
        entity_data = json.loads(target.model_dump_json())
        sys_prompt = build_possession_system_prompt(entity_data)
        self.possession_history = [{"role": "system", "content": sys_prompt}]
        return f"POSSESSION_STARTED:{target.descriptor.name}"

    async def _tool_generate_narrative(self, params: dict) -> str:
        """Generate a project narrative using the fact-checking loop."""
        if not self.controller:
            return "Error: No project loaded."
        
        mode = params.get("mode")
        focus = params.get("focus")
        entity_filter = params.get("entity_filter")
        
        try:
            result = await self.generate_project_narrative(mode, focus, entity_filter)
            return f"NARRATIVE_GENERATED\n\n{result}"
        except Exception as e:
            return f"Error generating narrative: {e}"

    def _exit_possession(self):
        """Exit possession mode."""
        self.possession_target = None
        self.possession_history = []
        console.print("[blue]Returned to ForgeManager mode.[/blue]")

    def _reindex_ids(self, entities: List[Entity], relationships: List[Relationship]) -> tuple[List[Entity], List[Relationship]]:
        """Re-index entity and relationship IDs to start from 001 and be contiguous.

        This ensures that the output files have clean, sequential IDs starting from 001,
        even after alias resolution has removed entities and relationships.

        Args:
            entities: List of entities to re-index
            relationships: List of relationships to re-index

        Returns:
            Tuple of (re-indexed entities, re-indexed relationships)
        """
        if not entities:
            return entities, relationships

        # Create ID mapping
        id_map = {}

        # Re-index entities
        for i, entity in enumerate(entities, start=1):
            new_id = f"ENTITY_{i:03d}"
            id_map[entity.id] = new_id
            entity.id = new_id

        # Re-index relationships
        for i, rel in enumerate(relationships, start=1):
            new_id = f"REL_{i:03d}"
            rel.id = new_id
            # Update references to entities
            if rel.source_id in id_map:
                rel.source_id = id_map[rel.source_id]
            if rel.target_id in id_map:
                rel.target_id = id_map[rel.target_id]

        # Update entity references within entities (e.g., spatial current_location_id, region_id)
        for entity in entities:
            if entity.spatial:
                if entity.spatial.region_id and entity.spatial.region_id in id_map:
                    entity.spatial.region_id = id_map[entity.spatial.region_id]
                if entity.spatial.current_location_id and entity.spatial.current_location_id in id_map:
                    entity.spatial.current_location_id = id_map[entity.spatial.current_location_id]

        console.print(f"[dim]Re-indexed {len(entities)} entities and {len(relationships)} relationships to start from 001[/dim]")
        return entities, relationships
