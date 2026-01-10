"""
Entity Grid Component.

AG Grid wrapper for displaying and editing entities.
Supports selection tracking for Assistant context awareness.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from nicegui import ui

from forge.legacy_nicegui.state import get_session, set_selected_entities
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.core.models.entity import Entity

logger = get_logger("frontend.entity_grid")


class EntityGrid:
    """AG Grid wrapper for entity display and editing."""
    
    DEFAULT_COLUMNS = [
        {"field": "id", "headerName": "ID", "width": 120, "sortable": True},
        {"field": "name", "headerName": "Name", "flex": 1, "sortable": True, "filter": True, "editable": True},
        {"field": "entity_type", "headerName": "Type", "width": 120, "sortable": True, "filter": True},
        {"field": "description", "headerName": "Description", "flex": 2, "editable": True},
        {"field": "tags", "headerName": "Tags", "width": 150, "valueFormatter": "value ? value.join(', ') : ''"},
    ]
    
    def __init__(
        self,
        on_select: Callable[[list["Entity"]], None] | None = None,
        on_edit: Callable[["Entity"], None] | None = None,
        entity_type_filter: str | None = None,
    ) -> None:
        """Initialize the entity grid.
        
        Args:
            on_select: Callback when selection changes
            on_edit: Callback when a row is double-clicked for editing
            entity_type_filter: Optional filter to show only specific entity types
        """
        self.on_select = on_select
        self.on_edit = on_edit
        self.entity_type_filter = entity_type_filter
        self._entities: list["Entity"] = []
        self._grid: ui.aggrid | None = None
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        """Build the grid UI."""
        self._grid = ui.aggrid({
            "columnDefs": self.DEFAULT_COLUMNS,
            "rowData": [],
            "rowSelection": "multiple",
            "animateRows": True,
            "pagination": True,
            "paginationPageSize": 50,
            "defaultColDef": {
                "resizable": True,
            },
        }).classes("w-full h-96")
        
        # Wire up events
        self._grid.on("selectionChanged", self._on_selection_changed)
        self._grid.on("cellDoubleClicked", self._on_cell_double_clicked)
        self._grid.on("cellValueChanged", self._on_cell_value_changed)
    
    async def refresh(self) -> None:
        """Refresh grid data from database."""
        try:
            session = get_session()
            
            if self.entity_type_filter:
                self._entities = session.db.get_entities_by_type(self.entity_type_filter)
            else:
                self._entities = session.db.get_all_entities()
            
            # Convert to row data
            row_data = [self._entity_to_row(e) for e in self._entities]
            self._grid.options["rowData"] = row_data
            self._grid.update()
            
            logger.debug(f"Grid refreshed with {len(self._entities)} entities")
            
        except Exception as e:
            logger.error(f"Failed to refresh grid: {e}")
    
    def _entity_to_row(self, entity: "Entity") -> dict[str, Any]:
        """Convert an Entity to a grid row dictionary."""
        return {
            "id": entity.id,
            "name": entity.name,
            "entity_type": entity.entity_type.value if hasattr(entity.entity_type, "value") else str(entity.entity_type),
            "description": entity.description,
            "tags": entity.tags,
            "aliases": entity.aliases,
            "_entity": entity,  # Keep reference for callbacks
        }
    
    def _on_selection_changed(self, e: Any) -> None:
        """Handle row selection changes."""
        selected_rows = e.args.get("selectedRows", []) if e.args else []
        selected_entities = [
            row.get("_entity") for row in selected_rows 
            if row.get("_entity")
        ]
        
        # Update global context
        set_selected_entities(selected_entities)
        
        # Call custom callback
        if self.on_select:
            self.on_select(selected_entities)
    
    def _on_cell_double_clicked(self, e: Any) -> None:
        """Handle cell double-click for editing."""
        if self.on_edit and e.args:
            row_data = e.args.get("data", {})
            entity = row_data.get("_entity")
            if entity:
                self.on_edit(entity)
    
    async def _on_cell_value_changed(self, e: Any) -> None:
        """Handle inline cell edits."""
        if not e.args:
            return
        
        row_data = e.args.get("data", {})
        field = e.args.get("colId")
        new_value = e.args.get("newValue")
        entity = row_data.get("_entity")
        
        if not entity or not field:
            return
        
        try:
            # Update entity
            setattr(entity, field, new_value)
            
            # Save to database
            session = get_session()
            session.db.save_entity(entity)
            
            logger.info(f"Entity {entity.id} updated: {field} = {new_value}")
            
        except Exception as e:
            logger.error(f"Failed to save entity edit: {e}")
            ui.notify(f"Failed to save: {e}", type="negative")
    
    def get_selected(self) -> list["Entity"]:
        """Get currently selected entities."""
        return [
            e for e in self._entities 
            if e.id in self._get_selected_ids()
        ]
    
    def _get_selected_ids(self) -> set[str]:
        """Get IDs of selected rows."""
        # This would need async implementation with grid API
        return set()
