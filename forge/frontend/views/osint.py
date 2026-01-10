"""OSINT View - Phase 0: Extraction & Sentinel."""

from __future__ import annotations

import flet as ft

from forge.frontend import style
from forge.frontend.state import FletXState
from forge.utils.logging import get_logger

logger = get_logger("frontend.osint")


def render_osint_view(state: FletXState) -> ft.Control:
    """Render OSINT extraction view.
    
    Args:
        state: FletXState instance
        
    Returns:
        Control representing OSINT view
    """
    if not state.has_project:
        return _render_no_project(state)
    
    # TODO: Implement full OSINT view with drag-and-drop, Sentinel triage
    return ft.Container(
        content=style.mono_text("OSINT View - Coming Soon", size=16, color=style.COLORS["text_dim"]),
        padding=24,
        alignment=ft.alignment.center,
        expand=True,
    )


def _render_no_project(state: FletXState) -> ft.Control:
    """Render no project message."""
    return ft.Container(
        content=ft.Column(
            controls=[
                style.mono_text("[X]", size=48, color=style.COLORS["text_muted"]),
                style.mono_text("No Project Loaded", size=18, color=style.COLORS["text_dim"]),
                style.forge_button("GO TO PROJECTS", on_click=lambda _: state.page.go("/"), primary=True),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=16,
        ),
        expand=True,
        alignment=ft.alignment.center,
    )
