"""
ANVIL Page - Phase 5: Finalize & Export.

Provides:
- Validation report (orphaned entities, missing fields)
- Export center (JSON, Markdown World Bible, SQLite backup)
- Final merge suggestions
"""

from __future__ import annotations

from datetime import datetime

from nicegui import ui

from forge.frontend.state import get_session, is_project_loaded
from forge.utils.logging import get_logger

logger = get_logger("frontend.anvil")


def content() -> None:
    """Render the ANVIL page content."""
    if not is_project_loaded():
        _render_no_project()
        return
    
    # Page header
    ui.html('<h1 class="mono" style="font-size: 1.6rem; font-weight: 600; color: #e0e0e0; margin-bottom: 8px;">FININT_EXPORT</h1>', sanitize=False)
    ui.html('<p class="mono" style="font-size: 0.8rem; color: #555; margin-bottom: 24px;">Validate data integrity and export your world to various formats.</p>', sanitize=False)
    
    with ui.row().classes("w-full gap-6"):
        # Left: Validation
        with ui.element("div").classes("forge-card p-4 flex-grow"):
            _render_validation_panel()
        
        # Right: Export
        with ui.element("div").classes("forge-card p-4").style("width: 320px; flex-shrink: 0;"):
            _render_export_panel()


def _render_no_project() -> None:
    """Render message when no project is loaded."""
    with ui.column().classes("items-center justify-center").style("min-height: 400px;"):
        ui.html('<span class="mono" style="color: #333; font-size: 3rem; margin-bottom: 16px;">[X]</span>', sanitize=False)
        ui.html('<span class="mono" style="color: #888; font-size: 1.2rem; margin-bottom: 8px;">No Project Loaded</span>', sanitize=False)
        with ui.element("div").classes("cursor-pointer px-6 py-2 rounded mt-4").style(
            "background: #00b8d4; color: #000; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;"
        ).on("click", lambda: ui.navigate.to("/")):
            ui.html('GO TO PROJECTS', sanitize=False)


def _render_validation_panel() -> None:
    """Render the validation report panel."""
    with ui.row().classes("items-center justify-between mb-4"):
        ui.html('<span class="mono" style="color: #e0e0e0; font-size: 0.9rem; font-weight: 500;">VALIDATION_REPORT</span>', sanitize=False)
        with ui.row().classes("gap-2"):
            with ui.element("div").classes("cursor-pointer px-3 py-1 rounded").style(
                "background: #00b8d4; color: #000; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;"
            ).on("click", _run_validation):
                ui.html('RUN VALIDATION', sanitize=False)
            with ui.element("div").classes("forge-btn cursor-pointer px-3 py-1").on("click", _auto_fix_issues):
                ui.html('AUTO-FIX', sanitize=False)
    
    # Issues list
    issues = _get_validation_issues()
    
    if not issues:
        with ui.row().classes("items-center q-pa-md bg-positive-1 rounded"):
            ui.icon("check_circle", size="md").classes("text-positive")
            ui.label("All validations passed! Your data is ready for export.").classes("q-ml-sm")
    else:
        ui.label(f"{len(issues)} issues found").classes("text-subtitle2 text-warning q-mb-sm")
        
        with ui.scroll_area().classes("h-80"):
            for issue in issues:
                _render_issue_card(issue)


def _render_issue_card(issue: dict) -> None:
    """Render a single validation issue."""
    severity_colors = {
        "error": "negative",
        "warning": "warning",
        "info": "info",
    }
    severity_icons = {
        "error": "error",
        "warning": "warning",
        "info": "info",
    }
    
    severity = issue.get("severity", "info")
    
    with ui.card().classes(f"w-full q-mb-sm border-left-{severity_colors[severity]}"):
        with ui.row().classes("items-center"):
            ui.icon(
                severity_icons[severity],
                size="sm",
            ).classes(f"text-{severity_colors[severity]}")
            
            with ui.column().classes("flex-grow q-ml-sm"):
                ui.label(issue.get("title", "Unknown Issue")).classes("text-weight-medium")
                ui.label(issue.get("description", "")).classes("text-caption text-grey-5")
                
                if issue.get("entity_id"):
                    ui.label(f"Entity: {issue['entity_id']}").classes("text-caption")
            
            if issue.get("auto_fixable"):
                ui.button("Fix", icon="build").props("flat size=sm").on(
                    "click", lambda i=issue: _fix_issue(i)
                )


def _render_export_panel() -> None:
    """Render the export options panel."""
    ui.html('<div class="section-label mb-4">EXPORT CENTER</div>', sanitize=False)
    
    exports = [
        {
            "id": "json",
            "icon": "{}",
            "label": "EXPORT TO JSON",
            "description": "Standard JSON format with all entities and relationships",
            "action": _export_json,
        },
        {
            "id": "markdown",
            "icon": "MD",
            "label": "WORLD BIBLE",
            "description": "Human-readable Markdown document",
            "action": _export_world_bible,
        },
        {
            "id": "sqlite",
            "icon": "DB",
            "label": "DATABASE BACKUP",
            "description": "Full SQLite backup with timestamp",
            "action": _export_database,
        },
    ]
    
    for export in exports:
        with ui.element("div").classes("p-3 rounded mb-2 cursor-pointer").style(
            "background: #111; border: 1px solid #333; transition: all 0.15s ease;"
        ).on("click", export["action"]):
            with ui.row().classes("items-center gap-3"):
                ui.html(f'<span class="mono" style="color: #00b8d4; font-size: 0.8rem; width: 24px;">{export["icon"]}</span>', sanitize=False)
                with ui.column():
                    ui.html(f'<span class="mono" style="color: #e0e0e0; font-size: 0.8rem;">{export["label"]}</span>', sanitize=False)
                    ui.html(f'<span class="mono" style="color: #555; font-size: 0.65rem;">{export["description"]}</span>', sanitize=False)
                    ui.label(export["description"]).classes("text-caption text-grey-5")
    
    ui.separator().classes("q-my-md")
    
    # Last export info
    ui.label("Export History").classes("text-subtitle2 q-mb-sm")
    ui.label("No recent exports").classes("text-caption text-grey-5")


def _get_validation_issues() -> list[dict]:
    """Get validation issues from the FinalizeOrchestrator."""
    try:
        session = get_session()
        from forge.phases.p5_finalize.orchestrator import FinalizeOrchestrator
        
        orchestrator = FinalizeOrchestrator(session.db)
        return orchestrator.get_validation_issues()
        
    except Exception as e:
        logger.error(f"Failed to get validation issues: {e}")
        return []


async def _run_validation() -> None:
    """Run full validation check."""
    ui.notify("Running validation...", type="info")
    
    try:
        session = get_session()
        from forge.phases.p5_finalize.orchestrator import FinalizeOrchestrator
        
        orchestrator = FinalizeOrchestrator(session.db)
        issues = orchestrator.validate_all()
        
        if issues:
            ui.notify(f"Found {len(issues)} issues", type="warning")
        else:
            ui.notify("All validations passed!", type="positive")
        
        # Refresh the page
        ui.navigate.to("/anvil")
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        ui.notify(f"Validation failed: {e}", type="negative")


async def _auto_fix_issues() -> None:
    """Attempt to auto-fix all fixable issues."""
    ui.notify("Auto-fixing issues...", type="info")
    # TODO: Implement auto-fix logic


async def _fix_issue(issue: dict) -> None:
    """Fix a single issue."""
    ui.notify(f"Fixing: {issue.get('title', 'issue')}", type="info")
    # TODO: Implement single issue fix


async def _export_json() -> None:
    """Export to JSON format."""
    try:
        session = get_session()
        from forge.phases.p5_finalize.exporter import Exporter
        
        exporter = Exporter(session.project_path)
        output_path = await exporter.export_json()
        
        ui.notify(f"Exported to: {output_path}", type="positive")
        
    except Exception as e:
        logger.error(f"JSON export failed: {e}")
        ui.notify(f"Export failed: {e}", type="negative")


async def _export_world_bible() -> None:
    """Export to Markdown World Bible."""
    try:
        session = get_session()
        from forge.phases.p5_finalize.exporter import Exporter
        
        exporter = Exporter(session.project_path)
        output_path = await exporter.export_world_bible()
        
        ui.notify(f"Exported to: {output_path}", type="positive")
        
    except Exception as e:
        logger.error(f"World Bible export failed: {e}")
        ui.notify(f"Export failed: {e}", type="negative")


async def _export_database() -> None:
    """Create database backup."""
    try:
        session = get_session()
        from forge.phases.p5_finalize.exporter import Exporter
        
        exporter = Exporter(session.project_path)
        output_path = await exporter.backup_database()
        
        ui.notify(f"Backup saved to: {output_path}", type="positive")
        
    except Exception as e:
        logger.error(f"Database backup failed: {e}")
        ui.notify(f"Backup failed: {e}", type="negative")
