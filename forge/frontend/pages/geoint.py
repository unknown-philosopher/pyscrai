"""
GEOINT Page - Phase 4: Cartography.

Displays:
- Leaflet map with entity markers
- Draggable markers for coordinate updates
- Support for custom map images (fantasy worlds)
"""

from __future__ import annotations

from typing import Any

from nicegui import ui

from forge.frontend.state import get_session, is_project_loaded
from forge.utils.logging import get_logger

logger = get_logger("frontend.geoint")


def content() -> None:
    """Render the GEOINT page content."""
    if not is_project_loaded():
        _render_no_project()
        return
    
    # Page header
    ui.html('<h1 class="mono" style="font-size: 1.6rem; font-weight: 600; color: #e0e0e0; margin-bottom: 8px;">GEOINT_CARTOGRAPHY</h1>', sanitize=False)
    ui.html('<p class="mono" style="font-size: 0.8rem; color: #555; margin-bottom: 24px;">Visualize and manage entity locations on the map.</p>', sanitize=False)
    
    # Toolbar
    with ui.row().classes("w-full mb-4 gap-3 items-center"):
        # Map source selector
        ui.html('<span class="mono" style="color: #555; font-size: 0.7rem;">SOURCE:</span>', sanitize=False)
        map_source = ui.select(
            options=["OpenStreetMap", "Local Image"],
            value="OpenStreetMap",
        ).classes("w-40").props("outlined dense dark options-dense")
        
        # Layer toggles
        ui.html('<span class="mono" style="color: #555; font-size: 0.7rem; margin-left: 16px;">LAYERS:</span>', sanitize=False)
        ui.checkbox("Actors", value=True).classes("ml-2").props("dense dark")
        ui.checkbox("Locations", value=True).props("dense dark")
        ui.checkbox("Regions", value=True).props("dense dark")
        
        ui.space()
        
        with ui.element("div").classes("forge-btn cursor-pointer px-3 py-1").on("click", _refresh_map):
            ui.html('REFRESH', sanitize=False)
        with ui.element("div").classes("forge-btn cursor-pointer px-3 py-1").on("click", _upload_map_image):
            ui.html('UPLOAD MAP', sanitize=False)
    
    # Map container
    with ui.element("div").classes("forge-card w-full p-2"):
        _render_map()
    
    # Entity list with coordinates
    with ui.expansion("ENTITIES WITH COORDINATES").classes("w-full mt-4").props("dense dark"):
        _render_coordinate_list()


def _render_no_project() -> None:
    """Render message when no project is loaded."""
    with ui.column().classes("items-center justify-center").style("min-height: 400px;"):
        ui.html('<span class="mono" style="color: #333; font-size: 3rem; margin-bottom: 16px;">[X]</span>', sanitize=False)
        ui.html('<span class="mono" style="color: #888; font-size: 1.2rem; margin-bottom: 8px;">No Project Loaded</span>', sanitize=False)
        with ui.element("div").classes("cursor-pointer px-6 py-2 rounded mt-4").style(
            "background: #00b8d4; color: #000; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;"
        ).on("click", lambda: ui.navigate.to("/")):
            ui.html('GO TO PROJECTS', sanitize=False)


def _render_map() -> None:
    """Render the Leaflet map with entity markers."""
    try:
        entities = _get_map_entities()
        
        # Create Leaflet map
        map_widget = ui.leaflet(center=(0, 0), zoom=2).classes("w-full h-96")
        
        # Add markers for entities with coordinates
        for entity in entities:
            coords = entity.get("coordinates")
            if coords and len(coords) == 2:
                marker = map_widget.marker(latlng=coords)
                
                # Bind popup with entity info
                marker.bind_popup(f"""
                    <b>{entity.get('name', 'Unknown')}</b><br>
                    <small>{entity.get('entity_type', '')}</small><br>
                    <em>{entity.get('description', '')[:100]}...</em>
                """)
                
                # Make marker draggable and handle updates
                # Note: Full drag handling requires custom JS
        
        if not entities:
            with ui.column().classes("absolute-center"):
                ui.label("No entities with coordinates").classes("text-grey-5")
                ui.label("Add coordinates to entities in HUMINT phase").classes("text-caption text-grey-6")
        
    except Exception as e:
        logger.error(f"Failed to render map: {e}")
        ui.label(f"Error loading map: {e}").classes("text-negative")


def _get_map_entities() -> list[dict[str, Any]]:
    """Get entities that have coordinates."""
    try:
        session = get_session()
        from forge.phases.p4_map.orchestrator import MapOrchestrator
        
        orchestrator = MapOrchestrator(session.db)
        entities = orchestrator.get_map_entities()
        
        return [
            {
                "id": e.id,
                "name": e.name,
                "entity_type": e.entity_type.value if hasattr(e.entity_type, "value") else str(e.entity_type),
                "description": e.description,
                "coordinates": e.coordinates,
                "layer": e.layer.value if hasattr(e.layer, "value") else str(e.layer),
            }
            for e in entities
        ]
        
    except Exception as e:
        logger.error(f"Failed to get map entities: {e}")
        return []


def _render_coordinate_list() -> None:
    """Render list of entities with their coordinates."""
    entities = _get_map_entities()
    
    if not entities:
        ui.label("No entities with coordinates").classes("text-grey-5")
        return
    
    # Table of entities
    columns = [
        {"name": "name", "label": "Name", "field": "name", "sortable": True},
        {"name": "type", "label": "Type", "field": "entity_type"},
        {"name": "lat", "label": "Latitude", "field": lambda e: e["coordinates"][0] if e.get("coordinates") else "-"},
        {"name": "lng", "label": "Longitude", "field": lambda e: e["coordinates"][1] if e.get("coordinates") else "-"},
        {"name": "layer", "label": "Layer", "field": "layer"},
    ]
    
    ui.table(
        columns=columns,
        rows=entities,
        row_key="id",
    ).classes("w-full")


async def _refresh_map() -> None:
    """Refresh the map view."""
    ui.notify("Refreshing map...", type="info")
    ui.navigate.to("/geoint")


async def _upload_map_image() -> None:
    """Upload a custom map image for fantasy worlds."""
    with ui.dialog() as dialog, ui.card().classes("w-96"):
        ui.label("Upload Map Image").classes("text-h6 q-mb-md")
        
        ui.markdown(
            "Upload a custom map image for fantasy/fictional worlds. "
            "The image will use a flat X/Y coordinate system (CRS.Simple)."
        ).classes("text-body2 text-grey-5 q-mb-md")
        
        ui.upload(
            label="Select Image",
            on_upload=lambda e: _handle_map_upload(e, dialog),
        ).props("accept='.jpg,.jpeg,.png,.webp'").classes("w-full")
        
        with ui.row().classes("q-mt-md justify-end"):
            ui.button("Cancel").props("flat").on("click", dialog.close)
    
    dialog.open()


async def _handle_map_upload(event, dialog) -> None:
    """Handle map image upload."""
    try:
        # Save the image to the project directory
        session = get_session()
        map_path = session.project_path / "map.png"
        
        content = event.content.read()
        map_path.write_bytes(content)
        
        ui.notify("Map image uploaded successfully", type="positive")
        dialog.close()
        
    except Exception as e:
        logger.error(f"Map upload failed: {e}")
        ui.notify(f"Upload failed: {e}", type="negative")


async def _update_entity_coordinates(entity_id: str, lat: float, lng: float) -> None:
    """Update entity coordinates after marker drag."""
    try:
        session = get_session()
        from forge.phases.p4_map.orchestrator import MapOrchestrator
        
        orchestrator = MapOrchestrator(session.db)
        await orchestrator.update_entity_coordinates(entity_id, lat, lng)
        
        ui.notify("Location updated", type="positive")
        
    except Exception as e:
        logger.error(f"Coordinate update failed: {e}")
        ui.notify(f"Update failed: {e}", type="negative")
