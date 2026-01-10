"""
Landing Page - Project Selection.

Intelligence platform entry point. Allows users to:
- Select an existing project
- Create a new project
- Load a project from the file system
"""

from __future__ import annotations

from pathlib import Path

from nicegui import ui

from forge.frontend.state import get_session
from forge.utils.logging import get_logger

logger = get_logger("frontend.landing")


def content() -> None:
    """Render the landing page content."""
    # Page header
    ui.html('<h1 class="mono" style="font-size: 1.8rem; font-weight: 600; color: #e0e0e0; margin-bottom: 8px;">Welcome to Forge</h1>', sanitize=False)
    ui.html('<p class="mono" style="font-size: 0.85rem; color: #666; margin-bottom: 32px;">Select or create a project to begin.</p>', sanitize=False)
    
    with ui.row().classes("w-full gap-6"):
        # Existing projects panel
        with ui.element("div").classes("forge-card flex-grow p-6"):
            ui.html('<div class="section-label">Recent Projects</div>', sanitize=False)
            _render_project_list()
        
        # Create new project panel  
        with ui.element("div").classes("forge-card p-6").style("width: 320px; flex-shrink: 0;"):
            ui.html('<div class="section-label">New Project</div>', sanitize=False)
            _render_create_form()


def _render_project_list() -> None:
    """Render the list of existing projects."""
    try:
        session = get_session()
        projects_dir = session.config.projects_dir
        
        if not projects_dir.exists():
            ui.html('<span class="mono" style="color: #555; font-size: 0.85rem;">No projects found.</span>', sanitize=False)
            return
        
        # List project directories
        projects = [
            p for p in projects_dir.iterdir()
            if p.is_dir() and (p / "project.json").exists()
        ]
        
        if not projects:
            ui.html('<span class="mono" style="color: #555; font-size: 0.85rem;">No projects found.</span>', sanitize=False)
        else:
            with ui.column().classes("w-full gap-2 mt-4"):
                for project_path in sorted(projects):
                    _render_project_item(project_path)
    
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        ui.html(f'<span class="mono" style="color: #ff5252; font-size: 0.85rem;">Error loading projects: {e}</span>', sanitize=False)


def _render_project_item(project_path: Path) -> None:
    """Render a single project item in the list."""
    # Read manifest for description
    desc = "No description"
    try:
        import json
        manifest_path = project_path / "project.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
            desc = manifest.get("description", "No description")
    except Exception:
        pass
    
    with ui.element("div").classes(
        "cursor-pointer p-3 rounded"
    ).style(
        "background: #1a1a1a; border: 1px solid #333; transition: all 0.15s ease;"
    ).on("click", lambda p=project_path: _load_project(p.name)):
        with ui.row().classes("items-center w-full"):
            # Folder indicator
            ui.html('<span style="color: #00b8d4; margin-right: 12px; font-size: 0.9rem;">[DIR]</span>', sanitize=False)
            
            with ui.column().classes("flex-grow"):
                ui.html(f'<span class="mono" style="color: #e0e0e0; font-size: 0.9rem;">{project_path.name}</span>', sanitize=False)
                ui.html(f'<span class="mono" style="color: #555; font-size: 0.75rem;">{desc}</span>', sanitize=False)
            
            # Arrow indicator
            ui.html('<span class="mono" style="color: #444;">›</span>', sanitize=False)


def _render_create_form() -> None:
    """Render the new project creation form."""
    with ui.column().classes("w-full gap-4 mt-4"):
        name_input = ui.input(
            placeholder="Project Name",
        ).classes("w-full forge-input").props("outlined dense dark")
        
        desc_input = ui.input(
            placeholder="Description",
        ).classes("w-full forge-input").props("outlined dense dark")
        
        with ui.column().classes("w-full"):
            ui.html('<span class="mono" style="color: #666; font-size: 0.7rem; margin-bottom: 4px;">Template</span>', sanitize=False)
            template_select = ui.select(
                options=["blank", "espionage", "fantasy", "scifi"],
                value="blank",
            ).classes("w-full").props("outlined dense dark options-dense")
        
        with ui.element("div").classes(
            "w-full text-center py-2 px-4 mt-4 cursor-pointer rounded"
        ).style(
            "background: #00b8d4; color: #000; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; font-weight: 500; letter-spacing: 0.5px;"
        ).on("click", lambda: _create_project(name_input.value, desc_input.value, template_select.value)):
            ui.html('+ CREATE PROJECT', sanitize=False)


async def _load_project(project_name: str) -> None:
    """Load an existing project and navigate to dashboard."""
    try:
        session = get_session()
        session.load_project(project_name)
        
        ui.notify(f"Loaded project: {project_name}", type="positive")
        ui.navigate.to("/dashboard")
        
    except Exception as e:
        logger.error(f"Failed to load project: {e}")
        ui.notify(f"Failed to load project: {e}", type="negative")


async def _create_project(name: str, description: str, template: str) -> None:
    """Create a new project and navigate to dashboard."""
    if not name or not name.strip():
        ui.notify("Please enter a project name.", type="warning")
        return
    
    # Sanitize name
    name = name.strip().replace(" ", "_").lower()
    
    try:
        session = get_session()
        session.create_project(
            name=name,
            description=description or f"Project: {name}",
            template=template if template != "blank" else None,
        )
        
        ui.notify(f"Created project: {name}", type="positive")
        ui.navigate.to("/dashboard")
        
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        ui.notify(f"Failed to create project: {e}", type="negative")
