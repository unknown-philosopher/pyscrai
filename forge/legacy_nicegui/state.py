"""
Forge Frontend State Management.

Provides a singleton wrapper around ForgeState for UI access.
This module bridges the backend state with the NiceGUI frontend.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.app.state import ForgeState
    from forge.core.models.entity import Entity

logger = get_logger("frontend.state")

# Singleton session state
_session: "ForgeState | None" = None

# UI context tracking
_ui_context: dict[str, Any] = {
    "active_page": "landing",
    "selected_entities": [],
    "selected_relationships": [],
}


def initialize_session(state: "ForgeState") -> None:
    """Initialize the frontend session with a ForgeState instance.
    
    Args:
        state: Pre-configured ForgeState from app initialization
    """
    global _session
    _session = state
    logger.info(f"Frontend session initialized (session_id={state.session_id})")


def get_session() -> "ForgeState":
    """Get the current session state.
    
    Returns:
        The active ForgeState instance
        
    Raises:
        RuntimeError: If session not initialized
    """
    global _session
    
    if _session is None:
        # Lazy initialization if not pre-configured
        from forge.app.state import get_global_state
        _session = get_global_state()
        
        if _session is None:
            raise RuntimeError(
                "Frontend session not initialized. "
                "Call initialize_session() or ensure ForgeState is configured."
            )
    
    return _session


def get_ui_context() -> dict[str, Any]:
    """Get the current UI context for Assistant awareness.
    
    Returns:
        Dictionary with active_page, selected_entities, etc.
    """
    return _ui_context.copy()


def set_active_page(page: str) -> None:
    """Update the active page in UI context.
    
    Args:
        page: Page identifier (e.g., 'osint', 'humint')
    """
    _ui_context["active_page"] = page
    logger.debug(f"Active page set to: {page}")


def set_selected_entities(entities: list["Entity"]) -> None:
    """Update the selected entities in UI context.
    
    Args:
        entities: List of currently selected Entity objects
    """
    _ui_context["selected_entities"] = entities
    logger.debug(f"Selected entities updated: {len(entities)} items")


def clear_selection() -> None:
    """Clear all UI selections."""
    _ui_context["selected_entities"] = []
    _ui_context["selected_relationships"] = []


def is_project_loaded() -> bool:
    """Check if a project is currently loaded.
    
    Returns:
        True if a project is active
    """
    try:
        session = get_session()
        return session.has_project
    except RuntimeError:
        return False
