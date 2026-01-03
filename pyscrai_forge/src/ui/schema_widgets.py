# pyscrai_forge/harvester/ui/schema_widgets.py
import tkinter as tk
from tkinter import ttk
import json

class SchemaWidgetFactory:
    """Generates Tkinter widgets based on schema definitions."""

    @staticmethod
    def create_widget(parent, field_name, field_def, current_value=None, callback=None):
        """
        Creates a widget for a specific field definition.

        Args:
            parent: Parent widget
            field_name: Name of the field
            field_def: Dictionary defining the field (type, description, etc.)
            current_value: Current value of the field
            callback: Function to call when value changes (arg: new_value)
        """
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)

        # Label
        label_text = field_name.replace('_', ' ').title()
        if field_def.get('required', False):
            label_text += " *"
        ttk.Label(frame, text=label_text, width=20, anchor='w').pack(side=tk.LEFT)

        field_type = field_def.get('type', 'string')
        var = None
        widget = None

        # Helper to trace variable changes
        def on_change(*args):
            if callback:
                try:
                    val = var.get()
                    # Convert to appropriate type if needed
                    if field_type == 'integer':
                        val = int(val) if val else 0
                    elif field_type == 'float':
                        val = float(val) if val else 0.0
                    elif field_type == 'boolean':
                        val = bool(val)
                    callback(val)
                except ValueError:
                    pass # Ignore conversion errors during typing

        if field_type == 'string':
            var = tk.StringVar(value=str(current_value) if current_value is not None else "")
            var.trace_add("write", on_change)
            widget = ttk.Entry(frame, textvariable=var)
            widget.pack(side=tk.LEFT, fill=tk.X, expand=True)

        elif field_type == 'integer':
            var = tk.StringVar(value=str(current_value) if current_value is not None else "0")
            var.trace_add("write", on_change)
            widget = ttk.Spinbox(frame, from_=-999999, to=999999, textvariable=var)
            widget.pack(side=tk.LEFT, fill=tk.X, expand=True)

        elif field_type == 'float':
            var = tk.StringVar(value=str(current_value) if current_value is not None else "0.0")
            var.trace_add("write", on_change)
            widget = ttk.Entry(frame, textvariable=var) # Use Entry for float for flexibility
            widget.pack(side=tk.LEFT, fill=tk.X, expand=True)

        elif field_type == 'boolean':
            var = tk.BooleanVar(value=bool(current_value) if current_value is not None else False)
            def on_bool_change():
                if callback:
                    callback(var.get())
            widget = ttk.Checkbutton(frame, variable=var, command=on_bool_change)
            widget.pack(side=tk.LEFT, anchor='w')

        elif field_type == 'select' or field_type == 'enum':
            options = field_def.get('options', [])
            var = tk.StringVar(value=str(current_value) if current_value is not None else (options[0] if options else ""))
            var.trace_add("write", on_change)
            widget = ttk.Combobox(frame, textvariable=var, values=options, state="readonly")
            widget.pack(side=tk.LEFT, fill=tk.X, expand=True)

        elif field_type == 'list':
            # Simple comma-separated list for now
            # In a real rich editor, this would be a Listbox with add/remove buttons
            initial_val = ", ".join(map(str, current_value)) if isinstance(current_value, list) else ""
            var = tk.StringVar(value=initial_val)

            def on_list_change(*args):
                if callback:
                    # simplistic parsing: comma separated
                    items = [item.strip() for item in var.get().split(',') if item.strip()]
                    callback(items)

            var.trace_add("write", on_list_change)
            widget = ttk.Entry(frame, textvariable=var)
            widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            ttk.Label(frame, text="(comma separated)").pack(side=tk.LEFT, padx=5)

        else:
             # Fallback to text entry
            var = tk.StringVar(value=str(current_value) if current_value is not None else "")
            var.trace_add("write", on_change)
            widget = ttk.Entry(frame, textvariable=var)
            widget.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Tooltip/Description if available
        if field_def.get('description'):
            # This is a placeholder. In a real app, use a proper Tooltip library
            pass

        return frame
