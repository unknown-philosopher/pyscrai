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


class ReviewerApp:
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
            callbacks=self._get_callbacks()
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
        if packet_path and packet_path.exists():
            self.logger.info(f"Loading packet: {packet_path}")
            if self.data_manager.load_from_packet(packet_path):
                self.state_manager.transition_to(AppState.COMPONENT_EDITOR)
    
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
        
        # Add initial message
        self._append_to_assistant("Assistant", "Hello! I can help you with entity extraction, relationship mapping, and world-building. What would you like to do?")
    
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
                # Build context from current data
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
            
            # Tools
            "browse_db": self._on_browse_db,
            "validate_project": self._on_validate_project,
            "preferences": self._on_preferences,
            "show_documentation": self._on_show_documentation,
            "show_about": self._on_show_about,
        }
    
    # Project callbacks
    def _on_project_loaded(self, project_path: Path) -> None:
        """Callback when project is loaded."""
        self.data_manager.set_db_path(self.project_controller.db_path)
        self._update_ui_for_project()
        # Transition to dashboard after loading project
        self.state_manager.transition_to(AppState.DASHBOARD)
    
    def _on_project_closed(self) -> None:
        """Callback when project is closed."""
        self.data_manager.clear_data()
        self.data_manager.set_db_path(None)
        self._update_ui_for_project()
        self.state_manager.transition_to(AppState.LANDING)
    
    def _on_new_project(self) -> None:
        """Handle new project action."""
        self.logger.info("User initiated new project creation.")
        result = self.project_controller.new_project_wizard(self.root)
        if result:
            self._update_ui_for_project()
            self.menu_manager.refresh_recent_projects()
            # Transition to dashboard after creating project
            self.state_manager.transition_to(AppState.DASHBOARD)
    
    def _on_open_project(self) -> None:
        """Handle open project action."""
        self.logger.info("User initiated open project dialog.")
        result = self.project_controller.open_project_dialog(self.root)
        if result:
            self._update_ui_for_project()
            self.menu_manager.refresh_recent_projects()
            # Transition to dashboard after opening project
            self.state_manager.transition_to(AppState.DASHBOARD)
    
    def _on_open_recent(self, project_path: Path) -> None:
        """Handle open recent project action."""
        self.logger.info(f"User requested to open recent project: {project_path}")
        if self.project_controller.open_recent_project(project_path, self.root):
            self._update_ui_for_project()
            self.menu_manager.refresh_recent_projects()
            # Transition to dashboard after opening recent project
            self.state_manager.transition_to(AppState.DASHBOARD)
    
    def _on_close_project(self) -> None:
        """Handle close project action."""
        if self.project_controller.current_project:
            if messagebox.askyesno("Close Project", "Close the current project?", parent=self.root):
                self.logger.info(f"Closing project: {self.project_controller.current_project}")
                self.project_controller.close_project()
    
    def _on_clear_recent(self) -> None:
        """Handle clear recent projects action."""
        self.logger.info("Clearing recent projects list.")
        self.user_config.clear_recent_projects()
        self._save_user_config()
        self.menu_manager.refresh_recent_projects()
    
    def _on_project_settings(self) -> None:
        """Handle project settings action."""
        self.logger.info("Opening project settings.")
        self.project_controller.open_project_manager(self.root)
    
    def _on_browse_files(self) -> None:
        """Handle browse files action."""
        self.project_controller.open_file_browser(self.root)
    
    def _on_project_stats(self) -> None:
        """Handle project statistics action."""
        if not self.project_controller.current_project:
            messagebox.showwarning("No Project", "Please load a project first.", parent=self.root)
            return
        
        # Simple stats dialog
        stats_win = tk.Toplevel(self.root)
        stats_win.title("Project Statistics")
        stats_win.geometry("400x300")
        stats_win.transient(self.root)
        
        try:
            from pyscrai_forge.src import storage
            if self.project_controller.db_path and self.project_controller.db_path.exists():
                entities = storage.load_all_entities(self.project_controller.db_path)
                relationships = storage.load_all_relationships(self.project_controller.db_path)
                
                stats_text = f"Project: {self.project_controller.manifest.name if self.project_controller.manifest else 'Unknown'}\n\n"
                stats_text += f"Total Entities: {len(entities)}\n"
                stats_text += f"Total Relationships: {len(relationships)}\n\n"
                
                # Count by type
                type_counts = {}
                for e in entities:
                    t = e.descriptor.entity_type.value if hasattr(e.descriptor, 'entity_type') else "unknown"
                    type_counts[t] = type_counts.get(t, 0) + 1
                
                stats_text += "Entities by Type:\n"
                for entity_type, count in sorted(type_counts.items()):
                    stats_text += f"  • {entity_type.title()}: {count}\n"
                
                ttk.Label(stats_win, text=stats_text, justify=tk.LEFT, font=("Arial", 10)).pack(padx=20, pady=20)
            else:
                ttk.Label(stats_win, text="Database not initialized yet.", font=("Arial", 10)).pack(padx=20, pady=20)
        except Exception as e:
            ttk.Label(stats_win, text=f"Error loading stats: {e}", font=("Arial", 10), foreground="red").pack(padx=20, pady=20)
        
        ttk.Button(stats_win, text="Close", command=stats_win.destroy).pack(pady=10)
    
    # Data callbacks
    def _on_import_file(self) -> None:
        """Handle import file action."""
        if not self.project_controller.current_project:
            messagebox.showwarning("No Project", "Please load or create a project first.", parent=self.root)
            return
        
        from pyscrai_forge.src.ui.import_dialog import ImportDialog
        
        def on_import(text, metadata, file_path, reset_counters=False):
            # Use ForgeManager to extract entities
            import asyncio
            import threading
            from pyscrai_forge.agents.manager import ForgeManager
            from pyscrai_forge.prompts.core import Genre
            from pyscrai_core.llm_interface import create_provider
            from pathlib import Path
            import os
            
            # Get provider settings from project manifest instead of .env
            # Reload manifest from disk to ensure we have the latest settings
            self.project_controller._load_manifest()
            manifest = self.project_controller.manifest
            if not manifest:
                messagebox.showerror("Error", "No project manifest found. Please create or load a project first.")
                return
            
            # Get API key from environment (only API keys should remain in .env)
            provider_name = manifest.llm_provider
            env_key_map = {
                "openrouter": "OPENROUTER_API_KEY",
                "cherry": "CHERRY_API_KEY",
                "lm_studio": "LM_STUDIO_API_KEY",
                "lm_proxy": "LM_PROXY_API_KEY",
            }
            api_key = os.getenv(env_key_map.get(provider_name, ""), "not-needed")
            
            # Create progress dialog
            progress_win = tk.Toplevel(self.root)
            progress_win.title("Extracting Entities...")
            progress_win.geometry("400x150")
            progress_win.transient(self.root)
            progress_win.grab_set()
            
            progress_label = tk.Label(progress_win, text="Initializing LLM provider...", pady=20)
            progress_label.pack()
            
            progress_status = tk.Label(progress_win, text="", fg="gray")
            progress_status.pack()
            
            result_container = {"entities": None, "relationships": None, "report": None, "error": None}
            
            def update_progress(msg, status=""):
                try:
                    progress_label.config(text=msg)
                    progress_status.config(text=status)
                    progress_win.update()
                except:
                    pass
            
            async def run_extraction():
                try:
                    # Store provider and model for consistent display
                    provider_name = manifest.llm_provider
                    model_name = manifest.llm_default_model
                    
                    update_progress("Connecting to LLM provider...", 
                                  f"Provider: {provider_name} | Model: {model_name}")
                    
                    # Create provider from project manifest settings
                    provider = create_provider(
                        provider_name,
                        api_key=api_key,
                        base_url=manifest.llm_base_url,
                        timeout=60.0
                    )
                    
                    # Store the default model on the provider
                    if hasattr(provider, 'default_model'):
                        provider.default_model = model_name
                    
                    model = model_name
                    
                    # Use current project path if available
                    project_path = None
                    if self.project_controller.current_project:
                        project_path = self.project_controller.current_project
                    
                    # Reset ID counters if requested - do this AFTER getting project path
                    # but BEFORE creating ForgeManager (which loads the project and counters)
                    if reset_counters:
                        from pyscrai_core import reset_id_counters
                        from pyscrai_core.models import set_id_counters_path
                        
                        # Set the counters path first so reset can write to the file
                        if project_path:
                            set_id_counters_path(project_path / ".id_counters.json")
                        
                        reset_id_counters()
                        update_progress("ID counters reset", "Starting from ENTITY_001 and REL_001")
                    
                    async with provider:
                        manager = ForgeManager(provider, project_path=project_path, hil_callback=None)
                        
                        # Get the template from the project manifest if available
                        template_name = None
                        if manager.controller and manager.controller.manifest:
                            template_name = manager.controller.manifest.template
                        
                        # Run extraction pipeline (creates review packet)
                        update_progress("Running extraction pipeline...", f"Provider: {provider_name} | Model: {model_name}")
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                            tmp_path = Path(tmp.name)
                        
                        try:
                            # Check for verbose mode via environment variable or config
                            import os
                            verbose = os.getenv("PYSCRAI_VERBOSE", "").lower() in ("1", "true", "yes")
                            
                            packet_path = await manager.run_extraction_pipeline(
                                text=text,
                                genre=Genre.GENERIC,
                                output_path=tmp_path,
                                template_name=template_name,
                                verbose=verbose
                            )
                            
                            # Load the packet to get entities and relationships
                            import json
                            with open(packet_path, 'r', encoding='utf-8') as f:
                                packet = json.load(f)
                            
                            # Convert back to Entity/Relationship objects
                            from pyscrai_core import Entity, Relationship, RelationshipType
                            entities = []
                            for e_data in packet.get('entities', []):
                                entities.append(Entity.model_validate(e_data))
                            
                            relationships = []
                            for r_data in packet.get('relationships', []):
                                relationships.append(Relationship.model_validate(r_data))
                            
                            # Extract validation report from packet
                            from pyscrai_forge.agents.validator import ValidationReport
                            validation_data = packet.get('validation_report', {})
                            report = ValidationReport(
                                critical_errors=validation_data.get('critical_errors', []),
                                warnings=validation_data.get('warnings', [])
                            )
                            
                            return entities, relationships, report
                        except ValueError as ve:
                            # Handle pipeline failures (e.g., Scout phase failed)
                            raise Exception(f"Extraction pipeline failed: {ve}")
                        
                except Exception as e:
                    raise Exception(f"LLM connection or extraction failed: {str(e)}")
            
            def run_async_in_thread():
                """Run the async extraction in a separate thread with its own event loop."""
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        entities, relationships, report = loop.run_until_complete(run_extraction())
                        result_container["entities"] = entities
                        result_container["relationships"] = relationships
                        result_container["report"] = report
                    finally:
                        loop.close()
                except Exception as e:
                    result_container["error"] = str(e)
                
                # Schedule cleanup in main thread
                self.root.after(0, finish_extraction)
            
            def finish_extraction():
                """Handle extraction results in main thread."""
                try:
                    progress_win.destroy()
                except:
                    pass
                
                if result_container["error"]:
                    messagebox.showerror("Extraction Error", result_container["error"], parent=self.root)
                    return
                
                entities = result_container["entities"]
                relationships = result_container["relationships"]
                report = result_container["report"]
                
                # Load into data manager
                self.data_manager.entities = entities
                self.data_manager.relationships = relationships
                self.data_manager.validation_report = report.model_dump() if hasattr(report, 'model_dump') else {}
                
                # Transition to component editor to show results
                self.state_manager.transition_to(AppState.COMPONENT_EDITOR)
                
                # Update UI references and refresh after transition (treeviews are now created)
                self._refresh_component_editor_ui()
                
                if len(entities) == 0:
                    messagebox.showwarning(
                        "No Entities Found",
                        f"No entities were extracted from {file_path}.\n\n"
                        "Possible reasons:\n"
                        "• Text may not contain recognizable entities\n"
                        "• LLM connection issues (check terminal for errors)\n"
                        "• Model may need different prompting"
                    )
                else:
                    out_path = None
                    if self.project_controller.current_project:
                        import datetime
                        import re
                        data_dir = self.project_controller.current_project / "data"
                        data_dir.mkdir(exist_ok=True)
                        src_name = Path(file_path).stem if file_path else "imported"
                        timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
                        safe_src = re.sub(r'[^a-zA-Z0-9_\-]', '_', src_name)
                        out_name = f"entity_components_{timestamp}_{safe_src}.json"
                        out_path = data_dir / out_name
                        backup_data = {
                            "entities": [json.loads(e.model_dump_json()) for e in entities],
                            "relationships": [json.loads(r.model_dump_json()) for r in relationships],
                            "validation_report": report.model_dump() if hasattr(report, 'model_dump') else {}
                        }
                        try:
                            with open(out_path, "w", encoding="utf-8") as f:
                                json.dump(backup_data, f, indent=2)
                        except Exception as e:
                            print(f"[WARN] Failed to save backup JSON: {e}")
                    
                    messagebox.showinfo(
                        "Import Complete",
                        f"Extracted {len(entities)} entities and {len(relationships)} relationships from {file_path}.\n\n"
                        f"Validation: {'✓ Passed' if report.is_valid else f'✗ {len(report.critical_errors)} errors'}\n\n"
                        f"Backup saved to: {out_path if out_path else '[no project loaded]'}"
                    )
            
            # Start extraction in background thread
            thread = threading.Thread(target=run_async_in_thread, daemon=True)
            thread.start()
        
        ImportDialog(self.root, on_import=on_import)
    
    def _on_load_data_file(self) -> None:
        """Handle load data file action."""
        if self.data_manager.load_from_file(self.root):
            self.state_manager.transition_to(AppState.COMPONENT_EDITOR)
            # Update UI references and refresh after transition
            self._refresh_component_editor_ui()
    
    def _on_add_entity(self) -> None:
        """Handle add entity action."""
        self.data_manager.add_entity()
    
    def _on_delete_selected_entity(self) -> None:
        """Handle delete selected entity action."""
        self.data_manager.delete_selected_entity()
    
    def _on_edit_entity(self) -> None:
        """Handle edit entity action."""
        self.data_manager.edit_entity()
    
    def _on_add_relationship(self) -> None:
        """Handle add relationship action."""
        self.data_manager.add_relationship()
    
    def _on_delete_selected_relationship(self) -> None:
        """Handle delete selected relationship action."""
        self.data_manager.delete_selected_relationship()
    
    def _on_edit_relationship(self) -> None:
        """Handle edit relationship action."""
        self.data_manager.edit_relationship()
    
    def _on_commit_to_db(self) -> None:
        """Handle commit to database action."""
        self.data_manager.commit_to_database()
    
    def _on_export_data(self) -> None:
        """Handle export data action."""
        self.data_manager.export_data(self.root)
    
    def _on_edit_components(self) -> None:
        """Handle edit components action."""
        if not self.project_controller.current_project:
            messagebox.showwarning("No Project", "Please load a project first.", parent=self.root)
            return
        self.state_manager.transition_to(AppState.COMPONENT_EDITOR)
    
    def _on_refine_components(self) -> None:
        """Handle refine components action - opens chat dialog for entity refinement."""
        if not self.project_controller.current_project:
            messagebox.showwarning("No Project", "Please load a project first.", parent=self.root)
            return
        
        # Get current entities and relationships from data manager
        entities = self.data_manager.entities
        relationships = self.data_manager.relationships
        
        if not entities:
            messagebox.showinfo("No Entities", "No entities to refine. Import or create some first.", parent=self.root)
            return
        
        # Open chat dialog for refinement
        from pyscrai_forge.src.ui.dialogs.chat_dialog import ChatDialog
        
        # Try to create a UserProxyAgent with LLM provider
        user_proxy = None
        try:
            from pyscrai_forge.agents.user_proxy import UserProxyAgent
            from pyscrai_core.llm_interface import create_provider
            import os
            
            # Get provider settings from project manifest
            manifest = self.project_controller.manifest
            if manifest:
                provider_name = manifest.llm_provider
                env_key_map = {
                    "openrouter": "OPENROUTER_API_KEY",
                    "cherry": "CHERRY_API_KEY",
                    "lm_studio": "LM_STUDIO_API_KEY",
                    "lm_proxy": "LM_PROXY_API_KEY",
                }
                api_key = os.getenv(env_key_map.get(provider_name, ""), "not-needed")
                
                provider = create_provider(
                    manifest.llm_provider,
                    api_key=api_key,
                    base_url=manifest.llm_base_url,
                    timeout=60.0
                )
                
                if hasattr(provider, 'default_model'):
                    provider.default_model = manifest.llm_default_model
                
                model = manifest.llm_default_model
                user_proxy = UserProxyAgent(provider, model)
        except Exception as e:
            self.logger.warning(f"Could not create UserProxyAgent: {e}. Chat will be limited.")
        
        # For now, use a simple callback that updates the data manager
        def on_operation_executed(updated_entities, updated_relationships):
            self.data_manager.entities = updated_entities
            self.data_manager.relationships = updated_relationships
            self.data_manager.refresh_ui()
            self.logger.info(f"Refined entities: {len(updated_entities)} entities, {len(updated_relationships)} relationships")
        
        # Create and show chat dialog
        chat_dialog = ChatDialog(
            self.root,
            entities=entities,
            relationships=relationships,
            user_proxy=user_proxy,
            on_operation_executed=on_operation_executed
        )
    
    
    def _on_browse_db(self) -> None:
        """Handle browse database action."""
        from pyscrai_forge.src.ui.windows.db_explorer import DatabaseExplorerWindow
        
        db_path = self.project_controller.db_path if self.project_controller.db_path else None
        DatabaseExplorerWindow(self.root, db_path=db_path)
    
    def _on_validate_project(self) -> None:
        """Handle validate project action."""
        if not self.project_controller.current_project:
            messagebox.showinfo("No Project", "Please load a project first.", parent=self.root)
            return
        
        # Simple validation
        issues = []
        
        if not self.project_controller.manifest:
            issues.append("No project manifest found")
        else:
            if not self.project_controller.manifest.name:
                issues.append("Project name is missing")
        
        if self.project_controller.db_path and self.project_controller.db_path.exists():
            try:
                from pyscrai_forge.src import storage
                entities = storage.load_all_entities(self.project_controller.db_path)
                relationships = storage.load_all_relationships(self.project_controller.db_path)
                
                # Check for orphaned relationships
                entity_ids = {e.id for e in entities}
                for rel in relationships:
                    if rel.source_id not in entity_ids:
                        issues.append(f"Relationship {rel.id} references missing source entity: {rel.source_id}")
                    if rel.target_id not in entity_ids:
                        issues.append(f"Relationship {rel.id} references missing target entity: {rel.target_id}")
            except Exception as e:
                issues.append(f"Error reading database: {e}")
        
        if issues:
            messagebox.showwarning("Validation Issues", "\n".join(issues[:10]), parent=self.root)
        else:
            messagebox.showinfo("Validation", "Project validation passed!", parent=self.root)
    
    def _on_preferences(self) -> None:
        """Handle preferences action."""
        messagebox.showinfo("Preferences", "Preferences dialog coming soon!", parent=self.root)
    
    def _on_show_documentation(self) -> None:
        """Handle show documentation action."""
        messagebox.showinfo("Documentation", "Documentation coming soon!", parent=self.root)
    
    def _on_show_about(self) -> None:
        """Handle show about action."""
        about_text = "PyScrAI|Forge\n\n"
        about_text += "Worldbuilding & Entity Management Toolkit\n"
        about_text += "Version 0.9.8\n\n"
        about_text += "By Tyler Hamilton"
        messagebox.showinfo("About PyScrAI|Forge", about_text, parent=self.root)
    
    def _on_data_changed(self) -> None:
        """Callback when data changes."""
        # Refresh UI if we're in component editor
        if self.state_manager.current_state == AppState.COMPONENT_EDITOR:
            self._refresh_component_editor_ui()
    
    def _refresh_component_editor_ui(self) -> None:
        """Refresh component editor UI with current data."""
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

