"""
App Shell - The "Cockpit" Layout.

3-pane tactical interface:
- Nav Rail (Left): Icon-only navigation
- Mission Area (Center): Active view content
- Comms Panel (Right): AG-UI suggestion cards (collapsible)
"""

from __future__ import annotations

from typing import Any, Callable

import flet as ft

from forge.frontend import style
from forge.frontend.state import FletXState

logger = None  # Will be initialized


class AppShell:
    """The Cockpit app shell with 3-pane layout."""
    
    def __init__(self, page: ft.Page, state: FletXState):
        """Initialize the app shell.
        
        Args:
            page: Flet page instance
            state: FletXState instance
        """
        global logger
        from forge.utils.logging import get_logger
        logger = get_logger("frontend.app_shell")
        
        self.page = page
        self.state = state
        self.current_view: Callable[[], ft.Control] | None = None
        self.current_route = "/"
        
        # Refs for dynamic updates
        self._content_area = ft.Ref[ft.Container]()
        self._comms_drawer = ft.Ref[ft.Container]()
        self._comms_panel_open = False  # Simple bool state, not a Ref
        
        # Build UI
        self._build_ui()
        
        # Setup routing (will be triggered by main.py after route handler is set up)
        self._setup_routing()
        
        logger.info("App shell initialized")
    
    def _build_ui(self) -> None:
        """Build the 3-pane layout."""
        # Apply theme
        self.page.theme = style.get_theme()
        self.page.bgcolor = style.COLORS["bg_dark"]
        
        # Main layout: Row with 3 panes
        main_layout = ft.Row(
            controls=[
                self._build_nav_rail(),  # Left: Navigation
                ft.VerticalDivider(width=1, color=style.COLORS["border"]),
                self._build_mission_area(),  # Center: Content
                ft.VerticalDivider(width=1, color=style.COLORS["border"]),
                self._build_comms_panel(),  # Right: AG-UI (collapsible)
            ],
            spacing=0,
            expand=True,
        )
        
        # Header
        header = self._build_header()
        
        # Footer
        footer = self._build_footer()
        
        # Main container
        self.page.add(
            ft.Column(
                controls=[
                    header,
                    main_layout,
                    footer,
                ],
                spacing=0,
                expand=True,
            )
        )
        
        self.page.update()
    
    def _build_header(self) -> ft.Container:
        """Build the header bar."""
        return ft.Container(
            content=ft.Row(
                controls=[
                    # Logo
                    ft.Row(
                        controls=[
                            style.mono_text("PyScrAI", size=18, color=style.COLORS["accent"], weight=ft.FontWeight.W_600),
                            style.mono_text("|", size=14, color=style.COLORS["text_muted"]),
                            style.mono_text("FORGE", size=12, color=style.COLORS["text_dim"]),
                        ],
                        spacing=4,
                    ),
                    ft.Container(width=1, height=20, bgcolor=style.COLORS["border"]),
                    # Menu items (placeholders)
                    style.mono_text("FILE", size=10, color=style.COLORS["text_dim"]),
                    style.mono_text("VIEW", size=10, color=style.COLORS["text_dim"]),
                    style.mono_text("DB", size=10, color=style.COLORS["text_dim"]),
                    style.mono_text("TOOLS", size=10, color=style.COLORS["text_dim"]),
                    ft.Container(expand=True),  # Spacer
                    # Right controls
                    style.forge_button("[CONFIG]"),
                    style.forge_button("[ALERTS]"),
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=style.COLORS["bg_panel"],
            border=ft.border.only(bottom=ft.BorderSide(1, style.COLORS["border"])),
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            height=48,
        )
    
    def _build_nav_rail(self) -> ft.Container:
        """Build the left navigation rail (icon-only)."""
        nav_items = []
        
        for phase in style.PHASES:
            phase_id = phase["id"]
            icon_name = phase.get("icon", "circle")
            route = phase["route"]
            label = phase["label"]
            
            # Use string-based Material Icon names
            icon_map = {
                "dashboard": "dashboard",
                "search": "search",
                "people": "people",
                "hub": "hub",
                "description": "description",
                "map": "map",
                "check_circle": "check_circle",
            }
            icon = icon_map.get(icon_name, "circle")
            
            # Create icon - use text color instead of dim for better visibility
            # Check if this is the current route
            is_active = route == self.current_route
            icon_color = style.COLORS["accent"] if is_active else style.COLORS["text"]
            
            # Create click handler with proper route capture (important: use default parameter)
            def make_click_handler(route_path: str):
                """Create a click handler that captures the route correctly."""
                return lambda _: self.navigate(route_path)
            
            nav_item = ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(
                            icon,
                            size=24,
                            color=icon_color,
                        ),
                        style.mono_text(phase["num"] if phase["num"] else "", size=8, color=style.COLORS["text_muted"]),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=2,
                ),
                on_click=make_click_handler(route),
                tooltip=label,
                padding=12,
                border_radius=4,
                width=60,
                height=60,
                bgcolor=style.COLORS["bg_hover"] if is_active else style.COLORS["bg_panel"],
            )
            nav_items.append(nav_item)
        
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(height=8),  # Top spacing
                    *nav_items,
                    ft.Container(expand=True),  # Bottom spacer
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            bgcolor=style.COLORS["bg_panel"],
            width=72,
            padding=ft.padding.symmetric(horizontal=6, vertical=8),
        )
    
    def _build_mission_area(self) -> ft.Container:
        """Build the center mission area (content)."""
        return ft.Container(
            ref=self._content_area,
            content=ft.Container(),  # Placeholder - will be replaced by views
            expand=True,
            padding=16,
            bgcolor=style.COLORS["bg_dark"],
        )
    
    def _build_comms_panel(self) -> ft.Container:
        """Build the right comms panel (AG-UI drawer, collapsible)."""
        # Toggle button (fixed position)
        toggle_btn = ft.IconButton(
            icon="chat",
            icon_color=style.COLORS["accent"],
            tooltip="Toggle AG-UI Panel",
            on_click=lambda _: self._toggle_comms_panel(),
        )
        
        # Panel content (will be populated by ag_ui component)
        panel_content = ft.Column(
            controls=[
                style.mono_text("COMMS PANEL", size=12, color=style.COLORS["text_dim"]),
                ft.Divider(height=1, color=style.COLORS["border"]),
                ft.Container(
                    content=style.mono_text("No suggestions", size=10, color=style.COLORS["text_muted"]),
                    padding=16,
                ),
            ],
            spacing=8,
            expand=True,
        )
        
        # Drawer container (hidden by default)
        drawer = ft.Container(
            ref=self._comms_drawer,
            content=panel_content,
            width=380,
            bgcolor=style.COLORS["bg_panel"],
            border=ft.border.only(left=ft.BorderSide(1, style.COLORS["border"])),
            padding=16,
            visible=False,  # Hidden by default
        )
        
        # Panel container with toggle button overlay
        return ft.Container(
            content=ft.Stack(
                controls=[
                    drawer,
                    ft.Container(
                        content=toggle_btn,
                        alignment=ft.Alignment(1, -1),  # top-right: x=1 (right), y=-1 (top)
                        padding=8,
                    ),
                ],
            ),
            width=0,  # Collapsed by default
        )
    
    def _toggle_comms_panel(self) -> None:
        """Toggle the comms panel visibility."""
        if self._comms_drawer.current:
            visible = self._comms_drawer.current.visible
            self._comms_drawer.current.visible = not visible
            # Adjust width
            if not visible:
                # Open
                self._comms_drawer.current.width = 380
            else:
                # Close
                self._comms_drawer.current.width = 0
            
            self.page.update()
            self._comms_panel_open = not visible
            logger.debug(f"Comms panel toggled: {not visible}")
    
    def _build_footer(self) -> ft.Container:
        """Build the footer status bar."""
        # Project info
        project_info = ft.Row(
            controls=[
                style.mono_text("PROJECT: ", size=10, color=style.COLORS["text_dim"]),
                style.mono_text("NONE", size=10, color=style.COLORS["accent"]),
                ft.Container(width=1, height=12, bgcolor=style.COLORS["border"]),
                style.mono_text("DB: 0 ENTITIES, 0 RELATIONSHIPS", size=10, color=style.COLORS["text_dim"]),
            ],
            spacing=8,
        )
        
        # Status indicators
        status_info = ft.Row(
            controls=[
                ft.Container(
                    width=6,
                    height=6,
                    bgcolor=style.COLORS["success"],
                    border_radius=3,
                ),
                style.mono_text("CONNECTED", size=10, color=style.COLORS["success"]),
                ft.Container(width=1, height=12, bgcolor=style.COLORS["border"]),
                style.mono_text("v.3.0.0", size=10, color=style.COLORS["text_dim"]),
            ],
            spacing=6,
        )
        
        return ft.Container(
            content=ft.Row(
                controls=[
                    project_info,
                    ft.Container(expand=True),  # Spacer
                    status_info,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=style.COLORS["bg_panel"],
            border=ft.border.only(top=ft.BorderSide(1, style.COLORS["border"])),
            padding=ft.padding.symmetric(horizontal=16, vertical=6),
            height=32,
        )
    
    def _setup_routing(self) -> None:
        """Setup navigation routing."""
        # Route handler will be set up in main.py after shell is created
        # This just ensures we have a placeholder
        pass
    
    def _on_route_change(self, route: ft.RouteChangeEvent) -> None:
        """Handle route changes - called by main.py route handler.
        
        This updates internal state when route changes.
        
        Args:
            route: Route change event
        """
        route_path = route.route if route.route else "/"
        self.current_route = route_path
        self.state.set_active_page(self._route_to_page_id(route_path))
        logger.debug(f"Route changed to: {route_path}")
    
    def _route_to_page_id(self, route: str) -> str:
        """Convert route to page ID.
        
        Args:
            route: Route path
            
        Returns:
            Page identifier
        """
        if route == "/" or route == "":
            return "landing"
        return route.strip("/").split("/")[0] or "landing"
    
    def navigate(self, route: str) -> None:
        """Navigate to a route.
        
        Args:
            route: Route path
        """
        if route.startswith("/"):
            self.page.go(route)
        else:
            self.page.go(f"/{route}")
    
    def set_view(self, view_fn: Callable[[], ft.Control]) -> None:
        """Set the current view content.
        
        Args:
            view_fn: Function that returns the view content
        """
        if self._content_area.current:
            self.current_view = view_fn
            content = view_fn()
            self._content_area.current.content = content
            self.page.update()
            logger.debug(f"View set: {view_fn.__name__}")
    
    def set_view_content(self, content: ft.Control) -> None:
        """Set the current view content directly.
        
        Args:
            content: Control to display as view content
        """
        if self._content_area.current:
            self._content_area.current.content = content
            self.page.update()
            logger.debug(f"View content updated")
    
    def _load_landing_view(self) -> None:
        """Load the landing view as fallback."""
        try:
            from forge.frontend.views import landing
            view_content = landing.render_landing_view(self.state)
            self.set_view_content(view_content)
        except Exception as e:
            logger.error(f"Failed to load landing view: {e}")
            # Show error message
            self.set_view_content(
                ft.Container(
                    content=style.mono_text(f"Error loading view: {e}", size=14, color=style.COLORS["error"]),
                    expand=True,
                    alignment=ft.alignment.center,
                )
            )
    