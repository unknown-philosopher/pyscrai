"""Project management for PyScrAI|Forge application.

Handles project loading, saving, and management operations.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from tkinter import messagebox
from typing import TYPE_CHECKING, Callable, Optional

from pyscrai_forge.src.logging_config import get_logger

if TYPE_CHECKING:
    from pyscrai_core import ProjectManifest
    from pyscrai_forge.src.user_config import UserConfig


class ProjectController:
    """Handles project loading, saving, and management."""
    
    def __init__(
        self,
        user_config: "UserConfig",
        on_project_loaded: Optional[Callable[[Path], None]] = None,
        on_project_closed: Optional[Callable[[], None]] = None,
    ):
        """Initialize project controller.
        
        Args:
            user_config: User configuration instance
            on_project_loaded: Callback when project is loaded
            on_project_closed: Callback when project is closed
        """
        self.logger = get_logger(__name__)
        self.user_config = user_config
        self.on_project_loaded = on_project_loaded
        self.on_project_closed = on_project_closed
        
        self.current_project: Optional[Path] = None
        self.db_path: Optional[Path] = None
        self.manifest: Optional["ProjectManifest"] = None
    
    def load_project(self, project_path: Path, parent_window=None) -> bool:
        """Load a project and return success status.
        
        Args:
            project_path: Path to project directory
            parent_window: Parent window for dialogs (optional)
            
        Returns:
            True if project loaded successfully, False otherwise
        """
        self.logger.info(f"Attempting to load project from: {project_path}")
        
        if not project_path.exists():
            self.logger.error(f"Project directory not found: {project_path}")
            if parent_window:
                messagebox.showerror("Error", f"Project directory not found: {project_path}", parent=parent_window)
            return False
        
        # Check for project.json
        manifest_path = project_path / "project.json"
        if not manifest_path.exists():
            self.logger.warning(f"No project.json found in {project_path}")
            if parent_window:
                from tkinter import messagebox
                if not messagebox.askyesno(
                    "No Project Manifest",
                    f"No project.json found in {project_path}.\n\n"
                    "This may not be a valid PyScrAI project. Create a new project here?",
                    parent=parent_window
                ):
                    return False
                # Create a basic manifest
                self.logger.info(f"Creating new project at: {project_path}")
                from pyscrai_core.project import ProjectController as CoreProjectController
                try:
                    CoreProjectController.create_project(project_path, name=project_path.name)
                    self.logger.info("Project created successfully")
                except Exception as e:
                    self.logger.error(f"Failed to create project: {e}")
                    messagebox.showerror("Error", f"Failed to create project: {e}", parent=parent_window)
                    return False
            else:
                return False
        
        self.current_project = project_path
        self.db_path = project_path / "world.db"
        self._load_manifest()
        
        # Add to recent projects
        if self.manifest:
            self.logger.info(f"Project loaded: {self.manifest.name} ({self.manifest.version})")
            self.user_config.add_recent_project(project_path, self.manifest.name)
            # Note: add_recent_project() already calls save() internally
        
        # Notify callback
        if self.on_project_loaded:
            self.on_project_loaded(project_path)
        
        return True
    
    def close_project(self) -> None:
        """Close the current project."""
        if self.current_project:
            self.logger.info(f"Closing project: {self.current_project}")
        
        self.current_project = None
        self.db_path = None
        self.manifest = None
        
        # Notify callback
        if self.on_project_closed:
            self.on_project_closed()
    
    def _load_manifest(self) -> None:
        """Load project manifest if available."""
        if not self.current_project:
            return
        
        manifest_path = self.current_project / "project.json"
        if manifest_path.exists():
            try:
                from pyscrai_core import ProjectManifest
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                    self.manifest = ProjectManifest.model_validate(manifest_data)
            except Exception as e:
                self.logger.error(f"Failed to load manifest: {e}")
    
    def open_project_dialog(self, parent_window) -> Optional[Path]:
        """Open project directory dialog.
        
        Args:
            parent_window: Parent window for dialog
            
        Returns:
            Selected project path or None
        """
        from tkinter import filedialog
        d = filedialog.askdirectory(title="Open Project", parent=parent_window)
        if d:
            path = Path(d)
            if self.load_project(path, parent_window):
                return path
        return None
    
    def open_recent_project(self, project_path: Path, parent_window=None) -> bool:
        """Open a recent project.
        
        Args:
            project_path: Path to recent project
            parent_window: Parent window for dialogs (optional)
            
        Returns:
            True if opened successfully, False otherwise
        """
        if project_path.exists():
            return self.load_project(project_path, parent_window)
        else:
            if parent_window:
                messagebox.showerror(
                    "Error",
                    f"Project directory not found: {project_path}",
                    parent=parent_window
                )
            # Remove from recent projects
            self.user_config.recent_projects = [
                p for p in self.user_config.recent_projects if Path(p.path) != project_path
            ]
            # Save via ConfigManager
            try:
                from pyscrai_forge.src.config_manager import ConfigManager
                config_mgr = ConfigManager.get_instance()
                config_mgr._config = self.user_config
                config_mgr.save_config()
            except Exception:
                # Fallback to direct save
                self.user_config.save()
            return False
    
    def new_project_wizard(self, parent_window) -> Optional[Path]:
        """Launch the new project wizard.
        
        Args:
            parent_window: Parent window for wizard
            
        Returns:
            Created project path or None
        """
        from pyscrai_forge.src.ui.dialogs.project_wizard import ProjectWizardDialog
        
        result_path = None
        
        def on_complete(project_path):
            nonlocal result_path
            if project_path:
                if self.load_project(project_path, parent_window):
                    result_path = project_path
        
        ProjectWizardDialog(parent_window, on_complete=on_complete)
        return result_path
    
    def open_project_manager(self, parent_window) -> None:
        """Open the project manager window.
        
        Args:
            parent_window: Parent window
        """
        from pyscrai_forge.src.ui.windows.project_manager import ProjectManagerWindow
        from tkinter import messagebox
        
        if not self.current_project:
            if not messagebox.askyesno(
                "No Project",
                "No project is currently loaded. Create a new project configuration?",
                parent=parent_window
            ):
                return
        
        ProjectManagerWindow(parent_window, project_path=self.current_project)
    
    def open_file_browser(self, parent_window) -> None:
        """Open the project directory in OS file browser.
        
        Args:
            parent_window: Parent window for error dialogs
        """
        if not self.current_project:
            messagebox.showwarning(
                "No Project",
                "Please load or create a project first.",
                parent=parent_window
            )
            return
        
        # Open OS file browser (cross-platform)
        try:
            if os.name == 'nt':  # Windows
                subprocess.Popen(f'explorer "{self.current_project}"')
            else:
                import platform
                if platform.system() == 'Darwin':  # macOS
                    subprocess.Popen(['open', str(self.current_project)])
                else:  # Linux
                    subprocess.Popen(['xdg-open', str(self.current_project)])
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to open file browser:\n{str(e)}",
                parent=parent_window
            )

