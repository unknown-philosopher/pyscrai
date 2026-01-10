"""
Dashboard Page - Project Overview.

Intelligence platform dashboard displaying:
- Project summary with key metrics
- Document/source overview
- Entity type breakdown
- Quick navigation to pipeline phases
"""

from __future__ import annotations

from datetime import datetime

from nicegui import ui

from forge.frontend.state import get_session, is_project_loaded
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
    
    # Project header with better organization
    with ui.column().classes("w-full mb-8"):
        with ui.row().classes("items-center gap-4 mb-2"):
            ui.html(f'<h1 class="mono" style="font-size: 1.6rem; font-weight: 600; color: #e0e0e0;">{project_name.upper()}</h1>', sanitize=False)
            ui.html('<span class="forge-badge forge-badge-active">ACTIVE</span>', sanitize=False)
        
        # Description
        desc = project.description if project and project.description else "No description provided."
        ui.html(f'<p class="mono" style="color: #666; font-size: 0.85rem;">{desc}</p>', sanitize=False)
    
    # Main grid layout - 2 columns: left (metrics/info), right (phases above quick actions)
    with ui.grid(columns=2).classes("w-full gap-6").style("grid-template-columns: 1fr 340px;"):
        # Left column - metrics and info stacked
        with ui.column().classes("gap-6"):
            _render_metrics_section()
            _render_sources_section()
        
        # Right column - pipeline phases above quick actions
        with ui.column().classes("gap-6"):
            _render_phase_progress()
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


def _render_metrics_section() -> None:
    """Render the key metrics cards."""
    ui.html('<div class="section-label mb-4">PROJECT METRICS</div>', sanitize=False)
    
    try:
        session = get_session()
        stats = session.get_stats()
        
        entity_count = stats.get("entity_count", 0)
        rel_count = stats.get("relationship_count", 0)
        doc_count = stats.get("document_count", 0)
        
    except Exception as e:
        logger.error(f"Failed to load stats: {e}")
        entity_count = 0
        rel_count = 0
        doc_count = 0
    
    with ui.row().classes("gap-4"):
        # Entities card
        with ui.element("div").classes("forge-card p-4 cursor-pointer").style(
            "min-width: 140px;"
        ).on("click", lambda: ui.navigate.to("/humint")):
            ui.html('<div class="mono" style="color: #555; font-size: 0.7rem; margin-bottom: 8px;">ENTITIES</div>', sanitize=False)
            ui.html(f'<div class="mono" style="color: #00b8d4; font-size: 2rem; font-weight: 600;">{entity_count}</div>', sanitize=False)
            ui.html('<div class="mono" style="color: #444; font-size: 0.65rem; margin-top: 4px;">View in HUMINT →</div>', sanitize=False)
        
        # Relationships card
        with ui.element("div").classes("forge-card p-4 cursor-pointer").style(
            "min-width: 140px;"
        ).on("click", lambda: ui.navigate.to("/sigint")):
            ui.html('<div class="mono" style="color: #555; font-size: 0.7rem; margin-bottom: 8px;">RELATIONSHIPS</div>', sanitize=False)
            ui.html(f'<div class="mono" style="color: #00b8d4; font-size: 2rem; font-weight: 600;">{rel_count}</div>', sanitize=False)
            ui.html('<div class="mono" style="color: #444; font-size: 0.65rem; margin-top: 4px;">View in SIGINT →</div>', sanitize=False)
        
        # Documents card
        with ui.element("div").classes("forge-card p-4 cursor-pointer").style(
            "min-width: 140px;"
        ).on("click", lambda: ui.navigate.to("/osint")):
            ui.html('<div class="mono" style="color: #555; font-size: 0.7rem; margin-bottom: 8px;">DOCUMENTS</div>', sanitize=False)
            ui.html(f'<div class="mono" style="color: #00b8d4; font-size: 2rem; font-weight: 600;">{doc_count}</div>', sanitize=False)
            ui.html('<div class="mono" style="color: #444; font-size: 0.65rem; margin-top: 4px;">View in OSINT →</div>', sanitize=False)


def _render_sources_section() -> None:
    """Render the source documents overview."""
    ui.html('<div class="section-label mb-4">PROJECT INFO</div>', sanitize=False)
    
    with ui.element("div").classes("forge-card p-4"):
        try:
            session = get_session()
            project = session.project
            
            if project:
                created = project.created_at.strftime("%Y-%m-%d %H:%M") if project.created_at else "Unknown"
                modified = project.last_modified_at.strftime("%Y-%m-%d %H:%M") if project.last_modified_at else "Unknown"
                
                with ui.column().classes("gap-3"):
                    with ui.row().classes("items-center gap-4"):
                        ui.html('<span class="mono" style="color: #555; font-size: 0.75rem; width: 80px;">CREATED:</span>', sanitize=False)
                        ui.html(f'<span class="mono" style="color: #888; font-size: 0.8rem;">{created}</span>', sanitize=False)
                    
                    with ui.row().classes("items-center gap-4"):
                        ui.html('<span class="mono" style="color: #555; font-size: 0.75rem; width: 80px;">MODIFIED:</span>', sanitize=False)
                        ui.html(f'<span class="mono" style="color: #888; font-size: 0.8rem;">{modified}</span>', sanitize=False)
                    
                    if project.template:
                        with ui.row().classes("items-center gap-4"):
                            ui.html('<span class="mono" style="color: #555; font-size: 0.75rem; width: 80px;">TEMPLATE:</span>', sanitize=False)
                            ui.html(f'<span class="mono" style="color: #888; font-size: 0.8rem;">{project.template.upper()}</span>', sanitize=False)
            else:
                ui.html('<span class="mono" style="color: #555;">No project info available.</span>', sanitize=False)
                
        except Exception as e:
            logger.error(f"Failed to load project info: {e}")
            ui.html('<span class="mono" style="color: #555;">Unable to load project info.</span>', sanitize=False)


def _render_quick_actions() -> None:
    """Render quick action buttons."""
    ui.html('<div class="section-label mb-4">QUICK ACTIONS</div>', sanitize=False)
    
    with ui.element("div").classes("forge-card p-4"):
        with ui.column().classes("gap-2 w-full"):
            # Upload documents
            with ui.element("div").classes(
                "p-3 rounded cursor-pointer w-full"
            ).style(
                "background: #1a1a1a; border: 1px solid #333; transition: all 0.15s ease;"
            ).on("click", lambda: ui.navigate.to("/osint")):
                with ui.row().classes("items-center gap-3"):
                    ui.html('<span class="mono" style="color: #00b8d4; font-size: 1rem;">+</span>', sanitize=False)
                    with ui.column():
                        ui.html('<span class="mono" style="color: #e0e0e0; font-size: 0.8rem;">Upload Documents</span>', sanitize=False)
                        ui.html('<span class="mono" style="color: #555; font-size: 0.65rem;">Add source files for extraction</span>', sanitize=False)
            
            # Add entity
            with ui.element("div").classes(
                "p-3 rounded cursor-pointer w-full"
            ).style(
                "background: #1a1a1a; border: 1px solid #333; transition: all 0.15s ease;"
            ).on("click", lambda: ui.navigate.to("/humint")):
                with ui.row().classes("items-center gap-3"):
                    ui.html('<span class="mono" style="color: #00b8d4; font-size: 1rem;">◆</span>', sanitize=False)
                    with ui.column():
                        ui.html('<span class="mono" style="color: #e0e0e0; font-size: 0.8rem;">Manage Entities</span>', sanitize=False)
                        ui.html('<span class="mono" style="color: #555; font-size: 0.65rem;">View and edit knowledge graph</span>', sanitize=False)
            
            # View network
            with ui.element("div").classes(
                "p-3 rounded cursor-pointer w-full"
            ).style(
                "background: #1a1a1a; border: 1px solid #333; transition: all 0.15s ease;"
            ).on("click", lambda: ui.navigate.to("/sigint")):
                with ui.row().classes("items-center gap-3"):
                    ui.html('<span class="mono" style="color: #00b8d4; font-size: 1rem;">⬡</span>', sanitize=False)
                    with ui.column():
                        ui.html('<span class="mono" style="color: #e0e0e0; font-size: 0.8rem;">View Network</span>', sanitize=False)
                        ui.html('<span class="mono" style="color: #555; font-size: 0.65rem;">Relationship visualization</span>', sanitize=False)
            
            # Export
            with ui.element("div").classes(
                "p-3 rounded cursor-pointer w-full"
            ).style(
                "background: #1a1a1a; border: 1px solid #333; transition: all 0.15s ease;"
            ).on("click", lambda: ui.navigate.to("/anvil")):
                with ui.row().classes("items-center gap-3"):
                    ui.html('<span class="mono" style="color: #00b8d4; font-size: 1rem;">↓</span>', sanitize=False)
                    with ui.column():
                        ui.html('<span class="mono" style="color: #e0e0e0; font-size: 0.8rem;">Export Project</span>', sanitize=False)
                        ui.html('<span class="mono" style="color: #555; font-size: 0.65rem;">Finalize and download</span>', sanitize=False)


def _render_phase_progress() -> None:
    """Render the pipeline phase progress."""
    ui.html('<div class="section-label mb-4">PIPELINE PHASES</div>', sanitize=False)
    
    with ui.element("div").classes("forge-card p-4"):
        phases = [
            ("01", "OSINT", "Document Extraction", "/osint"),
            ("02", "HUMINT", "Entity Management", "/humint"),
            ("03", "SIGINT", "Relationship Mapping", "/sigint"),
            ("04", "SYNTH", "Narrative Generation", "/synth"),
            ("05", "GEOINT", "Geographic Mapping", "/geoint"),
            ("06", "FININT", "Export & Finalize", "/anvil"),
        ]
        
        with ui.column().classes("gap-1 w-full"):
            for num, name, desc, route in phases:
                with ui.element("div").classes(
                    "p-2 rounded cursor-pointer"
                ).style(
                    "transition: all 0.15s ease;"
                ).on("click", lambda r=route: ui.navigate.to(r)):
                    with ui.row().classes("items-center gap-3"):
                        ui.html(f'<span class="mono" style="color: #444; font-size: 0.65rem; width: 16px;">{num}</span>', sanitize=False)
                        with ui.column():
                            ui.html(f'<span class="mono" style="color: #888; font-size: 0.8rem;">{name}</span>', sanitize=False)
                            ui.html(f'<span class="mono" style="color: #444; font-size: 0.6rem;">{desc}</span>', sanitize=False)
