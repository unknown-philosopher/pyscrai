"""
FletX State Management.

Bridges ForgeState singleton to Flet's reactive state system.
This allows both imperative backend updates and reactive UI updates.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

import flet as ft

from forge.app.state import ForgeState, get_state
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.core.models.entity import Entity

logger = get_logger("frontend.state")


# UI context tracking
@dataclass
class UIContext:
    """UI context for Assistant awareness."""
    active_page: str = "landing"
    selected_entities: list["Entity"] = field(default_factory=list)
    selected_relationships: list[str] = field(default_factory=list)


class FletXState:
    """FletX state wrapper bridging ForgeState to Flet reactive state.
    
    This class provides reactive state management for Flet while
    maintaining access to the backend ForgeState singleton.
    """
    
    def __init__(self, page: ft.Page, forge_state: ForgeState | None = None):
        """Initialize FletX state wrapper.
        
        Args:
            page: Flet page instance
            forge_state: Optional ForgeState instance (uses global if None)
        """
        self.page = page
        self._forge_state = forge_state or get_state()
        self._ui_context = UIContext()
        
        # Reactive state variables (simple types, not Flet Refs)
        # Flet Refs only work with Control objects, not primitives
        self.project_name: str = ""
        self.project_loaded: bool = False
        self.entity_count: int = 0
        self.relationship_count: int = 0
        self.dirty: bool = False
        
        # UI context state
        self.active_page: str = "landing"
        self.selected_entities_count: int = 0
        
        # Event listeners for state changes
        self._listeners: list[Callable[[], None]] = []
        self._lock = threading.Lock()
        
        # Initialize reactive state
        self._sync_state()
        
        logger.info("FletX state initialized")
    
    def _sync_state(self) -> None:
        """Synchronize reactive state from ForgeState."""
        try:
            with self._lock:
                # Project info
                if self._forge_state.has_project and self._forge_state.project:
                    self.project_name = self._forge_state.project.name
                    self.project_loaded = True
                else:
                    self.project_name = ""
                    self.project_loaded = False
                
                # Stats
                stats = self._forge_state.get_stats()
                self.entity_count = stats.get("entity_count", 0)
                self.relationship_count = stats.get("relationship_count", 0)
                self.dirty = stats.get("dirty", False)
                
                # UI context
                self.active_page = self._ui_context.active_page
                self.selected_entities_count = len(self._ui_context.selected_entities)
                
        except Exception as e:
            logger.error(f"Failed to sync state: {e}")
    
    def refresh(self) -> None:
        """Refresh reactive state and notify listeners."""
        self._sync_state()
        self._notify_listeners()
    
    def _notify_listeners(self) -> None:
        """Notify all registered listeners of state changes."""
        for listener in self._listeners:
            try:
                listener()
            except Exception as e:
                logger.error(f"Listener error: {e}")
    
    def add_listener(self, callback: Callable[[], None]) -> None:
        """Add a listener for state changes.
        
        Args:
            callback: Function to call when state changes
        """
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable[[], None]) -> None:
        """Remove a listener.
        
        Args:
            callback: Listener to remove
        """
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    # ========== ForgeState Access ==========
    
    @property
    def forge_state(self) -> ForgeState:
        """Get the underlying ForgeState instance."""
        return self._forge_state
    
    # ========== UI Context Management ==========
    
    def set_active_page(self, page: str) -> None:
        """Update the active page in UI context.
        
        Args:
            page: Page identifier (e.g., 'osint', 'humint')
        """
        self._ui_context.active_page = page
        self.active_page = page
        logger.debug(f"Active page set to: {page}")
    
    def set_selected_entities(self, entities: list["Entity"]) -> None:
        """Update the selected entities in UI context.
        
        Args:
            entities: List of currently selected Entity objects
        """
        self._ui_context.selected_entities = entities
        self.selected_entities_count = len(entities)
        logger.debug(f"Selected entities updated: {len(entities)} items")
    
    def clear_selection(self) -> None:
        """Clear all UI selections."""
        self._ui_context.selected_entities = []
        self._ui_context.selected_relationships = []
        self.selected_entities_count = 0
    
    def get_ui_context(self) -> dict[str, Any]:
        """Get the current UI context for Assistant awareness.
        
        Returns:
            Dictionary with active_page, selected_entities, etc.
        """
        return {
            "active_page": self._ui_context.active_page,
            "selected_entities": self._ui_context.selected_entities,
            "selected_relationships": self._ui_context.selected_relationships,
        }
    
    # ========== Project Management ==========
    
    def load_project(self, project_name: str) -> None:
        """Load a project and refresh state.
        
        Args:
            project_name: Name of the project to load
        """
        try:
            self._forge_state.load_project(project_name)
            self.refresh()
            logger.info(f"Project loaded: {project_name}")
        except Exception as e:
            logger.error(f"Failed to load project: {e}")
            raise
    
    def create_project(
        self,
        name: str,
        description: str = "",
        **kwargs: Any,
    ) -> None:
        """Create a new project and refresh state.
        
        Args:
            name: Project name
            description: Project description
            **kwargs: Additional project settings
        """
        try:
            self._forge_state.create_project(name, description, **kwargs)
            self.refresh()
            logger.info(f"Project created: {name}")
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            raise
    
    def close_project(self) -> None:
        """Close the current project and refresh state."""
        try:
            self._forge_state.close_project()
            self.refresh()
            logger.info("Project closed")
        except Exception as e:
            logger.error(f"Failed to close project: {e}")
            raise
    
    # ========== Convenience Properties ==========
    
    @property
    def has_project(self) -> bool:
        """Check if a project is currently loaded."""
        return self._forge_state.has_project
    
    @property
    def project(self) -> Any:
        """Get the current project manifest."""
        return self._forge_state.project if self._forge_state.has_project else None


# Global FletX state instance (singleton per page)
_fletx_state: FletXState | None = None


def init_fletx_state(page: ft.Page, forge_state: ForgeState | None = None) -> FletXState:
    """Initialize the global FletX state instance.
    
    Args:
        page: Flet page instance
        forge_state: Optional ForgeState instance
        
    Returns:
        Initialized FletXState instance
    """
    global _fletx_state
    _fletx_state = FletXState(page, forge_state)
    return _fletx_state


def get_fletx_state() -> FletXState:
    """Get the global FletX state instance.
    
    Returns:
        FletXState singleton
        
    Raises:
        RuntimeError: If state hasn't been initialized
    """
    global _fletx_state
    if _fletx_state is None:
        raise RuntimeError("FletX state not initialized. Call init_fletx_state() first.")
    return _fletx_state
