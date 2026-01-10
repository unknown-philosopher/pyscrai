# pyscrai_forge/harvester/ui/dialogs/schema_field_dialog.py
"""Dialog for adding or editing entity schema fields."""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable


class SchemaFieldDialog(tk.Toplevel):
    """Modal dialog for adding or editing a schema field."""

    FIELD_TYPES = ["string", "integer", "float", "boolean", "select", "list"]

    def __init__(self, parent, field_data: Optional[dict] = None, on_save: Optional[Callable] = None):
        """
        Initialize the schema field dialog.

        Args:
            parent: Parent window
            field_data: Existing field data for editing (None for new field)
            on_save: Callback function(field_dict) called when saving
        """
        super().__init__(parent)
        self.title("Add Schema Field" if field_data is None else "Edit Schema Field")
        self.geometry("500x400")
        self.transient(parent)
        self.grab_set()

        self.field_data = field_data or {}
        self.on_save = on_save
        self.result = None

        self._create_ui()
        self._populate_fields()

        # Center dialog
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _create_ui(self):
        """Build the dialog UI."""
        # Main form frame
        form_frame = ttk.Frame(self, padding=15)
        form_frame.pack(fill=tk.BOTH, expand=True)

        # Field Name
        ttk.Label(form_frame, text="Field Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(form_frame, textvariable=self.name_var, width=40)
        self.name_entry.grid(row=0, column=1, sticky=tk.EW, pady=5)
        self.name_entry.focus()

        # Field Type
        ttk.Label(form_frame, text="Field Type:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.type_var = tk.StringVar()
        self.type_combo = ttk.Combobox(
            form_frame,
            textvariable=self.type_var,
            values=self.FIELD_TYPES,
            state="readonly",
            width=38
        )
        self.type_combo.grid(row=1, column=1, sticky=tk.EW, pady=5)
        self.type_combo.bind("<<ComboboxSelected>>", self._on_type_changed)

        # Required checkbox
        self.required_var = tk.BooleanVar()
        self.required_check = ttk.Checkbutton(form_frame, text="Required Field", variable=self.required_var)
        self.required_check.grid(row=2, column=1, sticky=tk.W, pady=5)

        # Default Value
        ttk.Label(form_frame, text="Default Value:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.default_var = tk.StringVar()
        self.default_entry = ttk.Entry(form_frame, textvariable=self.default_var, width=40)
        self.default_entry.grid(row=3, column=1, sticky=tk.EW, pady=5)

        # Description
        ttk.Label(form_frame, text="Description:").grid(row=4, column=0, sticky=tk.NW, pady=5)
        self.description_text = tk.Text(form_frame, height=4, width=40, wrap=tk.WORD)
        self.description_text.grid(row=4, column=1, sticky=tk.EW, pady=5)

        # Options (for select/list types)
        ttk.Label(form_frame, text="Options (one per line):").grid(row=5, column=0, sticky=tk.NW, pady=5)
        self.options_frame = ttk.Frame(form_frame)
        self.options_frame.grid(row=5, column=1, sticky=tk.EW, pady=5)

        self.options_text = tk.Text(self.options_frame, height=5, width=40, wrap=tk.WORD)
        self.options_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        options_scroll = ttk.Scrollbar(self.options_frame, orient=tk.VERTICAL, command=self.options_text.yview)
        options_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.options_text.config(yscrollcommand=options_scroll.set)

        ttk.Label(
            self.options_frame,
            text="(Only for 'select' or 'list' types)",
            foreground="gray",
            font=("Arial", 8)
        ).pack(anchor=tk.W)

        # Initially hide options
        self.options_frame.grid_remove()

        form_frame.columnconfigure(1, weight=1)

        # Button frame
        button_frame = ttk.Frame(self, padding=10)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(button_frame, text="Save", command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT)

    def _populate_fields(self):
        """Populate fields with existing data if editing."""
        if not self.field_data:
            self.type_combo.current(0)  # Default to "string"
            return

        self.name_var.set(self.field_data.get("name", ""))
        field_type = self.field_data.get("type", "string")
        if field_type in self.FIELD_TYPES:
            self.type_var.set(field_type)
        else:
            self.type_var.set("string")

        self.required_var.set(self.field_data.get("required", False))
        self.default_var.set(self.field_data.get("default", ""))
        self.description_text.insert("1.0", self.field_data.get("description", ""))

        options = self.field_data.get("options", [])
        if options:
            self.options_text.insert("1.0", "\n".join(options))

        self._on_type_changed(None)

    def _on_type_changed(self, event):
        """Show/hide options field based on type selection."""
        field_type = self.type_var.get()
        if field_type in ["select", "list"]:
            self.options_frame.grid()
        else:
            self.options_frame.grid_remove()

    def _validate(self) -> bool:
        """Validate field data."""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Validation Error", "Field name is required.", parent=self)
            return False

        # Check valid identifier
        if not name.replace("_", "").isalnum() or name[0].isdigit():
            messagebox.showerror(
                "Validation Error",
                "Field name must be a valid identifier (letters, numbers, underscores; cannot start with number).",
                parent=self
            )
            return False

        field_type = self.type_var.get()
        if not field_type:
            messagebox.showerror("Validation Error", "Field type is required.", parent=self)
            return False

        # Validate options for select/list
        if field_type in ["select", "list"]:
            options_text = self.options_text.get("1.0", tk.END).strip()
            if not options_text:
                messagebox.showerror(
                    "Validation Error",
                    f"Options are required for '{field_type}' type.",
                    parent=self
                )
                return False

        return True

    def _save(self):
        """Save the field data."""
        if not self._validate():
            return

        # Build result dict
        self.result = {
            "name": self.name_var.get().strip(),
            "type": self.type_var.get(),
            "required": self.required_var.get(),
            "description": self.description_text.get("1.0", tk.END).strip()
        }

        # Add default if provided
        default_val = self.default_var.get().strip()
        if default_val:
            self.result["default"] = default_val

        # Add options if applicable
        field_type = self.type_var.get()
        if field_type in ["select", "list"]:
            options_text = self.options_text.get("1.0", tk.END).strip()
            options = [opt.strip() for opt in options_text.splitlines() if opt.strip()]
            self.result["options"] = options

        if self.on_save:
            self.on_save(self.result)

        self.destroy()

    def get_result(self) -> Optional[dict]:
        """Get the field data result (for non-callback usage)."""
        return self.result
