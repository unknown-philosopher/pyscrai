"""Project management operations for PyScrAI|Forge.

This module contains the ProjectOperationsMixin class with all project-related
callback methods extracted from main_app.py for better separation of concerns.
"""

from __future__ import annotations

from pathlib import Path
from tkinter import messagebox, ttk
import tkinter as tk

from .state_manager import AppState


class ProjectOperationsMixin:
    """Mixin class for project management operations.
    
    This mixin provides all project-related callback methods that can be
    mixed into the main ReviewerApp class. Methods expect access to:
    - self.project_controller
    - self.data_manager
    - self.state_manager
    - self.menu_manager
    - self.user_config
    - self.root
    - self.logger
    - self._update_ui_for_project (from main class)
    - self._save_user_config (from main class)
    """
    
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

