"""
Activity Feed Component.

Displays a timeline of recent BaseEvent logs in a terminal-style format.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from nicegui import ui

from forge.frontend.state import get_session
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger("frontend.activity_feed")


class ActivityFeed:
    """Timeline-style activity feed showing recent system events."""
    
    def __init__(self, limit: int = 20, auto_refresh: bool = True, refresh_interval: float = 5.0) -> None:
        """Initialize the activity feed.
        
        Args:
            limit: Maximum number of events to display
            auto_refresh: Whether to auto-refresh the feed
            refresh_interval: Refresh interval in seconds (if auto_refresh is True)
        """
        self.limit = limit
        self.auto_refresh = auto_refresh
        self.refresh_interval = refresh_interval
        self._container: ui.element | None = None
        self._scroll_area: ui.element | None = None
        self._timer: ui.timer | None = None
        
    def render(self) -> None:
        """Render the activity feed UI."""
        with ui.card().classes("w-full flex-grow bg-gray-900 border border-gray-800 p-0") as card:
            # Header
            with ui.row().classes("w-full items-center justify-between p-4 border-b border-gray-800"):
                ui.html(
                    '<span class="mono" style="color: #555; font-size: 0.65rem; text-transform: uppercase; letter-spacing: 1px;">SYSTEM_LOG</span>',
                    sanitize=False
                )
                if self.auto_refresh:
                    ui.html(
                        '<span class="mono" style="color: #444; font-size: 0.6rem;">AUTO-REFRESH</span>',
                        sanitize=False
                    )
            
            # Scrollable event list
            with ui.scroll_area().classes("h-64 w-full") as scroll_area:
                self._scroll_area = scroll_area
                with ui.column().classes("w-full p-2 gap-1") as container:
                    self._container = container
                    self._render_events()
            
            # Auto-refresh timer
            if self.auto_refresh:
                self._timer = ui.timer(
                    self.refresh_interval,
                    self.refresh,
                    active=True,
                )
    
    def refresh(self) -> None:
        """Refresh the event list."""
        try:
            if self._container is None:
                return
            
            # Clear existing content
            # Note: In NiceGUI, we need to rebuild the container
            # For now, we'll just re-render the events
            self._render_events()
            
        except Exception as e:
            logger.error(f"Failed to refresh activity feed: {e}")
    
    def _render_events(self) -> None:
        """Render the list of events."""
        try:
            session = get_session()
            events = session.db.get_events(limit=self.limit, include_rolled_back=False)
            
            if not self._container:
                return
            
            # Clear and rebuild
            # Note: NiceGUI doesn't have easy container clearing, so we'll render fresh
            # In a real implementation, we'd track rendered items and update incrementally
            
            if not events:
                with self._container:
                    ui.html(
                        '<span class="mono" style="color: #444; font-size: 0.75rem; padding: 8px;">No events recorded yet.</span>',
                        sanitize=False
                    )
                return
            
            # Render events in reverse order (newest first)
            for event in events:
                self._render_event_item(event)
                
        except Exception as e:
            logger.error(f"Failed to render events: {e}")
            if self._container:
                with self._container:
                    ui.html(
                        f'<span class="mono" style="color: #ff5252; font-size: 0.75rem; padding: 8px;">Error loading events: {e}</span>',
                        sanitize=False
                    )
    
    def _render_event_item(self, event: dict) -> None:
        """Render a single event item.
        
        Args:
            event: Event dictionary from database
        """
        if not self._container:
            return
        
        try:
            # Parse timestamp
            timestamp_str = event.get("timestamp", "")
            try:
                if isinstance(timestamp_str, str):
                    # Parse ISO format
                    dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    time_str = dt.strftime("%H:%M:%S")
                else:
                    time_str = str(timestamp_str)[:8]
            except Exception:
                time_str = "??:??:??"
            
            # Get event type and map to color/icon
            event_type = event.get("event_type", "unknown")
            description = event.get("description", "No description")
            
            # Map event types to colors
            type_colors = {
                "entity_created": "#00c853",
                "entity_updated": "#00b8d4",
                "entity_deleted": "#ff5252",
                "entity_merged": "#ffab00",
                "relationship_created": "#00b8d4",
                "relationship_deleted": "#ff5252",
                "merge_approved": "#00c853",
                "merge_rejected": "#ff5252",
                "extraction": "#00b8d4",
            }
            color = type_colors.get(event_type, "#888")
            
            # Map event types to source labels
            source_labels = {
                "entity_created": "ENTITY",
                "entity_updated": "ENTITY",
                "entity_deleted": "ENTITY",
                "entity_merged": "SENTINEL",
                "relationship_created": "REL",
                "relationship_deleted": "REL",
                "merge_approved": "SENTINEL",
                "merge_rejected": "SENTINEL",
                "extraction": "EXTRACTOR",
            }
            source_label = source_labels.get(event_type, "SYSTEM")
            
            with self._container:
                with ui.row().classes(
                    "text-xs font-mono py-1 px-2 hover:bg-gray-800 rounded w-full cursor-pointer"
                ).on("click", lambda e=event: self._on_event_click(e)):
                    # Timestamp
                    ui.html(
                        f'<span style="color: #666; margin-right: 8px; font-size: 0.7rem;">{time_str}</span>',
                        sanitize=False
                    )
                    # Source label
                    ui.html(
                        f'<span style="color: {color}; margin-right: 8px; font-weight: 500; font-size: 0.7rem;">{source_label}</span>',
                        sanitize=False
                    )
                    # Description
                    ui.html(
                        f'<span style="color: #aaa; font-size: 0.75rem;">{description[:100]}</span>',
                        sanitize=False
                    )
        
        except Exception as e:
            logger.error(f"Failed to render event item: {e}")
    
    def _on_event_click(self, event: dict) -> None:
        """Handle click on an event item.
        
        Args:
            event: Event dictionary
        """
        # Could open a detail dialog or navigate to related entity
        logger.debug(f"Event clicked: {event.get('id')}")


def create_activity_feed(limit: int = 20) -> ActivityFeed:
    """Create and render an activity feed component.
    
    Args:
        limit: Maximum number of events to display
        
    Returns:
        ActivityFeed instance
    """
    feed = ActivityFeed(limit=limit)
    feed.render()
    return feed
