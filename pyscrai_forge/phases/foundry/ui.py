"""Phase 1: FOUNDRY - Entity Extraction and Staging UI.

This module provides the main UI panel for the Foundry phase,
which handles entity extraction, editing, and staging to JSON.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING, Callable, Optional, List, Any

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
        self.relationships: List["Relationship"] = []  # Not used in Foundry, but kept for compatibility
        self.validation_report: dict = {}
        
        # UI components
        self.entities_tree: Optional[ttk.Treeview] = None
        self.relationships_tree: Optional[ttk.Treeview] = None  # Not used in Foundry
        self.validation_label: Optional[ttk.Label] = None
        
        # Data manager reference (set by state_manager for entity editing)
        self.data_manager: Optional[Any] = None
        
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
        
        # Main content area with horizontal paned window
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left: Source Data Pool
        source_frame = ttk.Frame(main_paned)
        main_paned.add(source_frame, weight=1)
        self._build_source_pool_panel(source_frame)
        
        # Right: Entities
        entities_frame = ttk.Frame(main_paned)
        main_paned.add(entities_frame, weight=2)
        self._build_entities_panel(entities_frame)
        
        # Bottom action bar
        self._build_action_bar()
    
    def _build_source_pool_panel(self, parent: ttk.Frame) -> None:
        """Build the source data pool panel."""
        # Header
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(
            header_frame,
            text="Source Data Pool",
            font=("Segoe UI", 12, "bold")
        ).pack(side=tk.LEFT)
        
        self.source_count_label = ttk.Label(
            header_frame,
            text="(0 sources)",
            font=("Segoe UI", 10),
            foreground="gray"
        )
        self.source_count_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Toolbar
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(
            toolbar,
            text="Add Files...",
            command=self._on_add_sources
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar,
            text="Toggle Active",
            command=self._on_toggle_source_active
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar,
            text="Remove",
            command=self._on_remove_source
        ).pack(side=tk.LEFT, padx=2)
        
        # Source list treeview
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("filename", "chars", "status", "active")
        self.sources_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8)
        
        self.sources_tree.heading("filename", text="Source File")
        self.sources_tree.heading("chars", text="Chars")
        self.sources_tree.heading("status", text="Status")
        self.sources_tree.heading("active", text="Active")
        
        self.sources_tree.column("filename", width=150)
        self.sources_tree.column("chars", width=60)
        self.sources_tree.column("status", width=70)
        self.sources_tree.column("active", width=50)
        
        # Tag for inactive sources
        self.sources_tree.tag_configure("inactive", foreground="gray")
        self.sources_tree.tag_configure("extracted", foreground="#4a9eff")
        
        self.sources_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        source_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.sources_tree.yview)
        source_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.sources_tree.config(yscrollcommand=source_scroll.set)
        
        # Bind double-click to toggle active
        self.sources_tree.bind("<Double-1>", lambda e: self._on_toggle_source_active())
        
        # Re-extract button at bottom
        extract_frame = ttk.Frame(parent)
        extract_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(
            extract_frame,
            text="Extract from Active Sources",
            command=self._on_extract_from_sources
        ).pack(fill=tk.X)
        
        # Load existing sources
        self._refresh_sources_list()
    
    def _refresh_sources_list(self) -> None:
        """Refresh the sources list from staging."""
        if not self.project_path:
            return
        
        try:
            from pyscrai_forge.src.staging import StagingService
            staging = StagingService(self.project_path)
            sources = staging.get_all_sources()
            
            # Clear current items
            for item in self.sources_tree.get_children():
                self.sources_tree.delete(item)
            
            # Add sources
            active_count = 0
            for source in sources:
                tags = []
                if not source.get("active", True):
                    tags.append("inactive")
                elif source.get("extracted", False):
                    tags.append("extracted")
                else:
                    active_count += 1
                
                if source.get("active", True):
                    active_count += 1
                
                self.sources_tree.insert("", tk.END, iid=source["id"], values=(
                    source.get("original_filename", source["id"]),
                    f"{source.get('char_count', 0):,}",
                    "Extracted" if source.get("extracted") else "Ready",
                    "✓" if source.get("active", True) else "✗"
                ), tags=tuple(tags))
            
            # Update count
            total = len(sources)
            active = sum(1 for s in sources if s.get("active", True))
            self.source_count_label.config(text=f"({active}/{total} active)")
            
        except Exception as e:
            print(f"Error loading sources: {e}")
    
    def _on_add_sources(self) -> None:
        """Add new source files."""
        from tkinter import filedialog
        
        formats = [
            ("All Supported", "*.pdf *.html *.htm *.docx *.png *.jpg *.jpeg *.txt *.md"),
            ("Text Files", "*.txt *.md"),
            ("PDF Files", "*.pdf"),
            ("Word Files", "*.docx"),
            ("HTML Files", "*.html *.htm"),
            ("Images", "*.png *.jpg *.jpeg"),
            ("All Files", "*.*")
        ]
        
        filenames = filedialog.askopenfilenames(parent=self, filetypes=formats)
        if not filenames or not self.project_path:
            return
        
        from pyscrai_forge.src.staging import StagingService
        from pyscrai_forge.src.converters import create_registry, ConversionResult
        
        staging = StagingService(self.project_path)
        registry = create_registry()
        
        added = 0
        for filename in filenames:
            path = Path(filename)
            try:
                # Convert file to text
                if path.suffix.lower() in ('.txt', '.md'):
                    with open(path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    result = ConversionResult(text=text, metadata={})
                else:
                    result = registry.convert(path)
                
                if result.error:
                    messagebox.showerror("Error", f"Failed to convert {path.name}: {result.error}")
                    continue
                
                # Save to source pool
                staging.save_source_file(
                    file_path=path,
                    text_content=result.text,
                    metadata=result.metadata,
                    active=True
                )
                added += 1
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add {path.name}: {e}")
        
        if added > 0:
            self._refresh_sources_list()
            messagebox.showinfo("Sources Added", f"Added {added} source file(s) to the pool.")
    
    def _on_toggle_source_active(self) -> None:
        """Toggle active status for selected sources."""
        selection = self.sources_tree.selection()
        if not selection or not self.project_path:
            return
        
        from pyscrai_forge.src.staging import StagingService
        staging = StagingService(self.project_path)
        
        for source_id in selection:
            try:
                # Get current state
                sources = staging.get_all_sources()
                source = next((s for s in sources if s["id"] == source_id), None)
                if source:
                    new_active = not source.get("active", True)
                    staging.set_source_active(source_id, new_active)
            except Exception as e:
                print(f"Error toggling source {source_id}: {e}")
        
        self._refresh_sources_list()
    
    def _on_remove_source(self) -> None:
        """Remove selected sources from the pool."""
        selection = self.sources_tree.selection()
        if not selection or not self.project_path:
            return
        
        if not messagebox.askyesno("Confirm Removal", 
            f"Remove {len(selection)} source(s) from the pool?\n\nThis will not affect already-extracted entities."):
            return
        
        from pyscrai_forge.src.staging import StagingService
        staging = StagingService(self.project_path)
        
        for source_id in selection:
            try:
                staging.delete_source(source_id)
            except Exception as e:
                print(f"Error removing source {source_id}: {e}")
        
        self._refresh_sources_list()
    
    def _on_extract_from_sources(self) -> None:
        """Trigger extraction from all active sources."""
        # Use the extract_from_pool callback if available
        extract_callback = self.callbacks.get("extract_from_pool")
        if extract_callback:
            extract_callback()
        else:
            # Fallback: show info message
            messagebox.showinfo(
                "Extract from Sources",
                "Please use the 'Import File...' button to trigger extraction."
            )
    
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
        self.entities_tree.bind("<Double-1>", self._on_double_click_entity)
        
        # Enable sorting
        try:
            from pyscrai_forge.src.ui.widgets.treeview_sorter import TreeviewSorter
            self.entities_sorter = TreeviewSorter(self.entities_tree)
            self.entities_sorter.enable_sorting_for_all_columns()
        except ImportError:
            pass
    
    def _build_relationships_panel(self, parent: ttk.Frame) -> None:
        """Build the relationships panel.
        
        NOTE: This method is deprecated for Foundry phase.
        Relationships are handled in the Loom phase (Phase 2).
        This method is kept for compatibility but should not be called.
        """
        # Foundry doesn't display relationships - they're handled in Loom phase
        ttk.Label(
            parent,
            text="Relationships are handled in the Loom phase",
            font=("Segoe UI", 10),
            foreground="gray"
        ).pack(anchor=tk.W, pady=20)
    
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
        # Foundry doesn't display relationships - they're handled in Loom phase
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
        critical = len(self.validation_report.get("critical_errors", []))
        warnings = len(self.validation_report.get("warnings", []))
        
        if critical > 0:
            text = f"{num_entities} entities | {critical} errors"
            self.validation_label.configure(text=text, foreground="#ff5555")
        elif warnings > 0:
            text = f"{num_entities} entities | {warnings} warnings"
            self.validation_label.configure(text=text, foreground="#ffaa00")
        elif num_entities > 0:
            text = f"{num_entities} entities | Valid"
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
    
    def _on_double_click_entity(self, event) -> None:
        """Handle double-click on entity to edit."""
        # Get the selected item
        selection = self.entities_tree.selection()
        if not selection:
            return
        
        # Get entity ID from the first column
        item = selection[0]
        values = self.entities_tree.item(item, "values")
        if not values or len(values) == 0:
            return
        
        entity_id = values[0]  # ID is first column
        
        # Find the entity
        entity = next((e for e in self.entities if e.id == entity_id), None)
        if not entity:
            return
        
        # Ensure data_manager has the entities_tree reference
        if self.data_manager:
            # Temporarily set entities_tree to FoundryPanel's treeview
            old_tree = self.data_manager.entities_tree
            old_entities = self.data_manager.entities
            old_manifest = self.data_manager.manifest
            old_project_path = self.data_manager.project_path
            old_root = self.data_manager.root
            
            self.data_manager.entities_tree = self.entities_tree
            self.data_manager.entities = self.entities
            # Get manifest from callbacks if available
            get_manifest = self.callbacks.get("get_manifest")
            if get_manifest:
                self.data_manager.manifest = get_manifest()
            self.data_manager.project_path = self.project_path
            self.data_manager.root = self.winfo_toplevel()
            
            try:
                # Call edit_entity directly with the entity_id
                self.data_manager.edit_entity(entity_id=entity_id)
            finally:
                # Restore old references
                if old_tree:
                    self.data_manager.entities_tree = old_tree
                if old_entities:
                    self.data_manager.entities = old_entities
                if old_manifest:
                    self.data_manager.manifest = old_manifest
                if old_project_path:
                    self.data_manager.project_path = old_project_path
                if old_root:
                    self.data_manager.root = old_root

