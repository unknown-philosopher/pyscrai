"""Menu management for PyScrAI|Forge application.

Handles menu bar construction and menu state updates.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from pyscrai_forge.src.user_config import UserConfig, RecentProject


class MenuManager:
    """Builds and manages application menu bar."""
    
    def __init__(
        self,
        root: tk.Tk,
        callbacks: dict[str, Callable],
        user_config: Optional["UserConfig"] = None,
    ):
        """Initialize menu manager.
        
        Args:
            root: Main Tk window
            callbacks: Dictionary of callback functions for menu actions
            user_config: User configuration (for recent projects)
        """
        self.root = root
        self.callbacks = callbacks
        self.user_config = user_config
        
        # Menu references
        self.file_menu: Optional[tk.Menu] = None
        self.project_menu: Optional[tk.Menu] = None
        self.data_menu: Optional[tk.Menu] = None
        self.tools_menu: Optional[tk.Menu] = None
        self.recent_menu: Optional[tk.Menu] = None
    
    def build_menubar(self) -> tk.Menu:
        """Build the complete menu bar.
        
        Returns:
            The created menu bar
        """
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        self.file_menu = tk.Menu(menubar, tearoff=0)
        self.file_menu.add_command(label="New Project...", command=self.callbacks.get("new_project"))
        self.file_menu.add_command(label="Open Project...", command=self.callbacks.get("open_project"))
        
        # Recent projects submenu
        self.recent_menu = tk.Menu(self.file_menu, tearoff=0)
        self.file_menu.add_cascade(label="Recent Projects", menu=self.recent_menu)
        self._update_recent_projects_menu()
        
        self.file_menu.add_separator()
        self.file_menu.add_command(
            label="Close Project",
            command=self.callbacks.get("close_project"),
            state=tk.DISABLED
        )
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=self.file_menu)
        
        # Project menu (only enabled when project loaded)
        self.project_menu = tk.Menu(menubar, tearoff=0)
        self.project_menu.add_command(
            label="Project Settings...",
            command=self.callbacks.get("project_settings")
        )
        self.project_menu.add_command(
            label="Open Project Files",
            command=self.callbacks.get("browse_files")
        )
        self.project_menu.add_command(
            label="Project Statistics",
            command=self.callbacks.get("project_stats")
        )
        menubar.add_cascade(label="Project", menu=self.project_menu)
        
        # Data menu (only enabled when project loaded)
        self.data_menu = tk.Menu(menubar, tearoff=0)
        self.data_menu.add_command(
            label="Import & Extract...",
            command=self.callbacks.get("import_file")
        )
        self.data_menu.add_separator()
        self.data_menu.add_command(
            label="Component Editor",
            command=self.callbacks.get("edit_components")
        )
        self.data_menu.add_command(
            label="Database Explorer...",
            command=self.callbacks.get("browse_db")
        )
        self.data_menu.add_separator()
        self.data_menu.add_command(
            label="Export Project Data...",
            command=self.callbacks.get("export_data")
        )
        menubar.add_cascade(label="Data", menu=self.data_menu)
        
        # Tools menu (always available)
        self.tools_menu = tk.Menu(menubar, tearoff=0)
        self.tools_menu.add_command(
            label="Validate Project",
            command=self.callbacks.get("validate_project")
        )
        self.tools_menu.add_command(
            label="Preferences...",
            command=self.callbacks.get("preferences")
        )
        menubar.add_cascade(label="Tools", menu=self.tools_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(
            label="Documentation",
            command=self.callbacks.get("show_documentation")
        )
        help_menu.add_command(
            label="About PyScrAI|Forge",
            command=self.callbacks.get("show_about")
        )
        menubar.add_cascade(label="Help", menu=help_menu)
        
        return menubar
    
    def update_menu_states(self, has_project: bool) -> None:
        """Update menu item enabled/disabled states.
        
        Args:
            has_project: Whether a project is currently loaded
        """
        # File menu
        if self.file_menu:
            self.file_menu.entryconfig(
                "Close Project",
                state=tk.NORMAL if has_project else tk.DISABLED
            )
        
        # Project menu
        if self.project_menu:
            for i in range(self.project_menu.index(tk.END) + 1):
                try:
                    self.project_menu.entryconfig(
                        i,
                        state=tk.NORMAL if has_project else tk.DISABLED
                    )
                except Exception:
                    pass
        
        # Data menu
        if self.data_menu:
            for i in range(self.data_menu.index(tk.END) + 1):
                try:
                    self.data_menu.entryconfig(
                        i,
                        state=tk.NORMAL if has_project else tk.DISABLED
                    )
                except Exception:
                    pass
    
    def _update_recent_projects_menu(self) -> None:
        """Update the recent projects submenu."""
        if not self.recent_menu:
            return
        
        self.recent_menu.delete(0, tk.END)
        
        if self.user_config and self.user_config.recent_projects:
            for proj in self.user_config.recent_projects[:10]:
                self.recent_menu.add_command(
                    label=f"{proj.name}",
                    command=lambda p=Path(proj.path): self.callbacks.get("open_recent")(p)
                )
            self.recent_menu.add_separator()
        
        self.recent_menu.add_command(
            label="Clear Recent",
            command=self.callbacks.get("clear_recent")
        )
    
    def refresh_recent_projects(self) -> None:
        """Refresh the recent projects menu (call after updating user_config)."""
        self._update_recent_projects_menu()

