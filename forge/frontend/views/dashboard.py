"""
Dashboard View - Control Center.

Intelligence platform dashboard with metrics, activity feed, and analytics.
"""

from __future__ import annotations

import flet as ft

from forge.frontend import style
from forge.frontend.components.activity_feed import create_activity_feed
from forge.frontend.state import FletXState
from forge.utils.logging import get_logger

logger = get_logger("frontend.dashboard")


def render_dashboard_view(state: FletXState) -> ft.Control:
    """Render the dashboard view.
    
    Args:
        state: FletXState instance
        
    Returns:
        Control representing the dashboard view
    """
    if not state.has_project:
        return _render_no_project(state)
    
    # Project header
    project = state.project
    project_name = project.name if project else "UNKNOWN"
    
    header = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    style.mono_text(project_name.upper(), size=20, weight=ft.FontWeight.W_600),
                    style.forge_badge("ACTIVE", severity="active"),
                ],
                spacing=12,
            ),
            ft.Container(height=4),
            style.mono_text(
                project.description if project and project.description else "No description provided",
                size=12,
                color=style.COLORS["text_dim"],
            ),
        ],
        spacing=0,
    )
    
    # Metrics row
    metrics_row = _render_metrics_row(state)
    
    # Main content grid: Activity & Charts (left) and Quick Actions (right)
    main_content = ft.Row(
        controls=[
            # Left: Activity & Visualization (2/3 width)
            ft.Container(
                content=ft.Column(
                    controls=[
                        _render_entity_distribution(state),
                        ft.Container(height=16),
                        create_activity_feed(state, limit=20),
                    ],
                    spacing=0,
                    expand=True,
                ),
                expand=2,
            ),
            ft.VerticalDivider(width=1, color=style.COLORS["border"]),
            # Right: Quick Actions (1/3 width)
            ft.Container(
                content=_render_quick_actions(state),
                expand=1,
            ),
        ],
        spacing=24,
        expand=True,
    )
    
    return ft.Column(
        controls=[
            header,
            ft.Container(height=24),
            metrics_row,
            ft.Container(height=24),
            main_content,
        ],
        spacing=0,
        expand=True,
    )


def _render_no_project(state: FletXState) -> ft.Control:
    """Render message when no project is loaded.
    
    Args:
        state: FletXState instance
        
    Returns:
        Control with no project message
    """
    return ft.Container(
        content=ft.Column(
            controls=[
                style.mono_text("[X]", size=48, color=style.COLORS["text_muted"]),
                style.mono_text("No Project Loaded", size=18, color=style.COLORS["text_dim"]),
                style.mono_text("Select or create a project to continue", size=12, color=style.COLORS["text_muted"]),
                ft.Container(height=24),
                style.forge_button(
                    "GO TO PROJECTS",
                    on_click=lambda _: state.page.go("/"),
                    primary=True,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        expand=True,
        alignment=ft.Alignment(0, 0),
    )


def _render_metrics_row(state: FletXState) -> ft.Control:
    """Render horizontal metrics row.
    
    Args:
        state: FletXState instance
        
    Returns:
        Control with metrics cards
    """
    try:
        stats = state.forge_state.get_stats()
        entity_count = stats.get("entity_count", 0)
        rel_count = stats.get("relationship_count", 0)
        doc_count = stats.get("document_count", 0)
        alert_count = 0  # TODO: Implement alert counting
    except Exception as e:
        logger.error(f"Failed to load stats: {e}")
        entity_count = 0
        rel_count = 0
        doc_count = 0
        alert_count = 0
    
    metrics = [
        {
            "label": "ENTITIES",
            "value": str(entity_count),
            "subtext": "View in HUMINT →",
            "color": style.COLORS["accent"],
            "route": "/humint",
        },
        {
            "label": "RELATIONS",
            "value": str(rel_count),
            "subtext": "High connectivity",
            "color": style.COLORS["success"],
            "route": "/sigint",
        },
        {
            "label": "DOCUMENTS",
            "value": str(doc_count),
            "subtext": "1 pending extraction" if doc_count > 0 else "No documents",
            "color": style.COLORS["warning"],
            "route": "/osint",
        },
        {
            "label": "ALERTS",
            "value": str(alert_count),
            "subtext": f"{alert_count} Validation Errors" if alert_count > 0 else "All clear",
            "color": style.COLORS["error"] if alert_count > 0 else style.COLORS["success"],
        },
    ]
    
    metric_cards = []
    for metric in metrics:
        card = _render_metric_card(state, metric)
        metric_cards.append(card)
    
    return ft.Row(
        controls=metric_cards,
        spacing=16,
    )


def _render_metric_card(state: FletXState, metric: dict) -> ft.Control:
    """Render a single metric card.
    
    Args:
        state: FletXState instance
        metric: Metric dictionary with label, value, subtext, color, route
        
    Returns:
        Control representing metric card
    """
    route = metric.get("route")
    
    content = ft.Column(
        controls=[
            style.mono_label(metric["label"], size=10),
            ft.Container(height=8),
            style.mono_text(metric["value"], size=32, weight=ft.FontWeight.W_600),
            ft.Container(height=4),
            style.mono_text(metric["subtext"], size=10, color=style.COLORS["text_dim"]),
        ],
        spacing=0,
    )
    
    card = style.forge_card(
        content=content,
        padding=16,
        width=200,
        on_click=lambda _: state.page.go(route) if route else None,
    )
    
    if route:
        card.cursor = ft.MouseCursor.CLICK
    
    return card


def _render_entity_distribution(state: FletXState) -> ft.Control:
    """Render entity distribution chart.
    
    Args:
        state: FletXState instance
        
    Returns:
        Control with entity distribution visualization
    """
    section_label = style.mono_label("DATASET_COMPOSITION")
    
    try:
        entities = state.forge_state.db.get_all_entities()
        
        # Count by type
        type_counts: dict[str, int] = {}
        for entity in entities:
            etype = entity.entity_type.value if hasattr(entity.entity_type, "value") else str(entity.entity_type)
            type_counts[etype] = type_counts.get(etype, 0) + 1
        
        if not type_counts:
            content = ft.Container(
                content=style.mono_text(
                    "No entities yet. Upload documents to begin extraction.",
                    size=12,
                    color=style.COLORS["text_muted"],
                ),
                padding=16,
                alignment=ft.Alignment(0, 0),
            )
        else:
            # Create a simple bar chart representation
            # TODO: Replace with Plotly chart when DuckDB analytics is integrated
            bars = []
            max_count = max(type_counts.values()) if type_counts else 1
            
            for etype, count in sorted(type_counts.items()):
                bar_width = (count / max_count) * 200 if max_count > 0 else 0
                bars.append(
                    ft.Row(
                        controls=[
                            style.mono_text(etype, size=10, color=style.COLORS["text_dim"]),
                            ft.Container(expand=True),
                            ft.Container(
                                width=bar_width,
                                height=20,
                                bgcolor=style.COLORS["accent"],
                                border_radius=2,
                            ),
                            ft.Container(width=8),
                            style.mono_text(str(count), size=10),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    )
                )
            
            content = ft.Column(
                controls=bars,
                spacing=8,
            )
        
    except Exception as e:
        logger.error(f"Failed to render entity distribution: {e}")
        content = ft.Container(
            content=style.mono_text(f"Error loading chart: {e}", size=12, color=style.COLORS["error"]),
            padding=16,
            alignment=ft.Alignment(0, 0),
        )
    
    return ft.Column(
        controls=[
            section_label,
            ft.Container(height=8),
            style.forge_card(
                content=content,
                padding=16,
                height=200,
            ),
        ],
        spacing=0,
    )


def _render_quick_actions(state: FletXState) -> ft.Control:
    """Render quick action buttons.
    
    Args:
        state: FletXState instance
        
    Returns:
        Control with quick actions
    """
    section_label = style.mono_label("QUICK_OPS")
    
    actions = [
        ("UPLOAD SOURCE", "upload", "/osint", True),
        ("NEW ENTITY", "add", "/humint", False),
        ("RUN EXPORT", "download", "/anvil", False),
    ]
    
    action_buttons = []
    for label, icon, route, primary in actions:
        btn = style.forge_button(
            label,
            icon=icon,
            primary=primary,
            on_click=lambda _, r=route: state.page.go(r),
        )
        action_buttons.append(btn)
    
    return ft.Column(
        controls=[
            section_label,
            ft.Container(height=12),
            *action_buttons,
        ],
        spacing=8,
    )
