"""
OSINT Page - Phase 0: Extraction & Sentinel.

Handles:
- Document upload and chunking visualization
- Sentinel triage: comparing new extractions vs database candidates
- Merge/reject/commit actions
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nicegui import ui

from forge.legacy_nicegui.components.file_picker import FilePicker
from forge.legacy_nicegui.state import get_session, is_project_loaded
from forge.utils.logging import get_logger

logger = get_logger("frontend.osint")


# Module state for extraction progress
_extraction_state = {
    "status": "idle",
    "progress": 0.0,
    "current_chunk": 0,
    "total_chunks": 0,
    "pending_candidates": [],
}


def content() -> None:
    """Render the OSINT page content."""
    if not is_project_loaded():
        _render_no_project()
        return
    
    # Page header
    ui.html('<h1 class="mono" style="font-size: 1.6rem; font-weight: 600; color: #e0e0e0; margin-bottom: 8px;">OSINT_EXTRACTION</h1>', sanitize=False)
    ui.html('<p class="mono" style="font-size: 0.8rem; color: #555; margin-bottom: 24px;">Upload source documents for entity extraction. Sentinel identifies potential duplicates.</p>', sanitize=False)
    
    # Resizable splitter layout
    # Note: NiceGUI doesn't have built-in splitter, so we use a flex-based layout with drag handle
    with ui.element("div").classes("w-full").style("display: flex; gap: 8px; height: calc(100vh - 300px);"):
        # Left panel: Source documents (resizable)
        with ui.element("div").classes("forge-card p-4").style("width: 320px; min-width: 250px; flex-shrink: 0; overflow-y: auto;") as left_panel:
            _render_source_panel()
        
        # Resize handle (visual separator)
        ui.html('<div style="width: 4px; background: #333; cursor: col-resize; flex-shrink: 0;" id="splitter-handle"></div>', sanitize=False)
        
        # Right panel: Sentinel triage (flexible)
        with ui.element("div").classes("forge-card p-4 flex-grow").style("overflow-y: auto;"):
            _render_sentinel_panel()


def _render_no_project() -> None:
    """Render message when no project is loaded."""
    with ui.column().classes("items-center justify-center").style("min-height: 400px;"):
        ui.html('<span class="mono" style="color: #333; font-size: 3rem; margin-bottom: 16px;">[X]</span>', sanitize=False)
        ui.html('<span class="mono" style="color: #888; font-size: 1.2rem; margin-bottom: 8px;">No Project Loaded</span>', sanitize=False)
        with ui.element("div").classes("cursor-pointer px-6 py-2 rounded mt-4").style(
            "background: #00b8d4; color: #000; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;"
        ).on("click", lambda: ui.navigate.to("/")):
            ui.html('GO TO PROJECTS', sanitize=False)


def _render_source_panel() -> None:
    """Render the source document upload panel."""
    ui.html('<div class="section-label">SOURCE DOCUMENTS</div>', sanitize=False)
    
    # File picker
    picker = FilePicker(
        on_upload=_handle_file_upload,
        multiple=True,
        label="Upload Documents",
    )
    
    ui.html('<div style="height: 1px; background: #333; margin: 16px 0;"></div>', sanitize=False)
    
    # Extraction controls
    ui.html('<div class="section-label">EXTRACTION CONTROLS</div>', sanitize=False)
    
    with ui.row().classes("gap-2 mt-3"):
        with ui.element("div").classes("cursor-pointer px-4 py-2 rounded").style(
            "background: #00b8d4; color: #000; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;"
        ).on("click", _start_extraction):
            ui.html('EXTRACT ALL', sanitize=False)
        
        with ui.element("div").classes("forge-btn cursor-pointer px-4 py-2").on("click", lambda: picker.clear()):
            ui.html('CLEAR QUEUE', sanitize=False)
    
    # Progress indicator
    ui.html('<div style="height: 1px; background: #333; margin: 16px 0;"></div>', sanitize=False)
    ui.html('<span class="mono" style="color: #555; font-size: 0.75rem;">STATUS: IDLE</span>', sanitize=False)
    ui.linear_progress(value=0).classes("w-full mt-2").style("height: 3px;")


def _render_sentinel_panel() -> None:
    """Render the Sentinel triage panel."""
    with ui.row().classes("items-center justify-between mb-4"):
        ui.html('<span class="mono" style="color: #e0e0e0; font-size: 0.9rem; font-weight: 500;">SENTINEL_TRIAGE</span>', sanitize=False)
        ui.html('<span class="forge-badge forge-badge-info">ACTIVE</span>', sanitize=False)
    
    # Split view header
    with ui.row().classes("w-full mb-3"):
        with ui.column().classes("w-1/2"):
            ui.html('<span class="mono" style="color: #555; font-size: 0.7rem;">NEW EXTRACTIONS</span>', sanitize=False)
        with ui.column().classes("w-1/2"):
            ui.html('<span class="mono" style="color: #555; font-size: 0.7rem;">DATABASE MATCHES</span>', sanitize=False)
    
    # Candidate cards
    candidates = _extraction_state.get("pending_candidates", [])
    
    if not candidates:
        with ui.column().classes("items-center justify-center h-64 w-full"):
            ui.icon("check_circle", size="xl").classes("text-grey-6 q-mb-md")
            ui.label("No pending candidates").classes("text-grey-5")
            ui.label(
                "Upload and extract documents to populate this view."
            ).classes("text-caption text-grey-6")
    else:
        with ui.scroll_area().classes("h-96 w-full"):
            for candidate in candidates:
                _render_candidate_card(candidate)


def _render_candidate_card(candidate: dict[str, Any]) -> None:
    """Render a single merge candidate card with diff highlighting."""
    new_entity = candidate.get("new_entity", {})
    db_entity = candidate.get("db_entity", {})
    similarity = candidate.get("similarity", 0.0)
    
    with ui.card().classes("w-full mb-2").style("background: #1a1a1a; border: 1px solid #333;"):
        with ui.row().classes("w-full items-start"):
            # New extraction (left) - highlight differences in green
            with ui.column().classes("w-1/2 pr-4"):
                ui.html('<span class="mono" style="color: #555; font-size: 0.7rem; text-transform: uppercase;">NEW EXTRACTION</span>', sanitize=False)
                
                # Name with diff highlighting
                new_name = new_entity.get("name", "Unknown")
                db_name = db_entity.get("name", "")
                if new_name != db_name:
                    ui.html(f'<div class="mono" style="color: #00c853; font-weight: 600; font-size: 0.9rem; margin-top: 4px; padding: 2px 4px; background: rgba(0, 200, 83, 0.1);">{new_name}</div>', sanitize=False)
                else:
                    ui.html(f'<div class="mono" style="color: #e0e0e0; font-weight: 600; font-size: 0.9rem; margin-top: 4px;">{new_name}</div>', sanitize=False)
                
                # Type
                new_type = new_entity.get("entity_type", "")
                db_type = db_entity.get("entity_type", "")
                if new_type != db_type:
                    ui.html(f'<div class="mono" style="color: #00c853; font-size: 0.7rem; margin-top: 4px; padding: 2px 4px; background: rgba(0, 200, 83, 0.1);">{new_type}</div>', sanitize=False)
                else:
                    ui.html(f'<div class="mono" style="color: #888; font-size: 0.7rem; margin-top: 4px;">{new_type}</div>', sanitize=False)
                
                # Description with diff
                new_desc = new_entity.get("description", "")[:100]
                db_desc = db_entity.get("description", "")[:100]
                if new_desc != db_desc:
                    ui.html(f'<div class="mono" style="color: #00c853; font-size: 0.75rem; margin-top: 8px; padding: 4px; background: rgba(0, 200, 83, 0.05); line-height: 1.4;">{new_desc}...</div>', sanitize=False)
                else:
                    ui.html(f'<div class="mono" style="color: #aaa; font-size: 0.75rem; margin-top: 8px; line-height: 1.4;">{new_desc}...</div>', sanitize=False)
            
            # Similarity indicator
            with ui.column().classes("items-center px-4"):
                color = "#00c853" if similarity > 0.9 else "#ffab00" if similarity > 0.8 else "#888"
                ui.html(
                    f'<div class="mono forge-badge" style="background: {color}; color: #000; padding: 4px 8px; border-radius: 2px; margin-bottom: 8px;">{similarity:.0%}</div>',
                    sanitize=False
                )
                ui.html('<span class="mono" style="color: #555; font-size: 1.2rem;">↔</span>', sanitize=False)
            
            # Database match (right) - highlight differences in red (missing in new)
            with ui.column().classes("w-1/2 pl-4"):
                ui.html('<span class="mono" style="color: #555; font-size: 0.7rem; text-transform: uppercase;">DATABASE MATCH</span>', sanitize=False)
                
                # Name with diff highlighting
                if db_name != new_name:
                    ui.html(f'<div class="mono" style="color: #ff5252; font-weight: 600; font-size: 0.9rem; margin-top: 4px; padding: 2px 4px; background: rgba(255, 82, 82, 0.1);">{db_name}</div>', sanitize=False)
                else:
                    ui.html(f'<div class="mono" style="color: #e0e0e0; font-weight: 600; font-size: 0.9rem; margin-top: 4px;">{db_name}</div>', sanitize=False)
                
                # Type
                if db_type != new_type:
                    ui.html(f'<div class="mono" style="color: #ff5252; font-size: 0.7rem; margin-top: 4px; padding: 2px 4px; background: rgba(255, 82, 82, 0.1);">{db_type}</div>', sanitize=False)
                else:
                    ui.html(f'<div class="mono" style="color: #888; font-size: 0.7rem; margin-top: 4px;">{db_type}</div>', sanitize=False)
                
                # Description with diff
                if db_desc != new_desc:
                    ui.html(f'<div class="mono" style="color: #ff5252; font-size: 0.75rem; margin-top: 8px; padding: 4px; background: rgba(255, 82, 82, 0.05); line-height: 1.4;">{db_desc}...</div>', sanitize=False)
                else:
                    ui.html(f'<div class="mono" style="color: #aaa; font-size: 0.75rem; margin-top: 8px; line-height: 1.4;">{db_desc}...</div>', sanitize=False)
        
        # Actions
        with ui.row().classes("w-full mt-4 justify-end gap-2"):
            with ui.element("div").classes("cursor-pointer px-3 py-1 rounded").style(
                "background: #00b8d4; color: #000; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;"
            ).on("click", lambda c=candidate: _approve_merge(c)):
                ui.html('MERGE', sanitize=False)
            
            with ui.element("div").classes("forge-btn cursor-pointer px-3 py-1").on("click", lambda c=candidate: _keep_both(c)):
                ui.html('KEEP BOTH', sanitize=False)
            
            with ui.element("div").classes("cursor-pointer px-3 py-1 rounded").style(
                "background: #ff5252; color: #fff; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;"
            ).on("click", lambda c=candidate: _reject_candidate(c)):
                ui.html('REJECT', sanitize=False)


async def _handle_file_upload(path: Path, content: bytes) -> None:
    """Handle uploaded file content."""
    logger.info(f"File queued for extraction: {path.name}")
    # Store content for extraction
    # This would typically save to a staging area


async def _start_extraction() -> None:
    """Start the extraction process on all queued files."""
    try:
        session = get_session()
        
        # Get the extraction orchestrator
        from forge.phases.p0_extraction.orchestrator import ExtractionOrchestrator
        
        orchestrator = ExtractionOrchestrator(
            llm_provider=session.llm,
            db_manager=session.db,
            file_manager=session.file_manager,
        )
        
        # Subscribe to progress updates
        def on_progress(progress):
            _extraction_state["status"] = progress.status.value
            _extraction_state["progress"] = progress.percent_complete
            _extraction_state["current_chunk"] = progress.current_chunk
            _extraction_state["total_chunks"] = progress.total_chunks
        
        orchestrator.subscribe(on_progress)
        
        ui.notify("Extraction started...", type="info")
        
        # TODO: Actually run extraction on queued files
        # await orchestrator.extract_from_file(file_path)
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        ui.notify(f"Extraction failed: {e}", type="negative")


async def _approve_merge(candidate: dict[str, Any]) -> None:
    """Approve a merge candidate."""
    try:
        session = get_session()
        from forge.phases.p0_extraction.sentinel import Sentinel
        
        sentinel = Sentinel(session.db, session.vector_memory)
        await sentinel.accept_merge(candidate.get("id"))
        
        ui.notify("Entities merged successfully", type="positive")
        # Refresh the view
        
    except Exception as e:
        logger.error(f"Merge failed: {e}")
        ui.notify(f"Merge failed: {e}", type="negative")


async def _keep_both(candidate: dict[str, Any]) -> None:
    """Keep both entities (reject merge, create new)."""
    try:
        session = get_session()
        from forge.phases.p0_extraction.sentinel import Sentinel
        
        sentinel = Sentinel(session.db, session.vector_memory)
        await sentinel.reject_merge(candidate.get("id"))
        
        ui.notify("Both entities retained", type="info")
        
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        ui.notify(f"Operation failed: {e}", type="negative")


async def _reject_candidate(candidate: dict[str, Any]) -> None:
    """Reject/discard a candidate."""
    try:
        # Remove from pending list
        _extraction_state["pending_candidates"] = [
            c for c in _extraction_state["pending_candidates"]
            if c.get("id") != candidate.get("id")
        ]
        
        ui.notify("Candidate discarded", type="warning")
        
    except Exception as e:
        logger.error(f"Rejection failed: {e}")
        ui.notify(f"Rejection failed: {e}", type="negative")
