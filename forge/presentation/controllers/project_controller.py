"""Project controller for session management and configuration."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Any

import flet as ft

# Try to import tkinter, but make it optional
try:
    import tkinter as tk
    from tkinter import filedialog
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    tk: Any = None
    filedialog: Any = None

if TYPE_CHECKING:
    from forge.core.app_controller import AppController
    from forge.domain.session.session_manager import SessionManager

logger = logging.getLogger(__name__)


class ProjectController:
    """Handles project settings, save/load, and configuration UI."""
    
    def __init__(self, app_controller: AppController, session_manager: SessionManager, page: ft.Page):
        self.app_controller = app_controller
        self.session_manager = session_manager
        self.page = page
    
    def build_view(self) -> ft.Control:
        """Build the project management view."""
        
        # --- Project Actions ---
        
        async def on_open_project(e):
            """Open a project file using file dialog."""
            if not TKINTER_AVAILABLE:
                await self.app_controller.push_agui_log(
                    "File dialog not available. Please install python3-tk: sudo apt-get install python3-tk",
                    "error"
                )
                return
            
            # Hide the tkinter root window
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            # Open file dialog
            file_path = filedialog.askopenfilename(
                title="Open Project",
                filetypes=[("DuckDB Database", "*.duckdb"), ("All Files", "*.*")],
                initialdir=os.getcwd(),
            )
            
            root.destroy()
            
            if file_path:
                await self.app_controller.push_agui_log(f"Opening project: {file_path}", "info")
                await self.session_manager.open_project(file_path)
            else:
                await self.app_controller.push_agui_log("Project open cancelled", "info")
        
        async def on_save_project(e):
            """Save the current project using file dialog."""
            if not TKINTER_AVAILABLE:
                await self.app_controller.push_agui_log(
                    "File dialog not available. Please install python3-tk: sudo apt-get install python3-tk",
                    "error"
                )
                return
            
            # Hide the tkinter root window
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            # Save file dialog
            file_path = filedialog.asksaveasfilename(
                title="Save Project",
                defaultextension=".duckdb",
                filetypes=[("DuckDB Database", "*.duckdb"), ("All Files", "*.*")],
                initialdir=os.getcwd(),
                initialfile="project.duckdb",
            )
            
            root.destroy()
            
            if file_path:
                await self.app_controller.push_agui_log(f"Saving project to: {file_path}", "info")
                await self.session_manager.save_project(file_path)
            else:
                await self.app_controller.push_agui_log("Project save cancelled", "info")
            
        async def on_reset_click(e):
            """Reset the current project (clear all data)."""
            await self.app_controller.push_agui_log("Resetting project...", "warning")
            await self.session_manager.clear_session()

        # --- Configuration Inputs ---
        
        api_key_input = ft.TextField(
            label="OpenRouter API Key",
            password=True,
            can_reveal_password=True,
            value=os.getenv("OPENROUTER_API_KEY", ""),
            border_color="rgba(255,255,255,0.2)",
        )
        
        model_dropdown = ft.Dropdown(
            label="Default Model",
            options=[
                ft.dropdown.Option("anthropic/claude-3-opus"),
                ft.dropdown.Option("anthropic/claude-3-sonnet"),
                ft.dropdown.Option("openai/gpt-4-turbo"),
                ft.dropdown.Option("mistralai/mistral-large"),
            ],
            value=os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-sonnet"),
            border_color="rgba(255,255,255,0.2)",
        )

        def on_save_config(e):
            # In a real app, this might update a .env file or internal config state
            # For now, we just log it
            asyncio.create_task(self.app_controller.push_agui_log("Configuration updated (Runtime only)", "success"))

        # --- Layout ---

        return ft.Container(
            padding=20,
            content=ft.Column(
                [
                    # Header
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.SETTINGS_APPLICATIONS, size=32, color=ft.Colors.CYAN_300),
                            ft.Text(
                                "Project Management",
                                size=24,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.WHITE),
                        ],
                        spacing=12,
                    ),
                    
                    ft.Divider(color="rgba(255, 255, 255, 0.1)", height=20),
                    
                    # Project Management Section
                    ft.Text("Project Management", size=18, weight=ft.FontWeight.W_600, color=ft.Colors.CYAN_200),
                    ft.Text("Open, save, or reset your intelligence project.", size=12, color=ft.Colors.WHITE54),
                    
                    ft.Container(height=10),
                    
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                "Open Project",
                                icon=ft.Icons.FOLDER_OPEN,
                                on_click=lambda e: asyncio.create_task(on_open_project(e)),
                                bgcolor=ft.Colors.BLUE_700,
                                color=ft.Colors.WHITE,
                                tooltip="Open an existing project file",
                            ),
                            ft.ElevatedButton(
                                "Save Project",
                                icon=ft.Icons.SAVE,
                                on_click=lambda e: asyncio.create_task(on_save_project(e)),
                                bgcolor=ft.Colors.GREEN_700,
                                color=ft.Colors.WHITE,
                                tooltip="Save current project to a file",
                            ),
                            ft.ElevatedButton(
                                "New Project",
                                icon=ft.Icons.CREATE_NEW_FOLDER,
                                on_click=lambda e: self.new_project(e),
                                bgcolor=ft.Colors.AMBER_400,
                                color=ft.Colors.WHITE,
                                tooltip="Start a new intelligence project",
                            ),
                            ft.ElevatedButton(
                                "Reset",
                                icon=ft.Icons.DELETE_FOREVER,
                                on_click=lambda e: asyncio.create_task(on_reset_click(e)),
                                bgcolor=ft.Colors.RED_700,
                                color=ft.Colors.WHITE,
                                tooltip="Clear all data and start fresh",
                            ),
                        ],
                        spacing=10,
                    ),
                    
                    ft.Divider(color="rgba(255, 255, 255, 0.1)", height=40),
                    
                    # Configuration Section
                    ft.Text("Configuration", size=18, weight=ft.FontWeight.W_600, color=ft.Colors.CYAN_200),
                    ft.Text("Runtime settings for LLM and Intelligence Services.", size=12, color=ft.Colors.WHITE54),
                    
                    ft.Container(height=10),
                    
                    api_key_input,
                    ft.Container(height=10),
                    model_dropdown,
                    ft.Container(height=10),
                    
                    ft.ElevatedButton(
                        "Save Configuration",
                        icon=ft.Icons.SAVE,
                        on_click=on_save_config,
                        bgcolor=ft.Colors.BLUE_700,
                        color=ft.Colors.WHITE,
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
            )
        )

    def new_project(self, e):
        """Start a new project: clear only the workspace UI, keep database intact."""
        # Log and clear workspace asynchronously (UI only, no database clear)
        asyncio.create_task(self.app_controller.push_agui_log("Starting new project...", "info"))
        asyncio.create_task(self.session_manager.clear_workspace_only())
        # Notify the user in the UI (use setattr/getattr to avoid static-type complaints)
        snack = ft.SnackBar(ft.Text("New project started!"))
        setattr(self.page, "snack_bar", snack)
        getattr(self.page, "snack_bar").open = True
        self.page.update()