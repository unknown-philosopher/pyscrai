"""Phase 5: ANVIL - Finalization and Merge UI Panel.

This module provides the main UI panel for the Anvil phase,
handling merge conflict resolution and database commit.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from pyscrai_core import Entity, Relationship

from pyscrai_forge.phases.anvil.merger import (
    MergeAction,
    MergeConflict,
    SmartMergeEngine,
)


class AnvilPanel(ttk.Frame):
    """Main panel for the Anvil phase - Finalization and Merge.
    
    Features:
    - Staging vs Canon diff viewer
    - Conflict resolution UI
    - Merge/Reject/Skip controls
    - Provenance tracking display
    - Final commit to world.db
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        project_path: Optional[Path] = None,
        callbacks: Optional[dict[str, Callable]] = None,
        **kwargs
    ):
        """Initialize the Anvil panel.
        
        Args:
            parent: Parent widget
            project_path: Path to the current project
            callbacks: Dictionary of callback functions
        """
        super().__init__(parent, **kwargs)
        
        self.project_path = project_path
        self.callbacks = callbacks or {}
        self.db_path = project_path / "world.db" if project_path else None
        
        # Data
        self.staging_entities: List["Entity"] = []
        self.staging_relationships: List["Relationship"] = []
        self.canon_entities: List["Entity"] = []
        self.canon_relationships: List["Relationship"] = []
        self.conflicts: List[MergeConflict] = []
        self.resolutions: Dict[str, MergeAction] = {}
        
        # Merge engine
        self.merge_engine = SmartMergeEngine(similarity_threshold=0.8)
        
        # UI components
        self.staging_tree: Optional[ttk.Treeview] = None
        self.canon_tree: Optional[ttk.Treeview] = None
        self.conflict_tree: Optional[ttk.Treeview] = None
        self.diff_text: Optional[tk.Text] = None
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        """Build the Anvil phase UI."""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        ttk.Label(
            header_frame,
            text="Phase 5: ANVIL",
            font=("Segoe UI", 16, "bold")
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            header_frame,
            text="Finalization & Merge",
            font=("Segoe UI", 11),
            foreground="gray"
        ).pack(side=tk.LEFT, padx=(15, 0))
        
        # Stats bar
        self.stats_label = ttk.Label(
            header_frame,
            text="",
            font=("Segoe UI", 9),
            foreground="gray"
        )
        self.stats_label.pack(side=tk.RIGHT)
        
        # Main content - three columns
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left: Staging data
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)
        self._build_staging_panel(left_frame)
        
        # Center: Diff viewer
        center_frame = ttk.Frame(main_paned)
        main_paned.add(center_frame, weight=1)
        self._build_diff_panel(center_frame)
        
        # Right: Canon data
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)
        self._build_canon_panel(right_frame)
        
        # Bottom: Conflicts and actions
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=tk.X, padx=10, pady=5)
        self._build_conflicts_panel(bottom_frame)
        
        # Action bar
        self._build_action_bar()
    
    def _build_staging_panel(self, parent: ttk.Frame) -> None:
        """Build the staging data panel."""
        # Header
        header = ttk.Frame(parent)
        header.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(header, text="Staging Data", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        
        ttk.Button(
            header,
            text="Load",
            command=self._on_load_staging,
            width=8
        ).pack(side=tk.RIGHT)
        
        # Treeview
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.staging_tree = ttk.Treeview(
            tree_frame,
            columns=("name", "type", "action"),
            show="headings",
            selectmode=tk.BROWSE
        )
        
        self.staging_tree.heading("name", text="Name")
        self.staging_tree.heading("type", text="Type")
        self.staging_tree.heading("action", text="Action")
        
        self.staging_tree.column("name", width=100)
        self.staging_tree.column("type", width=60)
        self.staging_tree.column("action", width=60)
        
        # Color by action
        self.staging_tree.tag_configure("create", foreground="#55ff55")
        self.staging_tree.tag_configure("update", foreground="#ffff55")
        self.staging_tree.tag_configure("merge", foreground="#55ffff")
        self.staging_tree.tag_configure("skip", foreground="#888888")
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.staging_tree.yview)
        self.staging_tree.configure(yscrollcommand=scrollbar.set)
        
        self.staging_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.staging_tree.bind("<<TreeviewSelect>>", self._on_staging_select)
    
    def _build_diff_panel(self, parent: ttk.Frame) -> None:
        """Build the diff viewer panel."""
        # Header
        header = ttk.Frame(parent)
        header.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(header, text="Differences", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        
        # Diff text
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.diff_text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            state=tk.DISABLED
        )
        
        # Configure tags for diff highlighting
        self.diff_text.tag_configure("added", foreground="#55ff55")
        self.diff_text.tag_configure("removed", foreground="#ff5555")
        self.diff_text.tag_configure("changed", foreground="#ffff55")
        self.diff_text.tag_configure("header", foreground="#569cd6", font=("Consolas", 10, "bold"))
        
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.diff_text.yview)
        self.diff_text.configure(yscrollcommand=scrollbar.set)
        
        self.diff_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _build_canon_panel(self, parent: ttk.Frame) -> None:
        """Build the canon database panel."""
        # Header
        header = ttk.Frame(parent)
        header.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(header, text="Canon Database", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        
        ttk.Button(
            header,
            text="Refresh",
            command=self._on_load_canon,
            width=8
        ).pack(side=tk.RIGHT)
        
        # Treeview
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canon_tree = ttk.Treeview(
            tree_frame,
            columns=("name", "type"),
            show="headings",
            selectmode=tk.BROWSE
        )
        
        self.canon_tree.heading("name", text="Name")
        self.canon_tree.heading("type", text="Type")
        
        self.canon_tree.column("name", width=120)
        self.canon_tree.column("type", width=60)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.canon_tree.yview)
        self.canon_tree.configure(yscrollcommand=scrollbar.set)
        
        self.canon_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canon_tree.bind("<<TreeviewSelect>>", self._on_canon_select)
    
    def _build_conflicts_panel(self, parent: ttk.Frame) -> None:
        """Build the conflicts panel."""
        conflicts_frame = ttk.LabelFrame(parent, text="Merge Conflicts", padding=10)
        conflicts_frame.pack(fill=tk.X)
        
        # Action buttons
        btn_frame = ttk.Frame(conflicts_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(
            btn_frame,
            text="Analyze",
            command=self._on_analyze_merge,
            width=10
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            btn_frame,
            text="Create",
            command=lambda: self._set_selected_action(MergeAction.CREATE),
            width=8
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            btn_frame,
            text="Update",
            command=lambda: self._set_selected_action(MergeAction.UPDATE),
            width=8
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            btn_frame,
            text="Merge",
            command=lambda: self._set_selected_action(MergeAction.MERGE),
            width=8
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            btn_frame,
            text="Skip",
            command=lambda: self._set_selected_action(MergeAction.SKIP),
            width=8
        ).pack(side=tk.LEFT, padx=2)
        
        # Conflict list
        tree_frame = ttk.Frame(conflicts_frame)
        tree_frame.pack(fill=tk.X)
        
        self.conflict_tree = ttk.Treeview(
            tree_frame,
            columns=("staging", "conflict", "canon", "similarity", "action"),
            show="headings",
            height=4,
            selectmode=tk.BROWSE
        )
        
        self.conflict_tree.heading("staging", text="Staging")
        self.conflict_tree.heading("conflict", text="Conflict")
        self.conflict_tree.heading("canon", text="Canon")
        self.conflict_tree.heading("similarity", text="Sim%")
        self.conflict_tree.heading("action", text="Action")
        
        self.conflict_tree.column("staging", width=100)
        self.conflict_tree.column("conflict", width=120)
        self.conflict_tree.column("canon", width=100)
        self.conflict_tree.column("similarity", width=50)
        self.conflict_tree.column("action", width=60)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.conflict_tree.yview)
        self.conflict_tree.configure(yscrollcommand=scrollbar.set)
        
        self.conflict_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.conflict_tree.bind("<<TreeviewSelect>>", self._on_conflict_select)
    
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
            text="← Back to Cartography",
            command=self.callbacks.get("go_to_cartography", lambda: None)
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            action_frame,
            text="Commit to World DB",
            command=self._on_commit
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Separator(action_frame, orient=tk.VERTICAL).pack(side=tk.RIGHT, padx=10, fill=tk.Y, pady=2)
        
        ttk.Button(
            action_frame,
            text="Return to Dashboard",
            command=self.callbacks.get("transition_to_dashboard", lambda: None)
        ).pack(side=tk.RIGHT, padx=5)
    
    def set_data(
        self,
        entities: List["Entity"],
        relationships: List["Relationship"]
    ) -> None:
        """Set the staging data.
        
        Args:
            entities: Entities from staging
            relationships: Relationships from staging
        """
        self.staging_entities = entities
        self.staging_relationships = relationships
        
        # Set default actions
        for entity in entities:
            if entity.id not in self.resolutions:
                self.resolutions[entity.id] = MergeAction.CREATE
        
        self._refresh_staging_tree()
        self._on_load_canon()
        self._update_stats()
    
    def _refresh_staging_tree(self) -> None:
        """Refresh the staging treeview."""
        if not self.staging_tree:
            return
        
        for item in self.staging_tree.get_children():
            self.staging_tree.delete(item)
        
        for entity in self.staging_entities:
            name = entity.descriptor.name if hasattr(entity, "descriptor") else entity.id
            entity_type = ""
            if hasattr(entity, "descriptor") and hasattr(entity.descriptor, "entity_type"):
                entity_type = entity.descriptor.entity_type.value if hasattr(entity.descriptor.entity_type, "value") else ""
            
            action = self.resolutions.get(entity.id, MergeAction.CREATE)
            
            self.staging_tree.insert(
                "",
                tk.END,
                iid=entity.id,
                values=(name, entity_type[:6], action.value),
                tags=(action.value,)
            )
    
    def _refresh_canon_tree(self) -> None:
        """Refresh the canon treeview."""
        if not self.canon_tree:
            return
        
        for item in self.canon_tree.get_children():
            self.canon_tree.delete(item)
        
        for entity in self.canon_entities:
            name = entity.descriptor.name if hasattr(entity, "descriptor") else entity.id
            entity_type = ""
            if hasattr(entity, "descriptor") and hasattr(entity.descriptor, "entity_type"):
                entity_type = entity.descriptor.entity_type.value if hasattr(entity.descriptor.entity_type, "value") else ""
            
            self.canon_tree.insert(
                "",
                tk.END,
                iid=entity.id,
                values=(name, entity_type[:6])
            )
    
    def _refresh_conflicts_tree(self) -> None:
        """Refresh the conflicts treeview."""
        if not self.conflict_tree:
            return
        
        for item in self.conflict_tree.get_children():
            self.conflict_tree.delete(item)
        
        for i, conflict in enumerate(self.conflicts):
            action = self.resolutions.get(conflict.staging_id, conflict.suggested_action)
            
            self.conflict_tree.insert(
                "",
                tk.END,
                iid=str(i),
                values=(
                    conflict.staging_id[:15],
                    conflict.conflict_type.value,
                    conflict.canon_id[:15] if conflict.canon_id else "-",
                    f"{conflict.similarity * 100:.0f}%",
                    action.value
                )
            )
    
    def _on_load_staging(self) -> None:
        """Load staging data from files."""
        if not self.project_path:
            messagebox.showwarning("No Project", "Please load a project first.")
            return
        
        try:
            from pyscrai_forge.src.staging import StagingService
            from pyscrai_core import Entity, Relationship
            
            staging = StagingService(self.project_path)
            
            # Load graph staging (includes entities and relationships)
            entity_dicts, rel_dicts, _ = staging.load_graph_staging()
            
            self.staging_entities = [Entity.model_validate(e) for e in entity_dicts]
            self.staging_relationships = [Relationship.model_validate(r) for r in rel_dicts]
            
            # Set default actions
            for entity in self.staging_entities:
                if entity.id not in self.resolutions:
                    self.resolutions[entity.id] = MergeAction.CREATE
            
            self._refresh_staging_tree()
            self._update_stats()
            
            messagebox.showinfo(
                "Staging Loaded",
                f"Loaded {len(self.staging_entities)} entities and {len(self.staging_relationships)} relationships."
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load staging: {e}")
    
    def _on_load_canon(self) -> None:
        """Load canon data from database."""
        if not self.db_path or not self.db_path.exists():
            return
        
        try:
            from pyscrai_forge.src import storage
            
            self.canon_entities = storage.load_all_entities(self.db_path)
            self.canon_relationships = storage.load_all_relationships(self.db_path)
            
            self._refresh_canon_tree()
            self._update_stats()
            
        except Exception as e:
            logger.warning(f"Failed to load canon data: {e}")
    
    def _on_analyze_merge(self) -> None:
        """Analyze staging for merge conflicts."""
        if not self.staging_entities:
            messagebox.showinfo("No Data", "Load staging data first.")
            return
        
        self.conflicts = self.merge_engine.analyze_merge(
            staging_entities=self.staging_entities,
            canon_entities=self.canon_entities,
            staging_relationships=self.staging_relationships,
            canon_relationships=self.canon_relationships
        )
        
        # Apply suggested actions
        for conflict in self.conflicts:
            self.resolutions[conflict.staging_id] = conflict.suggested_action
        
        self._refresh_conflicts_tree()
        self._refresh_staging_tree()
        
        summary = self.merge_engine.get_merge_summary(self.conflicts)
        messagebox.showinfo(
            "Analysis Complete",
            f"Found {summary['total']} conflicts:\n"
            + "\n".join(f"  • {k}: {v}" for k, v in summary['by_type'].items())
        )
    
    def _on_staging_select(self, event) -> None:
        """Handle staging item selection."""
        selection = self.staging_tree.selection()
        if not selection:
            return
        
        entity_id = selection[0]
        self._show_entity_diff(entity_id)
    
    def _on_canon_select(self, event) -> None:
        """Handle canon item selection."""
        selection = self.canon_tree.selection()
        if not selection:
            return
        
        entity_id = selection[0]
        self._show_entity_details(entity_id, "canon")
    
    def _on_conflict_select(self, event) -> None:
        """Handle conflict selection."""
        selection = self.conflict_tree.selection()
        if not selection:
            return
        
        idx = int(selection[0])
        if 0 <= idx < len(self.conflicts):
            conflict = self.conflicts[idx]
            self._show_conflict_diff(conflict)
    
    def _show_entity_diff(self, entity_id: str) -> None:
        """Show diff for a staging entity."""
        self.diff_text.configure(state=tk.NORMAL)
        self.diff_text.delete("1.0", tk.END)
        
        # Find the entity
        staging_entity = None
        for e in self.staging_entities:
            if e.id == entity_id:
                staging_entity = e
                break
        
        if not staging_entity:
            self.diff_text.insert(tk.END, "Entity not found")
            self.diff_text.configure(state=tk.DISABLED)
            return
        
        # Show entity details
        self.diff_text.insert(tk.END, "STAGING ENTITY\n", "header")
        self.diff_text.insert(tk.END, f"ID: {staging_entity.id}\n")
        
        if hasattr(staging_entity, "descriptor"):
            desc = staging_entity.descriptor
            self.diff_text.insert(tk.END, f"Name: {getattr(desc, 'name', 'N/A')}\n", "added")
            self.diff_text.insert(tk.END, f"Type: {getattr(desc, 'entity_type', 'N/A')}\n")
            self.diff_text.insert(tk.END, f"Description: {getattr(desc, 'description', 'N/A')}\n")
        
        # Check for matching canon entity
        canon_entity = None
        for e in self.canon_entities:
            if e.id == entity_id:
                canon_entity = e
                break
        
        if canon_entity:
            self.diff_text.insert(tk.END, "\nCANON ENTITY\n", "header")
            if hasattr(canon_entity, "descriptor"):
                desc = canon_entity.descriptor
                self.diff_text.insert(tk.END, f"Name: {getattr(desc, 'name', 'N/A')}\n", "removed")
        
        self.diff_text.configure(state=tk.DISABLED)
    
    def _show_entity_details(self, entity_id: str, source: str) -> None:
        """Show entity details."""
        entities = self.canon_entities if source == "canon" else self.staging_entities
        
        entity = None
        for e in entities:
            if e.id == entity_id:
                entity = e
                break
        
        if not entity:
            return
        
        self.diff_text.configure(state=tk.NORMAL)
        self.diff_text.delete("1.0", tk.END)
        
        self.diff_text.insert(tk.END, f"{source.upper()} ENTITY\n", "header")
        self.diff_text.insert(tk.END, f"ID: {entity.id}\n")
        
        if hasattr(entity, "descriptor"):
            desc = entity.descriptor
            self.diff_text.insert(tk.END, f"Name: {getattr(desc, 'name', 'N/A')}\n")
            self.diff_text.insert(tk.END, f"Type: {getattr(desc, 'entity_type', 'N/A')}\n")
            self.diff_text.insert(tk.END, f"Description: {getattr(desc, 'description', 'N/A')}\n")
        
        self.diff_text.configure(state=tk.DISABLED)
    
    def _show_conflict_diff(self, conflict: MergeConflict) -> None:
        """Show diff for a conflict."""
        self.diff_text.configure(state=tk.NORMAL)
        self.diff_text.delete("1.0", tk.END)
        
        self.diff_text.insert(tk.END, f"CONFLICT: {conflict.conflict_type.value}\n", "header")
        self.diff_text.insert(tk.END, f"{conflict.description}\n\n")
        self.diff_text.insert(tk.END, f"Similarity: {conflict.similarity * 100:.1f}%\n")
        self.diff_text.insert(tk.END, f"Suggested: {conflict.suggested_action.value}\n\n")
        
        if conflict.details and "differences" in conflict.details:
            self.diff_text.insert(tk.END, "DIFFERENCES\n", "header")
            for diff in conflict.details["differences"]:
                self.diff_text.insert(tk.END, f"  {diff['attribute']}:\n")
                self.diff_text.insert(tk.END, f"    - {diff['canon']}\n", "removed")
                self.diff_text.insert(tk.END, f"    + {diff['staging']}\n", "added")
        
        self.diff_text.configure(state=tk.DISABLED)
    
    def _set_selected_action(self, action: MergeAction) -> None:
        """Set action for selected item."""
        # Check staging selection
        staging_selection = self.staging_tree.selection()
        if staging_selection:
            entity_id = staging_selection[0]
            self.resolutions[entity_id] = action
            self._refresh_staging_tree()
            self._refresh_conflicts_tree()
            return
        
        # Check conflict selection
        conflict_selection = self.conflict_tree.selection()
        if conflict_selection:
            idx = int(conflict_selection[0])
            if 0 <= idx < len(self.conflicts):
                entity_id = self.conflicts[idx].staging_id
                self.resolutions[entity_id] = action
                self._refresh_staging_tree()
                self._refresh_conflicts_tree()
    
    def _update_stats(self) -> None:
        """Update the stats label."""
        staging_count = len(self.staging_entities)
        canon_count = len(self.canon_entities)
        conflict_count = len(self.conflicts)
        
        self.stats_label.configure(
            text=f"Staging: {staging_count} | Canon: {canon_count} | Conflicts: {conflict_count}"
        )
    
    def _on_commit(self) -> None:
        """Commit changes to the database."""
        if not self.staging_entities:
            messagebox.showinfo("No Data", "No staging data to commit.")
            return
        
        if not self.db_path:
            messagebox.showerror("Error", "No database path set.")
            return
        
        # Count actions
        action_counts = {}
        for entity_id, action in self.resolutions.items():
            action_counts[action.value] = action_counts.get(action.value, 0) + 1
        
        summary = "\n".join(f"  {k}: {v}" for k, v in action_counts.items())
        
        if not messagebox.askyesno(
            "Confirm Commit",
            f"Commit the following changes?\n\n{summary}\n\nThis cannot be undone."
        ):
            return
        
        try:
            result = self.merge_engine.execute_merge(
                staging_entities=self.staging_entities,
                staging_relationships=self.staging_relationships,
                resolutions=self.resolutions,
                db_path=self.db_path
            )
            
            # Track provenance
            try:
                from pyscrai_forge.phases.anvil.provenance import ProvenanceTracker
                tracker = ProvenanceTracker(self.db_path)
                
                for entity in self.staging_entities:
                    action = self.resolutions.get(entity.id)
                    if action in (MergeAction.CREATE, MergeAction.UPDATE):
                        tracker.record_entity_changes(
                            old_entity=None,
                            new_entity=entity,
                            source="anvil:merge"
                        )
            except Exception as e:
                logger.warning(f"Provenance tracking failed: {e}")
            
            messagebox.showinfo(
                "Commit Complete",
                f"Successfully committed:\n"
                f"  Created: {len(result.created)}\n"
                f"  Updated: {len(result.updated)}\n"
                f"  Merged: {len(result.merged)}\n"
                f"  Skipped: {len(result.skipped)}"
            )
            
            # Refresh canon view
            self._on_load_canon()
            
        except Exception as e:
            messagebox.showerror("Error", f"Commit failed: {e}")


# Import logger
import logging
logger = logging.getLogger(__name__)

