"""
AG-UI Component - Advisor Suggestions.

Displays structured advisor suggestions in the Comms Panel (right drawer).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import flet as ft

from forge.frontend import style
from forge.frontend.state import FletXState
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.core.actions import ActionExecutor

logger = get_logger("frontend.ag_ui")


@dataclass
class AdvisorSuggestion:
    """Advisor suggestion structure.
    
    This defines how advisors communicate with the UI.
    """
    id: str
    advisor_name: str  # e.g., "SIGINT Advisor"
    severity: str  # "INFO", "WARNING", "OPPORTUNITY"
    message: str  # "Actor X has no connections."
    
    # The Payload defines what happens if User accepts
    suggested_action: str  # e.g., "LINK_ENTITIES"
    action_payload: dict  # {"source": "X", "target": "Y", "type": "associate"}


class AGUIPanel:
    """AG-UI panel component displaying advisor suggestions."""
    
    def __init__(self, state: FletXState):
        """Initialize AG-UI panel.
        
        Args:
            state: FletXState instance
        """
        self.state = state
        self.suggestions: list[AdvisorSuggestion] = []
        self._suggestion_cards: list[ft.Control] = []
        self._container_ref = ft.Ref[ft.Column]()
        self._action_executor: "ActionExecutor | None" = None
        
        logger.info("AG-UI panel initialized")
    
    def render(self) -> ft.Control:
        """Render the AG-UI panel.
        
        Returns:
            Control representing the AG-UI panel
        """
        # Header
        header = ft.Row(
            controls=[
                style.mono_text("COMMS PANEL", size=12, color=style.COLORS["text_dim"], weight=ft.FontWeight.W_500),
                ft.Container(expand=True),
                style.forge_badge("AG-UI", severity="active"),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        
        # Suggestions list
        suggestions_list = ft.Column(
            ref=self._container_ref,
            controls=self._render_suggestions(),
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        
        return ft.Column(
            controls=[
                header,
                ft.Divider(height=1, color=style.COLORS["border"]),
                suggestions_list,
            ],
            spacing=8,
            expand=True,
        )
    
    def _render_suggestions(self) -> list[ft.Control]:
        """Render all suggestion cards.
        
        Returns:
            List of suggestion card controls
        """
        if not self.suggestions:
            return [
                ft.Container(
                    content=style.mono_text("No suggestions", size=12, color=style.COLORS["text_muted"]),
                    padding=16,
                    alignment=ft.alignment.center,
                )
            ]
        
        cards = []
        for suggestion in self.suggestions:
            cards.append(self._render_suggestion_card(suggestion))
        
        return cards
    
    def _render_suggestion_card(self, suggestion: AdvisorSuggestion) -> ft.Control:
        """Render a single suggestion card.
        
        Args:
            suggestion: AdvisorSuggestion instance
            
        Returns:
            Control representing suggestion card
        """
        # Map severity to border color
        severity_colors = {
            "INFO": style.COLORS["accent"],
            "WARNING": style.COLORS["warning"],
            "OPPORTUNITY": style.COLORS["success"],
            "ERROR": style.COLORS["error"],
        }
        border_color = severity_colors.get(suggestion.severity.upper(), style.COLORS["border"])
        
        # Header with advisor name and severity
        header = ft.Row(
            controls=[
                style.mono_text(suggestion.advisor_name.upper(), size=10, color=style.COLORS["text_dim"]),
                ft.Container(expand=True),
                style.forge_badge(suggestion.severity, severity=suggestion.severity.lower()),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        
        # Message (with typewriter effect simulation - simplified)
        message_text = style.mono_text(suggestion.message, size=11, color=style.COLORS["text"])
        
        # Action buttons
        buttons_row = ft.Row(
            controls=[
                style.forge_button(
                    "[APPLY]",
                    primary=True,
                    on_click=lambda _, s=suggestion: self._apply_suggestion(s),
                ),
                style.forge_button(
                    "[DISMISS]",
                    on_click=lambda _, s=suggestion: self._dismiss_suggestion(s),
                ),
            ],
            spacing=8,
        )
        
        return style.forge_card(
            content=ft.Column(
                controls=[
                    header,
                    ft.Container(height=8),
                    message_text,
                    ft.Container(height=12),
                    buttons_row,
                ],
                spacing=0,
            ),
            padding=12,
            border=ft.border.all(2, border_color),
        )
    
    def _apply_suggestion(self, suggestion: AdvisorSuggestion) -> None:
        """Apply a suggestion by executing the action.
        
        Args:
            suggestion: AdvisorSuggestion to apply
        """
        try:
            # Get action executor
            if self._action_executor is None:
                from forge.core.actions import ActionExecutor
                self._action_executor = ActionExecutor(self.state.forge_state)
            
            # Execute action
            result = self._action_executor.execute(
                suggestion.suggested_action,
                suggestion.action_payload,
            )
            
            if result.get("success"):
                style.show_terminal_toast(
                    self.state.page,
                    f"Applied: {suggestion.message}",
                    "success",
                )
                self._dismiss_suggestion(suggestion)
            else:
                error_msg = result.get("error", "Unknown error")
                style.show_terminal_toast(
                    self.state.page,
                    f"Failed to apply: {error_msg}",
                    "error",
                )
            
            logger.info(f"Applied suggestion: {suggestion.id}")
            
        except Exception as e:
            logger.error(f"Failed to apply suggestion: {e}")
            style.show_terminal_toast(
                self.state.page,
                f"Error: {str(e)}",
                "error",
            )
    
    def _dismiss_suggestion(self, suggestion: AdvisorSuggestion) -> None:
        """Dismiss a suggestion.
        
        Args:
            suggestion: AdvisorSuggestion to dismiss
        """
        if suggestion in self.suggestions:
            self.suggestions.remove(suggestion)
            self._refresh_display()
            logger.debug(f"Dismissed suggestion: {suggestion.id}")
    
    def add_suggestion(self, suggestion: AdvisorSuggestion) -> None:
        """Add a new suggestion to the panel.
        
        Args:
            suggestion: AdvisorSuggestion to add
        """
        # Check if suggestion already exists
        existing = next((s for s in self.suggestions if s.id == suggestion.id), None)
        if existing:
            logger.debug(f"Suggestion {suggestion.id} already exists, updating")
            self.suggestions.remove(existing)
        
        self.suggestions.append(suggestion)
        self._refresh_display()
        logger.info(f"Added suggestion: {suggestion.id} from {suggestion.advisor_name}")
    
    def clear_suggestions(self) -> None:
        """Clear all suggestions."""
        self.suggestions.clear()
        self._refresh_display()
        logger.debug("Cleared all suggestions")
    
    def _refresh_display(self) -> None:
        """Refresh the display with current suggestions."""
        if self._container_ref.current:
            self._container_ref.current.controls = self._render_suggestions()
            self.state.page.update()


# Global AG-UI panel instance (singleton per state)
_ag_ui_panel: AGUIPanel | None = None


def get_ag_ui_panel(state: FletXState) -> AGUIPanel:
    """Get or create the AG-UI panel instance.
    
    Args:
        state: FletXState instance
        
    Returns:
        AGUIPanel instance
    """
    global _ag_ui_panel
    
    if _ag_ui_panel is None:
        _ag_ui_panel = AGUIPanel(state)
    
    return _ag_ui_panel
