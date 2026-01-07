"""Phase 1: FOUNDRY - Entity Extraction and Staging UI.

This module provides the main UI panel for the Foundry phase,
which handles entity extraction, editing, and staging to JSON.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Callable, Optional, List

if TYPE_CHECKING:
    from pyscrai_core import Entity, Relationship
    from pyscrai_core import ProjectManifest


class FoundryPanel(ttk.Frame):
    """Main panel for the Foundry phase - Entity Extraction and Staging.
    
    Features:
    - Entity listing with validation status
    - Entity editing (double-click)
    - Add/delete entities
    - Staging to entities_staging.json
    - Phase navigation (proceed to Loom)
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        project_path: Optional[Path] = None,
        callbacks: Optional[dict[str, Callable]] = None,
        **kwargs
    ):
        """Initialize the Foundry panel.
        
        Args:
            parent: Parent widget
            project_path: Path to the current project
            callbacks: Dictionary of callback functions for actions
        """
        super().__init__(parent, **kwargs)
        
        self.project_path = project_path
        self.callbacks = callbacks or {}
        
        # Data references (will be set by parent)
        self.entities: List["Entity"] = []
        self.relationships: List["Relationship"] = []
        self.validation_report: dict = {}
        
        # UI components
        self.entities_tree: Optional[ttk.Treeview] = None
        self.relationships_tree: Optional[ttk.Treeview] = None
        self.validation_label: Optional[ttk.Label] = None
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        """Build the Foundry phase UI."""
        # Header with phase info
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        ttk.Label(
            header_frame,
            text="Phase 1: FOUNDRY",
            font=("Segoe UI", 16, "bold")
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            header_frame,
            text="Entity Extraction & Staging",
            font=("Segoe UI", 11),
            foreground="gray"
        ).pack(side=tk.LEFT, padx=(15, 0))
        
        # Validation banner
        validation_frame = ttk.Frame(self)
        validation_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.validation_label = ttk.Label(
            validation_frame,
            text="No entities loaded",
            font=("Segoe UI", 10)
        )
        self.validation_label.pack(side=tk.LEFT)
        
        # Main content paned window
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left: Entities panel
        entities_frame = ttk.Frame(paned)
        paned.add(entities_frame, weight=2)
        
        self._build_entities_panel(entities_frame)
        
        # Right: Relationships panel
        rel_frame = ttk.Frame(paned)
        paned.add(rel_frame, weight=1)
        
        self._build_relationships_panel(rel_frame)
        
        # Bottom action bar
        self._build_action_bar()
    
    def _build_entities_panel(self, parent: ttk.Frame) -> None:
        """Build the entities panel."""
        # Header
        ttk.Label(
            parent,
            text="Entities",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor=tk.W, pady=(0, 5))
        
        # Toolbar
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(
            toolbar,
            text="Import File...",
            command=self.callbacks.get("import_file", lambda: None)
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar,
            text="Load Data...",
            command=self.callbacks.get("load_data_file", lambda: None)
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=8, fill=tk.Y, pady=2)
        
        ttk.Button(
            toolbar,
            text="Add Entity",
            command=self.callbacks.get("add_entity", lambda: None)
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar,
            text="Delete Selected",
            command=self.callbacks.get("delete_selected_entity", lambda: None)
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=8, fill=tk.Y, pady=2)
        
        ttk.Button(
            toolbar,
            text="Refine with AI",
            command=self.callbacks.get("refine_components", lambda: None)
        ).pack(side=tk.LEFT, padx=2)
        
        # Treeview
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.entities_tree = ttk.Treeview(
            tree_frame,
            columns=("id", "type", "name", "issues"),
            show="headings",
            selectmode=tk.EXTENDED
        )
        
        self.entities_tree.heading("id", text="ID")
        self.entities_tree.heading("type", text="Type")
        self.entities_tree.heading("name", text="Name")
        self.entities_tree.heading("issues", text="Issues")
        
        self.entities_tree.column("id", width=120)
        self.entities_tree.column("type", width=80)
        self.entities_tree.column("name", width=150)
        self.entities_tree.column("issues", width=150)
        
        # Tag configuration for validation status
        self.entities_tree.tag_configure("error", background="#550000", foreground="white")
        self.entities_tree.tag_configure("warning", background="#554400", foreground="white")
        self.entities_tree.tag_configure("valid", background="", foreground="")
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.entities_tree.yview)
        self.entities_tree.configure(yscrollcommand=scrollbar.set)
        
        self.entities_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Double-click to edit
        self.entities_tree.bind("<Double-1>", lambda e: self.callbacks.get("edit_entity", lambda: None)())
        
        # Enable sorting
        try:
            from pyscrai_forge.src.ui.widgets.treeview_sorter import TreeviewSorter
            self.entities_sorter = TreeviewSorter(self.entities_tree)
            self.entities_sorter.enable_sorting_for_all_columns()
        except ImportError:
            pass
    
    def _build_relationships_panel(self, parent: ttk.Frame) -> None:
        """Build the relationships panel."""
        # Header
        ttk.Label(
            parent,
            text="Relationships",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor=tk.W, pady=(0, 5))
        
        # Toolbar
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(
            toolbar,
            text="Add Relationship",
            command=self.callbacks.get("add_relationship", lambda: None)
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar,
            text="Delete Selected",
            command=self.callbacks.get("delete_selected_relationship", lambda: None)
        ).pack(side=tk.LEFT, padx=2)
        
        # Treeview
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.relationships_tree = ttk.Treeview(
            tree_frame,
            columns=("source", "target", "type", "issues"),
            show="headings",
            selectmode=tk.EXTENDED
        )
        
        self.relationships_tree.heading("source", text="Source")
        self.relationships_tree.heading("target", text="Target")
        self.relationships_tree.heading("type", text="Type")
        self.relationships_tree.heading("issues", text="Issues")
        
        self.relationships_tree.column("source", width=100)
        self.relationships_tree.column("target", width=100)
        self.relationships_tree.column("type", width=80)
        self.relationships_tree.column("issues", width=100)
        
        self.relationships_tree.tag_configure("error", background="#550000", foreground="white")
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.relationships_tree.yview)
        self.relationships_tree.configure(yscrollcommand=scrollbar.set)
        
        self.relationships_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Double-click to edit
        self.relationships_tree.bind("<Double-1>", lambda e: self.callbacks.get("edit_relationship", lambda: None)())
        
        # Enable sorting
        try:
            from pyscrai_forge.src.ui.widgets.treeview_sorter import TreeviewSorter
            self.relationships_sorter = TreeviewSorter(self.relationships_tree)
            self.relationships_sorter.enable_sorting_for_all_columns()
        except ImportError:
            pass
    
    def _build_action_bar(self) -> None:
        """Build the bottom action bar with staging and navigation."""
        action_frame = ttk.Frame(self)
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Left: Project info
        project_text = f"Project: {self.project_path.name if self.project_path else 'None'}"
        ttk.Label(
            action_frame,
            text=project_text,
            font=("Segoe UI", 9, "italic"),
            foreground="gray"
        ).pack(side=tk.LEFT)
        
        # Right: Action buttons
        ttk.Button(
            action_frame,
            text="← Back to Dashboard",
            command=self.callbacks.get("transition_to_dashboard", lambda: None)
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            action_frame,
            text="Proceed to Loom →",
            command=self._on_proceed_to_loom
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Separator(action_frame, orient=tk.VERTICAL).pack(side=tk.RIGHT, padx=10, fill=tk.Y, pady=2)
        
        ttk.Button(
            action_frame,
            text="Save to Staging",
            command=self._on_save_staging
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            action_frame,
            text="Commit to Database",
            command=self.callbacks.get("commit_to_db", lambda: None)
        ).pack(side=tk.RIGHT, padx=5)
    
    def _on_save_staging(self) -> None:
        """Save current entities to staging JSON."""
        if not self.project_path:
            messagebox.showwarning("No Project", "Please load a project first.")
            return
        
        if not self.entities:
            messagebox.showinfo("No Data", "No entities to save to staging.")
            return
        
        try:
            from pyscrai_forge.src.staging import StagingService
            
            staging = StagingService(self.project_path)
            artifact_path = staging.save_entities_staging(
                entities=self.entities,
                source_text="",
                metadata={"phase": "foundry"}
            )
            
            messagebox.showinfo(
                "Staging Saved",
                f"Saved {len(self.entities)} entities to staging.\n\n{artifact_path}"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save staging: {e}")
    
    def _on_proceed_to_loom(self) -> None:
        """Proceed to Loom phase after saving staging."""
        if not self.entities:
            if not messagebox.askyesno(
                "No Entities",
                "No entities to proceed with. Continue to Loom anyway?"
            ):
                return
        
        # Auto-save to staging before proceeding
        if self.entities and self.project_path:
            try:
                from pyscrai_forge.src.staging import StagingService
                staging = StagingService(self.project_path)
                staging.save_entities_staging(self.entities)
            except Exception as e:
                if not messagebox.askyesno(
                    "Staging Error",
                    f"Failed to save staging: {e}\n\nContinue anyway?"
                ):
                    return
        
        # Call the navigation callback
        go_to_loom = self.callbacks.get("go_to_loom")
        if go_to_loom:
            go_to_loom()
    
    def set_data(
        self,
        entities: List["Entity"],
        relationships: List["Relationship"],
        validation_report: dict
    ) -> None:
        """Set the data to display.
        
        Args:
            entities: List of Entity objects
            relationships: List of Relationship objects
            validation_report: Validation report dictionary
        """
        self.entities = entities
        self.relationships = relationships
        self.validation_report = validation_report
        self.refresh()
    
    def refresh(self) -> None:
        """Refresh the UI with current data."""
        self._refresh_entities()
        self._refresh_relationships()
        self._refresh_validation()
    
    def _refresh_entities(self) -> None:
        """Refresh the entities treeview."""
        if not self.entities_tree:
            return
        
        # Clear existing items
        for item in self.entities_tree.get_children():
            self.entities_tree.delete(item)
        
        # Get entity issues from validation report
        entity_issues = {}
        for error in self.validation_report.get("critical_errors", []):
            if "entity_id" in error:
                entity_issues.setdefault(error["entity_id"], []).append(error.get("message", "Error"))
        
        # Add entities
        for entity in self.entities:
            entity_type = ""
            if hasattr(entity, "descriptor") and hasattr(entity.descriptor, "entity_type"):
                entity_type = entity.descriptor.entity_type.value if hasattr(entity.descriptor.entity_type, "value") else str(entity.descriptor.entity_type)
            
            name = ""
            if hasattr(entity, "descriptor") and hasattr(entity.descriptor, "name"):
                name = entity.descriptor.name
            
            issues = entity_issues.get(entity.id, [])
            issues_str = "; ".join(issues) if issues else ""
            
            tag = "error" if issues else "valid"
            
            self.entities_tree.insert(
                "",
                tk.END,
                values=(entity.id, entity_type, name, issues_str),
                tags=(tag,)
            )
    
    def _refresh_relationships(self) -> None:
        """Refresh the relationships treeview."""
        if not self.relationships_tree:
            return
        
        # Clear existing items
        for item in self.relationships_tree.get_children():
            self.relationships_tree.delete(item)
        
        # Build entity name lookup
        entity_names = {}
        for entity in self.entities:
            if hasattr(entity, "descriptor") and hasattr(entity.descriptor, "name"):
                entity_names[entity.id] = entity.descriptor.name
            else:
                entity_names[entity.id] = entity.id
        
        # Add relationships
        for rel in self.relationships:
            source_name = entity_names.get(rel.source_id, rel.source_id)
            target_name = entity_names.get(rel.target_id, rel.target_id)
            
            rel_type = ""
            if hasattr(rel, "relationship_type"):
                rel_type = rel.relationship_type.value if hasattr(rel.relationship_type, "value") else str(rel.relationship_type)
            
            # Check for orphaned relationships
            orphaned = rel.source_id not in entity_names or rel.target_id not in entity_names
            issues = "Orphaned" if orphaned else ""
            tag = "error" if orphaned else ""
            
            self.relationships_tree.insert(
                "",
                tk.END,
                values=(source_name, target_name, rel_type, issues),
                tags=(tag,) if tag else ()
            )
    
    def _refresh_validation(self) -> None:
        """Refresh the validation status label."""
        if not self.validation_label:
            return
        
        num_entities = len(self.entities)
        num_relationships = len(self.relationships)
        critical = len(self.validation_report.get("critical_errors", []))
        warnings = len(self.validation_report.get("warnings", []))
        
        if critical > 0:
            text = f"{num_entities} entities, {num_relationships} relationships | {critical} errors"
            self.validation_label.configure(text=text, foreground="#ff5555")
        elif warnings > 0:
            text = f"{num_entities} entities, {num_relationships} relationships | {warnings} warnings"
            self.validation_label.configure(text=text, foreground="#ffaa00")
        elif num_entities > 0:
            text = f"{num_entities} entities, {num_relationships} relationships | Valid"
            self.validation_label.configure(text=text, foreground="#55ff55")
        else:
            text = "No entities loaded"
            self.validation_label.configure(text=text, foreground="gray")
    
    def get_selected_entity_ids(self) -> List[str]:
        """Get IDs of selected entities."""
        selected = self.entities_tree.selection() if self.entities_tree else []
        ids = []
        for item in selected:
            values = self.entities_tree.item(item, "values")
            if values:
                ids.append(values[0])  # ID is first column
        return ids
    
    def get_selected_relationship_ids(self) -> List[str]:
        """Get IDs of selected relationships (using index as ID)."""
        selected = self.relationships_tree.selection() if self.relationships_tree else []
        # For relationships, we return the index since they may not have stable IDs
        indices = []
        all_items = self.relationships_tree.get_children() if self.relationships_tree else []
        for item in selected:
            try:
                idx = all_items.index(item)
                indices.append(idx)
            except ValueError:
                pass
        return indices

