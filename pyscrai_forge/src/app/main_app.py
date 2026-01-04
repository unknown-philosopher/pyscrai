"""Main application controller for PyScrAI|Forge.

Coordinates all managers and handles high-level application logic.
"""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Optional

import sv_ttk

from .data_manager import DataManager
from .menu_manager import MenuManager
from .project_manager import ProjectController
from .state_manager import AppState, AppStateManager

if TYPE_CHECKING:
    from pyscrai_core import ProjectManifest
    from pyscrai_forge.src.user_config import UserConfig


class ReviewerApp:
    """Main application controller (coordinator)."""
    
    def __init__(self, packet_path: Path | None = None, project_path: Path | None = None):
        """Initialize the application.
        
        Args:
            packet_path: Optional path to review packet file
            project_path: Optional path to project directory
        """
        self.root = tk.Tk()
        self.root.title("PyScrAI|Forge - Tyler Hamilton v0.9.0")
        self.root.geometry("1400x900")
        
        # Load user config via ConfigManager
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
        
        # Build UI structure first
        self._build_ui_structure()
        
        # Initialize state manager (needs UI components)
        self.state_manager = AppStateManager(
            root=self.root,
            main_container=self.main_container,
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
            if self.project_controller.load_project(project_path, self.root):
                self.state_manager.transition_to(AppState.DASHBOARD)
            else:
                self.state_manager.transition_to(AppState.LANDING)
        else:
            self.state_manager.transition_to(AppState.LANDING)
        
        # Load packet if provided
        if packet_path and packet_path.exists():
            if self.data_manager.load_from_packet(packet_path):
                self.state_manager.transition_to(AppState.COMPONENT_EDITOR)
    
    def _save_user_config(self) -> None:
        """Save user configuration to disk via ConfigManager."""
        # Update the config manager's reference
        self.config_manager._config = self.user_config
        self.config_manager.save_config()
    
    def _build_ui_structure(self) -> None:
        """Build the basic UI structure (menu, status bar, container)."""
        # Status bar
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_bar = ttk.Label(status_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X)
        
        # Main container (will be populated by state builders)
        self.main_container = tk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)
    
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
            "transition_to_dashboard": lambda: self.state_manager.transition_to(AppState.DASHBOARD),
            
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
        result = self.project_controller.new_project_wizard(self.root)
        if result:
            self._update_ui_for_project()
            self.menu_manager.refresh_recent_projects()
            # Transition to dashboard after creating project
            self.state_manager.transition_to(AppState.DASHBOARD)
    
    def _on_open_project(self) -> None:
        """Handle open project action."""
        result = self.project_controller.open_project_dialog(self.root)
        if result:
            self._update_ui_for_project()
            self.menu_manager.refresh_recent_projects()
            # Transition to dashboard after opening project
            self.state_manager.transition_to(AppState.DASHBOARD)
    
    def _on_open_recent(self, project_path: Path) -> None:
        """Handle open recent project action."""
        if self.project_controller.open_recent_project(project_path, self.root):
            self._update_ui_for_project()
            self.menu_manager.refresh_recent_projects()
            # Transition to dashboard after opening recent project
            self.state_manager.transition_to(AppState.DASHBOARD)
    
    def _on_close_project(self) -> None:
        """Handle close project action."""
        if self.project_controller.current_project:
            if messagebox.askyesno("Close Project", "Close the current project?", parent=self.root):
                self.project_controller.close_project()
    
    def _on_clear_recent(self) -> None:
        """Handle clear recent projects action."""
        self.user_config.clear_recent_projects()
        self._save_user_config()
        self.menu_manager.refresh_recent_projects()
    
    def _on_project_settings(self) -> None:
        """Handle project settings action."""
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
        
        def on_import(text, metadata, file_path, interactive=False):
            # Use ForgeManager to extract entities
            import asyncio
            import threading
            from pyscrai_forge.agents.manager import ForgeManager
            from pyscrai_forge.prompts.core import Genre
            from pyscrai_core.llm_interface.provider_factory import create_provider_from_env
            from pathlib import Path
            
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
                    update_progress("Connecting to LLM provider...", "This requires API key configuration")
                    provider, model = create_provider_from_env()
                    
                    # Use current project path if available
                    project_path = None
                    if self.project_controller.current_project:
                        project_path = self.project_controller.current_project
                    
                    async with provider:
                        # Create HIL callback if interactive mode is enabled
                        hil_callback = None
                        if interactive:
                            from pyscrai_forge.src.app.hil_modal import TkinterHIL
                            hil = TkinterHIL(self.root)
                            hil_callback = hil.callback
                        
                        manager = ForgeManager(provider, project_path=project_path, hil_callback=hil_callback)
                        
                        # Run extraction pipeline (creates review packet)
                        update_progress("Running extraction pipeline...", f"Model: {model or 'default'}")
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                            tmp_path = Path(tmp.name)
                        
                        try:
                            packet_path = await manager.run_extraction_pipeline(
                                text=text,
                                genre=Genre.GENERIC,
                                output_path=tmp_path,
                                interactive=interactive
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
        about_text += "Version 0.9.5\n\n"
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

