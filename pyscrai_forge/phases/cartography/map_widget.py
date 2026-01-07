"""Phase 4: CARTOGRAPHY - Map Canvas Widget.

This module provides an interactive grid map canvas for placing
entities with drag-and-drop, region drawing, and visualization.
"""

from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import ttk
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from pyscrai_core import Entity


@dataclass
class MapEntity:
    """An entity placed on the map."""
    id: str
    name: str
    x: float = 0.0
    y: float = 0.0
    entity_type: str = ""
    canvas_id: Optional[int] = None
    label_id: Optional[int] = None
    data: dict = field(default_factory=dict)


@dataclass
class MapRegion:
    """A region boundary on the map."""
    name: str
    x: float
    y: float
    width: float
    height: float
    color: str = "#404060"
    canvas_id: Optional[int] = None
    label_id: Optional[int] = None


class MapCanvas(tk.Canvas):
    """Interactive grid map canvas for entity placement.
    
    Features:
    - Grid background
    - Entity icons with drag-to-position
    - Region boundaries (rectangles)
    - Pan and zoom
    - Coordinate display
    """
    
    # Entity type icons (simple shapes)
    ENTITY_SHAPES = {
        "location": "square",
        "place": "square",
        "character": "circle",
        "person": "circle",
        "organization": "diamond",
        "faction": "diamond",
        "item": "triangle",
        "object": "triangle",
        "event": "star",
    }
    
    ENTITY_COLORS = {
        "location": "#4aff9e",
        "place": "#4aff9e",
        "character": "#4a9eff",
        "person": "#4a9eff",
        "organization": "#ff9e4a",
        "faction": "#ff9e4a",
        "item": "#9e4aff",
        "object": "#9e4aff",
        "event": "#ff4a9e",
    }
    
    def __init__(
        self,
        parent: tk.Widget,
        grid_size: int = 50,
        on_entity_selected: Optional[Callable[[str], None]] = None,
        on_entity_moved: Optional[Callable[[str, float, float], None]] = None,
        on_entity_double_click: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        """Initialize the map canvas.
        
        Args:
            parent: Parent widget
            grid_size: Size of grid cells in pixels
            on_entity_selected: Callback when entity is selected
            on_entity_moved: Callback when entity is moved
            on_entity_double_click: Callback when entity is double-clicked
        """
        kwargs.setdefault("bg", "#1a1a2e")
        kwargs.setdefault("highlightthickness", 0)
        
        super().__init__(parent, **kwargs)
        
        # Callbacks
        self.on_entity_selected = on_entity_selected
        self.on_entity_moved = on_entity_moved
        self.on_entity_double_click = on_entity_double_click
        
        # Grid settings
        self.grid_size = grid_size
        self.show_grid = True
        self.show_coordinates = True
        
        # Data
        self.entities: Dict[str, MapEntity] = {}
        self.regions: List[MapRegion] = []
        
        # State
        self.selected_entity: Optional[str] = None
        self.dragging_entity: Optional[str] = None
        self.drag_offset: Tuple[float, float] = (0, 0)
        
        # Pan/zoom
        self.pan_offset = (0.0, 0.0)
        self.zoom_level = 1.0
        self.panning = False
        self.pan_start: Optional[Tuple[float, float]] = None
        
        # Coordinate label
        self.coord_text_id: Optional[int] = None
        
        # Bind events
        self._bind_events()
        
        # Initial render
        self.after(100, self.render)
    
    def _bind_events(self) -> None:
        """Bind mouse and keyboard events."""
        self.bind("<Button-1>", self._on_click)
        self.bind("<Double-Button-1>", self._on_double_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Motion>", self._on_motion)
        
        # Pan with middle mouse
        self.bind("<Button-2>", self._start_pan)
        self.bind("<B2-Motion>", self._do_pan)
        self.bind("<ButtonRelease-2>", self._end_pan)
        
        # Zoom with scroll
        self.bind("<MouseWheel>", self._on_scroll)
        
        # Right-click context menu
        self.bind("<Button-3>", self._on_right_click)
    
    def load_entities(self, entities: List["Entity"]) -> None:
        """Load entities onto the map.
        
        Args:
            entities: List of Entity objects
        """
        self.entities.clear()
        
        for entity in entities:
            name = entity.descriptor.name if hasattr(entity, "descriptor") else entity.id
            entity_type = ""
            if hasattr(entity, "descriptor") and hasattr(entity.descriptor, "entity_type"):
                entity_type = entity.descriptor.entity_type.value if hasattr(entity.descriptor.entity_type, "value") else ""
            
            self.entities[entity.id] = MapEntity(
                id=entity.id,
                name=name,
                entity_type=entity_type.lower(),
                data={"entity": entity}
            )
        
        self.render()
    
    def set_positions(self, positions: Dict[str, Tuple[float, float]]) -> None:
        """Set entity positions.
        
        Args:
            positions: Dict mapping entity ID to (x, y) position
        """
        for entity_id, (x, y) in positions.items():
            if entity_id in self.entities:
                self.entities[entity_id].x = x
                self.entities[entity_id].y = y
        
        self.render()
    
    def get_positions(self) -> Dict[str, Tuple[float, float]]:
        """Get current entity positions.
        
        Returns:
            Dict mapping entity ID to (x, y) position
        """
        return {
            entity_id: (entity.x, entity.y)
            for entity_id, entity in self.entities.items()
        }
    
    def add_region(
        self,
        name: str,
        x: float,
        y: float,
        width: float,
        height: float,
        color: str = "#404060"
    ) -> None:
        """Add a region boundary.
        
        Args:
            name: Region name
            x, y: Top-left corner
            width, height: Size
            color: Fill color
        """
        self.regions.append(MapRegion(
            name=name,
            x=x, y=y,
            width=width, height=height,
            color=color
        ))
        self.render()
    
    def clear_regions(self) -> None:
        """Clear all regions."""
        self.regions.clear()
        self.render()
    
    def render(self) -> None:
        """Render the map."""
        self.delete("all")
        
        # Draw grid
        if self.show_grid:
            self._draw_grid()
        
        # Draw regions (behind entities)
        for region in self.regions:
            self._draw_region(region)
        
        # Draw entities
        for entity in self.entities.values():
            self._draw_entity(entity)
        
        # Coordinate display
        if self.show_coordinates:
            self._draw_coordinate_display()
    
    def _draw_grid(self) -> None:
        """Draw the background grid."""
        width = self.winfo_width() or 800
        height = self.winfo_height() or 600
        
        grid_color = "#2a2a3e"
        
        # Calculate grid offset for panning
        offset_x = self.pan_offset[0] % (self.grid_size * self.zoom_level)
        offset_y = self.pan_offset[1] % (self.grid_size * self.zoom_level)
        
        cell_size = self.grid_size * self.zoom_level
        
        # Vertical lines
        x = offset_x
        while x < width:
            self.create_line(x, 0, x, height, fill=grid_color, tags="grid")
            x += cell_size
        
        # Horizontal lines
        y = offset_y
        while y < height:
            self.create_line(0, y, width, y, fill=grid_color, tags="grid")
            y += cell_size
    
    def _draw_region(self, region: MapRegion) -> None:
        """Draw a region boundary."""
        x, y = self._to_canvas_coords(region.x, region.y)
        w = region.width * self.zoom_level
        h = region.height * self.zoom_level
        
        # Semi-transparent fill
        region.canvas_id = self.create_rectangle(
            x, y, x + w, y + h,
            fill=region.color,
            outline="#606080",
            width=2,
            stipple="gray25",
            tags=("region", f"region_{region.name}")
        )
        
        # Label
        region.label_id = self.create_text(
            x + 5, y + 5,
            text=region.name,
            fill="#a0a0c0",
            font=("Segoe UI", 10, "bold"),
            anchor=tk.NW,
            tags=("region_label",)
        )
    
    def _draw_entity(self, entity: MapEntity) -> None:
        """Draw an entity on the map."""
        x, y = self._to_canvas_coords(entity.x, entity.y)
        size = 20 * self.zoom_level
        
        # Get shape and color
        shape = self.ENTITY_SHAPES.get(entity.entity_type, "circle")
        color = self.ENTITY_COLORS.get(entity.entity_type, "#888888")
        
        # Check if selected
        is_selected = entity.id == self.selected_entity
        outline_color = "#ffcc00" if is_selected else "#ffffff"
        outline_width = 3 if is_selected else 1
        
        # Draw shape
        if shape == "circle":
            entity.canvas_id = self.create_oval(
                x - size, y - size, x + size, y + size,
                fill=color, outline=outline_color, width=outline_width,
                tags=("entity", f"entity_{entity.id}")
            )
        elif shape == "square":
            entity.canvas_id = self.create_rectangle(
                x - size, y - size, x + size, y + size,
                fill=color, outline=outline_color, width=outline_width,
                tags=("entity", f"entity_{entity.id}")
            )
        elif shape == "diamond":
            points = [x, y - size, x + size, y, x, y + size, x - size, y]
            entity.canvas_id = self.create_polygon(
                points,
                fill=color, outline=outline_color, width=outline_width,
                tags=("entity", f"entity_{entity.id}")
            )
        elif shape == "triangle":
            points = [x, y - size, x + size, y + size, x - size, y + size]
            entity.canvas_id = self.create_polygon(
                points,
                fill=color, outline=outline_color, width=outline_width,
                tags=("entity", f"entity_{entity.id}")
            )
        else:
            # Default circle
            entity.canvas_id = self.create_oval(
                x - size, y - size, x + size, y + size,
                fill=color, outline=outline_color, width=outline_width,
                tags=("entity", f"entity_{entity.id}")
            )
        
        # Label
        label = entity.name if len(entity.name) <= 12 else entity.name[:10] + "..."
        entity.label_id = self.create_text(
            x, y + size + 10,
            text=label,
            fill="white",
            font=("Segoe UI", 8),
            tags=("entity_label", f"label_{entity.id}")
        )
    
    def _draw_coordinate_display(self) -> None:
        """Draw coordinate display in corner."""
        width = self.winfo_width() or 800
        
        self.coord_text_id = self.create_text(
            width - 10, 10,
            text="X: 0  Y: 0",
            fill="#606060",
            font=("Consolas", 9),
            anchor=tk.NE,
            tags=("coord_display",)
        )
    
    def _to_canvas_coords(self, x: float, y: float) -> Tuple[float, float]:
        """Convert map coordinates to canvas coordinates."""
        return (
            x * self.zoom_level + self.pan_offset[0],
            y * self.zoom_level + self.pan_offset[1]
        )
    
    def _from_canvas_coords(self, cx: float, cy: float) -> Tuple[float, float]:
        """Convert canvas coordinates to map coordinates."""
        return (
            (cx - self.pan_offset[0]) / self.zoom_level,
            (cy - self.pan_offset[1]) / self.zoom_level
        )
    
    def _find_entity_at(self, x: float, y: float) -> Optional[str]:
        """Find an entity at the given canvas coordinates."""
        mx, my = self._from_canvas_coords(x, y)
        
        for entity_id, entity in self.entities.items():
            dx = entity.x - mx
            dy = entity.y - my
            dist = math.sqrt(dx * dx + dy * dy)
            
            if dist <= 20:  # Entity radius
                return entity_id
        
        return None
    
    def _on_click(self, event: tk.Event) -> None:
        """Handle left click."""
        entity_id = self._find_entity_at(event.x, event.y)
        
        if entity_id:
            self.selected_entity = entity_id
            self.dragging_entity = entity_id
            
            # Store offset from entity center
            entity = self.entities[entity_id]
            cx, cy = self._to_canvas_coords(entity.x, entity.y)
            self.drag_offset = (event.x - cx, event.y - cy)
            
            if self.on_entity_selected:
                self.on_entity_selected(entity_id)
        else:
            self.selected_entity = None
        
        self.render()
    
    def _on_double_click(self, event: tk.Event) -> None:
        """Handle double-click."""
        entity_id = self._find_entity_at(event.x, event.y)
        
        if entity_id and self.on_entity_double_click:
            self.on_entity_double_click(entity_id)
    
    def _on_drag(self, event: tk.Event) -> None:
        """Handle mouse drag."""
        if self.dragging_entity:
            entity = self.entities.get(self.dragging_entity)
            if entity:
                # Update position
                new_x, new_y = self._from_canvas_coords(
                    event.x - self.drag_offset[0],
                    event.y - self.drag_offset[1]
                )
                
                # Snap to grid (optional)
                # new_x = round(new_x / self.grid_size) * self.grid_size
                # new_y = round(new_y / self.grid_size) * self.grid_size
                
                entity.x = new_x
                entity.y = new_y
                
                self.render()
    
    def _on_release(self, event: tk.Event) -> None:
        """Handle mouse release."""
        if self.dragging_entity:
            entity = self.entities.get(self.dragging_entity)
            if entity and self.on_entity_moved:
                self.on_entity_moved(self.dragging_entity, entity.x, entity.y)
        
        self.dragging_entity = None
        self.drag_offset = (0, 0)
    
    def _on_motion(self, event: tk.Event) -> None:
        """Handle mouse motion."""
        # Update coordinate display
        if self.show_coordinates:
            mx, my = self._from_canvas_coords(event.x, event.y)
            if self.coord_text_id:
                self.itemconfig(
                    self.coord_text_id,
                    text=f"X: {int(mx)}  Y: {int(my)}"
                )
    
    def _start_pan(self, event: tk.Event) -> None:
        """Start panning."""
        self.panning = True
        self.pan_start = (event.x, event.y)
    
    def _do_pan(self, event: tk.Event) -> None:
        """Pan the canvas."""
        if self.panning and self.pan_start:
            dx = event.x - self.pan_start[0]
            dy = event.y - self.pan_start[1]
            
            self.pan_offset = (
                self.pan_offset[0] + dx,
                self.pan_offset[1] + dy
            )
            
            self.pan_start = (event.x, event.y)
            self.render()
    
    def _end_pan(self, event: tk.Event) -> None:
        """Stop panning."""
        self.panning = False
        self.pan_start = None
    
    def _on_scroll(self, event: tk.Event) -> None:
        """Handle mouse wheel zoom."""
        if event.delta > 0:
            factor = 1.1
        else:
            factor = 0.9
        
        old_zoom = self.zoom_level
        self.zoom_level = max(0.2, min(5.0, self.zoom_level * factor))
        
        if self.zoom_level != old_zoom:
            self.render()
    
    def _on_right_click(self, event: tk.Event) -> None:
        """Handle right-click context menu."""
        entity_id = self._find_entity_at(event.x, event.y)
        
        menu = tk.Menu(self, tearoff=0)
        
        if entity_id:
            entity = self.entities[entity_id]
            menu.add_command(label=f"Edit {entity.name}", command=lambda: self.on_entity_double_click(entity_id) if self.on_entity_double_click else None)
            menu.add_separator()
            menu.add_command(label="Center on Entity", command=lambda: self._center_on_entity(entity_id))
        else:
            mx, my = self._from_canvas_coords(event.x, event.y)
            menu.add_command(label=f"Position: ({int(mx)}, {int(my)})")
            menu.add_separator()
            menu.add_command(label="Reset View", command=self._reset_view)
            menu.add_command(label="Toggle Grid", command=self._toggle_grid)
        
        menu.tk_popup(event.x_root, event.y_root)
    
    def _center_on_entity(self, entity_id: str) -> None:
        """Center the view on an entity."""
        entity = self.entities.get(entity_id)
        if not entity:
            return
        
        width = self.winfo_width() / 2
        height = self.winfo_height() / 2
        
        self.pan_offset = (
            width - entity.x * self.zoom_level,
            height - entity.y * self.zoom_level
        )
        
        self.render()
    
    def _reset_view(self) -> None:
        """Reset pan and zoom."""
        self.pan_offset = (0.0, 0.0)
        self.zoom_level = 1.0
        self.render()
    
    def _toggle_grid(self) -> None:
        """Toggle grid visibility."""
        self.show_grid = not self.show_grid
        self.render()
    
    def snap_to_grid(self, entity_id: str) -> None:
        """Snap an entity to the nearest grid point."""
        entity = self.entities.get(entity_id)
        if entity:
            entity.x = round(entity.x / self.grid_size) * self.grid_size
            entity.y = round(entity.y / self.grid_size) * self.grid_size
            self.render()
    
    def snap_all_to_grid(self) -> None:
        """Snap all entities to grid."""
        for entity in self.entities.values():
            entity.x = round(entity.x / self.grid_size) * self.grid_size
            entity.y = round(entity.y / self.grid_size) * self.grid_size
        self.render()

