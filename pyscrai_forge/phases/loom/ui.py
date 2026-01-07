"""Phase 2: LOOM - Relationship Mapping UI Panel.

This module provides the main UI panel for the Loom phase,
combining the graph visualization with relationship editing tools.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Callable, List, Optional

from pyscrai_forge.phases.loom.graph_viz import GraphCanvas, LayoutAlgorithm

if TYPE_CHECKING:
    from pyscrai_core import Entity, Relationship


class LoomPanel(ttk.Frame):
    """Main panel for the Loom phase - Relationship Mapping.
    
    Features:
    - Interactive graph visualization
    - Relationship inference via LoomAgent
    - Conflict detection
    - Staging to graph_staging.json
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        project_path: Optional[Path] = None,
        callbacks: Optional[dict[str, Callable]] = None,
        **kwargs
    ):
        """Initialize the Loom panel.
        
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
        
        # UI components
        self.graph_canvas: Optional[GraphCanvas] = None
        self.relationship_list: Optional[ttk.Treeview] = None
        self.conflict_list: Optional[ttk.Treeview] = None
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        """Build the Loom phase UI."""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        ttk.Label(
            header_frame,
            text="Phase 2: LOOM",
            font=("Segoe UI", 16, "bold")
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            header_frame,
            text="Relationship Mapping & Graph Visualization",
            font=("Segoe UI", 11),
            foreground="gray"
        ).pack(side=tk.LEFT, padx=(15, 0))
        
        # Main content container
        content_container = ttk.Frame(self)
        content_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Main content - horizontal split
        main_paned = ttk.PanedWindow(content_container, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Left: Graph canvas
        graph_frame = ttk.Frame(main_paned)
        main_paned.add(graph_frame, weight=3)
        
        self._build_graph_panel(graph_frame)
        
        # Right: Relationship/conflict panels
        right_paned = ttk.PanedWindow(main_paned, orient=tk.VERTICAL)
        main_paned.add(right_paned, weight=1)
        
        # Relationships list
        rel_frame = ttk.Frame(right_paned)
        right_paned.add(rel_frame, weight=2)
        self._build_relationships_panel(rel_frame)
        
        # Conflicts/suggestions
        conflict_frame = ttk.Frame(right_paned)
        right_paned.add(conflict_frame, weight=1)
        self._build_conflicts_panel(conflict_frame)
        
        # Bottom action bar (packed in content_container, not self)
        self._build_action_bar(content_container)
    
    def _build_graph_panel(self, parent: ttk.Frame) -> None:
        """Build the graph visualization panel."""
        # Toolbar
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(toolbar, text="Graph View", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y, pady=2)
        
        # Layout options
        ttk.Label(toolbar, text="Layout:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.layout_var = tk.StringVar(value="spring")
        layout_combo = ttk.Combobox(
            toolbar,
            textvariable=self.layout_var,
            values=["spring", "circular", "shell", "kamada_kawai"],
            state="readonly",
            width=12
        )
        layout_combo.pack(side=tk.LEFT)
        layout_combo.bind("<<ComboboxSelected>>", self._on_layout_change)
        
        ttk.Button(
            toolbar,
            text="Recalculate",
            command=self._recalculate_layout
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            toolbar,
            text="Center View",
            command=lambda: self.graph_canvas.center_view() if self.graph_canvas else None
        ).pack(side=tk.LEFT)
        
        # Graph canvas
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.graph_canvas = GraphCanvas(
            canvas_frame,
            on_node_selected=self._on_node_selected,
            on_edge_selected=self._on_edge_selected,
            on_node_double_click=self._on_node_double_click,
            on_edge_created=self._on_edge_created,
            on_node_moved=self._on_node_moved
        )
        self.graph_canvas.pack(fill=tk.BOTH, expand=True)
    
    def _build_relationships_panel(self, parent: ttk.Frame) -> None:
        """Build the relationships list panel."""
        # Header
        header = ttk.Frame(parent)
        header.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(header, text="Relationships", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        
        ttk.Button(
            header,
            text="+ Add",
            command=self._on_add_relationship,
            width=8
        ).pack(side=tk.RIGHT)
        
        ttk.Button(
            header,
            text="Infer",
            command=self._on_infer_relationships,
            width=8
        ).pack(side=tk.RIGHT, padx=5)
        
        # Treeview
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.relationship_list = ttk.Treeview(
            tree_frame,
            columns=("source", "type", "target"),
            show="headings",
            selectmode=tk.BROWSE
        )
        
        self.relationship_list.heading("source", text="Source")
        self.relationship_list.heading("type", text="Type")
        self.relationship_list.heading("target", text="Target")
        
        self.relationship_list.column("source", width=80)
        self.relationship_list.column("type", width=80)
        self.relationship_list.column("target", width=80)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.relationship_list.yview)
        self.relationship_list.configure(yscrollcommand=scrollbar.set)
        
        self.relationship_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection
        self.relationship_list.bind("<<TreeviewSelect>>", self._on_relationship_list_select)
        self.relationship_list.bind("<Delete>", self._on_delete_relationship)
    
    def _build_conflicts_panel(self, parent: ttk.Frame) -> None:
        """Build the conflicts/suggestions panel."""
        # Header
        header = ttk.Frame(parent)
        header.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(header, text="Issues & Suggestions", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        
        ttk.Button(
            header,
            text="Detect",
            command=self._on_detect_conflicts,
            width=8
        ).pack(side=tk.RIGHT)
        
        # Treeview
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.conflict_list = ttk.Treeview(
            tree_frame,
            columns=("type", "description"),
            show="headings",
            selectmode=tk.BROWSE
        )
        
        self.conflict_list.heading("type", text="Type")
        self.conflict_list.heading("description", text="Description")
        
        self.conflict_list.column("type", width=80)
        self.conflict_list.column("description", width=200)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.conflict_list.yview)
        self.conflict_list.configure(yscrollcommand=scrollbar.set)
        
        self.conflict_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _build_action_bar(self, parent: ttk.Frame) -> None:
        """Build the bottom action bar."""
        action_frame = ttk.Frame(parent)
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
            text="← Back to Foundry",
            command=self.callbacks.get("go_to_foundry", lambda: None)
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            action_frame,
            text="Proceed to Chronicle →",
            command=self._on_proceed_to_chronicle
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
        self.refresh()
    
    def refresh(self) -> None:
        """Refresh the UI with current data."""
        # Load into graph canvas
        if self.graph_canvas:
            self.graph_canvas.load_from_entities(
                self.entities,
                self.relationships,
                layout=LayoutAlgorithm(self.layout_var.get())
            )
        
        # Refresh relationships list
        self._refresh_relationships_list()
    
    def _refresh_relationships_list(self) -> None:
        """Refresh the relationships list."""
        if not self.relationship_list:
            return
        
        # Clear
        for item in self.relationship_list.get_children():
            self.relationship_list.delete(item)
        
        # Build entity name lookup
        entity_names = {}
        for e in self.entities:
            if hasattr(e, "descriptor") and hasattr(e.descriptor, "name"):
                entity_names[e.id] = e.descriptor.name
            else:
                entity_names[e.id] = e.id
        
        # Add relationships
        for rel in self.relationships:
            source_name = entity_names.get(rel.source_id, rel.source_id)
            target_name = entity_names.get(rel.target_id, rel.target_id)
            
            rel_type = ""
            if hasattr(rel, "relationship_type"):
                rel_type = rel.relationship_type.value if hasattr(rel.relationship_type, "value") else str(rel.relationship_type)
            
            self.relationship_list.insert(
                "",
                tk.END,
                values=(source_name, rel_type, target_name)
            )
    
    def _on_layout_change(self, event) -> None:
        """Handle layout algorithm change."""
        self._recalculate_layout()
    
    def _recalculate_layout(self) -> None:
        """Recalculate the graph layout."""
        if self.graph_canvas:
            layout = LayoutAlgorithm(self.layout_var.get())
            self.graph_canvas._calculate_layout(layout)
            self.graph_canvas.render()
    
    def _on_node_selected(self, node_id: str) -> None:
        """Handle node selection in graph."""
        # Could highlight related relationships
        pass
    
    def _on_edge_selected(self, source_id: str, target_id: str) -> None:
        """Handle edge selection in graph."""
        pass
    
    def _on_node_double_click(self, node_id: str) -> None:
        """Handle node double-click to edit entity."""
        edit_entity = self.callbacks.get("edit_entity")
        if edit_entity:
            # Find the entity and trigger edit
            for entity in self.entities:
                if entity.id == node_id:
                    edit_entity(entity)
                    break
    
    def _on_edge_created(self, source_id: str, target_id: str) -> None:
        """Handle edge creation via drag-connect."""
        # Show dialog to select relationship type
        self._show_new_relationship_dialog(source_id, target_id)
    
    def _on_node_moved(self, node_id: str, x: float, y: float) -> None:
        """Handle node movement."""
        # Layout positions are tracked in the graph canvas
        pass
    
    def _on_relationship_list_select(self, event) -> None:
        """Handle relationship list selection."""
        selection = self.relationship_list.selection()
        if selection:
            # Could highlight in graph
            pass
    
    def _on_delete_relationship(self, event) -> None:
        """Handle relationship deletion."""
        selection = self.relationship_list.selection()
        if not selection:
            return
        
        if messagebox.askyesno("Delete Relationship", "Delete the selected relationship?"):
            # Get the index and remove
            idx = self.relationship_list.index(selection[0])
            if 0 <= idx < len(self.relationships):
                rel = self.relationships[idx]
                self.relationships.pop(idx)
                
                if self.graph_canvas:
                    self.graph_canvas.remove_edge(rel.source_id, rel.target_id)
                
                self._refresh_relationships_list()
    
    def _on_add_relationship(self) -> None:
        """Handle add relationship button."""
        if len(self.entities) < 2:
            messagebox.showinfo("Need Entities", "Need at least 2 entities to create a relationship.")
            return
        
        # For now, just show a message
        # TODO: Implement full relationship dialog
        messagebox.showinfo(
            "Add Relationship",
            "To add a relationship:\n\n"
            "1. Right-click a node and select 'Start Edge From Here'\n"
            "2. Drag to another node\n"
            "3. Select the relationship type"
        )
    
    def _show_new_relationship_dialog(self, source_id: str, target_id: str) -> None:
        """Show dialog to create a new relationship."""
        dialog = tk.Toplevel(self)
        dialog.title("New Relationship")
        dialog.geometry("300x150")
        dialog.transient(self)
        dialog.grab_set()
        
        # Get entity names
        source_name = source_id
        target_name = target_id
        for e in self.entities:
            if e.id == source_id and hasattr(e, "descriptor"):
                source_name = e.descriptor.name
            if e.id == target_id and hasattr(e, "descriptor"):
                target_name = e.descriptor.name
        
        ttk.Label(
            dialog,
            text=f"{source_name} → {target_name}",
            font=("Segoe UI", 11, "bold")
        ).pack(pady=10)
        
        ttk.Label(dialog, text="Relationship Type:").pack()
        
        type_var = tk.StringVar(value="KNOWS")
        type_combo = ttk.Combobox(
            dialog,
            textvariable=type_var,
            values=["KNOWS", "FAMILY", "ALLIED_WITH", "ENEMY_OF", "MEMBER_OF", 
                    "LOCATED_IN", "OWNS", "WORKS_FOR", "CREATED_BY", "PART_OF"],
            state="readonly"
        )
        type_combo.pack(pady=5)
        
        def create():
            rel_type = type_var.get()
            
            # Create the relationship
            try:
                from pyscrai_core import Relationship, RelationshipType
                
                new_rel = Relationship(
                    source_id=source_id,
                    target_id=target_id,
                    relationship_type=RelationshipType(rel_type.lower())
                )
                self.relationships.append(new_rel)
                
                if self.graph_canvas:
                    self.graph_canvas.add_edge(source_id, target_id, rel_type)
                
                self._refresh_relationships_list()
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create relationship: {e}")
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Create", command=create).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def _on_infer_relationships(self) -> None:
        """Infer relationships using LoomAgent."""
        if not self.entities:
            messagebox.showinfo("No Entities", "No entities to analyze.")
            return
        
        # TODO: Wire to TaskQueue and LoomAgent
        messagebox.showinfo(
            "Infer Relationships",
            "Relationship inference will analyze entities and suggest connections.\n\n"
            "This feature requires LLM connection."
        )
    
    def _on_detect_conflicts(self) -> None:
        """Detect conflicts using LoomAgent."""
        if not self.entities:
            messagebox.showinfo("No Entities", "No entities to analyze.")
            return
        
        # TODO: Wire to TaskQueue and LoomAgent
        messagebox.showinfo(
            "Detect Conflicts",
            "Conflict detection will identify:\n"
            "• Potential duplicates\n"
            "• Contradictions\n"
            "• Missing relationships\n\n"
            "This feature requires LLM connection."
        )
    
    def _on_save_staging(self) -> None:
        """Save to graph staging JSON."""
        if not self.project_path:
            messagebox.showwarning("No Project", "Please load a project first.")
            return
        
        try:
            from pyscrai_forge.src.staging import StagingService
            
            staging = StagingService(self.project_path)
            
            # Get layout data from canvas
            layout_data = self.graph_canvas.get_layout() if self.graph_canvas else {}
            
            artifact_path = staging.save_graph_staging(
                entities=self.entities,
                relationships=self.relationships,
                layout_data=layout_data,
                metadata={"phase": "loom"}
            )
            
            messagebox.showinfo(
                "Staging Saved",
                f"Saved {len(self.entities)} entities and {len(self.relationships)} relationships.\n\n{artifact_path}"
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save staging: {e}")
    
    def _on_proceed_to_chronicle(self) -> None:
        """Proceed to Chronicle phase."""
        # Auto-save staging
        if self.entities and self.project_path:
            try:
                from pyscrai_forge.src.staging import StagingService
                staging = StagingService(self.project_path)
                staging.save_graph_staging(
                    self.entities,
                    self.relationships,
                    layout_data=self.graph_canvas.get_layout() if self.graph_canvas else {}
                )
            except Exception as e:
                if not messagebox.askyesno(
                    "Staging Error",
                    f"Failed to save staging: {e}\n\nContinue anyway?"
                ):
                    return
        
        go_to_chronicle = self.callbacks.get("go_to_chronicle")
        if go_to_chronicle:
            go_to_chronicle()

