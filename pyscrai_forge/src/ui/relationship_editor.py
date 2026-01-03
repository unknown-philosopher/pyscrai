# pyscrai_forge/harvester/ui/relationship_editor.py
import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Optional
import json

class RelationshipEditor(tk.Toplevel):
    def __init__(self, parent, relationship_data, entity_name_map: Optional[Dict[str, str]] = None, on_save=None):
        super().__init__(parent)
        self.title("Edit Relationship")
        self.geometry("500x600")
        self.transient(parent)
        self.grab_set()

        self.data = relationship_data.copy()
        # entity_name_map is {entity_id: entity_name}
        self.entity_name_map = entity_name_map or {}
        # Create reverse map for saving
        self.name_to_id_map = {v: k for k, v in self.entity_name_map.items()}
        self.on_save = on_save

        self._create_ui()

    def _create_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Get entity names for dropdown
        entity_names = sorted(self.entity_name_map.values())
        
        # Source (use source_id from Pydantic model)
        source_id = self.data.get('source_id', '')
        source_name = self.entity_name_map.get(source_id, source_id)
        self._add_combo(main_frame, "Source Entity", 'source_id', source_name, entity_names, is_entity=True)

        # Target (use target_id from Pydantic model)
        target_id = self.data.get('target_id', '')
        target_name = self.entity_name_map.get(target_id, target_id)
        self._add_combo(main_frame, "Target Entity", 'target_id', target_name, entity_names, is_entity=True)

        # Type (use relationship_type from Pydantic model) - enums expect lowercase values
        rel_types = [
            "alliance",
            "enmity",
            "trade",
            "owns",
            "occupies",
            "knows",
            "influences",
            "commands",
            "member_of",
            "custom",
        ]
        rel_type_value = self.data.get('relationship_type', 'custom')
        if isinstance(rel_type_value, dict):
            rel_type_value = rel_type_value.get('value', 'custom')
        elif hasattr(rel_type_value, 'value'):
            rel_type_value = rel_type_value.value
        rel_type_value = rel_type_value.lower() if isinstance(rel_type_value, str) else rel_type_value
        self._add_combo(main_frame, "Relationship Type", 'relationship_type', rel_type_value, rel_types)

        # Visibility (also lowercase per enum)
        vis_types = ["public", "private", "secret", "classified"]
        vis_value = self.data.get('visibility', 'public')
        if isinstance(vis_value, dict):
            vis_value = vis_value.get('value', 'public')
        elif hasattr(vis_value, 'value'):
            vis_value = vis_value.value
        vis_value = vis_value.lower() if isinstance(vis_value, str) else vis_value
        self._add_combo(main_frame, "Visibility", 'visibility', vis_value, vis_types)

        # Strength (-1.0 to 1.0)
        frame = ttk.Frame(main_frame)
        frame.pack(fill=tk.X, pady=5)
        ttk.Label(frame, text="Strength", width=15).pack(side=tk.LEFT)
        var = tk.DoubleVar(value=self.data.get('strength', 0.0))
        scale = ttk.Scale(frame, from_=-1.0, to=1.0, variable=var, orient=tk.HORIZONTAL)
        scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        lbl_val = ttk.Label(frame, text=f"{var.get():.2f}")
        lbl_val.pack(side=tk.LEFT, padx=5)

        def on_scale(val):
             v = float(val)
             self.data['strength'] = v
             lbl_val.config(text=f"{v:.2f}")
        scale.config(command=on_scale)

        # Description
        ttk.Label(main_frame, text="Description").pack(anchor='w', pady=(10, 0))
        txt = tk.Text(main_frame, height=5, width=40)
        txt.insert("1.0", self.data.get('description', ''))
        txt.pack(fill=tk.X, pady=2)
        def on_desc_change(event=None):
            self.data['description'] = txt.get("1.0", tk.END).strip()
        txt.bind("<FocusOut>", on_desc_change)

        # Metadata (Simple Key-Value for now)
        ttk.Label(main_frame, text="Metadata (JSON)").pack(anchor='w', pady=(10, 0))
        meta_txt = tk.Text(main_frame, height=5)
        # Metadata is stored as JSON string in Pydantic model
        meta_str = self.data.get('metadata', '{}')
        if isinstance(meta_str, str):
            try:
                # Parse and re-format for pretty display
                meta_dict = json.loads(meta_str)
                meta_txt.insert("1.0", json.dumps(meta_dict, indent=2))
            except:
                meta_txt.insert("1.0", meta_str)
        else:
            meta_txt.insert("1.0", json.dumps(meta_str, indent=2))
        meta_txt.pack(fill=tk.BOTH, expand=True)

        def on_meta_change(event=None):
            try:
                val = meta_txt.get("1.0", tk.END).strip()
                if val:
                    # Validate JSON and store as string
                    json.loads(val)  # Validate
                    self.data['metadata'] = val  # Store as string
            except:
                pass
        meta_txt.bind("<FocusOut>", on_meta_change)

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(btn_frame, text="Save", command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def _add_combo(self, parent, label, key, current_value, values, is_entity=False):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        ttk.Label(frame, text=label, width=15).pack(side=tk.LEFT)
        var = tk.StringVar(value=str(current_value))

        def on_change(event):
            selected_name = var.get()
            if is_entity:
                # Convert entity name back to ID
                entity_id = self.name_to_id_map.get(selected_name, selected_name)
                self.data[key] = entity_id
            else:
                self.data[key] = selected_name.lower() if isinstance(selected_name, str) else selected_name

        cb = ttk.Combobox(frame, textvariable=var, values=values)
        cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
        cb.bind("<<ComboboxSelected>>", on_change)
        cb.bind("<KeyRelease>", lambda e: on_change(None))

    def _save(self):
        if self.on_save:
            self.on_save(self.data)
        self.destroy()
