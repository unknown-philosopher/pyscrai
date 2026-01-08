"""Phase 2: LOOM - Graph Visualization with networkx + tk.Canvas.

This module provides an interactive graph canvas for visualizing
and editing entity relationships. Features include:
- Node dragging
- Edge creation via drag-connect
- Right-click context menus
- Edge weight visualization
- Multiple layout algorithms
"""

from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass, field
from enum import Enum
from tkinter import ttk
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from pyscrai_core import Entity, Relationship

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False


class LayoutAlgorithm(Enum):
    """Available graph layout algorithms."""
    SPRING = "spring"
    CIRCULAR = "circular"
    SHELL = "shell"
    KAMADA_KAWAI = "kamada_kawai"
    SPECTRAL = "spectral"


@dataclass
class NodeStyle:
    """Visual style for a graph node."""
    fill: str = "#2d5aa0"
    outline: str = "#4a7bc8"
    text_color: str = "white"
    width: int = 80  # Rectangle width
    height: int = 40  # Rectangle height
    font: tuple = ("Segoe UI", 9)
    selected_outline: str = "#ffd700"  # Gold for selection
    hover_fill: str = "#3d6ab0"


@dataclass
class EdgeStyle:
    """Visual style for a graph edge."""
    color: str = "#6c757d"  # Lighter gray for dark background
    width: int = 2
    selected_color: str = "#ffd700"  # Gold for selection
    arrow_size: int = 10


@dataclass
class GraphNode:
    """A node in the graph visualization."""
    id: str
    label: str
    x: float = 0.0
    y: float = 0.0
    entity_type: str = ""
    canvas_id: Optional[int] = None
    text_id: Optional[int] = None
    data: dict = field(default_factory=dict)


@dataclass 
class GraphEdge:
    """An edge in the graph visualization."""
    source_id: str
    target_id: str
    relationship_type: str
    weight: float = 1.0
    canvas_id: Optional[int] = None
    label_id: Optional[int] = None
    data: dict = field(default_factory=dict)


class GraphCanvas(tk.Canvas):
    """Interactive graph canvas for relationship visualization.
    
    Features:
    - Pan and zoom with mouse
    - Node dragging
    - Edge creation by dragging between nodes
    - Right-click context menus
    - Multiple layout algorithms via networkx
    """
    
    # Node color mapping by entity type (optimized for dark background)
    # Format: (fill_color, text_color, outline_color)
    TYPE_COLORS = {
        "actor": ("#2d5aa0", "white", "#4a7bc8"),  # Blue for actors
        "character": ("#2d5aa0", "white", "#4a7bc8"),
        "person": ("#2d5aa0", "white", "#4a7bc8"),
        "location": ("#2d7d4e", "white", "#4aaf6e"),  # Green for locations
        "place": ("#2d7d4e", "white", "#4aaf6e"),
        "polity": ("#b8860b", "white", "#daa520"),  # Gold for polities/organizations
        "organization": ("#b8860b", "white", "#daa520"),
        "faction": ("#b8860b", "white", "#daa520"),
        "item": ("#7b2cbf", "white", "#9d4edd"),  # Purple for items
        "object": ("#7b2cbf", "white", "#9d4edd"),
        "event": ("#c1121f", "white", "#e63946"),  # Red for events
        "concept": ("#f77f00", "white", "#fcbf49"),  # Orange for concepts
        "resource": ("#6c757d", "white", "#adb5bd"),  # Gray for resources
    }
    
    # Default node style (blue for unknown types)
    DEFAULT_NODE_COLOR = ("#2d5aa0", "white", "#4a7bc8")
    
    def __init__(
        self,
        parent: tk.Widget,
        on_node_selected: Optional[Callable[[str], None]] = None,
        on_edge_selected: Optional[Callable[[str, str], None]] = None,
        on_node_double_click: Optional[Callable[[str], None]] = None,
        on_edge_created: Optional[Callable[[str, str], None]] = None,
        on_node_moved: Optional[Callable[[str, float, float], None]] = None,
        **kwargs
    ):
        """Initialize the graph canvas.
        
        Args:
            parent: Parent widget
            on_node_selected: Callback when a node is selected
            on_edge_selected: Callback when an edge is selected
            on_node_double_click: Callback when a node is double-clicked
            on_edge_created: Callback when a new edge is created by dragging
            on_node_moved: Callback when a node is moved
        """
        # Set dark background
        kwargs.setdefault("bg", "#1e1e1e")
        kwargs.setdefault("highlightthickness", 0)
        
        super().__init__(parent, **kwargs)
        
        # Callbacks
        self.on_node_selected = on_node_selected
        self.on_edge_selected = on_edge_selected
        self.on_node_double_click = on_node_double_click
        self.on_edge_created = on_edge_created
        self.on_node_moved = on_node_moved
        
        # Graph data
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        
        # Selection state
        self.selected_node: Optional[str] = None
        self.selected_edge: Optional[Tuple[str, str]] = None
        self.hovered_node: Optional[str] = None
        
        # Dragging state
        self.dragging_node: Optional[str] = None
        self.drag_start: Optional[Tuple[float, float]] = None
        self.creating_edge: Optional[str] = None  # source_id when creating edge
        self.edge_preview_id: Optional[int] = None
        
        # Cluster colors (node_id -> color)
        self.cluster_colors: Dict[str, str] = {}
        
        # Pan/zoom state
        self.pan_offset = (0.0, 0.0)
        self.zoom_level = 1.0
        self.panning = False
        self.pan_start: Optional[Tuple[float, float]] = None
        
        # Styles
        self.node_style = NodeStyle()
        self.edge_style = EdgeStyle()
        
        # Bind events
        self._bind_events()
    
    def _bind_events(self) -> None:
        """Bind mouse and keyboard events."""
        # Mouse events
        self.bind("<Button-1>", self._on_click)
        self.bind("<Double-Button-1>", self._on_double_click)
        self.bind("<Button-3>", self._on_right_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Motion>", self._on_motion)
        
        # Pan with middle mouse or Ctrl+drag
        self.bind("<Button-2>", self._start_pan)
        self.bind("<B2-Motion>", self._do_pan)
        self.bind("<ButtonRelease-2>", self._end_pan)
        
        # Zoom with scroll wheel
        self.bind("<MouseWheel>", self._on_scroll)
        self.bind("<Button-4>", lambda e: self._zoom(1.1))  # Linux scroll up
        self.bind("<Button-5>", lambda e: self._zoom(0.9))  # Linux scroll down
        
        # Keyboard
        self.bind("<Delete>", self._on_delete)
        self.bind("<Escape>", self._on_escape)
    
    def load_from_entities(
        self,
        entities: List["Entity"],
        relationships: List["Relationship"],
        layout: LayoutAlgorithm = LayoutAlgorithm.SPRING
    ) -> None:
        """Load graph from entity and relationship data.
        
        Args:
            entities: List of Entity objects
            relationships: List of Relationship objects
            layout: Layout algorithm to use
        """
        self.nodes.clear()
        self.edges.clear()
        
        # Create nodes from entities
        for entity in entities:
            name = entity.descriptor.name if hasattr(entity, "descriptor") else entity.id
            entity_type = ""
            if hasattr(entity, "descriptor") and hasattr(entity.descriptor, "entity_type"):
                entity_type = entity.descriptor.entity_type.value if hasattr(entity.descriptor.entity_type, "value") else str(entity.descriptor.entity_type)
            
            self.nodes[entity.id] = GraphNode(
                id=entity.id,
                label=name,
                entity_type=entity_type.lower(),
                data={"entity": entity}
            )
        
        # Create edges from relationships
        for rel in relationships:
            if rel.source_id in self.nodes and rel.target_id in self.nodes:
                rel_type = ""
                if hasattr(rel, "relationship_type"):
                    rel_type = rel.relationship_type.value if hasattr(rel.relationship_type, "value") else str(rel.relationship_type)
                
                self.edges.append(GraphEdge(
                    source_id=rel.source_id,
                    target_id=rel.target_id,
                    relationship_type=rel_type,
                    data={"relationship": rel}
                ))
        
        # Calculate layout
        self._calculate_layout(layout)
        
        # Render
        self.render()
    
    def _calculate_layout(self, algorithm: LayoutAlgorithm) -> None:
        """Calculate node positions using networkx layout algorithm."""
        if not HAS_NETWORKX or not self.nodes:
            # Fallback to simple grid layout
            self._grid_layout()
            return
        
        # Build networkx graph
        G = nx.Graph()
        for node_id in self.nodes:
            G.add_node(node_id)
        
        for edge in self.edges:
            G.add_edge(edge.source_id, edge.target_id, weight=edge.weight)
        
        # Calculate layout
        try:
            if algorithm == LayoutAlgorithm.SPRING:
                pos = nx.spring_layout(G, k=2.0, iterations=50, seed=42)
            elif algorithm == LayoutAlgorithm.CIRCULAR:
                pos = nx.circular_layout(G)
            elif algorithm == LayoutAlgorithm.SHELL:
                pos = nx.shell_layout(G)
            elif algorithm == LayoutAlgorithm.KAMADA_KAWAI:
                pos = nx.kamada_kawai_layout(G)
            elif algorithm == LayoutAlgorithm.SPECTRAL:
                pos = nx.spectral_layout(G)
            else:
                pos = nx.spring_layout(G)
        except Exception:
            # Fallback to spring layout
            pos = nx.spring_layout(G, seed=42)
        
        # Get canvas dimensions
        width = self.winfo_width() or 800
        height = self.winfo_height() or 600
        
        # Scale positions to canvas (with padding)
        padding = 100
        for node_id, (x, y) in pos.items():
            # networkx returns positions in [-1, 1] range
            scaled_x = padding + (x + 1) * (width - 2 * padding) / 2
            scaled_y = padding + (y + 1) * (height - 2 * padding) / 2
            
            self.nodes[node_id].x = scaled_x
            self.nodes[node_id].y = scaled_y
    
    def _grid_layout(self) -> None:
        """Simple grid layout fallback when networkx is unavailable."""
        width = self.winfo_width() or 800
        height = self.winfo_height() or 600
        
        n = len(self.nodes)
        if n == 0:
            return
        
        cols = max(1, int(math.sqrt(n)))
        rows = math.ceil(n / cols)
        
        cell_width = width / (cols + 1)
        cell_height = height / (rows + 1)
        
        for i, node_id in enumerate(self.nodes):
            col = i % cols
            row = i // cols
            
            self.nodes[node_id].x = (col + 1) * cell_width
            self.nodes[node_id].y = (row + 1) * cell_height
    
    def render(self) -> None:
        """Render the graph to the canvas."""
        self.delete("all")
        
        # Draw edges first (behind nodes)
        for edge in self.edges:
            self._draw_edge(edge)
        
        # Draw nodes
        for node in self.nodes.values():
            self._draw_node(node)
        
        # Draw edge preview if creating
        if self.creating_edge and self.edge_preview_id:
            pass  # Already drawn in drag handler
    
    def _draw_node(self, node: GraphNode) -> None:
        """Draw a single node as a rectangle."""
        x, y = self._to_canvas_coords(node.x, node.y)
        w = self.node_style.width * self.zoom_level
        h = self.node_style.height * self.zoom_level
        
        # Get color - use cluster color if set, otherwise use entity type color
        if node.id in self.cluster_colors:
            fill = self.cluster_colors[node.id]
            text_color = "white"  # White text on colored background
            default_outline = self._darken_color(fill)
        else:
            color_info = self.TYPE_COLORS.get(node.entity_type, self.DEFAULT_NODE_COLOR)
            fill = color_info[0]
            text_color = color_info[1]
            default_outline = color_info[2] if len(color_info) > 2 else self.node_style.outline
        
        # Adjust for selection/hover
        if node.id == self.selected_node:
            outline = self.node_style.selected_outline
            outline_width = 3
        elif node.id == self.hovered_node:
            # Lighten the fill color for hover (add ~30% brightness)
            # Simple approach: increase RGB values by 20%
            fill = self._lighten_color(fill)
            outline = default_outline
            outline_width = 2
        else:
            outline = default_outline
            outline_width = 2
        
        # Draw rectangle
        node.canvas_id = self.create_rectangle(
            x - w/2, y - h/2, x + w/2, y + h/2,
            fill=fill,
            outline=outline,
            width=outline_width,
            tags=("node", f"node_{node.id}")
        )
        
        # Draw label
        label = node.label if len(node.label) <= 12 else node.label[:10] + "..."
        node.text_id = self.create_text(
            x, y,
            text=label,
            fill=text_color,
            font=self.node_style.font,
            tags=("node_text", f"text_{node.id}")
        )
    
    def _draw_edge(self, edge: GraphEdge) -> None:
        """Draw a single edge."""
        source = self.nodes.get(edge.source_id)
        target = self.nodes.get(edge.target_id)
        
        if not source or not target:
            return
        
        x1, y1 = self._to_canvas_coords(source.x, source.y)
        x2, y2 = self._to_canvas_coords(target.x, target.y)
        
        # Calculate arrow endpoint (stop at rectangle edge)
        w = self.node_style.width * self.zoom_level / 2
        h = self.node_style.height * self.zoom_level / 2
        angle = math.atan2(y2 - y1, x2 - x1)
        
        # Calculate intersection with rectangle (simplified: use larger dimension)
        r = max(w, h)
        x2_adj = x2 - r * math.cos(angle)
        y2_adj = y2 - r * math.sin(angle)
        x1_adj = x1 + r * math.cos(angle)
        y1_adj = y1 + r * math.sin(angle)
        
        # Check if selected
        is_selected = self.selected_edge == (edge.source_id, edge.target_id)
        color = self.edge_style.selected_color if is_selected else self.edge_style.color
        width = (self.edge_style.width + 1) if is_selected else self.edge_style.width
        
        # Draw line with arrow
        edge.canvas_id = self.create_line(
            x1_adj, y1_adj, x2_adj, y2_adj,
            fill=color,
            width=width * self.zoom_level,
            arrow=tk.LAST,
            arrowshape=(
                self.edge_style.arrow_size * self.zoom_level,
                self.edge_style.arrow_size * 1.2 * self.zoom_level,
                self.edge_style.arrow_size * 0.5 * self.zoom_level
            ),
            tags=("edge", f"edge_{edge.source_id}_{edge.target_id}")
        )
        
        # Draw relationship type label at midpoint
        if edge.relationship_type:
            mid_x = (x1_adj + x2_adj) / 2
            mid_y = (y1_adj + y2_adj) / 2
            
            # Offset label slightly
            offset = 10
            perp_angle = angle + math.pi / 2
            mid_x += offset * math.cos(perp_angle)
            mid_y += offset * math.sin(perp_angle)
            
            edge.label_id = self.create_text(
                mid_x, mid_y,
                text=edge.relationship_type,
                fill="#b0b0b0",  # Lighter gray for better visibility on dark background
                font=("Segoe UI", 8),
                tags=("edge_label",)
            )
    
    def _to_canvas_coords(self, x: float, y: float) -> Tuple[float, float]:
        """Convert graph coordinates to canvas coordinates."""
        return (
            x * self.zoom_level + self.pan_offset[0],
            y * self.zoom_level + self.pan_offset[1]
        )
    
    def _from_canvas_coords(self, cx: float, cy: float) -> Tuple[float, float]:
        """Convert canvas coordinates to graph coordinates."""
        return (
            (cx - self.pan_offset[0]) / self.zoom_level,
            (cy - self.pan_offset[1]) / self.zoom_level
        )
    
    def _find_node_at(self, x: float, y: float) -> Optional[str]:
        """Find a node at the given canvas coordinates."""
        gx, gy = self._from_canvas_coords(x, y)
        
        w = self.node_style.width / 2
        h = self.node_style.height / 2
        
        for node_id, node in self.nodes.items():
            dx = abs(node.x - gx)
            dy = abs(node.y - gy)
            
            # Check if point is within rectangle bounds
            if dx <= w and dy <= h:
                return node_id
        
        return None
    
    def _on_click(self, event: tk.Event) -> None:
        """Handle left click."""
        node_id = self._find_node_at(event.x, event.y)
        
        # If in edge creation mode, don't change selected_node or start dragging
        # The edge will be created on release
        if self.creating_edge:
            # Still allow dragging for edge preview, but don't change selected_node
            if node_id:
                self.drag_start = (event.x, event.y)
            return
        
        if node_id:
            self.selected_node = node_id
            self.selected_edge = None
            self.dragging_node = node_id
            self.drag_start = (event.x, event.y)
            
            if self.on_node_selected:
                self.on_node_selected(node_id)
        else:
            # Check for edge selection
            self.selected_node = None
            self.selected_edge = None
        
        self.render()
    
    def _on_double_click(self, event: tk.Event) -> None:
        """Handle double click."""
        node_id = self._find_node_at(event.x, event.y)
        
        if node_id and self.on_node_double_click:
            self.on_node_double_click(node_id)
    
    def _on_right_click(self, event: tk.Event) -> None:
        """Handle right click for context menu."""
        node_id = self._find_node_at(event.x, event.y)
        
        menu = tk.Menu(self, tearoff=0)
        
        if node_id:
            # Use default parameter trick to properly capture node_id in lambda
            menu.add_command(
                label=f"Edit {self.nodes[node_id].label}",
                command=lambda nid=node_id: self.on_node_double_click(nid) if self.on_node_double_click else None
            )
            menu.add_separator()
            menu.add_command(
                label="Create Relationship From This Node",
                command=lambda nid=node_id: self._start_edge_creation(nid)
            )
        else:
            menu.add_command(label="Reset Layout", command=lambda: self._calculate_layout(LayoutAlgorithm.SPRING) or self.render())
            menu.add_command(label="Circular Layout", command=lambda: self._calculate_layout(LayoutAlgorithm.CIRCULAR) or self.render())
        
        menu.tk_popup(event.x_root, event.y_root)
    
    def _on_drag(self, event: tk.Event) -> None:
        """Handle mouse drag."""
        # If in edge creation mode, show edge preview
        if self.creating_edge and self.selected_node:
            # Draw edge preview from selected node to current mouse position
            source = self.nodes.get(self.selected_node)
            if source:
                x1, y1 = self._to_canvas_coords(source.x, source.y)
                
                if self.edge_preview_id:
                    self.delete(self.edge_preview_id)
                
                self.edge_preview_id = self.create_line(
                    x1, y1, event.x, event.y,
                    fill="#87CEEB",  # Sky blue for edge preview
                    width=2,
                    dash=(5, 5),
                    arrow=tk.LAST
                )
        elif self.dragging_node and self.drag_start:
            # Move the node
            dx = (event.x - self.drag_start[0]) / self.zoom_level
            dy = (event.y - self.drag_start[1]) / self.zoom_level
            
            node = self.nodes.get(self.dragging_node)
            if node:
                node.x += dx
                node.y += dy
                
                if self.on_node_moved:
                    self.on_node_moved(self.dragging_node, node.x, node.y)
            
            self.drag_start = (event.x, event.y)
            self.render()
    
    def _on_release(self, event: tk.Event) -> None:
        """Handle mouse release."""
        if self.creating_edge and self.selected_node:
            # Check if we released on another node
            target_id = self._find_node_at(event.x, event.y)
            
            if target_id and target_id != self.selected_node:
                # Create the edge
                if self.on_edge_created:
                    self.on_edge_created(self.selected_node, target_id)
            # If clicked on empty space or same node, cancel edge creation
            # (user can right-click again to restart)
            
            # Clean up
            if self.edge_preview_id:
                self.delete(self.edge_preview_id)
                self.edge_preview_id = None
            
            # Exit edge creation mode after creating edge or clicking elsewhere
            self.creating_edge = False
            # Keep selected_node for visual feedback, but clear it on next click
        
        self.dragging_node = None
        self.drag_start = None
        self.render()  # Re-render to update selection state
    
    def _on_motion(self, event: tk.Event) -> None:
        """Handle mouse motion for hover effects."""
        node_id = self._find_node_at(event.x, event.y)
        
        if node_id != self.hovered_node:
            self.hovered_node = node_id
            self.render()
    
    def _start_pan(self, event: tk.Event) -> None:
        """Start panning the canvas."""
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
            self._zoom(1.1)
        else:
            self._zoom(0.9)
    
    def _zoom(self, factor: float) -> None:
        """Zoom the canvas."""
        old_zoom = self.zoom_level
        self.zoom_level = max(0.2, min(5.0, self.zoom_level * factor))
        
        if self.zoom_level != old_zoom:
            self.render()
    
    def _on_delete(self, event: tk.Event) -> None:
        """Handle delete key."""
        # Could implement node/edge deletion here
        pass
    
    def _on_escape(self, event: tk.Event) -> None:
        """Handle escape key."""
        self.creating_edge = False
        if self.edge_preview_id:
            self.delete(self.edge_preview_id)
            self.edge_preview_id = None
        
        self.selected_node = None
        self.selected_edge = None
        self.render()
    
    def _start_edge_creation(self, node_id: str) -> None:
        """Start creating an edge from a node.
        
        Sets the node as selected and enters edge creation mode.
        User can then click on another node to create a relationship.
        """
        self.selected_node = node_id
        self.creating_edge = True
        # Re-render to show visual feedback (selected node will be highlighted)
        self.render()
    
    def set_layout(self, layout_positions: Dict[str, Tuple[float, float]]) -> None:
        """Set node positions from an external layout.
        
        Args:
            layout_positions: Dict mapping node ID to (x, y) position
        """
        for node_id, (x, y) in layout_positions.items():
            if node_id in self.nodes:
                self.nodes[node_id].x = x
                self.nodes[node_id].y = y
        
        self.render()
    
    def get_layout(self) -> Dict[str, Tuple[float, float]]:
        """Get current node positions.
        
        Returns:
            Dict mapping node ID to (x, y) position
        """
        return {
            node_id: (node.x, node.y)
            for node_id, node in self.nodes.items()
        }
    
    def add_edge(self, source_id: str, target_id: str, relationship_type: str = "") -> None:
        """Add an edge to the graph.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            relationship_type: Type of relationship
        """
        if source_id in self.nodes and target_id in self.nodes:
            self.edges.append(GraphEdge(
                source_id=source_id,
                target_id=target_id,
                relationship_type=relationship_type
            ))
            self.render()
    
    def remove_edge(self, source_id: str, target_id: str) -> None:
        """Remove an edge from the graph."""
        self.edges = [
            e for e in self.edges
            if not (e.source_id == source_id and e.target_id == target_id)
        ]
        self.render()
    
    def _darken_color(self, hex_color: str, factor: float = 0.7) -> str:
        """Darken a hex color.
        
        Args:
            hex_color: Hex color string (e.g., "#FF6B6B")
            factor: Darkening factor (0.0-1.0)
            
        Returns:
            Darkened hex color string
        """
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
        
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _darken_color(self, hex_color: str, factor: float = 0.7) -> str:
        """Darken a hex color.
        
        Args:
            hex_color: Hex color string (e.g., "#FF6B6B")
            factor: Darkening factor (0.0-1.0)
            
        Returns:
            Darkened hex color string
        """
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
        
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _lighten_color(self, hex_color: str) -> str:
        """Lighten a hex color by ~20% for hover effect.
        
        Args:
            hex_color: Hex color string (e.g., "#2d5aa0")
            
        Returns:
            Lightened hex color string
        """
        # Remove # if present
        hex_color = hex_color.lstrip('#')
        
        # Convert to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Lighten by 20% (but cap at 255)
        r = min(255, int(r * 1.2))
        g = min(255, int(g * 1.2))
        b = min(255, int(b * 1.2))
        
        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def center_view(self) -> None:
        """Center the view on the graph."""
        if not self.nodes:
            return
        
        # Calculate bounding box
        min_x = min(n.x for n in self.nodes.values())
        max_x = max(n.x for n in self.nodes.values())
        min_y = min(n.y for n in self.nodes.values())
        max_y = max(n.y for n in self.nodes.values())
        
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        canvas_center_x = self.winfo_width() / 2
        canvas_center_y = self.winfo_height() / 2
        
        self.pan_offset = (
            canvas_center_x - center_x * self.zoom_level,
            canvas_center_y - center_y * self.zoom_level
        )
        
        self.render()
    
    def clear_node_colors(self) -> None:
        """Clear cluster/node color overrides and restore default entity type colors."""
        self.cluster_colors.clear()
        self.render()

