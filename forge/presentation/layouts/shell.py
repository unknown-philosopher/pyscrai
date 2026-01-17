from __future__ import annotations

from typing import List, Optional

import flet as ft

from forge.core.app_controller import AppController
from forge.core.service_registry import get_session_manager
from forge.presentation.renderer import render_schema
# Import the new DashboardController
from forge.presentation.controllers.dashboard_controller import DashboardController


def apply_shell_theme(page: ft.Page) -> None:
    """Apply a dark, high-contrast baseline theme with improved readability."""
    page.theme = ft.Theme(
        font_family="Space Grotesk",
        color_scheme_seed="#48b0f7",
        visual_density=ft.VisualDensity.COMFORTABLE,
        use_material3=True,
    )
    page.bgcolor = "#000000"  # Pure black
    page.padding = 0


def _nav_destinations(items: List[dict]) -> List[ft.NavigationRailDestination]:
    destinations: List[ft.NavigationRailDestination] = []
    for item in items:
        icon_name = str(item.get("icon", "dashboard")).upper()
        icon = getattr(ft.Icons, icon_name, ft.Icons.DASHBOARD)
        destinations.append(
            ft.NavigationRailDestination(icon=icon, label=item.get("label", ""))
        )
    return destinations


def build_shell(page: ft.Page, controller: AppController) -> ft.View:
    apply_shell_theme(page)

    # Initialize the new Dashboard Controller
    dashboard_controller = DashboardController(controller, page)

    # --- UI primitives ---
    nav_rail = ft.NavigationRail(
        label_type=ft.NavigationRailLabelType.ALL,
        bgcolor="#0a0d1f",  # Refined dark blue
        indicator_color="#48b0f7",  # Cyan accent
        selected_label_text_style=ft.TextStyle(color="#E8F1F8"),  # Light text
        unselected_label_text_style=ft.TextStyle(color="#8A9BA8"),  # Muted text
        min_width=80,
        min_extended_width=180,
        destinations=_nav_destinations(controller.nav_items.value),
        selected_index=0,
    )

    status_text = ft.Text(controller.status_text.value, color="#B8C5D0", size=12)

    # AG-UI Feed List
    ag_feed = ft.ListView(spacing=8, auto_scroll=True)

    # Main Content Container
    content_container = ft.Container(
        expand=True,
        content=dashboard_controller.build_view(),  # Default to unified dashboard
    )

    # Intelligence Workspace (Scrollable)
    workspace = ft.Column(
        controls=[ft.Text("Awaiting Intel", color="#8A9BA8", size=14, italic=True)],
        scroll=ft.ScrollMode.AUTO,
        spacing=12,
    )

    def _sync_nav() -> None:
        nav_rail.destinations = _nav_destinations(controller.nav_items.value)
        ids = [item.get("id") for item in controller.nav_items.value]
        if controller.nav_selected.value in ids:
            nav_rail.selected_index = ids.index(controller.nav_selected.value)
        page.update()

    def _sync_status() -> None:
        status_text.value = controller.status_text.value
        page.update()

    def _sync_feed() -> None:
        # Color map for log levels
        level_colors = {
            "INFO": "#48b0f7",      # Cyan
            "SUCCESS": "#4ECDC4",   # Teal
            "WARNING": "#FFD93D",   # Yellow
            "ERROR": "#FF6B6B",     # Red
        }
        
        ag_feed.controls = [
            ft.Row(
                [
                    ft.Text(
                        entry.get("level", "info").upper(), 
                        color=level_colors.get(entry.get("level", "info").upper(), "#8A9BA8"), 
                        size=10, 
                        width=60,
                        weight=ft.FontWeight.W_600
                    ),
                    ft.Text(entry.get("message", ""), color="#E8F1F8", size=12, expand=True),
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
            for entry in controller.ag_feed.value
        ]
        page.update()

    def _sync_agui_panel() -> None:
        # Toggle visibility/width based on state
        ag_panel_container.visible = controller.is_agui_expanded.value
        page.update()

    def _sync_workspace() -> None:
        if not controller.workspace_schemas.value:
            workspace.controls = [ft.Text("Awaiting Intel", color="#8A9BA8", size=14, italic=True)]
        else:
            # Use the AG-UI renderer to render schemas
            rendered_components: List[ft.Control] = []
            for schema in controller.workspace_schemas.value:
                try:
                    component = render_schema(schema)
                    rendered_components.append(component)
                except Exception as e:
                    # Fallback to error display if rendering fails
                    rendered_components.append(
                        ft.Container(
                            bgcolor="rgba(255,59,48,0.1)",
                            padding=12,
                            border_radius=8,
                            border=ft.border.all(1, "#FF6B6B"),
                            content=ft.Text(
                                f"Render error: {str(e)}",
                                color="#FF6B6B",
                                size=12,
                            ),
                        )
                    )
            workspace.controls = rendered_components
        page.update()

    def _on_nav_change(e: ft.ControlEvent) -> None:
        rail = e.control
        if hasattr(rail, 'selected_index'):
            idx = rail.selected_index  # type: ignore[reportAttributeAccessIssue]
            items = controller.nav_items.value
            if 0 <= idx < len(items):
                nav_id = items[idx].get("id", "")
                controller.set_nav_selected(nav_id)
                
                # Switch Views
                if nav_id == "dashboard":
                    # Rebuild dashboard to refresh stats
                    content_container.content = dashboard_controller.build_view()
                
                elif nav_id == "intel":
                    # Show Intelligence Dashboard (Workspace)
                    content_container.content = ft.Container(
                        padding=20,
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.PSYCHOLOGY, size=32, color="#48b0f7"),
                                ft.Text("Intelligence Dashboard", size=24, weight=ft.FontWeight.W_700, color="#E8F1F8"),
                            ], spacing=12),
                            ft.Divider(color="rgba(255, 255, 255, 0.12)", height=1),
                            workspace,
                        ], spacing=16, scroll=ft.ScrollMode.AUTO)
                    )
        page.update()

    nav_rail.on_change = _on_nav_change  # type: ignore[assignment]

    # --- Listener Bindings ---
    controller.nav_items.listen(_sync_nav)
    controller.nav_selected.listen(_sync_nav)
    controller.status_text.listen(_sync_status)
    controller.ag_feed.listen(_sync_feed)
    controller.workspace_schemas.listen(_sync_workspace)
    controller.is_agui_expanded.listen(_sync_agui_panel)

    # --- Collapsible Panel Definition ---
    ag_panel_container = ft.Container(
        width=300, # Fixed width when open
        padding=14,
        bgcolor="rgba(255,255,255,0.04)",
        border_radius=12,
        border=ft.border.all(1, "rgba(255,255,255,0.08)"),
        animate_opacity=300, # Fade effect
        content=ft.Column(
            [
                ft.Row([
                    ft.Text("AG-UI Feed", weight=ft.FontWeight.W_600, color="#E8F1F8", size=14),
                    ft.IconButton(
                        ft.Icons.CLOSE, 
                        icon_size=18, 
                        icon_color="#8A9BA8",
                        on_click=lambda e: controller.toggle_agui()
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(color="rgba(255, 255, 255, 0.12)", height=1),
                ag_feed,
            ],
            spacing=10,
        ),
    )

    # --- Main Layout ---
    chrome = ft.Container(
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=["#0d1528", "#0a0f1c", "#060a12"],
        ),
        content=ft.Row(
            [
                nav_rail,
                ft.VerticalDivider(width=1, color="rgba(255,255,255,0.12)"),
                ft.Container(
                    expand=True,
                    padding=ft.padding.only(left=18, right=18, top=10, bottom=18),
                    content=ft.Column(
                        [
                            # Header Bar (minimal, just for AG-UI toggle)
                            ft.Row(
                                [
                                    ft.Container(expand=True),  # Spacer
                                    
                                    # Toggle Button for AG-UI
                                    ft.IconButton(
                                        icon=ft.Icons.VIEW_SIDEBAR,
                                        tooltip="Toggle AG-UI Feed",
                                        icon_color="#48b0f7",
                                        on_click=lambda e: controller.toggle_agui()
                                    )
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                height=36,  # Slightly taller for better clickability
                            ),
                            
                            # Content Area + Right Panel
                            ft.Row(
                                [
                                    ft.Container(
                                        expand=True, # Takes remaining space
                                        content=content_container,
                                        padding=0,
                                        bgcolor="rgba(255,255,255,0.025)",
                                        border_radius=12,
                                        border=ft.border.all(1, "rgba(255,255,255,0.06)"),
                                    ),
                                    
                                    # The collapsible panel
                                    ag_panel_container, 
                                ],
                                expand=True,
                                spacing=14,
                            ),
                        ],
                        spacing=0,
                    ),
                ),
            ],
            expand=True,
        ),
    )

    # Initial Sync
    _sync_nav()
    _sync_status()
    _sync_feed()
    _sync_workspace()
    _sync_agui_panel()

    return ft.View(
        route="/",
        controls=[chrome],
        bgcolor=ft.Colors.BLACK,
        padding=0,
    )
