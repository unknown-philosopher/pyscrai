"""Phase 4: CARTOGRAPHY - Spatial Anchoring UI Panel.

This module provides the main UI panel for the Cartography phase,
combining the map widget with position editing tools.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Tuple

from pyscrai_forge.phases.cartography.map_widget import MapCanvas

if TYPE_CHECKING:
    from pyscrai_core import Entity, Relationship


class CartographyPanel(ttk.Frame):
    """Main panel for the Cartography phase - Spatial Anchoring.
    
    Features:
    - Interactive grid map
    - Entity placement via drag-and-drop
    - Region management
    - Position suggestions via CartographerAgent
    - Staging to spatial_metadata.json
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        project_path: Optional[Path] = None,
        callbacks: Optional[dict[str, Callable]] = None,
        **kwargs
    ):
        """Initialize the Cartography panel.
        
        Args:
            parent: Parent widget
            project_path: Path to the current project
            callbacks: Dictionary of callback functions
        """
        super().__init__(parent, **kwargs)
        
        self.project_path = project_path
        self.callbacks = callbacks or {}
        
        # Data
        self.entities: List["Entity"] = []
        self.relationships: List["Relationship"] = []
        self.positions: Dict[str, Tuple[float, float]] = {}
        
        # UI components
        self.map_canvas: Optional[MapCanvas] = None
        self.entity_list: Optional[ttk.Treeview] = None
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        """Build the Cartography phase UI."""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        ttk.Label(
            header_frame,
            text="Phase 4: CARTOGRAPHY",
            font=("Segoe UI", 16, "bold")
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            header_frame,
            text="Spatial Anchoring & Map Placement",
            font=("Segoe UI", 11),
            foreground="gray"
        ).pack(side=tk.LEFT, padx=(15, 0))
        
        # Main content - horizontal split
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left: Map canvas
        map_frame = ttk.Frame(main_paned)
        main_paned.add(map_frame, weight=3)
        
        self._build_map_panel(map_frame)
        
        # Right: Entity list and controls
        right_frame = ttk.Frame(main_paned, width=280)
        right_frame.pack_propagate(False)
        main_paned.add(right_frame, weight=0)
        
        self._build_controls_panel(right_frame)
        
        # Bottom action bar
        self._build_action_bar()
    
    def _build_map_panel(self, parent: ttk.Frame) -> None:
        """Build the map visualization panel."""
        # Toolbar
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(toolbar, text="Map View", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y, pady=2)
        
        ttk.Button(
            toolbar,
            text="Auto Layout",
            command=self._on_auto_layout,
            width=10
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar,
            text="Snap to Grid",
            command=self._on_snap_to_grid,
            width=10
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar,
            text="Reset View",
            command=lambda: self.map_canvas._reset_view() if self.map_canvas else None,
            width=10
        ).pack(side=tk.LEFT, padx=2)
        
        # Map canvas
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.map_canvas = MapCanvas(
            canvas_frame,
            grid_size=50,
            on_entity_selected=self._on_entity_selected,
            on_entity_moved=self._on_entity_moved,
            on_entity_double_click=self._on_entity_double_click
        )
        self.map_canvas.pack(fill=tk.BOTH, expand=True)
    
    def _build_controls_panel(self, parent: ttk.Frame) -> None:
        """Build the controls and entity list panel."""
        # Position info
        pos_frame = ttk.LabelFrame(parent, text="Selected Entity", padding=10)
        pos_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.selected_label = ttk.Label(pos_frame, text="None selected")
        self.selected_label.pack(anchor=tk.W)
        
        pos_inputs = ttk.Frame(pos_frame)
        pos_inputs.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(pos_inputs, text="X:").pack(side=tk.LEFT)
        self.x_var = tk.StringVar(value="0")
        self.x_entry = ttk.Entry(pos_inputs, textvariable=self.x_var, width=8)
        self.x_entry.pack(side=tk.LEFT, padx=(2, 10))
        
        ttk.Label(pos_inputs, text="Y:").pack(side=tk.LEFT)
        self.y_var = tk.StringVar(value="0")
        self.y_entry = ttk.Entry(pos_inputs, textvariable=self.y_var, width=8)
        self.y_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            pos_inputs,
            text="Set",
            command=self._on_set_position,
            width=5
        ).pack(side=tk.LEFT, padx=5)
        
        # Entity list
        entity_frame = ttk.LabelFrame(parent, text="Entities", padding=10)
        entity_frame.pack(fill=tk.BOTH, expand=True)
        
        # Filter by type
        filter_frame = ttk.Frame(entity_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT)
        self.filter_var = tk.StringVar(value="all")
        filter_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.filter_var,
            values=["all", "location", "character", "organization", "item", "event"],
            state="readonly",
            width=12
        )
        filter_combo.pack(side=tk.LEFT, padx=5)
        filter_combo.bind("<<ComboboxSelected>>", self._on_filter_change)
        
        # Treeview
        tree_frame = ttk.Frame(entity_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.entity_list = ttk.Treeview(
            tree_frame,
            columns=("name", "type", "pos"),
            show="headings",
            selectmode=tk.BROWSE
        )
        
        self.entity_list.heading("name", text="Name")
        self.entity_list.heading("type", text="Type")
        self.entity_list.heading("pos", text="Position")
        
        self.entity_list.column("name", width=100)
        self.entity_list.column("type", width=60)
        self.entity_list.column("pos", width=80)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.entity_list.yview)
        self.entity_list.configure(yscrollcommand=scrollbar.set)
        
        self.entity_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.entity_list.bind("<<TreeviewSelect>>", self._on_list_select)
        self.entity_list.bind("<Double-1>", self._on_list_double_click)
        
        # Region controls
        region_frame = ttk.LabelFrame(parent, text="Regions", padding=10)
        region_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            region_frame,
            text="Add Region",
            command=self._on_add_region
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            region_frame,
            text="Clear Regions",
            command=lambda: self.map_canvas.clear_regions() if self.map_canvas else None
        ).pack(side=tk.LEFT, padx=2)
    
    def _build_action_bar(self) -> None:
        """Build the bottom action bar."""
        action_frame = ttk.Frame(self)
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Left: Phase info
        ttk.Label(
            action_frame,
            text=f"Project: {self.project_path.name if self.project_path else 'None'}",
            font=("Segoe UI", 9, "italic"),
            foreground="gray"
        ).pack(side=tk.LEFT)
        
        # Right: Action buttons
        ttk.Button(
            action_frame,
            text="← Back to Chronicle",
            command=self.callbacks.get("go_to_chronicle", lambda: None)
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            action_frame,
            text="Proceed to Anvil →",
            command=self._on_proceed_to_anvil
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Separator(action_frame, orient=tk.VERTICAL).pack(side=tk.RIGHT, padx=10, fill=tk.Y, pady=2)
        
        ttk.Button(
            action_frame,
            text="Save to Staging",
            command=self._on_save_staging
        ).pack(side=tk.RIGHT, padx=5)
    
    def set_data(
        self,
        entities: List["Entity"],
        relationships: List["Relationship"]
    ) -> None:
        """Set the data to display.
        
        Args:
            entities: List of Entity objects
            relationships: List of Relationship objects
        """
        self.entities = entities
        self.relationships = relationships
        
        # Load entities into map
        if self.map_canvas:
            self.map_canvas.load_entities(entities)
        
        # Auto-layout if no positions
        if not self.positions and entities:
            self._on_auto_layout()
        else:
            if self.map_canvas:
                self.map_canvas.set_positions(self.positions)
        
        self._refresh_entity_list()
    
    def _refresh_entity_list(self) -> None:
        """Refresh the entity list."""
        if not self.entity_list:
            return
        
        # Clear
        for item in self.entity_list.get_children():
            self.entity_list.delete(item)
        
        # Filter
        filter_type = self.filter_var.get()
        
        for entity in self.entities:
            name = entity.descriptor.name if hasattr(entity, "descriptor") else entity.id
            entity_type = ""
            if hasattr(entity, "descriptor") and hasattr(entity.descriptor, "entity_type"):
                entity_type = entity.descriptor.entity_type.value if hasattr(entity.descriptor.entity_type, "value") else ""
            
            # Apply filter
            if filter_type != "all" and entity_type.lower() != filter_type:
                continue
            
            # Get position
            pos = self.map_canvas.entities.get(entity.id) if self.map_canvas else None
            pos_str = f"({int(pos.x)}, {int(pos.y)})" if pos else "Not set"
            
            self.entity_list.insert(
                "",
                tk.END,
                iid=entity.id,
                values=(name, entity_type[:6], pos_str)
            )
    
    def _on_filter_change(self, event) -> None:
        """Handle filter change."""
        self._refresh_entity_list()
    
    def _on_entity_selected(self, entity_id: str) -> None:
        """Handle entity selection in map."""
        # Update selection info
        entity = None
        for e in self.entities:
            if e.id == entity_id:
                entity = e
                break
        
        if entity:
            name = entity.descriptor.name if hasattr(entity, "descriptor") else entity.id
            self.selected_label.configure(text=name)
            
            # Update position fields
            map_entity = self.map_canvas.entities.get(entity_id) if self.map_canvas else None
            if map_entity:
                self.x_var.set(str(int(map_entity.x)))
                self.y_var.set(str(int(map_entity.y)))
            
            # Select in list
            if self.entity_list.exists(entity_id):
                self.entity_list.selection_set(entity_id)
                self.entity_list.see(entity_id)
    
    def _on_entity_moved(self, entity_id: str, x: float, y: float) -> None:
        """Handle entity movement."""
        # Update position display
        self.x_var.set(str(int(x)))
        self.y_var.set(str(int(y)))
        
        # Update list
        if self.entity_list.exists(entity_id):
            self.entity_list.set(entity_id, "pos", f"({int(x)}, {int(y)})")
    
    def _on_entity_double_click(self, entity_id: str) -> None:
        """Handle entity double-click."""
        edit_entity = self.callbacks.get("edit_entity")
        if edit_entity:
            for entity in self.entities:
                if entity.id == entity_id:
                    edit_entity(entity)
                    break
    
    def _on_list_select(self, event) -> None:
        """Handle list selection."""
        selection = self.entity_list.selection()
        if selection:
            entity_id = selection[0]
            if self.map_canvas:
                self.map_canvas.selected_entity = entity_id
                self.map_canvas.render()
            
            self._on_entity_selected(entity_id)
    
    def _on_list_double_click(self, event) -> None:
        """Handle list double-click."""
        selection = self.entity_list.selection()
        if selection:
            entity_id = selection[0]
            if self.map_canvas:
                self.map_canvas._center_on_entity(entity_id)
    
    def _on_set_position(self) -> None:
        """Set position from entry fields."""
        if not self.map_canvas or not self.map_canvas.selected_entity:
            return
        
        try:
            x = float(self.x_var.get())
            y = float(self.y_var.get())
            
            entity = self.map_canvas.entities.get(self.map_canvas.selected_entity)
            if entity:
                entity.x = x
                entity.y = y
                self.map_canvas.render()
                self._refresh_entity_list()
                
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numbers for X and Y.")
    
    def _on_auto_layout(self) -> None:
        """Auto-layout entities using CartographerAgent."""
        if not self.entities:
            return
        
        try:
            from pyscrai_forge.phases.cartography.agent import CartographerAgent
            
            # Use simple auto-layout (non-LLM)
            agent = CartographerAgent(
                provider=None,  # Not needed for auto_layout
                grid_width=self.map_canvas.winfo_width() or 800,
                grid_height=self.map_canvas.winfo_height() or 600
            )
            
            positions = agent.auto_layout(self.entities, self.relationships)
            
            if self.map_canvas:
                self.map_canvas.set_positions(positions)
            
            self._refresh_entity_list()
            
        except Exception as e:
            messagebox.showerror("Error", f"Auto-layout failed: {e}")
    
    def _on_snap_to_grid(self) -> None:
        """Snap all entities to grid."""
        if self.map_canvas:
            self.map_canvas.snap_all_to_grid()
            self._refresh_entity_list()
    
    def _on_add_region(self) -> None:
        """Add a new region."""
        dialog = tk.Toplevel(self)
        dialog.title("Add Region")
        dialog.geometry("300x200")
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Region Name:").pack(pady=(10, 0))
        name_entry = ttk.Entry(dialog)
        name_entry.pack(pady=5)
        
        frame = ttk.Frame(dialog)
        frame.pack(pady=5)
        
        ttk.Label(frame, text="X:").pack(side=tk.LEFT)
        x_entry = ttk.Entry(frame, width=8)
        x_entry.insert(0, "100")
        x_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(frame, text="Y:").pack(side=tk.LEFT)
        y_entry = ttk.Entry(frame, width=8)
        y_entry.insert(0, "100")
        y_entry.pack(side=tk.LEFT, padx=2)
        
        frame2 = ttk.Frame(dialog)
        frame2.pack(pady=5)
        
        ttk.Label(frame2, text="Width:").pack(side=tk.LEFT)
        w_entry = ttk.Entry(frame2, width=8)
        w_entry.insert(0, "200")
        w_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(frame2, text="Height:").pack(side=tk.LEFT)
        h_entry = ttk.Entry(frame2, width=8)
        h_entry.insert(0, "150")
        h_entry.pack(side=tk.LEFT, padx=2)
        
        def create():
            try:
                name = name_entry.get().strip()
                if not name:
                    messagebox.showerror("Error", "Please enter a region name.")
                    return
                
                x = float(x_entry.get())
                y = float(y_entry.get())
                w = float(w_entry.get())
                h = float(h_entry.get())
                
                if self.map_canvas:
                    self.map_canvas.add_region(name, x, y, w, h)
                
                dialog.destroy()
                
            except ValueError:
                messagebox.showerror("Error", "Invalid values.")
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Create", command=create).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _on_save_staging(self) -> None:
        """Save to spatial staging JSON."""
        if not self.project_path:
            messagebox.showwarning("No Project", "Please load a project first.")
            return
        
        if not self.entities:
            messagebox.showinfo("No Data", "No entities to save.")
            return
        
        try:
            from pyscrai_forge.src.staging import StagingService
            
            # Get positions from canvas
            positions = self.map_canvas.get_positions() if self.map_canvas else {}
            
            # Get regions
            regions = []
            if self.map_canvas:
                for region in self.map_canvas.regions:
                    regions.append({
                        "name": region.name,
                        "x": region.x,
                        "y": region.y,
                        "width": region.width,
                        "height": region.height
                    })
            
            staging = StagingService(self.project_path)
            artifact_path = staging.save_spatial_staging(
                entity_positions=positions,
                regions=regions,
                metadata={"phase": "cartography"}
            )
            
            messagebox.showinfo(
                "Staging Saved",
                f"Saved {len(positions)} entity positions.\n\n{artifact_path}"
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save staging: {e}")
    
    def _on_proceed_to_anvil(self) -> None:
        """Proceed to Anvil phase."""
        # Auto-save staging
        if self.entities and self.project_path and self.map_canvas:
            try:
                from pyscrai_forge.src.staging import StagingService
                staging = StagingService(self.project_path)
                
                positions = self.map_canvas.get_positions()
                regions = [
                    {"name": r.name, "x": r.x, "y": r.y, "width": r.width, "height": r.height}
                    for r in self.map_canvas.regions
                ]
                
                staging.save_spatial_staging(positions, regions)
            except Exception:
                pass
        
        go_to_anvil = self.callbacks.get("go_to_anvil")
        if go_to_anvil:
            go_to_anvil()

