"""SYNTH View - Phase 3: Narrative."""

from __future__ import annotations

import flet as ft

from forge.frontend import style
from forge.frontend.state import FletXState
from forge.utils.logging import get_logger

logger = get_logger("frontend.synth")


def render_synth_view(state: FletXState) -> ft.Control:
    """Render SYNTH narrative view.
    
    Args:
        state: FletXState instance
        
    Returns:
        Control representing SYNTH view
    """
    if not state.has_project:
        return _render_no_project(state)
    
    # TODO: Implement full SYNTH view with narrative editor
    return ft.Container(
        content=style.mono_text("SYNTH View - Coming Soon", size=16, color=style.COLORS["text_dim"]),
        padding=24,
        alignment=ft.Alignment(0, 0),
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
        alignment=ft.Alignment(0, 0),
    )
