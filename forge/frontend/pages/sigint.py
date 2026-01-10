"""
SIGINT Page - Phase 2: Relationship Analysis.

Displays:
- Network graph visualization (ECharts)
- Adjacency matrix view
- Graph analysis tools (communities, shortest path, etc.)
"""

from __future__ import annotations

from typing import Any

from nicegui import ui

from forge.frontend.state import get_session, is_project_loaded
from forge.utils.logging import get_logger

logger = get_logger("frontend.sigint")


def content() -> None:
    """Render the SIGINT page content."""
    if not is_project_loaded():
        _render_no_project()
        return
    
    # Page header
    ui.html('<h1 class="mono" style="font-size: 1.6rem; font-weight: 600; color: #e0e0e0; margin-bottom: 8px;">SIGINT_NETWORK</h1>', sanitize=False)
    ui.html('<p class="mono" style="font-size: 0.8rem; color: #555; margin-bottom: 24px;">Visualize and analyze the relationship network between entities.</p>', sanitize=False)
    
    # View toggle
    with ui.row().classes("items-center gap-2 mb-4"):
        ui.html('<span class="mono" style="color: #555; font-size: 0.7rem;">VIEW:</span>', sanitize=False)
        view_mode = ui.toggle(
            ["Graph", "Matrix"],
            value="Graph",
        ).props("dense")
    
    # Toolbar
    with ui.row().classes("w-full mb-4 gap-2 items-center"):
        with ui.element("div").classes("cursor-pointer px-3 py-1 rounded").style(
            "background: #00b8d4; color: #000; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;"
        ).on("click", _refresh_graph):
            ui.html('REFRESH', sanitize=False)
        
        with ui.element("div").classes("forge-btn cursor-pointer px-3 py-1").on("click", _find_communities):
            ui.html('FIND COMMUNITIES', sanitize=False)
        with ui.element("div").classes("forge-btn cursor-pointer px-3 py-1").on("click", _find_key_actors):
            ui.html('KEY ACTORS', sanitize=False)
        
        ui.space()
        
        # Layout selector
        ui.html('<span class="mono" style="color: #555; font-size: 0.7rem;">LAYOUT:</span>', sanitize=False)
        ui.select(
            options=["Force", "Circular", "Hierarchical"],
            value="Force",
        ).classes("w-36").props("outlined dense dark options-dense")
    
    # Main content
    with ui.element("div").classes("forge-card w-full p-4"):
        with ui.element("div").classes("w-full").style("height: 500px;"):
            _render_graph()


def _render_no_project() -> None:
    """Render message when no project is loaded."""
    with ui.column().classes("items-center justify-center").style("min-height: 400px;"):
        ui.html('<span class="mono" style="color: #333; font-size: 3rem; margin-bottom: 16px;">[X]</span>', sanitize=False)
        ui.html('<span class="mono" style="color: #888; font-size: 1.2rem; margin-bottom: 8px;">No Project Loaded</span>', sanitize=False)
        with ui.element("div").classes("cursor-pointer px-6 py-2 rounded mt-4").style(
            "background: #00b8d4; color: #000; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;"
        ).on("click", lambda: ui.navigate.to("/")):
            ui.html('GO TO PROJECTS', sanitize=False)


def _render_graph() -> None:
    """Render the ECharts network graph."""
    try:
        graph_data = _get_graph_data()
        
        if not graph_data.get("nodes"):
            with ui.column().classes("items-center justify-center h-full"):
                ui.html('<span class="mono" style="color: #333; font-size: 2rem; margin-bottom: 16px;">[~]</span>', sanitize=False)
                ui.html('<span class="mono" style="color: #555; font-size: 0.9rem;">No relationships found</span>', sanitize=False)
                ui.html('<span class="mono" style="color: #444; font-size: 0.75rem;">Add entities and relationships to see the graph.</span>', sanitize=False)
            return
        
        # ECharts configuration
        chart_options = {
            "tooltip": {},
            "animationDurationUpdate": 1500,
            "animationEasingUpdate": "quinticInOut",
            "series": [
                {
                    "type": "graph",
                    "layout": "force",
                    "roam": True,
                    "draggable": True,
                    "data": graph_data.get("nodes", []),
                    "links": graph_data.get("edges", []),
                    "categories": [
                        {"name": "ACTOR"},
                        {"name": "POLITY"},
                        {"name": "LOCATION"},
                        {"name": "RESOURCE"},
                        {"name": "EVENT"},
                        {"name": "ABSTRACT"},
                    ],
                    "force": {
                        "repulsion": 500,
                        "edgeLength": [100, 200],
                    },
                    "emphasis": {
                        "focus": "adjacency",
                        "lineStyle": {"width": 4},
                    },
                    "label": {
                        "show": True,
                        "position": "right",
                    },
                    "lineStyle": {
                        "color": "source",
                        "curveness": 0.3,
                    },
                }
            ],
        }
        
        ui.echart(chart_options).classes("w-full h-full")
        
    except Exception as e:
        logger.error(f"Failed to render graph: {e}")
        ui.label(f"Error loading graph: {e}").classes("text-negative")


def _get_graph_data() -> dict[str, Any]:
    """Get graph data from the RelationshipsOrchestrator."""
    try:
        session = get_session()
        
        # Get entities
        entities = session.db.get_all_entities()
        relationships = session.db.get_all_relationships()
        
        # Build nodes
        type_to_category = {
            "ACTOR": 0,
            "POLITY": 1,
            "LOCATION": 2,
            "RESOURCE": 3,
            "EVENT": 4,
            "ABSTRACT": 5,
        }
        
        nodes = []
        for entity in entities:
            etype = entity.entity_type.value if hasattr(entity.entity_type, "value") else str(entity.entity_type)
            nodes.append({
                "id": entity.id,
                "name": entity.name,
                "symbolSize": 30,
                "category": type_to_category.get(etype, 5),
            })
        
        # Build edges
        edges = []
        for rel in relationships:
            edges.append({
                "source": rel.source_id,
                "target": rel.target_id,
                "label": {"show": True, "formatter": rel.label},
            })
        
        return {"nodes": nodes, "edges": edges}
        
    except Exception as e:
        logger.error(f"Failed to get graph data: {e}")
        return {"nodes": [], "edges": []}


async def _refresh_graph() -> None:
    """Refresh the graph visualization."""
    ui.notify("Refreshing graph...", type="info")
    # Force page refresh
    ui.navigate.to("/sigint")


async def _find_communities() -> None:
    """Run community detection algorithm."""
    try:
        session = get_session()
        from forge.phases.p2_relationships.orchestrator import RelationshipsOrchestrator
        
        orchestrator = RelationshipsOrchestrator(session.db)
        metrics = orchestrator.analyze_graph()
        
        ui.notify(
            f"Found {metrics.community_count} communities",
            type="positive",
        )
        
    except Exception as e:
        logger.error(f"Community detection failed: {e}")
        ui.notify(f"Analysis failed: {e}", type="negative")


async def _find_key_actors() -> None:
    """Identify key actors by centrality metrics."""
    try:
        session = get_session()
        from forge.phases.p2_relationships.orchestrator import RelationshipsOrchestrator
        
        orchestrator = RelationshipsOrchestrator(session.db)
        key_actors = orchestrator.find_key_actors(top_n=5)
        
        if key_actors:
            names = ", ".join([a.name for a in key_actors])
            ui.notify(f"Key actors: {names}", type="info")
        else:
            ui.notify("No key actors identified", type="warning")
        
    except Exception as e:
        logger.error(f"Key actor analysis failed: {e}")
        ui.notify(f"Analysis failed: {e}", type="negative")
