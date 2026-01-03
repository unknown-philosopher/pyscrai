# pyscrai_forge/harvester/ui/windows/db_explorer.py
"""Database explorer window for browsing entities and relationships."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Optional, List
from pyscrai_core import Entity, Relationship
from pyscrai_forge.src import storage
from ..widgets.stats_panel import StatsPanelWidget
from ..dialogs.query_dialog import QueryDialog
from ..entity_editor import TabbedEntityEditor
from ..relationship_editor import RelationshipEditor


class DatabaseExplorerWindow(tk.Toplevel):
    """Window for browsing and managing database contents."""

    def __init__(self, parent, db_path: Optional[Path] = None):
        """
        Initialize the database explorer.

        Args:
            parent: Parent window
            db_path: Optional initial database path
        """
        super().__init__(parent)
        self.title("Database Explorer")
        self.geometry("1200x800")
        self.transient(parent)

        self.db_path = db_path
        self.entities: List[Entity] = []
        self.relationships: List[Relationship] = []

        self._create_ui()

    def _create_ui(self):
        """Build the window UI."""
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="Open Database...", command=self._open_database).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Refresh", command=self._load_database).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="SQL Query...", command=self._open_query_dialog).pack(side=tk.LEFT, padx=2)

        # Red Reset DB button
        reset_btn = ttk.Button(toolbar, text="Reset DB", command=self._reset_database)
        reset_btn.pack(side=tk.LEFT, padx=12)

        self.db_label = ttk.Label(toolbar, text="No database loaded", foreground="gray")
        self.db_label.pack(side=tk.LEFT, padx=20)

        # Main paned window
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left: Entity/Relationship browser
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=3)

        # Notebook for entities and relationships
        self.browser_notebook = ttk.Notebook(left_frame)
        self.browser_notebook.pack(fill=tk.BOTH, expand=True)

        self._create_entities_tab()
        self._create_relationships_tab()

        # Right: Statistics panel
        right_frame = ttk.Frame(paned, width=250)
        paned.add(right_frame, weight=1)

        self.stats_panel = StatsPanelWidget(right_frame)
        self.stats_panel.pack(fill=tk.BOTH, expand=True)

        # Bottom status bar
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        self.status_label = ttk.Label(status_frame, text="Ready", foreground="gray")
        self.status_label.pack(side=tk.LEFT)

        ttk.Button(status_frame, text="Close", command=self.destroy).pack(side=tk.RIGHT)

        # Only load database after all widgets are created
        if self.db_path:
            self._load_database()

    def _reset_database(self):
        """Completely wipe all entities and relationships from the database after confirmation."""
        if not self.db_path or not self.db_path.exists():
            messagebox.showwarning("No Database", "Please select a database file first.", parent=self)
            return

        if not messagebox.askyesno(
            "Confirm Database Reset",
            "Are you sure you want to completely RESET this database?\n\nThis will permanently delete ALL entities and relationships.\n\nThis action cannot be undone.",
            parent=self
        ):
            return

        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM entities")
            cursor.execute("DELETE FROM relationships")
            conn.commit()
            conn.close()
            self._load_database()
            self.status_label.config(text="✓ Database reset (all data deleted)", foreground="red")
        except Exception as e:
            messagebox.showerror("Reset Error", f"Failed to reset database:\n\n{str(e)}", parent=self)


        # Main paned window
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left: Entity/Relationship browser
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=3)

        # Notebook for entities and relationships
        self.browser_notebook = ttk.Notebook(left_frame)
        self.browser_notebook.pack(fill=tk.BOTH, expand=True)

        self._create_entities_tab()
        self._create_relationships_tab()

        # Right: Statistics panel
        right_frame = ttk.Frame(paned, width=250)
        paned.add(right_frame, weight=1)

        self.stats_panel = StatsPanelWidget(right_frame)
        self.stats_panel.pack(fill=tk.BOTH, expand=True)

        # Bottom status bar
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        self.status_label = ttk.Label(status_frame, text="Ready", foreground="gray")
        self.status_label.pack(side=tk.LEFT)

        ttk.Button(status_frame, text="Close", command=self.destroy).pack(side=tk.RIGHT)

    def _create_entities_tab(self):
        """Create the entities browser tab."""
        tab = ttk.Frame(self.browser_notebook)
        self.browser_notebook.add(tab, text="Entities")

        # Toolbar
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(toolbar, text="Edit", command=self._edit_entity).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Delete", command=self._delete_entity).pack(side=tk.LEFT, padx=2)

        ttk.Label(toolbar, text="Filter:").pack(side=tk.LEFT, padx=(20, 5))
        self.entity_filter_var = tk.StringVar()
        self.entity_filter_var.trace_add("write", lambda *args: self._apply_entity_filter())
        ttk.Entry(toolbar, textvariable=self.entity_filter_var, width=30).pack(side=tk.LEFT)

        # Treeview
        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.entities_tree = ttk.Treeview(
            tree_frame,
            columns=("id", "type", "name"),
            show="headings",
            selectmode=tk.BROWSE
        )
        self.entities_tree.heading("id", text="ID")
        self.entities_tree.heading("type", text="Type")
        self.entities_tree.heading("name", text="Name")

        self.entities_tree.column("id", width=250)
        self.entities_tree.column("type", width=100)
        self.entities_tree.column("name", width=200)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.entities_tree.yview)
        self.entities_tree.config(yscrollcommand=scrollbar.set)

        self.entities_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.entities_tree.bind("<Double-1>", lambda e: self._edit_entity())
        
        # Enable column sorting
        from ..widgets.treeview_sorter import TreeviewSorter
        self.entities_sorter = TreeviewSorter(self.entities_tree)
        self.entities_sorter.enable_sorting_for_all_columns()

    def _create_relationships_tab(self):
        """Create the relationships browser tab."""
        tab = ttk.Frame(self.browser_notebook)
        self.browser_notebook.add(tab, text="Relationships")

        # Toolbar
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(toolbar, text="Edit", command=self._edit_relationship).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Delete", command=self._delete_relationship).pack(side=tk.LEFT, padx=2)

        # Treeview
        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.relationships_tree = ttk.Treeview(
            tree_frame,
            columns=("id", "source", "target", "type", "strength"),
            show="headings",
            selectmode=tk.BROWSE
        )
        self.relationships_tree.heading("id", text="ID")
        self.relationships_tree.heading("source", text="Source")
        self.relationships_tree.heading("target", text="Target")
        self.relationships_tree.heading("type", text="Type")
        self.relationships_tree.heading("strength", text="Strength")

        self.relationships_tree.column("id", width=200)
        self.relationships_tree.column("source", width=150)
        self.relationships_tree.column("target", width=150)
        self.relationships_tree.column("type", width=100)
        self.relationships_tree.column("strength", width=80)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.relationships_tree.yview)
        self.relationships_tree.config(yscrollcommand=scrollbar.set)

        self.relationships_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.relationships_tree.bind("<Double-1>", lambda e: self._edit_relationship())
        
        # Enable column sorting
        from ..widgets.treeview_sorter import TreeviewSorter
        self.relationships_sorter = TreeviewSorter(self.relationships_tree)
        # Custom sort for strength column (numeric)
        self.relationships_sorter.enable_sorting(
            "strength",
            sort_key=lambda item: float(item[4]) if len(item) > 4 and item[4] else 0.0
        )
        # Enable default sorting for other columns
        for col in ["id", "source", "target", "type"]:
            self.relationships_sorter.enable_sorting(col)

    def _open_database(self):
        """Open a database file dialog."""
        file_path = filedialog.askopenfilename(
            title="Select Database",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")],
            parent=self
        )

        if file_path:
            self.db_path = Path(file_path)
            self._load_database()

    def _load_database(self):
        """Load entities and relationships from the database."""
        # Ensure required widgets exist before proceeding
        if not hasattr(self, 'entities_tree') or not hasattr(self, 'relationships_tree') or not hasattr(self, 'status_label'):
            messagebox.showerror("UI Error", "Database Explorer UI is not fully initialized.", parent=self)
            return

        if not self.db_path or not self.db_path.exists():
            messagebox.showwarning("No Database", "Please select a database file first.", parent=self)
            return

        try:
            self.entities = storage.load_all_entities(self.db_path)
            self.relationships = storage.load_all_relationships(self.db_path)

            self._refresh_entities_tree()
            self._refresh_relationships_tree()
            self.stats_panel.update_stats(self.entities, self.relationships)

            self.db_label.config(text=f"Loaded: {self.db_path.name}")
            self.status_label.config(text=f"✓ Loaded {len(self.entities)} entities, {len(self.relationships)} relationships", foreground="green")

        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load database:\n\n{str(e)}", parent=self)
            if hasattr(self, 'status_label'):
                self.status_label.config(text="✗ Load failed", foreground="red")

    def _refresh_entities_tree(self):
        """Refresh the entities treeview."""
        self.entities_tree.delete(*self.entities_tree.get_children())

        filter_text = self.entity_filter_var.get().lower()

        for entity in self.entities:
            # Apply filter
            if filter_text:
                name = entity.descriptor.name if hasattr(entity, "descriptor") else ""
                entity_type = entity.descriptor.entity_type.value if hasattr(entity, "descriptor") else ""
                if filter_text not in name.lower() and filter_text not in entity_type.lower() and filter_text not in entity.id.lower():
                    continue

            entity_type = entity.descriptor.entity_type.value if hasattr(entity, "descriptor") else "unknown"
            name = entity.descriptor.name if hasattr(entity, "descriptor") else "Unnamed"

            self.entities_tree.insert("", tk.END, values=(entity.id, entity_type, name))

    def _apply_entity_filter(self):
        """Apply the entity filter."""
        self._refresh_entities_tree()

    def _refresh_relationships_tree(self):
        """Refresh the relationships treeview."""
        self.relationships_tree.delete(*self.relationships_tree.get_children())

        # Build entity ID to name lookup
        entity_names = {}
        for entity in self.entities:
            name = entity.descriptor.name if hasattr(entity, "descriptor") else "Unnamed"
            entity_names[entity.id] = name

        for rel in self.relationships:
            source_name = entity_names.get(rel.source_id, rel.source_id[:20])
            target_name = entity_names.get(rel.target_id, rel.target_id[:20])
            rel_type = rel.relationship_type.value if hasattr(rel.relationship_type, "value") else str(rel.relationship_type)

            self.relationships_tree.insert(
                "", tk.END,
                values=(rel.id, source_name, target_name, rel_type, f"{rel.strength:.2f}")
            )

    def _edit_entity(self):
        """Edit the selected entity."""
        selection = self.entities_tree.selection()
        if not selection:
            return

        item = selection[0]
        entity_id = self.entities_tree.item(item, "values")[0]

        # Find entity
        entity = next((e for e in self.entities if e.id == entity_id), None)
        if not entity:
            return

        # Open editor
        data = entity.model_dump()
        TabbedEntityEditor(self, data, on_save=lambda: self._on_entity_edited(entity_id))

    def _on_entity_edited(self, entity_id: str):
        """Callback after entity is edited."""
        # Reload from database
        self._load_database()

    def _delete_entity(self):
        """Delete the selected entity."""
        selection = self.entities_tree.selection()
        if not selection:
            return

        item = selection[0]
        entity_id, entity_type, name = self.entities_tree.item(item, "values")

        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete entity '{name}' ({entity_type})?\n\nThis action cannot be undone.",
            parent=self
        ):
            return

        try:
            storage.delete_entity(self.db_path, entity_id)
            self._load_database()
            self.status_label.config(text="✓ Entity deleted", foreground="green")
        except Exception as e:
            messagebox.showerror("Delete Error", str(e), parent=self)

    def _edit_relationship(self):
        """Edit the selected relationship."""
        selection = self.relationships_tree.selection()
        if not selection:
            return

        item = selection[0]
        rel_id = self.relationships_tree.item(item, "values")[0]

        # Find relationship
        rel = next((r for r in self.relationships if r.id == rel_id), None)
        if not rel:
            return

        # Open editor
        data = rel.model_dump()
        RelationshipEditor(self, data, self.entities, callback=lambda: self._on_relationship_edited(rel_id))

    def _on_relationship_edited(self, rel_id: str):
        """Callback after relationship is edited."""
        self._load_database()

    def _delete_relationship(self):
        """Delete the selected relationship."""
        selection = self.relationships_tree.selection()
        if not selection:
            return

        item = selection[0]
        rel_id = self.relationships_tree.item(item, "values")[0]

        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete relationship?\n\nThis action cannot be undone.",
            parent=self
        ):
            return

        try:
            storage.delete_relationship(self.db_path, rel_id)
            self._load_database()
            self.status_label.config(text="✓ Relationship deleted", foreground="green")
        except Exception as e:
            messagebox.showerror("Delete Error", str(e), parent=self)

    def _open_query_dialog(self):
        """Open the SQL query dialog."""
        if not self.db_path:
            messagebox.showwarning("No Database", "Please select a database file first.", parent=self)
            return

        QueryDialog(self, self.db_path)
