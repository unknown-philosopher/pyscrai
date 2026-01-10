# pyscrai_forge/harvester/ui/widgets/dependency_manager.py
"""Key-value editor for mod dependencies."""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Callable, Optional


class DependencyManagerWidget(ttk.Frame):
    """Widget for editing mod dependencies (key-value pairs)."""

    def __init__(self, parent, dependencies: Optional[Dict[str, str]] = None, on_change: Optional[Callable] = None):
        """
        Initialize the dependency manager widget.

        Args:
            parent: Parent widget
            dependencies: Initial dependencies dict
            on_change: Callback function() called when dependencies change
        """
        super().__init__(parent)
        self.dependencies = dependencies or {}
        self.on_change = on_change

        self._create_ui()
        self._refresh_tree()

    def _create_ui(self):
        """Build the widget UI."""
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(toolbar, text="Add Dependency", command=self._add_dependency).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Edit", command=self._edit_dependency).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Delete", command=self._delete_dependency).pack(side=tk.LEFT, padx=2)

        # Treeview
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("key", "value"),
            show="headings",
            selectmode=tk.BROWSE
        )
        self.tree.heading("key", text="Mod ID")
        self.tree.heading("value", text="Version")

        self.tree.column("key", width=200)
        self.tree.column("value", width=150)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.config(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Double-click to edit
        self.tree.bind("<Double-1>", lambda e: self._edit_dependency())

    def _refresh_tree(self):
        """Refresh the treeview with current dependencies."""
        self.tree.delete(*self.tree.get_children())

        for key, value in sorted(self.dependencies.items()):
            self.tree.insert("", tk.END, values=(key, value))

    def _add_dependency(self):
        """Add a new dependency."""
        self._show_edit_dialog()

    def _edit_dependency(self):
        """Edit the selected dependency."""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        key, value = self.tree.item(item, "values")
        self._show_edit_dialog(key, value)

    def _show_edit_dialog(self, existing_key: Optional[str] = None, existing_value: Optional[str] = None):
        """Show the add/edit dependency dialog."""
        dialog = tk.Toplevel(self)
        dialog.title("Edit Dependency" if existing_key else "Add Dependency")
        dialog.geometry("400x200")
        dialog.transient(self)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        x = self.winfo_toplevel().winfo_x() + (self.winfo_toplevel().winfo_width() // 2) - 200
        y = self.winfo_toplevel().winfo_y() + (self.winfo_toplevel().winfo_height() // 2) - 100
        dialog.geometry(f"+{x}+{y}")

        # Form
        form_frame = ttk.Frame(dialog, padding=15)
        form_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(form_frame, text="Mod ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        key_var = tk.StringVar(value=existing_key or "")
        key_entry = ttk.Entry(form_frame, textvariable=key_var, width=30)
        key_entry.grid(row=0, column=1, sticky=tk.EW, pady=5)
        key_entry.focus()

        ttk.Label(form_frame, text="Version:").grid(row=1, column=0, sticky=tk.W, pady=5)
        value_var = tk.StringVar(value=existing_value or "")
        value_entry = ttk.Entry(form_frame, textvariable=value_var, width=30)
        value_entry.grid(row=1, column=1, sticky=tk.EW, pady=5)

        form_frame.columnconfigure(1, weight=1)

        def save():
            key = key_var.get().strip()
            value = value_var.get().strip()

            if not key:
                messagebox.showerror("Validation Error", "Mod ID is required.", parent=dialog)
                return

            if not value:
                messagebox.showerror("Validation Error", "Version is required.", parent=dialog)
                return

            # Check duplicate (only if adding new or changing key)
            if key != existing_key and key in self.dependencies:
                messagebox.showwarning("Duplicate", f"Dependency '{key}' already exists.", parent=dialog)
                return

            # Remove old key if renaming
            if existing_key and existing_key != key:
                del self.dependencies[existing_key]

            self.dependencies[key] = value
            self._refresh_tree()
            if self.on_change:
                self.on_change()
            dialog.destroy()

        # Buttons
        button_frame = ttk.Frame(dialog, padding=10)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(button_frame, text="Save", command=save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT)

    def _delete_dependency(self):
        """Delete the selected dependency."""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        key, _ = self.tree.item(item, "values")

        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete dependency '{key}'?",
            parent=self
        ):
            return

        del self.dependencies[key]
        self._refresh_tree()
        if self.on_change:
            self.on_change()

    def get_dependencies(self) -> Dict[str, str]:
        """Get the current dependencies dictionary."""
        return self.dependencies

    def set_dependencies(self, dependencies: Dict[str, str]):
        """Set the dependencies dictionary and refresh."""
        self.dependencies = dependencies
        self._refresh_tree()
