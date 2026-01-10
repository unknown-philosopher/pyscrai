"""
Dashboard Page - Control Center.

Intelligence platform dashboard displaying:
- Horizontal metrics row (Entities, Relationships, Documents, Alerts)
- Activity feed showing recent BaseEvent logs
- Entity distribution visualization
- Quick action buttons
"""

from __future__ import annotations

from typing import Any

from nicegui import ui

from forge.legacy_nicegui.components.activity_feed import create_activity_feed
from forge.legacy_nicegui.components.ui_components import ForgeButton, ForgeMetricCard
from forge.legacy_nicegui.state import get_session, is_project_loaded
from forge.utils.logging import get_logger

logger = get_logger("frontend.dashboard")


def content() -> None:
    """Render the dashboard page content."""
    if not is_project_loaded():
        _render_no_project()
        return
    
    session = get_session()
    project = session.project
    project_name = project.name if project else "UNKNOWN"
    
    # Project header
    with ui.column().classes("w-full mb-6"):
        with ui.row().classes("items-center gap-4 mb-2"):
            ui.html(f'<h1 class="mono" style="font-size: 1.6rem; font-weight: 600; color: #e0e0e0;">{project_name.upper()}</h1>', sanitize=False)
            ui.html('<span class="forge-badge forge-badge-active">ACTIVE</span>', sanitize=False)
        
        # Description
        desc = project.description if project and project.description else "No description provided."
        ui.html(f'<p class="mono" style="color: #666; font-size: 0.85rem;">{desc}</p>', sanitize=False)
    
    # 1. Horizontal Metrics Row
    _render_metrics_row()
    
    # 2. Main Content Grid (2/3 Activity & Visualization, 1/3 Quick Actions)
    with ui.grid(columns=3).classes("w-full gap-6 mt-6"):
        # Left: Activity & Visualization (Span 2 columns)
        with ui.column().classes("col-span-2 gap-6"):
            # Entity Distribution Chart
            _render_entity_distribution()
            
            # Activity Feed
            create_activity_feed(limit=20)
        
        # Right: Quick Actions (Span 1 column)
        with ui.column().classes("col-span-1 gap-4"):
            _render_quick_actions()


def _render_no_project() -> None:
    """Render message when no project is loaded."""
    with ui.column().classes("items-center justify-center").style("min-height: 400px;"):
        ui.html('<span class="mono" style="color: #333; font-size: 3rem; margin-bottom: 16px;">[X]</span>', sanitize=False)
        ui.html('<span class="mono" style="color: #888; font-size: 1.2rem; margin-bottom: 8px;">No Project Loaded</span>', sanitize=False)
        ui.html('<span class="mono" style="color: #555; font-size: 0.85rem; margin-bottom: 24px;">Select or create a project to continue.</span>', sanitize=False)
        
        with ui.element("div").classes(
            "cursor-pointer px-6 py-2 rounded"
        ).style(
            "background: #00b8d4; color: #000; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;"
        ).on("click", lambda: ui.navigate.to("/")):
            ui.html('GO TO PROJECTS', sanitize=False)


def _render_metrics_row() -> None:
    """Render horizontal metrics row."""
    try:
        session = get_session()
        stats = session.get_stats()
        
        entity_count = stats.get("entity_count", 0)
        rel_count = stats.get("relationship_count", 0)
        doc_count = stats.get("document_count", 0)
        
        # Calculate alerts (validation errors, etc.)
        alert_count = 0  # TODO: Implement alert counting
        
    except Exception as e:
        logger.error(f"Failed to load stats: {e}")
        entity_count = 0
        rel_count = 0
        doc_count = 0
        alert_count = 0
    
    with ui.row().classes("w-full gap-4 mb-6"):
        # Entities metric
        metric_card = ForgeMetricCard(
            label="ENTITIES",
            value=str(entity_count),
            subtext="View in HUMINT →",
            icon="group"
        )
        metric_card.on("click", lambda: ui.navigate.to("/humint"))
        
        # Relationships metric
        metric_card = ForgeMetricCard(
            label="RELATIONS",
            value=str(rel_count),
            subtext="High connectivity",
            icon="hub"
        )
        metric_card.on("click", lambda: ui.navigate.to("/sigint"))
        
        # Documents metric
        metric_card = ForgeMetricCard(
            label="DOCUMENTS",
            value=str(doc_count),
            subtext="1 pending extraction" if doc_count > 0 else "No documents",
            icon="description"
        )
        metric_card.on("click", lambda: ui.navigate.to("/osint"))
        
        # Alerts metric
        ForgeMetricCard(
            label="ALERTS",
            value=str(alert_count),
            subtext=f"{alert_count} Validation Errors" if alert_count > 0 else "All clear",
            icon="warning"
        )


def _render_entity_distribution() -> None:
    """Render entity distribution chart."""
    ui.html('<div class="section-label mb-2">DATASET_COMPOSITION</div>', sanitize=False)
    
    with ui.card().classes("w-full h-64 bg-gray-900 border border-gray-800 p-4"):
        try:
            session = get_session()
            entities = session.db.get_all_entities()
            
            # Count by type
            type_counts: dict[str, int] = {}
            for entity in entities:
                etype = entity.entity_type.value if hasattr(entity.entity_type, "value") else str(entity.entity_type)
                type_counts[etype] = type_counts.get(etype, 0) + 1
            
            if not type_counts:
                ui.html(
                    '<span class="mono" style="color: #444; font-size: 0.75rem;">No entities yet. Upload documents to begin extraction.</span>',
                    sanitize=False
                )
                return
            
            # Create ECharts pie chart
            chart_data = {
                "tooltip": {
                    "trigger": "item",
                    "formatter": "{a} <br/>{b}: {c} ({d}%)"
                },
                "legend": {
                    "orient": "vertical",
                    "left": "left",
                    "textStyle": {"color": "#888", "fontFamily": "JetBrains Mono"}
                },
                "series": [
                    {
                        "name": "Entity Types",
                        "type": "pie",
                        "radius": ["40%", "70%"],
                        "avoidLabelOverlap": False,
                        "itemStyle": {
                            "borderRadius": 4,
                            "borderColor": "#0a0a0a",
                            "borderWidth": 2
                        },
                        "label": {
                            "show": True,
                            "formatter": "{b}: {c}",
                            "color": "#aaa",
                            "fontFamily": "JetBrains Mono",
                            "fontSize": 11
                        },
                        "emphasis": {
                            "label": {
                                "show": True,
                                "fontSize": 12,
                                "fontWeight": "bold"
                            }
                        },
                        "labelLine": {
                            "show": True
                        },
                        "data": [
                            {
                                "value": count,
                                "name": etype,
                                "itemStyle": {
                                    "color": {
                                        "ACTOR": "#00b8d4",
                                        "POLITY": "#00c853",
                                        "LOCATION": "#ffab00",
                                        "RESOURCE": "#ff5252",
                                        "EVENT": "#9c27b0",
                                        "ABSTRACT": "#607d8b",
                                    }.get(etype, "#888")
                                }
                            }
                            for etype, count in type_counts.items()
                        ]
                    }
                ]
            }
            
            ui.echart(chart_data).classes("w-full h-full")
            
        except Exception as e:
            logger.error(f"Failed to render entity distribution: {e}")
            ui.html(
                f'<span class="mono" style="color: #ff5252; font-size: 0.75rem;">Error loading chart: {e}</span>',
                sanitize=False
            )


def _render_quick_actions() -> None:
    """Render quick action buttons."""
    ui.html('<div class="section-label mb-4">QUICK_OPS</div>', sanitize=False)
    
    with ui.card().classes("w-full bg-gray-900 border border-gray-800 p-4"):
        with ui.column().classes("gap-2 w-full"):
            # Upload documents
            ForgeButton(
                "UPLOAD SOURCE",
                icon="upload",
                primary=True,
                on_click=lambda: ui.navigate.to("/osint")
            )
            
            # Add entity
            ForgeButton(
                "NEW ENTITY",
                icon="add",
                on_click=lambda: ui.navigate.to("/humint")
            )
            
            # Export
            ForgeButton(
                "RUN EXPORT",
                icon="download",
                on_click=lambda: ui.navigate.to("/anvil")
            )
