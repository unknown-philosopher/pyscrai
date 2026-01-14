from __future__ import annotations

from typing import List, Optional

import flet as ft

from forge.core.app_controller import AppController
from forge.core.service_registry import get_session_manager
from forge.presentation.renderer import render_schema
from forge.presentation.controllers.ingest_controller import IngestController
from forge.presentation.controllers.project_controller import ProjectController
from forge.presentation.controllers.graph_controller import GraphController


def apply_shell_theme(page: ft.Page) -> None:
    """Apply a dark, high-contrast baseline theme."""
    page.theme = ft.Theme(
        font_family="Space Grotesk",
        color_scheme_seed="#48b0f7",
        visual_density=ft.VisualDensity.COMPACT,
        use_material3=True,
    )
    page.bgcolor = ft.Colors.BLACK
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

    # Initialize ingest controller
    ingest_controller = IngestController(controller, page)
    
    def get_project_controller():
        """Lazy initialization of ProjectController when session_manager becomes available."""
        # Dynamically access the global session_manager (set in background thread)
        # This allows the UI to access it even if it was None when build_shell() was called
        sm = get_session_manager()
        if sm:
            return ProjectController(controller, sm, page)
        return None
    
    def get_graph_controller():
        """Lazy initialization of GraphController."""
        return GraphController(controller, page)

    # --- UI primitives ---
    nav_rail = ft.NavigationRail(
        label_type=ft.NavigationRailLabelType.ALL,
        bgcolor="#080b31",  # Dark blue accent
        indicator_color=ft.Colors.BLUE_400,
        min_width=80,
        min_extended_width=180,
        destinations=_nav_destinations(controller.nav_items.value),
        selected_index=0,
    )

    status_text = ft.Text(controller.status_text.value, color=ft.Colors.WHITE70)

    ag_feed = ft.ListView(spacing=8, auto_scroll=True)

    # Content container that switches based on navigation
    content_container = ft.Container(
        expand=True,
        content=ingest_controller.build_view(),  # Default to ingest view
    )

    workspace = ft.Column(
        controls=[ft.Text("Awaiting Intel", color=ft.Colors.WHITE70)],
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
        ag_feed.controls = [
            ft.Row(
                [
                    ft.Text(entry.get("level", "info").upper(), color=ft.Colors.AMBER_200),
                    ft.Text(entry.get("message", ""), color=ft.Colors.WHITE),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
            for entry in controller.ag_feed.value
        ]
        page.update()

    def _sync_workspace() -> None:
        if not controller.workspace_schemas.value:
            workspace.controls = [ft.Text("Awaiting Intel", color=ft.Colors.WHITE70)]
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
                            bgcolor="rgba(255,0,0,0.1)",
                            padding=12,
                            border_radius=8,
                            content=ft.Text(
                                f"Render error: {str(e)}",
                                color=ft.Colors.RED_300,
                            ),
                        )
                    )
            workspace.controls = rendered_components
        page.update()

    def _on_nav_change(e: ft.ControlEvent) -> None:
        rail = e.control
        if hasattr(rail, 'selected_index'):
            idx = rail.selected_index  # type: ignore[attr-defined]
            items = controller.nav_items.value
            if 0 <= idx < len(items):
                nav_id = items[idx].get("id", "")
                controller.set_nav_selected(nav_id)
                
                # Switch content based on navigation
                if nav_id == "ingest":
                    content_container.content = ingest_controller.build_view()
                elif nav_id == "graph":
                    graph_controller = get_graph_controller()
                    if graph_controller:
                        content_container.content = graph_controller.build_view()
                    else:
                        content_container.content = ft.Container(
                            padding=20,
                            content=ft.Column([  # type: ignore[arg-type]
                                ft.Text("Graph View", size=24, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
                                ft.Divider(color="rgba(255, 255, 255, 0.1)"),  # type: ignore[call-arg]
                                ft.Text("Loading graph view...", color=ft.Colors.WHITE70),
                            ])
                        )
                elif nav_id == "intel":
                    # Show workspace for intelligence view
                    content_container.content = ft.Container(
                        padding=20,
                        content=ft.Column([  # type: ignore[arg-type]
                            ft.Row([
                                ft.Icon(ft.Icons.PSYCHOLOGY, size=32, color=ft.Colors.CYAN_300),
                                ft.Text("Intelligence Dashboard", size=24, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
                            ], spacing=12),
                            ft.Divider(color="rgba(255, 255, 255, 0.1)"),  # type: ignore[call-arg]
                            workspace,
                        ], spacing=12, scroll=ft.ScrollMode.AUTO)
                    )
                elif nav_id == "project":
                    project_controller = get_project_controller()
                    if project_controller:
                        content_container.content = project_controller.build_view()
                    else:
                        content_container.content = ft.Container(
                            padding=20,
                            content=ft.Column([
                                ft.Text("Session Manager not initialized", color=ft.Colors.AMBER_300, size=16),
                                ft.Text("Please wait for services to initialize...", color=ft.Colors.WHITE70, size=12),
                            ])
                        )
        page.update()

    nav_rail.on_change = _on_nav_change  # type: ignore[assignment]

    # Attach reactive listeners
    controller.nav_items.listen(_sync_nav)
    controller.nav_selected.listen(_sync_nav)
    controller.status_text.listen(_sync_status)
    controller.ag_feed.listen(_sync_feed)
    controller.workspace_schemas.listen(_sync_workspace)

    chrome = ft.Container(
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=["#0b1224", "#0a0f1c", "#05080f"],
        ),
        content=ft.Row(
            [
                nav_rail,
                ft.VerticalDivider(width=1, color="rgba(255,255,255,0.1)"),
                ft.Container(
                    expand=True,
                    padding=16,
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text("PyScrAI Forge", size=18, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
                                    ft.Container(width=8),
                                    status_text,

                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Container(height=8),
                            ft.Row(
                                [
                                    ft.Container(
                                        expand=2,
                                        content=content_container,
                                        padding=0,
                                        bgcolor="rgba(255,255,255,0.04)",
                                        border_radius=12,
                                    ),
                                    ft.VerticalDivider(width=1, color="rgba(255,255,255,0.1)"),
                                    ft.Container(
                                        expand=1,
                                        padding=12,
                                        bgcolor="rgba(255,255,255,0.06)",
                                        border_radius=12,
                                        content=ft.Column(  # type: ignore[arg-type]
                                            [
                                                ft.Text("AG-UI Feed", weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
                                                ft.Divider(color="rgba(255,255,255,0.1)"),  # type: ignore[call-arg]
                                                ag_feed,
                                            ],
                                            spacing=8,
                                        ),
                                    ),
                                ],
                                expand=True,
                                spacing=12,
                            ),
                        ],
                        spacing=12,
                    ),
                ),
            ],
            expand=True,
        ),
    )

    _sync_nav()
    _sync_status()
    _sync_feed()
    _sync_workspace()

    return ft.View(
        route="/",
        controls=[chrome],
        bgcolor=ft.Colors.BLACK,
        padding=0,
    )
