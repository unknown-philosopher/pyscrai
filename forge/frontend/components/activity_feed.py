"""
Activity Feed Component - Terminal Style.

Displays recent BaseEvent logs in terminal format.
"""

from __future__ import annotations

from datetime import datetime

import flet as ft

from forge.frontend import style
from forge.frontend.state import FletXState
from forge.utils.logging import get_logger

logger = get_logger("frontend.activity_feed")


def create_activity_feed(state: FletXState, limit: int = 20) -> ft.Control:
    """Create and render an activity feed component.
    
    Args:
        state: FletXState instance
        limit: Maximum number of events to display
        
    Returns:
        Control representing the activity feed
    """
    # Get events from database
    try:
        if state.has_project:
            events = state.forge_state.db.get_events(limit=limit, include_rolled_back=False)
        else:
            events = []
    except Exception as e:
        logger.error(f"Failed to get events: {e}")
        events = []
    
    # Header
    header = ft.Row(
        controls=[
            style.mono_label("SYSTEM_LOG", size=10),
            ft.Container(expand=True),
            style.mono_text("AUTO-REFRESH", size=10, color=style.COLORS["text_muted"]),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )
    
    # Event list
    if not events:
        event_list = ft.Container(
            content=style.mono_text("No events recorded yet", size=12, color=style.COLORS["text_muted"]),
            padding=16,
            alignment=ft.alignment.center,
        )
    else:
        event_items = []
        for event in events:
            event_items.append(_render_event_item(event))
        
        event_list = ft.Column(
            controls=event_items,
            spacing=4,
            scroll=ft.ScrollMode.AUTO,
            height=300,
        )
    
    return style.forge_card(
        content=ft.Column(
            controls=[
                header,
                ft.Divider(height=1, color=style.COLORS["border"]),
                event_list,
            ],
            spacing=8,
        ),
        padding=0,
    )


def _render_event_item(event: dict) -> ft.Control:
    """Render a single event item.
    
    Args:
        event: Event dictionary from database
        
    Returns:
        Control representing event item
    """
    # Parse timestamp
    timestamp_str = event.get("timestamp", "")
    try:
        if isinstance(timestamp_str, str):
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            time_str = dt.strftime("%H:%M:%S")
        else:
            time_str = str(timestamp_str)[:8]
    except Exception:
        time_str = "??:??:??"
    
    # Get event type and map to color
    event_type = event.get("event_type", "unknown")
    description = event.get("description", "No description")
    
    # Map event types to colors
    type_colors = {
        "entity_created": style.COLORS["success"],
        "entity_updated": style.COLORS["accent"],
        "entity_deleted": style.COLORS["error"],
        "entity_merged": style.COLORS["warning"],
        "relationship_created": style.COLORS["accent"],
        "relationship_deleted": style.COLORS["error"],
        "merge_approved": style.COLORS["success"],
        "merge_rejected": style.COLORS["error"],
        "extraction": style.COLORS["accent"],
    }
    color = type_colors.get(event_type, style.COLORS["text_dim"])
    
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
    
    return ft.Container(
        content=ft.Row(
            controls=[
                style.mono_text(time_str, size=10, color=style.COLORS["text_muted"]),
                style.mono_text(source_label, size=10, color=color, weight=ft.FontWeight.W_500),
                style.mono_text(description[:100], size=10, color=style.COLORS["text_dim"]),
            ],
            spacing=8,
        ),
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        border_radius=2,
    )
