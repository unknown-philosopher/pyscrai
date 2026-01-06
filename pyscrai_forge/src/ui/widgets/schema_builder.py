# pyscrai_forge/harvester/ui/widgets/schema_builder.py
"""Grid-based editor for entity schemas."""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Callable, Optional
from pyscrai_core import EntityType
from ..dialogs.schema_field_dialog import SchemaFieldDialog


class SchemaBuilderWidget(ttk.Frame):
    """Widget for editing entity_schemas dictionary."""

    def __init__(self, parent, schemas: Optional[Dict] = None, on_change: Optional[Callable] = None):
        """
        Initialize the schema builder widget.

        Args:
            parent: Parent widget
            schemas: Initial entity_schemas dict
            on_change: Callback function() called when schemas change
        """
        super().__init__(parent)
        self.schemas = schemas or {}
        self.on_change = on_change

        self._create_ui()
        self._refresh_tree()

    def _create_ui(self):
        """Build the widget UI."""
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(toolbar, text="Add Entity Type", command=self._add_entity_type).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Add Field", command=self._add_field).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Edit Field", command=self._edit_field).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Delete", command=self._delete_selected).pack(side=tk.LEFT, padx=2)

        # Treeview
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("type", "required", "default", "description"),
            show="tree headings",
            selectmode=tk.BROWSE
        )
        self.tree.heading("#0", text="Field Name")
        self.tree.heading("type", text="Type")
        self.tree.heading("required", text="Required")
        self.tree.heading("default", text="Default")
        self.tree.heading("description", text="Description")

        # Make the grid ~30% wider for readability
        self.tree.column("#0", width=240)
        self.tree.column("type", width=130)
        self.tree.column("required", width=90)
        self.tree.column("default", width=170)
        self.tree.column("description", width=260)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.config(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Double-click to edit
        self.tree.bind("<Double-1>", lambda e: self._edit_field())

    def _refresh_tree(self):
        """Refresh the treeview with current schema data."""
        self.tree.delete(*self.tree.get_children())

        for entity_type, fields in sorted(self.schemas.items()):
            # Add entity type node
            entity_node = self.tree.insert("", tk.END, text=entity_type, tags=("entity_type",))
            self.tree.item(entity_node, open=True)

            # Add field nodes
            for field_name, field_spec in sorted(fields.items()):
                # Handle both string (legacy) and dict (rich) field specs
                if isinstance(field_spec, str):
                    # Legacy format: treat string as description, assume string type
                    field_type = "string"
                    required = ""
                    default = ""
                    description = field_spec
                elif isinstance(field_spec, dict):
                    # Rich format: dict with type, required, default, etc.
                    field_type = field_spec.get("type", "string")
                    required = "Yes" if field_spec.get("required", False) else ""
                    default_val = field_spec.get("default", field_spec.get("default_value", ""))
                    default = str(default_val) if default_val not in (None, "") else ""
                    description = field_spec.get("description", "")
                else:
                    # Fallback
                    field_type = "string"
                    required = ""
                    default = ""
                    description = ""

                self.tree.insert(
                    entity_node,
                    tk.END,
                    text=field_name,
                    values=(field_type, required, default, description),
                    tags=("field",)
                )

        # Style entity types as bold
        self.tree.tag_configure("entity_type", font=("Arial", 10, "bold"))

    def _add_entity_type(self):
        """Add a new entity type to the schema."""
        dialog = tk.Toplevel(self)
        dialog.title("Add Entity Type")
        dialog.geometry("400x150")
        dialog.transient(self)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = self.winfo_toplevel().winfo_x() + (self.winfo_toplevel().winfo_width() // 2) - 200
        y = self.winfo_toplevel().winfo_y() + (self.winfo_toplevel().winfo_height() // 2) - 75
        dialog.geometry(f"+{x}+{y}")

        ttk.Label(dialog, text="Select Entity Type:").pack(pady=10)

        type_var = tk.StringVar()
        type_combo = ttk.Combobox(
            dialog,
            textvariable=type_var,
            values=[e.value for e in EntityType],
            state="readonly",
            width=30
        )
        type_combo.pack(pady=5)
        type_combo.current(0)

        def save():
            entity_type = type_var.get()
            if entity_type in self.schemas:
                messagebox.showwarning("Duplicate", f"Entity type '{entity_type}' already exists.", parent=dialog)
                return

            self.schemas[entity_type] = {}
            self._refresh_tree()
            if self.on_change:
                self.on_change()
            dialog.destroy()

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Add", command=save).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT)

    def _add_field(self):
        from ..dialogs.schema_field_dialog import SchemaFieldDialog
        """Add a field to the selected entity type."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an entity type to add a field.", parent=self)
            return

        item = selection[0]
        tags = self.tree.item(item, "tags")

        # If field selected, get parent entity type
        if "field" in tags:
            item = self.tree.parent(item)

        entity_type = self.tree.item(item, "text")

        def on_save(field_data):
            field_name = field_data["name"]

            # Check duplicate
            if field_name in self.schemas[entity_type]:
                messagebox.showwarning("Duplicate Field", f"Field '{field_name}' already exists.", parent=self)
                return

            # Save field
            self.schemas[entity_type][field_name] = {
                "type": field_data["type"],
                "required": field_data["required"],
            }

            if "description" in field_data and field_data["description"]:
                self.schemas[entity_type][field_name]["description"] = field_data["description"]

            if "default" in field_data and field_data["default"] not in (None, ""):
                self.schemas[entity_type][field_name]["default"] = field_data["default"]

            if "options" in field_data:
                self.schemas[entity_type][field_name]["options"] = field_data["options"]

            self._refresh_tree()
            if self.on_change:
                self.on_change()

        SchemaFieldDialog(self, on_save=on_save)

    def _edit_field(self):
        from ..dialogs.schema_field_dialog import SchemaFieldDialog
        """Edit the selected field."""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        tags = self.tree.item(item, "tags")

        if "field" not in tags:
            return  # Can only edit fields

        parent_item = self.tree.parent(item)
        entity_type = self.tree.item(parent_item, "text")
        field_name = self.tree.item(item, "text")

        # Load existing field data
        field_spec = self.schemas[entity_type][field_name]
        
        # Handle both string (legacy) and dict (rich) field specs
        if isinstance(field_spec, str):
            # Legacy format: treat as description
            field_data = {
                "name": field_name,
                "type": "string",
                "required": False,
                "description": field_spec,
                "default": "",
                "options": []
            }
        elif isinstance(field_spec, dict):
            # Rich format: dict with type, required, default, etc.
            field_data = {
                "name": field_name,
                "type": field_spec.get("type", "string"),
                "required": field_spec.get("required", False),
                "description": field_spec.get("description", ""),
                "default": field_spec.get("default", field_spec.get("default_value", "")),
                "options": field_spec.get("options", [])
            }
        else:
            # Fallback
            field_data = {
                "name": field_name,
                "type": "string",
                "required": False,
                "description": "",
                "default": "",
                "options": []
            }

        def on_save(updated_data):
            new_name = updated_data["name"]

            # Handle rename
            if new_name != field_name:
                if new_name in self.schemas[entity_type]:
                    messagebox.showwarning("Duplicate Field", f"Field '{new_name}' already exists.", parent=self)
                    return
                del self.schemas[entity_type][field_name]

            # Save updated field
            self.schemas[entity_type][new_name] = {
                "type": updated_data["type"],
                "required": updated_data["required"],
            }

            if "description" in updated_data and updated_data["description"]:
                self.schemas[entity_type][new_name]["description"] = updated_data["description"]

            if "default" in updated_data and updated_data["default"] not in (None, ""):
                self.schemas[entity_type][new_name]["default"] = updated_data["default"]

            if "options" in updated_data:
                self.schemas[entity_type][new_name]["options"] = updated_data["options"]

            self._refresh_tree()
            if self.on_change:
                self.on_change()

        SchemaFieldDialog(self, field_data=field_data, on_save=on_save)

    def _delete_selected(self):
        """Delete the selected entity type or field."""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        tags = self.tree.item(item, "tags")

        if "entity_type" in tags:
            # Delete entity type
            entity_type = self.tree.item(item, "text")
            if not messagebox.askyesno(
                "Confirm Delete",
                f"Delete entity type '{entity_type}' and all its fields?",
                parent=self
            ):
                return

            del self.schemas[entity_type]

        elif "field" in tags:
            # Delete field
            parent_item = self.tree.parent(item)
            entity_type = self.tree.item(parent_item, "text")
            field_name = self.tree.item(item, "text")

            if not messagebox.askyesno(
                "Confirm Delete",
                f"Delete field '{field_name}'?",
                parent=self
            ):
                return

            del self.schemas[entity_type][field_name]

        self._refresh_tree()
        if self.on_change:
            self.on_change()

    def get_schemas(self) -> Dict:
        """Get the current schemas dictionary."""
        return self.schemas

    def set_schemas(self, schemas: Dict):
        """Set the schemas dictionary and refresh."""
        self.schemas = schemas
        self._refresh_tree()
