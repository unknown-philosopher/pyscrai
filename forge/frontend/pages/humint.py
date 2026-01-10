"""
HUMINT Page - Phase 1: Entity Management.

Displays:
- AG Grid with all entities
- Detail editor drawer
- Prefab schema form generation
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from forge.frontend.components.entity_grid import EntityGrid
from forge.frontend.state import get_session, is_project_loaded
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.core.models.entity import Entity

logger = get_logger("frontend.humint")


def content() -> None:
    """Render the HUMINT page content."""
    if not is_project_loaded():
        _render_no_project()
        return
    
    # Page header
    ui.html('<h1 class="mono" style="font-size: 1.6rem; font-weight: 600; color: #e0e0e0; margin-bottom: 8px;">HUMINT_ENTITIES</h1>', sanitize=False)
    ui.html('<p class="mono" style="font-size: 0.8rem; color: #555; margin-bottom: 24px;">View, edit, and manage all entities in the knowledge graph.</p>', sanitize=False)
    
    # Toolbar
    with ui.row().classes("w-full mb-4 items-center gap-3"):
        # Filter by type
        ui.html('<span class="mono" style="color: #555; font-size: 0.7rem;">TYPE:</span>', sanitize=False)
        type_filter = ui.select(
            options=["All", "ACTOR", "POLITY", "LOCATION", "REGION", "RESOURCE", "EVENT", "ABSTRACT"],
            value="All",
        ).classes("w-40").props("outlined dense dark options-dense")
        
        # Search
        ui.html('<span class="mono" style="color: #555; font-size: 0.7rem; margin-left: 16px;">SEARCH:</span>', sanitize=False)
        search_input = ui.input(
            placeholder="Enter query...",
        ).classes("flex-grow").props("outlined dense dark")
        
        # Actions
        with ui.element("div").classes("cursor-pointer px-4 py-2 rounded").style(
            "background: #00b8d4; color: #000; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;"
        ).on("click", _create_entity):
            ui.html('+ NEW ENTITY', sanitize=False)
        
        with ui.element("div").classes("forge-btn cursor-pointer px-4 py-2").on("click", _refresh_grid):
            ui.html('REFRESH', sanitize=False)
    
    # Entity grid
    grid = EntityGrid(
        on_select=_on_entity_select,
        on_edit=_open_entity_editor,
    )
    
    # Initial load
    ui.timer(0.1, lambda: grid.refresh(), once=True)


def _render_no_project() -> None:
    """Render message when no project is loaded."""
    with ui.column().classes("items-center justify-center").style("min-height: 400px;"):
        ui.html('<span class="mono" style="color: #333; font-size: 3rem; margin-bottom: 16px;">[X]</span>', sanitize=False)
        ui.html('<span class="mono" style="color: #888; font-size: 1.2rem; margin-bottom: 8px;">No Project Loaded</span>', sanitize=False)
        with ui.element("div").classes("cursor-pointer px-6 py-2 rounded mt-4").style(
            "background: #00b8d4; color: #000; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;"
        ).on("click", lambda: ui.navigate.to("/")):
            ui.html('GO TO PROJECTS', sanitize=False)


def _on_entity_select(entities: list["Entity"]) -> None:
    """Handle entity selection changes."""
    count = len(entities)
    if count == 1:
        logger.debug(f"Selected entity: {entities[0].name}")
    elif count > 1:
        logger.debug(f"Selected {count} entities")


def _open_entity_editor(entity: "Entity") -> None:
    """Open the entity detail editor drawer."""
    with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl"):
        ui.label(f"Edit: {entity.name}").classes("text-h6 q-mb-md")
        
        # Basic fields
        name_input = ui.input(
            label="Name",
            value=entity.name,
        ).classes("w-full").props("outlined")
        
        desc_input = ui.textarea(
            label="Description",
            value=entity.description,
        ).classes("w-full q-mt-sm").props("outlined")
        
        # Type selector
        type_select = ui.select(
            label="Entity Type",
            options=["ACTOR", "POLITY", "LOCATION", "REGION", "RESOURCE", "EVENT", "ABSTRACT"],
            value=entity.entity_type.value if hasattr(entity.entity_type, "value") else str(entity.entity_type),
        ).classes("w-full q-mt-sm").props("outlined")
        
        # Tags
        tags_input = ui.input(
            label="Tags (comma-separated)",
            value=", ".join(entity.tags) if entity.tags else "",
        ).classes("w-full q-mt-sm").props("outlined")
        
        # Aliases
        aliases_input = ui.input(
            label="Aliases (comma-separated)",
            value=", ".join(entity.aliases) if entity.aliases else "",
        ).classes("w-full q-mt-sm").props("outlined")
        
        # Attributes (JSON editor)
        ui.label("Custom Attributes (JSON)").classes("text-subtitle2 q-mt-md")
        import json
        attrs_editor = ui.codemirror(
            value=json.dumps(entity.attributes, indent=2) if entity.attributes else "{}",
            language="json",
        ).classes("w-full h-40")
        
        # Actions
        with ui.row().classes("w-full q-mt-lg justify-end q-gutter-sm"):
            ui.button("Cancel", color="grey").props("flat").on("click", dialog.close)
            ui.button("Save", icon="save", color="primary").on(
                "click",
                lambda: _save_entity(
                    entity,
                    name_input.value,
                    desc_input.value,
                    type_select.value,
                    tags_input.value,
                    aliases_input.value,
                    attrs_editor.value,
                    dialog,
                )
            )
    
    dialog.open()


async def _save_entity(
    entity: "Entity",
    name: str,
    description: str,
    entity_type: str,
    tags_str: str,
    aliases_str: str,
    attrs_json: str,
    dialog,
) -> None:
    """Save entity changes to the database."""
    import json
    
    try:
        # Update entity fields
        entity.name = name
        entity.description = description
        entity.tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        entity.aliases = [a.strip() for a in aliases_str.split(",") if a.strip()]
        
        # Parse attributes JSON
        try:
            entity.attributes = json.loads(attrs_json) if attrs_json else {}
        except json.JSONDecodeError as e:
            ui.notify(f"Invalid JSON in attributes: {e}", type="negative")
            return
        
        # Save to database
        session = get_session()
        session.db.save_entity(entity)
        
        ui.notify(f"Saved: {entity.name}", type="positive")
        dialog.close()
        
    except Exception as e:
        logger.error(f"Failed to save entity: {e}")
        ui.notify(f"Failed to save: {e}", type="negative")


async def _create_entity() -> None:
    """Open dialog to create a new entity."""
    with ui.dialog() as dialog, ui.card().classes("w-full max-w-lg"):
        ui.label("Create New Entity").classes("text-h6 q-mb-md")
        
        name_input = ui.input(label="Name").classes("w-full").props("outlined")
        
        type_select = ui.select(
            label="Entity Type",
            options=["ACTOR", "POLITY", "LOCATION", "REGION", "RESOURCE", "EVENT", "ABSTRACT"],
            value="ACTOR",
        ).classes("w-full q-mt-sm").props("outlined")
        
        desc_input = ui.textarea(label="Description").classes("w-full q-mt-sm").props("outlined")
        
        with ui.row().classes("w-full q-mt-lg justify-end q-gutter-sm"):
            ui.button("Cancel", color="grey").props("flat").on("click", dialog.close)
            ui.button("Create", icon="add", color="primary").on(
                "click",
                lambda: _do_create_entity(
                    name_input.value,
                    type_select.value,
                    desc_input.value,
                    dialog,
                )
            )
    
    dialog.open()


async def _do_create_entity(name: str, entity_type: str, description: str, dialog) -> None:
    """Actually create the entity."""
    if not name.strip():
        ui.notify("Name is required", type="warning")
        return
    
    try:
        from forge.core.models.entity import Entity, EntityType, create_entity
        
        entity = create_entity(
            entity_type=EntityType(entity_type),
            name=name.strip(),
            description=description.strip(),
        )
        
        session = get_session()
        session.db.save_entity(entity)
        
        ui.notify(f"Created: {entity.name}", type="positive")
        dialog.close()
        
    except Exception as e:
        logger.error(f"Failed to create entity: {e}")
        ui.notify(f"Failed to create: {e}", type="negative")


def _refresh_grid() -> None:
    """Refresh the entity grid."""
    ui.notify("Refreshing...", type="info")
    # The grid would be refreshed via its refresh() method
