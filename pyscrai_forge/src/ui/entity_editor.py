# pyscrai_forge/harvester/ui/entity_editor.py
import tkinter as tk
from tkinter import ttk, messagebox
import json
from .schema_widgets import SchemaWidgetFactory

class TabbedEntityEditor(tk.Toplevel):
    def __init__(self, parent, entity_data, project_manifest=None, on_save=None):
        super().__init__(parent)
        self.title("Edit Entity")
        self.geometry("600x700")
        self.transient(parent)
        self.grab_set()

        self.entity_data = entity_data.copy()
        self.project_manifest = project_manifest
        self.on_save = on_save

        # Ensure components exist (using lowercase keys to match Pydantic model_dump_json)
        for comp in ['descriptor', 'cognitive', 'spatial', 'state']:
            if comp not in self.entity_data:
                self.entity_data[comp] = {}

        self._create_ui()

    def _create_ui(self):
        # Notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Descriptor Tab
        self.descriptor_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.descriptor_frame, text="Descriptor")
        self._build_descriptor_tab()

        # Cognitive Tab
        self.cognitive_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.cognitive_frame, text="Cognitive")
        self._build_cognitive_tab()

        # Spatial Tab
        self.spatial_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.spatial_frame, text="Spatial")
        self._build_spatial_tab()

        # State Tab
        self.state_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.state_frame, text="State (Resources)")
        self._build_state_tab()

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(btn_frame, text="Save", command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def _build_descriptor_tab(self):
        comp = self.entity_data.get('descriptor', {})

        # Name
        self._add_field(self.descriptor_frame, "Name", comp.get('name', ''),
                        lambda v: comp.update({'name': v}))

        # Entity Type (should be dropdown based on project manifest if available)
        # For now, simple entry or list of known types
        # Pydantic EntityType enum expects lowercase values
        known_types = ["actor", "polity", "location", "region"]
        if self.project_manifest and hasattr(self.project_manifest, 'entity_schemas') and self.project_manifest.entity_schemas:
             known_types = list(self.project_manifest.entity_schemas.keys())

        # Entity Type selection triggers State tab rebuild
        def on_type_change(val):
            comp['entity_type'] = val.lower() if isinstance(val, str) else val
            # Rebuild state tab because schema depends on type
            for widget in self.state_frame.winfo_children():
                widget.destroy()
            self._build_state_tab()

        current_type = comp.get('entity_type', 'actor')
        if isinstance(current_type, str):
            current_type = current_type.lower()

        self._add_combo(self.descriptor_frame, "Entity Type", current_type,
                        known_types, on_type_change)

        # Bio (Text area)
        lbl = ttk.Label(self.descriptor_frame, text="Bio")
        lbl.pack(anchor='w', pady=(5, 0))
        txt = tk.Text(self.descriptor_frame, height=5, width=40)
        txt.insert("1.0", comp.get('bio', ''))
        txt.pack(fill=tk.X, pady=2)
        def on_bio_change(event=None):
            comp['bio'] = txt.get("1.0", tk.END).strip()
        # Use focus-out to ensure value is captured when dialog is saved
        txt.bind("<FocusOut>", on_bio_change)

        # Tags (List)
        tags_str = ", ".join(comp.get('tags', []))
        def on_tags_change(v):
            comp['tags'] = [t.strip() for t in v.split(',') if t.strip()]
        self._add_field(self.descriptor_frame, "Tags (comma separated)", tags_str, on_tags_change)

    def _build_cognitive_tab(self):
        comp = self.entity_data.get('cognitive')
        if comp is None:
            comp = {}
            self.entity_data['cognitive'] = comp

        self._add_field(self.cognitive_frame, "Model ID", comp.get('model_id', 'gpt-4'),
                       lambda v: comp.update({'model_id': v}))

        # Temperature (Scale)
        frame = ttk.Frame(self.cognitive_frame)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text="Temperature", width=20).pack(side=tk.LEFT)
        var = tk.DoubleVar(value=comp.get('temperature', 0.7))
        scale = ttk.Scale(frame, from_=0.0, to=1.0, variable=var, orient=tk.HORIZONTAL)
        scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        lbl_val = ttk.Label(frame, text=f"{var.get():.2f}")
        lbl_val.pack(side=tk.LEFT, padx=5)
        def on_scale(val):
             v = float(val)
             comp['temperature'] = v
             lbl_val.config(text=f"{v:.2f}")
        scale.config(command=on_scale)

        # System Prompt
        lbl = ttk.Label(self.cognitive_frame, text="System Prompt")
        lbl.pack(anchor='w', pady=(5, 0))
        txt = tk.Text(self.cognitive_frame, height=5)
        txt.insert("1.0", comp.get('system_prompt', ''))
        txt.pack(fill=tk.X, pady=2)
        def on_prompt_change(event=None):
            comp['system_prompt'] = txt.get("1.0", tk.END).strip()
        txt.bind("<FocusOut>", on_prompt_change)

    def _build_spatial_tab(self):
        comp = self.entity_data.get('spatial')
        if comp is None:
            comp = {}
            self.entity_data['spatial'] = comp

        frame = ttk.Frame(self.spatial_frame)
        frame.pack(fill=tk.X)

        # X, Y, Z
        self._add_field(frame, "X", comp.get('x', 0.0), lambda v: comp.update({'x': float(v) if v else 0.0}))
        self._add_field(frame, "Y", comp.get('y', 0.0), lambda v: comp.update({'y': float(v) if v else 0.0}))
        self._add_field(frame, "Z", comp.get('z', 0.0), lambda v: comp.update({'z': float(v) if v else 0.0}))

        self._add_field(self.spatial_frame, "Region ID", comp.get('region_id', ''),
                        lambda v: comp.update({'region_id': v}))
        self._add_field(self.spatial_frame, "Layer", comp.get('layer', 'physical'),
                        lambda v: comp.update({'layer': v}))

    def _build_state_tab(self):
        comp = self.entity_data.get('state')
        if comp is None:
            comp = {}
            self.entity_data['state'] = comp
        # resources_json is a JSON string, not a dict - parse it
        resources_json_str = comp.get('resources_json', '{}')
        try:
            resources = json.loads(resources_json_str) if resources_json_str else {}
        except json.JSONDecodeError:
            resources = {}

        # Check if we have a schema for the current entity type
        entity_type = self.entity_data.get('descriptor', {}).get('entity_type', 'Actor')

        schema = None
        if self.project_manifest and hasattr(self.project_manifest, 'entity_schemas') and self.project_manifest.entity_schemas:
            schema = self.project_manifest.entity_schemas.get(entity_type)

        if schema:
            ttk.Label(self.state_frame, text=f"Schema: {entity_type}", font=("", 10, "bold")).pack(pady=5)

            # Iterate through schema fields
            # Assuming schema is a dict of field_name -> field_def
            for field_name, field_def in schema.items():
                current_val = resources.get(field_name)

                def make_callback(fname):
                    return lambda val: resources.update({fname: val})

                SchemaWidgetFactory.create_widget(
                    self.state_frame,
                    field_name,
                    field_def,
                    current_value=current_val,
                    callback=make_callback(field_name)
                )

            # Handle extra fields not in schema
            extra_fields = [k for k in resources.keys() if k not in schema]
            if extra_fields:
                ttk.Label(self.state_frame, text="Extra Fields (Not in Schema):", foreground="red").pack(pady=10)
                for k in extra_fields:
                    ttk.Label(self.state_frame, text=f"{k}: {resources[k]}").pack(anchor='w')
        else:
            ttk.Label(self.state_frame, text=f"No schema found for {entity_type}. Using Raw JSON.").pack(pady=5)
            txt = tk.Text(self.state_frame, height=15)
            txt.insert("1.0", json.dumps(resources, indent=2))
            txt.pack(fill=tk.BOTH, expand=True)

            def on_json_change(event=None):
                try:
                    val = txt.get("1.0", tk.END).strip()
                    if val:
                        # Validate JSON but keep as string
                        json.loads(val)  # Validate
                        comp['resources_json'] = val  # Store as string
                except json.JSONDecodeError:
                    pass # Invalid JSON, maybe show indicator
            txt.bind("<FocusOut>", on_json_change)

    def _add_field(self, parent, label, value, callback):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text=label, width=20).pack(side=tk.LEFT)
        var = tk.StringVar(value=str(value))
        var.trace_add("write", lambda *args: callback(var.get()))
        ttk.Entry(frame, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _add_combo(self, parent, label, value, values, callback):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text=label, width=20).pack(side=tk.LEFT)
        var = tk.StringVar(value=str(value))

        def on_change(event):
            callback(var.get())

        cb = ttk.Combobox(frame, textvariable=var, values=values, state="readonly")
        cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
        cb.bind("<<ComboboxSelected>>", on_change)

    def _save(self):
        if self.on_save:
            # Convert resources dict back to JSON string for state component
            state_comp = self.entity_data.get('state', {})
            if 'resources_json' in state_comp:
                # If it's already a string (from text editor), keep it
                # If it's a dict (from schema widgets), stringify it
                if isinstance(state_comp['resources_json'], dict):
                    state_comp['resources_json'] = json.dumps(state_comp['resources_json'])
            self.on_save(self.entity_data)
        self.destroy()
