"""Phase 2: LOOM - Relationship Mapping UI Panel.

This module provides the main UI panel for the Loom phase,
combining the graph visualization with relationship editing tools.
"""

from __future__ import annotations

import asyncio
import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Any, Callable, List, Optional

from pyscrai_forge.phases.loom.graph_viz import GraphCanvas, LayoutAlgorithm

if TYPE_CHECKING:
    from pyscrai_core import Entity, Relationship
    from pyscrai_core.llm_interface.base import LLMProvider


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
        
        # Clustering and memory service
        self.memory_service = None
        self.clusters: dict = {}
        self.cluster_labels: dict = {}
        self.show_clusters = tk.BooleanVar(value=True)
        
        # LoomAssistant for relationship validation and suggestions
        self.assistant = None
        self.relationship_suggestions: List[Any] = []
        self.relationship_conflicts: List[Any] = []
        
        self._init_memory_service()
        self._build_ui()
    
    def _init_memory_service(self) -> None:
        """Initialize MemoryService for semantic clustering."""
        try:
            from pyscrai_core.memory_service import MemoryService
            if self.project_path:
                db_path = self.project_path / "world.db"
                self.memory_service = MemoryService.create(db_path if db_path.exists() else None)
            else:
                self.memory_service = MemoryService.create()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to initialize MemoryService: {e}")
            self.memory_service = None
    
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
        content_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 0))
        
        # Use vertical PanedWindow to properly balance content and action bar
        main_paned = ttk.PanedWindow(content_container, orient=tk.VERTICAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Top content area - horizontal split
        top_frame = ttk.Frame(main_paned)
        main_paned.add(top_frame, weight=1)
        
        # Horizontal split inside top frame
        horizontal_paned = ttk.PanedWindow(top_frame, orient=tk.HORIZONTAL)
        horizontal_paned.pack(fill=tk.BOTH, expand=True)
        
        # Left: Graph canvas
        graph_frame = ttk.Frame(horizontal_paned)
        horizontal_paned.add(graph_frame, weight=3)
        
        self._build_graph_panel(graph_frame)
        
        # Right: Relationship/conflict panels
        right_paned = ttk.PanedWindow(horizontal_paned, orient=tk.VERTICAL)
        horizontal_paned.add(right_paned, weight=1)
        
        # Relationships list
        rel_frame = ttk.Frame(right_paned)
        right_paned.add(rel_frame, weight=2)
        self._build_relationships_panel(rel_frame)
        
        # Conflicts/suggestions
        conflict_frame = ttk.Frame(right_paned)
        right_paned.add(conflict_frame, weight=1)
        self._build_conflicts_panel(conflict_frame)
        
        # Right: Assistant sidebar (similar to Foundry)
        assistant_frame = ttk.Frame(horizontal_paned)
        horizontal_paned.add(assistant_frame, weight=1)
        self._build_assistant_panel(assistant_frame)
        
        # Bottom action bar
        action_frame = ttk.Frame(main_paned)
        main_paned.add(action_frame, weight=0)  # weight=0 means minimum fixed size
        self._build_action_bar(action_frame)
    
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
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y, pady=2)
        
        # Cluster controls
        ttk.Checkbutton(
            toolbar,
            text="Show Clusters",
            variable=self.show_clusters,
            command=self._on_toggle_clusters
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            toolbar,
            text="Cluster Entities",
            command=self._on_cluster_entities,
            width=12
        ).pack(side=tk.LEFT, padx=5)
        
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
    
    def _build_assistant_panel(self, parent: ttk.Frame) -> None:
        """Build the LoomAssistant sidebar panel."""
        # Header
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(
            header_frame,
            text="Relationship Assistant",
            font=("Segoe UI", 12, "bold")
        ).pack(side=tk.LEFT)
        
        # Refresh button
        ttk.Button(
            header_frame,
            text="Refresh",
            command=self._refresh_assistant_suggestions
        ).pack(side=tk.RIGHT, padx=2)
        
        # Tab notebook for different views
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Missing Relationships
        missing_frame = ttk.Frame(notebook)
        notebook.add(missing_frame, text="Missing")
        self._build_missing_relationships_panel(missing_frame)
        
        # Tab 2: Conflicts
        conflicts_frame = ttk.Frame(notebook)
        notebook.add(conflicts_frame, text="Conflicts")
        self._build_conflicts_assistant_panel(conflicts_frame)
        
        # Tab 3: Validation
        validation_frame = ttk.Frame(notebook)
        notebook.add(validation_frame, text="Validation")
        self._build_validation_panel(validation_frame)
    
    def _build_missing_relationships_panel(self, parent: ttk.Frame) -> None:
        """Build panel for missing relationship suggestions."""
        # List with scrollbar
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.missing_relationships_text = tk.Text(
            list_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 9),
            height=15,
            state=tk.DISABLED
        )
        self.missing_relationships_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.missing_relationships_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.missing_relationships_text.config(yscrollcommand=scrollbar.set)
        
        # Action buttons
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.add_suggestion_btn = ttk.Button(
            action_frame,
            text="Add Selected",
            command=self._add_selected_suggestion,
            state=tk.DISABLED
        )
        self.add_suggestion_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
    
    def _build_conflicts_assistant_panel(self, parent: ttk.Frame) -> None:
        """Build panel for relationship conflicts."""
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.conflicts_text = tk.Text(
            list_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 9),
            height=15,
            state=tk.DISABLED
        )
        self.conflicts_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.conflicts_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.conflicts_text.config(yscrollcommand=scrollbar.set)
    
    def _build_validation_panel(self, parent: ttk.Frame) -> None:
        """Build panel for relationship validation."""
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.validation_text = tk.Text(
            list_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 9),
            height=15,
            state=tk.DISABLED
        )
        self.validation_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.validation_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.validation_text.config(yscrollcommand=scrollbar.set)
        
        # Validate button
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(
            action_frame,
            text="Validate All",
            command=self._validate_all_relationships
        ).pack(fill=tk.X)
    
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
            
            # Reapply cluster colors if enabled
            if self.show_clusters.get() and self.clusters:
                self._apply_cluster_colors()
        
        # Refresh relationships list
        self._refresh_relationships_list()
        
        # Auto-cluster if we have entities but no clusters
        if self.entities and not self.clusters and len(self.entities) >= 5:
            # Auto-cluster in background
            import threading
            def auto_cluster():
                try:
                    from pyscrai_forge.phases.loom.clustering import SemanticClusterer
                    if self.memory_service:
                        clusterer = SemanticClusterer(self.memory_service)
                        self.clusters = clusterer.cluster_entities(self.entities)
                        self.cluster_labels = clusterer.get_cluster_labels(self.clusters)
                        # Update UI in main thread
                        self.after(0, lambda: self._apply_cluster_colors() if self.show_clusters.get() else None)
                except Exception:
                    pass  # Silent fail for auto-cluster
            threading.Thread(target=auto_cluster, daemon=True).start()
        
        # Auto-refresh assistant suggestions
        if hasattr(self, 'assistant') and self.entities and self.relationships:
            self._refresh_assistant_suggestions()
    
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
    
    def _on_cluster_entities(self) -> None:
        """Cluster entities using semantic similarity."""
        if not self.entities or len(self.entities) < 2:
            messagebox.showinfo("Need Entities", "Need at least 2 entities to cluster.")
            return
        
        if not self.memory_service:
            messagebox.showwarning(
                "Memory Service Unavailable",
                "Semantic clustering requires MemoryService.\n\n"
                "This feature uses embeddings to group entities by context."
            )
            return
        
        try:
            from pyscrai_forge.phases.loom.clustering import SemanticClusterer
            
            clusterer = SemanticClusterer(self.memory_service)
            self.clusters = clusterer.cluster_entities(self.entities)
            self.cluster_labels = clusterer.get_cluster_labels(self.clusters)
            
            # Update graph with cluster colors
            if self.graph_canvas:
                self._apply_cluster_colors()
            
            # Show cluster info
            cluster_info = "\n".join([
                f"{label}: {len(entities)} entities"
                for cluster_id, entities in self.clusters.items()
                for label in [self.cluster_labels.get(cluster_id, cluster_id)]
            ])
            
            messagebox.showinfo(
                "Clustering Complete",
                f"Clustered {len(self.entities)} entities into {len(self.clusters)} groups:\n\n{cluster_info}"
            )
            
        except Exception as e:
            messagebox.showerror("Clustering Error", f"Failed to cluster entities: {e}")
    
    def _on_toggle_clusters(self) -> None:
        """Toggle cluster visualization."""
        if self.show_clusters.get() and self.clusters:
            self._apply_cluster_colors()
        elif self.graph_canvas:
            # Remove cluster colors
            self.graph_canvas.clear_node_colors()
    
    def _apply_cluster_colors(self) -> None:
        """Apply cluster colors to graph nodes."""
        if not self.graph_canvas or not self.clusters:
            return
        
        # Color palette for clusters
        colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8",
            "#F7DC6F", "#BB8FCE", "#85C1E2", "#F8B739", "#52BE80"
        ]
        
        cluster_colors = {}
        for i, (cluster_id, entities) in enumerate(self.clusters.items()):
            color = colors[i % len(colors)]
            cluster_colors[cluster_id] = color
            
            # Color all entities in this cluster
            for entity in entities:
                if hasattr(self.graph_canvas, 'set_node_color'):
                    self.graph_canvas.set_node_color(entity.id, color)
                elif hasattr(self.graph_canvas, 'color_node'):
                    self.graph_canvas.color_node(entity.id, color)
    
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
            # Pass the entity_id to the edit callback
            edit_entity(entity_id=node_id)
    
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
    
    def _check_llm_configured(self) -> tuple[bool, "LLMProvider" | None, str | None]:
        """Check if LLM is configured via project settings.
        
        Returns:
            Tuple of (is_configured, provider, model_name)
        """
        import os
        
        # Get manifest from callbacks
        manifest = self.callbacks.get("get_manifest")()
        if not manifest:
            return False, None, "No project loaded"
        
        # Check if LLM settings are configured
        if not manifest.llm_provider:
            return False, None, "No LLM provider configured in project settings"
        
        if not manifest.llm_default_model:
            return False, None, "No LLM model configured in project settings"
        
        # Get API key from environment
        provider_name = manifest.llm_provider
        env_key_map = {
            "openrouter": "OPENROUTER_API_KEY",
            "cherry": "CHERRY_API_KEY",
            "lm_studio": "LM_STUDIO_API_KEY",
            "lm_proxy": "LM_PROXY_API_KEY",
        }
        api_key = os.getenv(env_key_map.get(provider_name, ""), "")
        
        # Try to create the provider
        try:
            from pyscrai_core.llm_interface import create_provider
            
            provider = create_provider(
                provider_name,
                api_key=api_key if api_key else None,
                base_url=manifest.llm_base_url,
                timeout=60.0
            )
            
            if hasattr(provider, 'default_model'):
                provider.default_model = manifest.llm_default_model
            
            return True, provider, manifest.llm_default_model
            
        except Exception as e:
            return False, None, f"Failed to create LLM provider: {e}"
    
    def _on_infer_relationships(self) -> None:
        """Infer relationships using LoomAgent."""
        if not self.entities:
            messagebox.showinfo("No Entities", "No entities to analyze.")
            return
        
        # Check if LLM is configured
        is_configured, provider, model_name = self._check_llm_configured()
        
        if not is_configured:
            messagebox.showwarning(
                "LLM Connection Needed",
                f"Relationship inference requires an LLM connection.\n\n"
                f"Issue: {model_name}\n\n"  # model_name contains error message here
                f"Please configure an LLM provider in Project Settings."
            )
            return
        
        # Show progress dialog with better UX
        progress_win = tk.Toplevel(self)
        progress_win.title("Inferring Relationships")
        progress_win.geometry("400x120")
        progress_win.transient(self)
        progress_win.grab_set()
        progress_win.resizable(False, False)
        
        # Center on parent
        progress_win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 400) // 2
        y = self.winfo_y() + (self.winfo_height() - 120) // 2
        progress_win.geometry(f"+{x}+{y}")
        
        # Progress bar style
        style = ttk.Style()
        style.configure("pyscrai.Horizontal.TProgressbar", thickness=20)
        
        ttk.Label(
            progress_win,
            text="Analyzing entities and inferring relationships...",
            font=("Segoe UI", 11)
        ).pack(pady=(15, 5))
        
        progress_bar = ttk.Progressbar(
            progress_win,
            mode="indeterminate",
            style="pyscrai.Horizontal.TProgressbar",
            length=300
        )
        progress_bar.pack(pady=5)
        progress_bar.start(50)
        
        # Show cluster info if available
        cluster_info = ""
        if self.clusters:
            cluster_info = f" (using {len(self.clusters)} semantic clusters)"
        
        status_label = ttk.Label(
            progress_win,
            text=f"Processing {len(self.entities)} entities{cluster_info}...",
            font=("Segoe UI", 9),
            foreground="gray"
        )
        status_label.pack(pady=(5, 10))
        
        def run_inference():
            """Run relationship inference in background."""
            from pyscrai_forge.phases.loom.agent import LoomAgent
            import asyncio
            
            async def infer():
                async with provider:
                    # Pass memory_service for clustering
                    agent = LoomAgent(
                        provider,
                        model=model_name,
                        memory_service=self.memory_service
                    )
                    return await agent.infer_relationships(
                        self.entities,
                        existing_relationships=self.relationships,
                        use_clustering=True  # Enable clustering by default
                    )
            
            return asyncio.run(infer())
        
        def finish_inference():
            """Handle inference results."""
            try:
                progress_bar.stop()
                progress_win.destroy()
            except:
                pass
            
            inferred = run_inference()
            
            if not inferred:
                messagebox.showinfo(
                    "No Relationships Found",
                    "No new relationships could be inferred from the entity data.\n\n"
                    "Try adding more detailed entity descriptions."
                )
                return
            
            # Show results dialog
            self._show_inference_results(inferred)
        
        # Run in background
        import threading
        thread = threading.Thread(target=finish_inference, daemon=True)
        thread.start()
    
    def _show_inference_results(self, inferred: list) -> None:
        """Show inference results and allow adding relationships."""
        dialog = tk.Toplevel(self)
        dialog.title(f"Inferred {len(inferred)} Relationships")
        dialog.geometry("500x400")
        dialog.transient(self)
        
        # Results list
        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tree = ttk.Treeview(
            frame,
            columns=("source", "type", "target", "confidence"),
            show="headings"
        )
        tree.heading("source", text="Source")
        tree.heading("type", text="Type")
        tree.heading("target", text="Target")
        tree.heading("confidence", text="Confidence")
        
        tree.column("source", width=100)
        tree.column("type", width=80)
        tree.column("target", width=100)
        tree.column("confidence", width=80)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Build entity name lookup
        entity_names = {}
        for e in self.entities:
            if hasattr(e, "descriptor") and hasattr(e.descriptor, "name"):
                entity_names[e.id] = e.descriptor.name
            else:
                entity_names[e.id] = e.id
        
        # Populate tree
        for rel in inferred:
            source_name = entity_names.get(rel.source_id, rel.source_id)
            target_name = entity_names.get(rel.target_id, rel.target_id)
            tree.insert(
                "", tk.END,
                values=(source_name, rel.relationship_type, target_name, rel.confidence.value),
                tags=(rel.source_id, rel.target_id, rel.relationship_type)
            )
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def add_selected():
            """Add selected inferred relationships."""
            selected = tree.selection()
            if not selected:
                messagebox.showinfo("Select Relationships", "Please select relationships to add.")
                return
            
            from pyscrai_core import Relationship, RelationshipType
            
            added_count = 0
            for item_id in selected:
                tags = tree.item(item_id, "tags")
                source_id, target_id, rel_type = tags
                
                # Check if already exists
                exists = any(
                    r.source_id == source_id and r.target_id == target_id
                    for r in self.relationships
                )
                
                if not exists:
                    try:
                        new_rel = Relationship(
                            source_id=source_id,
                            target_id=target_id,
                            relationship_type=RelationshipType(rel_type.lower())
                        )
                        self.relationships.append(new_rel)
                        added_count += 1
                        
                        if self.graph_canvas:
                            self.graph_canvas.add_edge(source_id, target_id, rel_type)
                    except:
                        pass
            
            self._refresh_relationships_list()
            
            dialog.destroy()
            messagebox.showinfo(
                "Relationships Added",
                f"Added {added_count} relationship(s) to the graph."
            )
        
        ttk.Button(btn_frame, text="Add Selected", command=add_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def _on_detect_conflicts(self) -> None:
        """Detect conflicts using LoomAgent."""
        if not self.entities:
            messagebox.showinfo("No Entities", "No entities to analyze.")
            return
        
        # Check if LLM is configured
        is_configured, provider, model_name = self._check_llm_configured()
        
        if not is_configured:
            messagebox.showwarning(
                "LLM Connection Needed",
                f"Conflict detection requires an LLM connection.\n\n"
                f"Issue: {model_name}\n\n"  # model_name contains error message here
                f"Please configure an LLM provider in Project Settings."
            )
            return
        
        # Show progress dialog with better UX
        progress_win = tk.Toplevel(self)
        progress_win.title("Detecting Conflicts")
        progress_win.geometry("400x120")
        progress_win.transient(self)
        progress_win.grab_set()
        progress_win.resizable(False, False)
        
        # Center on parent
        progress_win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 400) // 2
        y = self.winfo_y() + (self.winfo_height() - 120) // 2
        progress_win.geometry(f"+{x}+{y}")
        
        # Progress bar style
        style = ttk.Style()
        style.configure("pyscrai.Horizontal.TProgressbar", thickness=20)
        
        ttk.Label(
            progress_win,
            text="Scanning entities and relationships for issues...",
            font=("Segoe UI", 11)
        ).pack(pady=(15, 5))
        
        progress_bar = ttk.Progressbar(
            progress_win,
            mode="indeterminate",
            style="pyscrai.Horizontal.TProgressbar",
            length=300
        )
        progress_bar.pack(pady=5)
        progress_bar.start(50)
        
        status_label = ttk.Label(
            progress_win,
            text=f"Analyzing {len(self.entities)} entities and {len(self.relationships)} relationships...",
            font=("Segoe UI", 9),
            foreground="gray"
        )
        status_label.pack(pady=(5, 10))
        
        def run_detection():
            """Run conflict detection in background."""
            from pyscrai_forge.phases.loom.agent import LoomAgent
            import asyncio
            
            async def detect():
                async with provider:
                    agent = LoomAgent(provider, model=model_name)
                    return await agent.detect_conflicts(
                        self.entities,
                        self.relationships
                    )
            
            return asyncio.run(detect())
        
        def finish_detection():
            """Handle detection results."""
            try:
                progress_bar.stop()
                progress_win.destroy()
            except:
                pass
            
            conflicts = run_detection()
            
            if not conflicts:
                messagebox.showinfo(
                    "No Conflicts Found",
                    "No conflicts or issues were detected in your entity data.\n\n"
                    "Your world appears to be consistent!"
                )
                return
            
            # Show results - also populates the Issues & Suggestions panel
            self._show_conflict_results(conflicts)
        
        # Run in background
        import threading
        thread = threading.Thread(target=finish_detection, daemon=True)
        thread.start()
    
    def _refresh_conflicts_list(self, conflicts: list) -> None:
        """Refresh the conflicts/suggestions list."""
        if not self.conflict_list:
            return
        
        # Clear
        for item in self.conflict_list.get_children():
            self.conflict_list.delete(item)
        
        # Populate
        for conflict in conflicts:
            entity_ids = ", ".join(conflict.entity_ids[:3])
            if len(conflict.entity_ids) > 3:
                entity_ids += "..."
            
            self.conflict_list.insert(
                "",
                tk.END,
                values=(
                    conflict.conflict_type.title(),
                    conflict.description
                )
            )
    
    def _show_conflict_results(self, conflicts: list) -> None:
        """Show conflict detection results."""
        # First, populate the Issues & Suggestions panel
        self._refresh_conflicts_list(conflicts)
        
        # Also show a dialog for detailed viewing
        dialog = tk.Toplevel(self)
        dialog.title(f"Found {len(conflicts)} Issue(s)")
        dialog.geometry("550x400")
        dialog.transient(self)
        
        # Results list
        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tree = ttk.Treeview(
            frame,
            columns=("type", "description", "entities"),
            show="headings"
        )
        tree.heading("type", text="Type")
        tree.heading("description", text="Description")
        tree.heading("entities", text="Entities")
        
        tree.column("type", width=100)
        tree.column("description", width=280)
        tree.column("entities", width=120)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate tree
        for conflict in conflicts:
            entity_ids = ", ".join(conflict.entity_ids[:3])
            if len(conflict.entity_ids) > 3:
                entity_ids += "..."
            
            tree.insert(
                "", tk.END,
                values=(
                    conflict.conflict_type.title(),
                    conflict.description,
                    entity_ids
                )
            )
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
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
    
    def _refresh_assistant_suggestions(self) -> None:
        """Refresh the assistant suggestions panel."""
        # Update the Missing Relationships text
        if hasattr(self, 'missing_relationships_text') and self.missing_relationships_text:
            self.missing_relationships_text.config(state=tk.NORMAL)
            self.missing_relationships_text.delete(1.0, tk.END)
            
            if self.relationship_suggestions:
                text = "Suggested Missing Relationships:\n\n"
                for suggestion in self.relationship_suggestions:
                    text += f"• {suggestion}\n"
                self.missing_relationships_text.insert(tk.END, text)
                if hasattr(self, 'add_suggestion_btn') and self.add_suggestion_btn:
                    self.add_suggestion_btn.config(state=tk.NORMAL)
            else:
                self.missing_relationships_text.insert(tk.END, "No suggestions available.\n\nRun 'Infer Relationships' to generate suggestions.")
                if hasattr(self, 'add_suggestion_btn') and self.add_suggestion_btn:
                    self.add_suggestion_btn.config(state=tk.DISABLED)
            
            self.missing_relationships_text.config(state=tk.DISABLED)
        
        # Update conflicts text
        if hasattr(self, 'conflicts_text') and self.conflicts_text:
            self.conflicts_text.config(state=tk.NORMAL)
            self.conflicts_text.delete(1.0, tk.END)
            
            if self.relationship_conflicts:
                text = "Detected Conflicts:\n\n"
                for conflict in self.relationship_conflicts:
                    text += f"• {conflict}\n"
                self.conflicts_text.insert(tk.END, text)
            else:
                self.conflicts_text.insert(tk.END, "No conflicts detected.\n\nRun 'Detect Conflicts' to scan for issues.")
            
            self.conflicts_text.config(state=tk.DISABLED)
    
    def _add_selected_suggestion(self) -> None:
        """Add the selected suggestion to relationships."""
        messagebox.showinfo(
            "Add Suggestion",
            "Select a relationship from the Infer dialog to add it."
        )
    
    def _validate_all_relationships(self) -> None:
        """Validate all relationships."""
        if not hasattr(self, 'validation_text') or not self.validation_text:
            return
        
        self.validation_text.config(state=tk.NORMAL)
        self.validation_text.delete(1.0, tk.END)
        
        if not self.relationships:
            self.validation_text.insert(tk.END, "No relationships to validate.")
            self.validation_text.config(state=tk.DISABLED)
            return
        
        valid_count = 0
        invalid_count = 0
        issues = []
        
        # Build entity lookup
        entity_ids = {e.id for e in self.entities}
        
        for rel in self.relationships:
            if rel.source_id not in entity_ids:
                invalid_count += 1
                issues.append(f"Source '{rel.source_id}' not found")
            elif rel.target_id not in entity_ids:
                invalid_count += 1
                issues.append(f"Target '{rel.target_id}' not found")
            elif rel.source_id == rel.target_id:
                invalid_count += 1
                issues.append("Self-referential relationship")
            else:
                valid_count += 1
        
        # Display results
        text = f"Validation Results:\n\n"
        text += f"Valid: {valid_count}\n"
        text += f"Issues: {invalid_count}\n\n"
        
        if issues:
            text += "Issues Found:\n"
            for issue in issues[:10]:  # Show first 10
                text += f"  • {issue}\n"
            if len(issues) > 10:
                text += f"  ... and {len(issues) - 10} more"
        
        self.validation_text.insert(tk.END, text)
        self.validation_text.config(state=tk.DISABLED)

