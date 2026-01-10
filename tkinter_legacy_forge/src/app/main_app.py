"""Main application controller for PyScrAI|Forge.

Coordinates all managers and handles high-level application logic.
Implements PyScrAI 2.0 Sequential Intelligence Pipeline with three-pane layout.
"""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Optional

import sv_ttk

from pyscrai_forge.src.logging_config import setup_logging, get_logger
from .data_manager import DataManager
from .menu_manager import MenuManager
from .project_manager import ProjectController
from .state_manager import AppState, AppStateManager, PHASE_STATES, is_phase_state
from .task_queue import TaskQueue
from .project_operations import ProjectOperationsMixin
from .data_operations import DataOperationsMixin

if TYPE_CHECKING:
    from pyscrai_core import ProjectManifest
    from pyscrai_forge.src.user_config import UserConfig


# Phase display names and icons
PHASE_INFO = {
    AppState.PHASE_FOUNDRY: {"name": "Foundry", "icon": "1", "desc": "Entity Extraction"},
    AppState.PHASE_LOOM: {"name": "Loom", "icon": "2", "desc": "Relationship Mapping"},
    AppState.PHASE_CHRONICLE: {"name": "Chronicle", "icon": "3", "desc": "Narrative Synthesis"},
    AppState.PHASE_CARTOGRAPHY: {"name": "Cartography", "icon": "4", "desc": "Spatial Anchoring"},
    AppState.PHASE_ANVIL: {"name": "Anvil", "icon": "5", "desc": "Finalization"},
}


class ReviewerApp(ProjectOperationsMixin, DataOperationsMixin):
    """Main application controller (coordinator)."""
    
    def __init__(self, packet_path: Path | None = None, project_path: Path | None = None):
        """Initialize the application.
        
        Args:
            packet_path: Optional path to review packet file
            project_path: Optional path to project directory
        """
        # Initialize logging
        setup_logging()
        self.logger = get_logger(__name__)
        self.logger.info("Initializing PyScrAI|Forge application...")
        
        self.root = tk.Tk()
        self.root.title("PyScrAI|Forge - Tyler Hamilton v0.9.0")
        self.root.geometry("1400x900")
        
        # Load user config via ConfigManager
        self.logger.info("Loading user configuration...")
        from pyscrai_forge.src.config_manager import ConfigManager
        self.config_manager = ConfigManager.get_instance()
        self.user_config = self.config_manager.get_config()
        
        # APPLY THEME HERE
        # Check user config preference, or default to dark
        theme = self.user_config.preferences.theme 
        if theme == "light":
            sv_ttk.set_theme("light")
        else:
            sv_ttk.set_theme("dark") # Default to dark

        # Initialize managers
        self.project_controller = ProjectController(
            self.user_config,
            on_project_loaded=self._on_project_loaded,
            on_project_closed=self._on_project_closed
        )
        
        self.data_manager = DataManager(
            db_path=None,
            on_data_changed=self._on_data_changed
        )
        
        # Build UI structure first (three-pane layout)
        self._build_ui_structure()
        
        # Initialize TaskQueue for async LLM operations
        self.task_queue = TaskQueue(self.root, poll_interval_ms=100, max_concurrent=3)
        
        # Initialize state manager (needs UI components)
        self.state_manager = AppStateManager(
            root=self.root,
            main_container=self.center_pane,  # Center pane is the main content area
            status_bar=self.status_bar,
            callbacks=self._get_callbacks(),
            on_state_changed=self._on_state_changed
        )
        
        # Initialize menu manager
        self.menu_manager = MenuManager(
            root=self.root,
            callbacks=self._get_callbacks(),
            user_config=self.user_config
        )
        self.menu_manager.build_menubar()
        
        # Load initial project if provided
        if project_path:
            self.logger.info(f"Loading initial project: {project_path}")
            if self.project_controller.load_project(project_path, self.root):
                self.state_manager.transition_to(AppState.DASHBOARD)
            else:
                self.logger.warning(f"Failed to load initial project: {project_path}")
                self.state_manager.transition_to(AppState.LANDING)
        else:
            # Auto-load last project if enabled and available
            if self.user_config.preferences.auto_load_last_project and self.user_config.recent_projects:
                last_project = self.user_config.recent_projects[0]
                last_project_path = Path(last_project.path)
                if last_project_path.exists():
                    self.logger.info(f"Auto-loading last project: {last_project_path}")
                    if self.project_controller.load_project(last_project_path, self.root):
                        self.state_manager.transition_to(AppState.DASHBOARD)
                    else:
                        self.logger.warning(f"Failed to auto-load last project: {last_project_path}")
                        self.state_manager.transition_to(AppState.LANDING)
                else:
                    self.logger.warning(f"Last project path does not exist: {last_project_path}")
                    self.state_manager.transition_to(AppState.LANDING)
            else:
                self.state_manager.transition_to(AppState.LANDING)
        
        # Load packet if provided
        # Load packet if provided
        if packet_path and packet_path.exists():
            self.logger.info(f"Loading packet: {packet_path}")
            if self.data_manager.load_from_packet(packet_path):
                self.state_manager.transition_to(AppState.PHASE_FOUNDRY)
                self._refresh_foundry_ui()
        self._refresh_foundry_ui()
    
    def _save_user_config(self) -> None:
        """Save user configuration to disk via ConfigManager."""
        # Update the config manager's reference
        self.logger.info("Saving user configuration...")
        self.config_manager._config = self.user_config
        self.config_manager.save_config()
    
    def _build_ui_structure(self) -> None:
        """Build the three-pane UI structure for PyScrAI 2.0 pipeline.
        
        Layout:
        +------------------+------------------------+------------------+
        |   Left Pane      |     Center Pane        |   Right Pane     |
        |   Navigation     |    Active Phase View   |   Assistant      |
        |   (fixed 180px)  |    (swappable)         |   (collapsible)  |
        +------------------+------------------------+------------------+
        """
        # Status bar at bottom
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_bar = ttk.Label(status_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X)
        
        # Main horizontal PanedWindow
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Left Pane: Navigation (fixed width ~180px)
        self.left_pane = ttk.Frame(self.main_paned, width=180)
        self.left_pane.pack_propagate(False)  # Keep fixed width
        self.main_paned.add(self.left_pane, weight=0)
        
        # Build navigation panel
        self._build_navigation_panel()
        
        # Center Pane: Main content area (swappable by state)
        self.center_pane = ttk.Frame(self.main_paned)
        self.main_paned.add(self.center_pane, weight=1)
        
        # Right Pane: Assistant sidebar (collapsible, default collapsed)
        self.right_pane = ttk.Frame(self.main_paned, width=350)
        self.right_pane.pack_propagate(False)
        # Start collapsed - don't add to paned window initially
        self.right_pane.configure(width=0)
        
        # Build assistant panel
        self._build_assistant_panel()
        
        # Track assistant visibility state
        self.assistant_visible = False
        
        # For backward compatibility
        self.main_container = self.center_pane
    
    def _build_navigation_panel(self) -> None:
        """Build the left navigation panel with phase buttons."""
        # Header
        header_frame = ttk.Frame(self.left_pane)
        header_frame.pack(fill=tk.X, padx=10, pady=(15, 10))
        
        ttk.Label(
            header_frame,
            text="PyScrAI|Forge",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor=tk.W)
        
        ttk.Label(
            header_frame,
            text="Pipeline Navigator",
            font=("Segoe UI", 9),
            foreground="gray"
        ).pack(anchor=tk.W)
        
        # Separator
        ttk.Separator(self.left_pane, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=10)
        
        # Quick actions
        quick_frame = ttk.Frame(self.left_pane)
        quick_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.nav_home_btn = ttk.Button(
            quick_frame,
            text="Home",
            command=lambda: self.state_manager.transition_to(AppState.LANDING),
            width=18
        )
        self.nav_home_btn.pack(pady=2)
        
        self.nav_dashboard_btn = ttk.Button(
            quick_frame,
            text="Overview",
            command=lambda: self.state_manager.transition_to(AppState.DASHBOARD),
            width=18
        )
        self.nav_dashboard_btn.pack(pady=2)
        
        # Separator before phases
        ttk.Separator(self.left_pane, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=10)
        
        # Phase label
        ttk.Label(
            self.left_pane,
            text="PIPELINE PHASES",
            font=("Segoe UI", 9, "bold"),
            foreground="gray"
        ).pack(anchor=tk.W, padx=15, pady=(0, 5))
        
        # Phase navigation buttons
        self.phase_buttons: dict[AppState, ttk.Button] = {}
        phases_frame = ttk.Frame(self.left_pane)
        phases_frame.pack(fill=tk.X, padx=10)
        
        for i, phase_state in enumerate(PHASE_STATES):
            info = PHASE_INFO[phase_state]
            
            btn_frame = ttk.Frame(phases_frame)
            btn_frame.pack(fill=tk.X, pady=2)
            
            # Phase number indicator
            num_label = ttk.Label(
                btn_frame,
                text=info["icon"],
                font=("Segoe UI", 10, "bold"),
                width=3
            )
            num_label.pack(side=tk.LEFT)
            
            # Phase button
            btn = ttk.Button(
                btn_frame,
                text=info["name"],
                command=lambda s=phase_state: self._on_phase_nav(s),
                width=14
            )
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.phase_buttons[phase_state] = btn
        
        # Spacer
        ttk.Frame(self.left_pane).pack(fill=tk.BOTH, expand=True)
        
        # Assistant toggle at bottom
        ttk.Separator(self.left_pane, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=10)
        
        self.assistant_toggle_btn = ttk.Button(
            self.left_pane,
            text="Show Assistant",
            command=self._toggle_assistant,
            width=18
        )
        self.assistant_toggle_btn.pack(padx=10, pady=(0, 15))
    
    def _build_assistant_panel(self) -> None:
        """Build the right assistant panel (persistent chat sidebar)."""
        # Header
        header_frame = ttk.Frame(self.right_pane)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(
            header_frame,
            text="Assistant",
            font=("Segoe UI", 12, "bold")
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            header_frame,
            text="X",
            width=3,
            command=self._collapse_assistant
        ).pack(side=tk.RIGHT)
        
        ttk.Separator(self.right_pane, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10)
        
        # Chat display area
        chat_frame = ttk.Frame(self.right_pane)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.assistant_chat_display = tk.Text(
            chat_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Segoe UI", 10),
            height=20
        )
        chat_scroll = ttk.Scrollbar(chat_frame, orient=tk.VERTICAL, command=self.assistant_chat_display.yview)
        self.assistant_chat_display.configure(yscrollcommand=chat_scroll.set)
        
        self.assistant_chat_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        chat_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Input area
        input_frame = ttk.Frame(self.right_pane)
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.assistant_input = ttk.Entry(input_frame)
        self.assistant_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.assistant_input.bind("<Return>", lambda e: self._on_assistant_send())
        
        ttk.Button(
            input_frame,
            text="Send",
            command=self._on_assistant_send,
            width=8
        ).pack(side=tk.RIGHT)
        
        # Add initial message (will be updated when phase changes)
        self._update_assistant_greeting()
    
    def _toggle_assistant(self) -> None:
        """Toggle assistant panel visibility."""
        if self.assistant_visible:
            self._collapse_assistant()
        else:
            self._expand_assistant()
    
    def _collapse_assistant(self) -> None:
        """Collapse the assistant panel."""
        # Robustly attempt to remove the right pane from the PanedWindow.
        # Note: `PanedWindow.panes()` returns widget path names (strings), so
        # comparing widget objects directly often fails. Use try/except to
        # call forget() and ignore errors if the pane isn't present.
        try:
            self.main_paned.forget(self.right_pane)
        except Exception:
            # Pane might not be present or forget could fail; ignore silently
            pass

        # Ensure the pane does not consume layout space
        try:
            self.right_pane.configure(width=0)
        except Exception:
            pass

        self.assistant_visible = False
        try:
            self.assistant_toggle_btn.configure(text="Show Assistant")
        except Exception:
            pass
    
    def _expand_assistant(self) -> None:
        """Expand the assistant panel."""
        panes = self.main_paned.panes()
        # Compare using widget name strings to determine presence
        if str(self.right_pane) not in panes:
            try:
                self.main_paned.add(self.right_pane, weight=0)
            except Exception:
                # If add fails (already present or other issue), ignore
                pass

        try:
            self.right_pane.configure(width=350)
        except Exception:
            pass

        self.assistant_visible = True
        try:
            self.assistant_toggle_btn.configure(text="Hide Assistant")
        except Exception:
            pass
    
    def _update_assistant_greeting(self) -> None:
        """Update assistant greeting based on current phase."""
        # Clear existing content
        self.assistant_chat_display.configure(state=tk.NORMAL)
        self.assistant_chat_display.delete(1.0, tk.END)
        
        # Set context-aware greeting
        if hasattr(self, 'state_manager') and self.state_manager.current_state == AppState.PHASE_FOUNDRY:
            greeting = """Hello! I'm your entity editing assistant for the Foundry phase.

I can help you edit entities using natural language commands. Try:
• "Change Elena Rossi's rank to Colonel"
• "Update Outpost Zeta's description to a military outpost"
• "Set health to 85 for all actors"
• "Merge entity A into entity B"
• "Add affiliation field to Marcus Thorne"

What would you like to do?"""
        else:
            greeting = "Hello! I can help you with entity extraction, relationship mapping, and world-building. What would you like to do?"
        
        self.assistant_chat_display.insert(tk.END, f"Assistant: {greeting}\n\n")
        self.assistant_chat_display.configure(state=tk.DISABLED)
        self.assistant_chat_display.see(tk.END)
    
    def _append_to_assistant(self, sender: str, message: str) -> None:
        """Append a message to the assistant chat display."""
        self.assistant_chat_display.configure(state=tk.NORMAL)
        self.assistant_chat_display.insert(tk.END, f"{sender}: {message}\n\n")
        self.assistant_chat_display.configure(state=tk.DISABLED)
        self.assistant_chat_display.see(tk.END)
    
    def _on_assistant_send(self) -> None:
        """Handle sending a message to the assistant via TaskQueue."""
        message = self.assistant_input.get().strip()
        if not message:
            return
        
        self.assistant_input.delete(0, tk.END)
        self._append_to_assistant("You", message)
        
        # Check if we have a project loaded with LLM settings
        manifest = self.project_controller.manifest
        if not manifest:
            self._append_to_assistant("Assistant", "Please load a project first to enable AI-powered assistance.")
            return
        
        # Submit the assistant query via TaskQueue
        async def run_assistant_query():
            """Run the assistant query in background."""
            import os
            from pyscrai_core.llm_interface import create_provider
            
            provider_name = manifest.llm_provider
            env_key_map = {
                "openrouter": "OPENROUTER_API_KEY",
                "cherry": "CHERRY_API_KEY",
                "lm_studio": "LM_STUDIO_API_KEY",
                "lm_proxy": "LM_PROXY_API_KEY",
            }
            api_key = os.getenv(env_key_map.get(provider_name, ""), "not-needed")
            
            provider = create_provider(
                provider_name,
                api_key=api_key,
                base_url=manifest.llm_base_url,
                timeout=60.0
            )
            
            if hasattr(provider, 'default_model'):
                provider.default_model = manifest.llm_default_model
            
            async with provider:
                # Check if we're in Foundry phase - use UserProxyAgent for entity editing
                if self.state_manager.current_state == AppState.PHASE_FOUNDRY:
                    from pyscrai_forge.agents.user_proxy import UserProxyAgent
                    from pyscrai_forge.src.app.operation_handlers import OperationHandler
                    
                    # Create UserProxyAgent
                    user_proxy = UserProxyAgent(provider, manifest.llm_default_model)
                    
                    # Get current entities and relationships
                    entities = self.data_manager.entities
                    relationships = self.data_manager.relationships
                    
                    if entities:
                        # Process command through UserProxyAgent
                        result = await user_proxy.process_command(message, entities, relationships)
                        
                        # If result is a dict with operation, execute it
                        if isinstance(result, dict) and result.get("operation"):
                            from pyscrai_forge.src.app.operation_handlers import OperationHandler
                            handler = OperationHandler(entities, relationships)
                            op_result, success = handler.execute_operation(result)
                            
                            if success:
                                # Update data manager with modified entities/relationships
                                self.data_manager.entities = handler.entities
                                self.data_manager.relationships = handler.relationships
                                
                                # Refresh Foundry UI
                                self.root.after(0, lambda: self._refresh_foundry_ui())
                                
                                return op_result
                            else:
                                return f"Error: {op_result}"
                        else:
                            # UserProxyAgent returned a string response
                            return str(result)
                    else:
                        return "No entities loaded. Please import or create entities first."
                else:
                    # General assistant mode for other phases
                    context_parts = []
                    if self.data_manager.entities:
                        entity_names = [e.descriptor.name for e in self.data_manager.entities[:10]]
                        context_parts.append(f"Current entities: {', '.join(entity_names)}")
                    
                    context = "\n".join(context_parts) if context_parts else "No entities loaded yet."
                    
                    # Simple assistant prompt
                    prompt = f"""You are a worldbuilding assistant for PyScrAI|Forge.
                    
Context:
{context}

User question: {message}

Provide a helpful, concise response focused on worldbuilding and entity management."""
                    
                    response = await provider.complete(
                        prompt=prompt,
                        model=manifest.llm_default_model,
                        max_tokens=500
                    )
                    
                    return response.content if hasattr(response, 'content') else str(response)
        
        def on_complete(result):
            self._append_to_assistant("Assistant", result)
            # If in Foundry phase and entities were modified, refresh UI
            if self.state_manager.current_state == AppState.PHASE_FOUNDRY:
                self.root.after(100, lambda: self._refresh_foundry_ui())
        
        def on_error(error):
            self._append_to_assistant("Assistant", f"Error: {error}")
        
        self.task_queue.submit(
            run_assistant_query(),
            on_complete=on_complete,
            on_error=on_error
        )
    
    def _on_phase_nav(self, phase: AppState) -> None:
        """Handle phase navigation button click."""
        if not self.project_controller.current_project:
            messagebox.showwarning(
                "No Project",
                "Please load or create a project first to access pipeline phases.",
                parent=self.root
            )
            return
        
        self.state_manager.transition_to(phase)
        # Update assistant greeting when phase changes
        if hasattr(self, 'assistant_chat_display'):
            self._update_assistant_greeting()
        self._update_phase_button_states()
    
    def _update_phase_button_states(self) -> None:
        """Update phase button visual states based on current state."""
        current = self.state_manager.current_state
        
        for phase_state, btn in self.phase_buttons.items():
            if phase_state == current:
                # Active phase - could add visual indicator via style
                pass
            else:
                # Inactive phase
                pass
    
    def _get_callbacks(self) -> dict:
        """Return callbacks for menu/dialog actions."""
        return {
            # Project operations
            "new_project": self._on_new_project,
            "open_project": self._on_open_project,
            "open_recent": self._on_open_recent,
            "close_project": self._on_close_project,
            "clear_recent": self._on_clear_recent,
            "project_settings": self._on_project_settings,
            "browse_files": self._on_browse_files,
            "project_stats": self._on_project_stats,
            
            # Data operations
            "import_file": self._on_import_file,
            "extract_from_pool": self._on_extract_from_pool,
            "load_data_file": self._on_load_data_file,
            "add_entity": self._on_add_entity,
            "delete_selected_entity": self._on_delete_selected_entity,
            "edit_entity": self._on_edit_entity,
            "add_relationship": self._on_add_relationship,
            "delete_selected_relationship": self._on_delete_selected_relationship,
            "edit_relationship": self._on_edit_relationship,
            "commit_to_db": self._on_commit_to_db,
            "export_data": self._on_export_data,
            
            # State transitions
            "edit_components": self._on_edit_components,
            "refine_components": self._on_refine_components,
            "transition_to_dashboard": lambda: self.state_manager.transition_to(AppState.DASHBOARD),
            
            # Pipeline phase transitions
            "go_to_foundry": lambda: self._on_phase_nav(AppState.PHASE_FOUNDRY),
            "go_to_loom": lambda: self._on_phase_nav(AppState.PHASE_LOOM),
            "go_to_chronicle": lambda: self._on_phase_nav(AppState.PHASE_CHRONICLE),
            "go_to_cartography": lambda: self._on_phase_nav(AppState.PHASE_CARTOGRAPHY),
            "go_to_anvil": lambda: self._on_phase_nav(AppState.PHASE_ANVIL),
            "toggle_assistant": self._toggle_assistant,
            "get_manifest": lambda: self.project_controller.manifest,
            
            # Tools
            "browse_db": self._on_browse_db,
            "validate_project": self._on_validate_project,
            "preferences": self._on_preferences,
            "show_documentation": self._on_show_documentation,
            "show_about": self._on_show_about,
        }
    
    # Project and data callbacks are now provided by mixins
    
    def _on_state_changed(self, new_state: AppState) -> None:
        """Callback when application state changes."""
        # Update assistant greeting when phase changes
        if hasattr(self, 'assistant_chat_display'):
            self._update_assistant_greeting()
    
    def _on_data_changed(self) -> None:
        """Callback when data changes."""
        # Refresh UI based on current state
        if self.state_manager.current_state == AppState.PHASE_FOUNDRY:
            self._refresh_foundry_ui()
        elif self.state_manager.current_state == AppState.COMPONENT_EDITOR:
            self._refresh_component_editor_ui()
    
    def _refresh_foundry_ui(self) -> None:
        """Refresh Foundry phase UI with current data."""
        # Get the FoundryPanel from state_manager
        foundry_panel = getattr(self.state_manager, 'foundry_panel', None)
        if foundry_panel:
            # Set data_manager reference in foundry_panel for entity editing
            foundry_panel.data_manager = self.data_manager
            
            # Update FoundryPanel with data from data_manager
            foundry_panel.set_data(
                entities=self.data_manager.entities,
                relationships=self.data_manager.relationships,
                validation_report=self.data_manager.validation_report
            )
        else:
            # Fallback: ensure UI references are set for data_manager
            if self.state_manager.entities_tree:
                self.data_manager.set_ui_references(
                    entities_tree=self.state_manager.entities_tree,
                    relationships_tree=None,  # Foundry doesn't use relationships_tree
                    validation_frame=None,
                    validation_label=self.state_manager.validation_label,
                    root=self.root,
                    project_path=self.project_controller.current_project,
                    manifest=self.project_controller.manifest,
                    entities_sorter=getattr(self.state_manager, 'entities_sorter', None),
                    relationships_sorter=None
                )
                self.data_manager.refresh_ui()
                self.data_manager.update_validation_status()
    
    def _refresh_component_editor_ui(self) -> None:
        """Refresh component editor UI with current data (legacy fallback)."""
        # Ensure UI references are set (including sorters)
        self.data_manager.set_ui_references(
            entities_tree=self.state_manager.entities_tree,
            relationships_tree=self.state_manager.relationships_tree,
            validation_frame=self.state_manager.validation_frame,
            validation_label=self.state_manager.validation_label,
            root=self.root,
            project_path=self.project_controller.current_project,
            manifest=self.project_controller.manifest,
            entities_sorter=getattr(self.state_manager, 'entities_sorter', None),
            relationships_sorter=getattr(self.state_manager, 'relationships_sorter', None)
        )
        # Refresh the UI
        self.data_manager.refresh_ui()
        self.data_manager.update_validation_status()
    
    def _update_ui_for_project(self) -> None:
        """Update UI components when project changes."""
        # Update state manager with project data
        # Refresh user_config from ConfigManager to ensure we have latest
        self.user_config = self.config_manager.get_config()
        self.state_manager.set_project_data(
            self.project_controller.current_project,
            self.project_controller.db_path,
            self.project_controller.manifest,
            self.user_config
        )
        
        # Update data manager with project data
        self.data_manager.set_ui_references(
            entities_tree=self.state_manager.entities_tree,
            relationships_tree=self.state_manager.relationships_tree,
            validation_frame=self.state_manager.validation_frame,
            validation_label=self.state_manager.validation_label,
            root=self.root,
            project_path=self.project_controller.current_project,
            manifest=self.project_controller.manifest
        )
        
        # Update menu states
        has_project = self.project_controller.current_project is not None
        self.menu_manager.update_menu_states(has_project)
        
        # Update window title
        self.state_manager.update_window_title()


# Main function for module execution
def main(packet_path: Path | None = None, project_path: Path | None = None) -> None:
    """Main entry point for forge.
    
    Args:
        packet_path: Optional path to review packet file
        project_path: Optional path to project directory
    """
    app = ReviewerApp(packet_path=packet_path, project_path=project_path)
    app.root.mainloop()

