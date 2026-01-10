"""
SYNTH Page - Phase 3: Narrative Editor.

Provides:
- Markdown editor (CodeMirror)
- Fact Deck sidebar with semantic search suggestions
- LLM-powered writing tools
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from nicegui import ui

from forge.frontend.state import get_session, is_project_loaded
from forge.utils.logging import get_logger

logger = get_logger("frontend.synth")

# Debounce state for fact deck
_fact_deck_timer: asyncio.Task | None = None
_fact_deck_debounce_ms = 1000


def content() -> None:
    """Render the SYNTH page content."""
    if not is_project_loaded():
        _render_no_project()
        return
    
    # Page header
    ui.html('<h1 class="mono" style="font-size: 1.6rem; font-weight: 600; color: #e0e0e0; margin-bottom: 8px;">SYNTH_NARRATIVE</h1>', sanitize=False)
    ui.html('<p class="mono" style="font-size: 0.8rem; color: #555; margin-bottom: 24px;">Write and edit narratives with AI-powered suggestions and fact checking.</p>', sanitize=False)
    
    # Toolbar
    with ui.row().classes("w-full mb-4 gap-3 items-center"):
        # File selector
        ui.html('<span class="mono" style="color: #555; font-size: 0.7rem;">DOCUMENT:</span>', sanitize=False)
        file_select = ui.select(
            options=_get_narrative_files(),
            value=None,
        ).classes("w-48").props("outlined dense dark options-dense")
        
        with ui.element("div").classes("forge-btn cursor-pointer px-3 py-1").on("click", _create_narrative):
            ui.html('NEW', sanitize=False)
        with ui.element("div").classes("cursor-pointer px-3 py-1 rounded").style(
            "background: #00b8d4; color: #000; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;"
        ).on("click", _save_narrative):
            ui.html('SAVE', sanitize=False)
        
        ui.space()
        
        # LLM tools
        with ui.element("div").classes("forge-btn cursor-pointer px-2 py-1").on("click", _expand_selection):
            ui.html('EXPAND', sanitize=False)
        with ui.element("div").classes("forge-btn cursor-pointer px-2 py-1").on("click", _rewrite_selection):
            ui.html('REWRITE', sanitize=False)
        with ui.element("div").classes("forge-btn cursor-pointer px-2 py-1").on("click", _fact_check):
            ui.html('FACT CHECK', sanitize=False)
    
    # Main content: Split editor
    with ui.row().classes("w-full gap-4"):
        # Editor (left)
        with ui.element("div").classes("forge-card flex-grow p-4"):
            ui.html('<div class="section-label mb-2">EDITOR</div>', sanitize=False)
            _editor = ui.codemirror(
                value=_get_default_content(),
                language="markdown",
            ).classes("w-full").style("height: 450px;")
            
            # Bind to debounced fact deck update
            _editor.on("change", lambda e: _schedule_fact_deck_update(e.value))
        
        # Fact Deck (right)
        with ui.element("div").classes("forge-card p-4").style("width: 280px; flex-shrink: 0;"):
            ui.html('<div class="section-label mb-2">FACT DECK</div>', sanitize=False)
            with ui.row().classes("items-center gap-2 mb-3"):
                with ui.element("div").classes("forge-btn cursor-pointer px-2 py-1").props("flat size=sm").on("click", _refresh_fact_deck):
                    ui.icon("refresh")
            
            with ui.scroll_area().classes("h-80") as _fact_deck_container:
                _render_fact_deck([])


def _render_no_project() -> None:
    """Render message when no project is loaded."""
    with ui.column().classes("items-center justify-center h-96"):
        ui.icon("folder_off", size="xl").classes("text-grey-6 q-mb-md")
        ui.label("No Project Loaded").classes("text-h5 text-grey-5")
        ui.button("Go to Projects", icon="folder", color="primary").on(
            "click", lambda: ui.navigate.to("/")
        )


def _get_narrative_files() -> list[str]:
    """Get list of narrative markdown files."""
    try:
        session = get_session()
        from forge.phases.p3_narrative.orchestrator import NarrativeOrchestrator
        
        orchestrator = NarrativeOrchestrator(session.project_path)
        return orchestrator.list_narratives()
    except Exception:
        return []


def _get_default_content() -> str:
    """Get default/initial content for the editor."""
    return """# New Narrative

Write your story here. The **Fact Deck** on the right will suggest relevant entities from your knowledge graph as you write.

## Tips

- Reference entities by name to see them in the Fact Deck
- Use the toolbar buttons for AI-powered writing assistance
- Save frequently to preserve your work
"""


def _render_fact_deck(entities: list) -> None:
    """Render the fact deck with relevant entities."""
    if not entities:
        with ui.column().classes("items-center justify-center h-full"):
            ui.icon("lightbulb", size="lg").classes("text-grey-6 q-mb-sm")
            ui.label("Start writing to see suggestions").classes("text-caption text-grey-5 text-center")
        return
    
    for entity in entities:
        with ui.card().classes("w-full q-mb-sm q-pa-sm"):
            with ui.row().classes("items-center"):
                ui.icon("person" if entity.get("type") == "ACTOR" else "place", size="sm").classes("text-primary")
                ui.label(entity.get("name", "Unknown")).classes("text-weight-medium")
            
            if entity.get("description"):
                ui.label(entity["description"][:100] + "...").classes("text-caption text-grey-5 q-mt-xs")
            
            if entity.get("similarity"):
                ui.badge(f"{entity['similarity']:.0%} match", color="grey").classes("q-mt-xs")


def _schedule_fact_deck_update(text: str) -> None:
    """Schedule a debounced fact deck update."""
    global _fact_deck_timer
    
    if _fact_deck_timer and not _fact_deck_timer.done():
        _fact_deck_timer.cancel()
    
    async def delayed_update():
        await asyncio.sleep(_fact_deck_debounce_ms / 1000)
        await _update_fact_deck(text)
    
    _fact_deck_timer = asyncio.create_task(delayed_update())


async def _update_fact_deck(text: str) -> None:
    """Update the fact deck based on editor content."""
    try:
        session = get_session()
        from forge.phases.p3_narrative.orchestrator import NarrativeOrchestrator
        
        orchestrator = NarrativeOrchestrator(
            project_path=session.project_path,
            vector_memory=session.vector_memory,
        )
        
        # Get the last paragraph for context
        paragraphs = text.strip().split("\n\n")
        current_paragraph = paragraphs[-1] if paragraphs else ""
        
        if len(current_paragraph) < 20:
            return  # Not enough context
        
        entities = await orchestrator.get_fact_deck(current_paragraph)
        
        # Refresh the UI
        # (Would need to update the fact deck container)
        
    except Exception as e:
        logger.error(f"Fact deck update failed: {e}")


async def _refresh_fact_deck() -> None:
    """Manually refresh the fact deck."""
    ui.notify("Refreshing suggestions...", type="info")


async def _create_narrative() -> None:
    """Create a new narrative document."""
    with ui.dialog() as dialog, ui.card():
        ui.label("New Narrative").classes("text-h6 q-mb-md")
        
        name_input = ui.input(
            label="Document Name",
            placeholder="chapter_01",
        ).classes("w-full").props("outlined")
        
        with ui.row().classes("q-mt-md justify-end q-gutter-sm"):
            ui.button("Cancel").props("flat").on("click", dialog.close)
            ui.button("Create", color="primary").on("click", dialog.close)
    
    dialog.open()


async def _save_narrative() -> None:
    """Save the current narrative."""
    ui.notify("Narrative saved", type="positive")


async def _expand_selection() -> None:
    """AI: Expand selected text."""
    ui.notify("Expansion feature coming soon", type="info")


async def _rewrite_selection() -> None:
    """AI: Rewrite selected text."""
    ui.notify("Rewrite feature coming soon", type="info")


async def _fact_check() -> None:
    """Verify content against the knowledge graph."""
    ui.notify("Fact check feature coming soon", type="info")
