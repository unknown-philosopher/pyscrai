"""
Landing View - Project Selection.

Project selection and creation interface.
"""

from __future__ import annotations

import flet as ft

from forge.frontend import style
from forge.frontend.state import FletXState
from forge.utils.logging import get_logger

logger = get_logger("frontend.landing")


def render_landing_view(state: FletXState) -> ft.Control:
    """Render the landing page with project selection/creation.
    
    Args:
        state: FletXState instance
        
    Returns:
        Control representing the landing view
    """
    # Header
    header = ft.Column(
        controls=[
            style.mono_text("Welcome to Forge", size=24, weight=ft.FontWeight.W_600),
            style.mono_label("Select or create a project to begin", size=12),
        ],
        spacing=8,
    )
    
    # Main grid: Project list (left) and Create form (right)
    main_content = ft.Row(
        controls=[
            _render_project_list(state),  # Left: Existing projects
            ft.VerticalDivider(width=1, color=style.COLORS["border"]),
            _render_create_form(state),  # Right: Create new project
        ],
        spacing=24,
        expand=True,
    )
    
    return ft.Column(
        controls=[
            header,
            ft.Container(height=24),  # Spacing
            main_content,
        ],
        spacing=0,
        expand=True,
    )


def _render_project_list(state: FletXState) -> ft.Control:
    """Render the list of existing projects.
    
    Args:
        state: FletXState instance
        
    Returns:
        Control with project list
    """
    # Get projects from config
    try:
        projects_dir = state.forge_state.config.projects_dir
        
        if not projects_dir.exists():
            projects = []
        else:
            # List project directories
            projects = [
                p for p in projects_dir.iterdir()
                if p.is_dir() and (p / "project.json").exists()
            ]
            projects = sorted(projects)
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        projects = []
    
    # Section label
    section_label = style.mono_label("Recent Projects")
    
    # Project items
    if not projects:
        project_items = ft.Container(
            content=style.mono_text("No projects found", size=12, color=style.COLORS["text_dim"]),
            padding=16,
            alignment=ft.alignment.center,
        )
    else:
        project_items = ft.Column(
            controls=[_render_project_item(state, p) for p in projects],
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
            height=400,
        )
    
    return ft.Container(
        content=ft.Column(
            controls=[
                section_label,
                ft.Container(height=12),
                project_items,
            ],
            spacing=0,
        ),
        expand=True,
        padding=16,
    )


def _render_project_item(state: FletXState, project_path) -> ft.Control:
    """Render a single project item.
    
    Args:
        state: FletXState instance
        project_path: Path to project directory
        
    Returns:
        Control representing project item
    """
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
    
    project_name = project_path.name
    
    return ft.Container(
        content=ft.Row(
            controls=[
                # Folder indicator
                ft.Icon("folder", color=style.COLORS["accent"], size=20),
                # Project info
                ft.Column(
                    controls=[
                        style.mono_text(project_name, size=14),
                        style.mono_text(desc, size=10, color=style.COLORS["text_dim"]),
                    ],
                    spacing=4,
                    expand=True,
                ),
                # Arrow indicator
                ft.Icon("arrow_forward", color=style.COLORS["text_muted"], size=16),
            ],
            spacing=12,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        on_click=lambda _: _load_project(state, project_name),
        tooltip=f"Load project: {project_name}",
        padding=12,
        bgcolor=style.COLORS["bg_card"],
        border=ft.border.all(1, style.COLORS["border"]),
        border_radius=4,
    )


def _render_create_form(state: FletXState) -> ft.Control:
    """Render the new project creation form.
    
    Args:
        state: FletXState instance
        
    Returns:
        Control with creation form
    """
    # Section label
    section_label = style.mono_label("New Project")
    
    # Form fields
    name_input = style.forge_input(
        label="Project Name",
        hint_text="Enter project name...",
    )
    
    desc_input = style.forge_input(
        label="Description",
        hint_text="Enter project description...",
        multiline=True,
    )
    
    template_select = style.forge_select(
        label="Template",
        options=["blank", "espionage", "fantasy", "scifi"],
        value="blank",
    )
    
    # Create button
    create_btn = style.forge_button(
        "CREATE PROJECT",
        icon="add",
        primary=True,
        on_click=lambda _: _create_project(state, name_input, desc_input, template_select),
    )
    
    return ft.Container(
        content=ft.Column(
            controls=[
                section_label,
                ft.Container(height=12),
                name_input,
                desc_input,
                template_select,
                ft.Container(height=16),
                create_btn,
            ],
            spacing=8,
        ),
        width=360,
        padding=16,
    )


def _load_project(state: FletXState, project_name: str) -> None:
    """Load a project.
    
    Args:
        state: FletXState instance
        project_name: Name of project to load
    """
    try:
        state.load_project(project_name)
        
        # Show success message
        style.show_terminal_toast(state.page, f"Loaded project: {project_name}", "success")
        
        # Navigate to dashboard
        state.page.go("/dashboard")
        
        logger.info(f"Project loaded: {project_name}")
    except Exception as e:
        logger.error(f"Failed to load project: {e}")
        style.show_terminal_toast(state.page, f"Failed to load project: {e}", "error")


def _create_project(
    state: FletXState,
    name_input: ft.TextField,
    desc_input: ft.TextField,
    template_select: ft.Dropdown,
) -> None:
    """Create a new project.
    
    Args:
        state: FletXState instance
        name_input: Name input field
        desc_input: Description input field
        template_select: Template select dropdown
    """
    name = name_input.value.strip() if name_input.value else ""
    
    if not name:
        style.show_terminal_toast(state.page, "Please enter a project name", "warning")
        return
    
    # Sanitize name
    name = name.replace(" ", "_").lower()
    description = desc_input.value.strip() if desc_input.value else f"Project: {name}"
    template = template_select.value if template_select.value != "blank" else None
    
    try:
        state.create_project(
            name=name,
            description=description,
            template=template,
        )
        
        # Show success message
        style.show_terminal_toast(state.page, f"Created project: {name}", "success")
        
        # Navigate to dashboard
        state.page.go("/dashboard")
        
        logger.info(f"Project created: {name}")
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        style.show_terminal_toast(state.page, f"Failed to create project: {e}", "error")
