from __future__ import annotations

from typing import List

import flet as ft

from forge.core.app_controller import AppController
from forge.presentation.renderer import render_schema


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


def _format_percent(value: float) -> str:
    return f"{float(value):.0f}%"


def build_shell(page: ft.Page, controller: AppController) -> ft.View:
    apply_shell_theme(page)

    # --- UI primitives ---
    nav_rail = ft.NavigationRail(
        label_type=ft.NavigationRailLabelType.ALL,
        bgcolor="rgba(255,255,255,0.1)",
        indicator_color=ft.Colors.BLUE_400,
        min_width=80,
        min_extended_width=180,
        destinations=_nav_destinations(controller.nav_items.value),
        selected_index=0,
    )

    status_text = ft.Text(controller.status_text.value, color=ft.Colors.WHITE70)

    gpu_kpi = ft.Text(
        _format_percent(float(controller.telemetry.value.get("gpu_util", 0.0))),
        size=28,
        weight=ft.FontWeight.W_700,
        color=ft.Colors.CYAN_ACCENT,
    )
    vram_kpi = ft.Text(
        f"{float(controller.telemetry.value.get('vram_used_gb', 0.0)):.1f} /"
        f" {float(controller.telemetry.value.get('vram_total_gb', 0.0)):.1f} GB",
        color=ft.Colors.WHITE,
    )

    ag_feed = ft.ListView(spacing=8, auto_scroll=True)

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

    def _sync_telemetry() -> None:
        data = controller.telemetry.value
        gpu_kpi.value = _format_percent(data.get("gpu_util", 0.0)) # type: ignore
        vram_kpi.value = (
            f"{data.get('vram_used_gb', 0.0):.1f} / {data.get('vram_total_gb', 0.0):.1f} GB"
        )
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
                controller.set_nav_selected(items[idx].get("id", ""))
        page.update()

    nav_rail.on_change = _on_nav_change  # type: ignore[assignment]

    # Attach reactive listeners
    controller.nav_items.listen(_sync_nav)
    controller.nav_selected.listen(_sync_nav)
    controller.telemetry.listen(_sync_telemetry)
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
                ft.Container(width=88, expand=False, content=ft.Column([nav_rail], expand=True)),
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
                                    ft.Row(
                                        [
                                            ft.Icon(ft.Icons.MEMORY, color=ft.Colors.BLUE_200),
                                            gpu_kpi,
                                            ft.Icon(ft.Icons.STACKED_LINE_CHART, color=ft.Colors.BLUE_200),
                                            vram_kpi,
                                        ],
                                        spacing=8,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Container(height=8),
                            ft.Row(
                                [
                                    ft.Container(
                                        expand=2,
                                        content=workspace,
                                        padding=12,
                                        bgcolor="rgba(255,255,255,0.04)",
                                        border_radius=12,
                                    ),
                                    ft.VerticalDivider(width=1, color="rgba(255,255,255,0.1)"),
                                    ft.Container(
                                        expand=1,
                                        padding=12,
                                        bgcolor="rgba(255,255,255,0.06)",
                                        border_radius=12,
                                        content=ft.Column(
                                            [
                                                ft.Text("AG-UI Feed", weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
                                                ft.Divider(color="rgba(255,255,255,0.1)"),
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
    _sync_telemetry()
    _sync_status()
    _sync_feed()
    _sync_workspace()

    return ft.View(
        route="/",
        controls=[chrome],
        bgcolor=ft.Colors.BLACK,
        padding=0,
    )
