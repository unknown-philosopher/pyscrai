# pyscrai_forge/harvester/ui/windows/project_manager.py
"""Project configuration manager window."""

import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Optional
from pyscrai_core import ProjectManifest
from ..widgets.schema_builder import SchemaBuilderWidget
from ..widgets.dependency_manager import DependencyManagerWidget


class ProjectManagerWindow(tk.Toplevel):
    """Window for editing ProjectManifest configuration."""

    def __init__(self, parent, project_path: Optional[Path] = None):
        """
        Initialize the project manager window.

        Args:
            parent: Parent window
            project_path: Path to project directory (optional, for editing existing project)
        """
        super().__init__(parent)
        self.title("Project Manager")
        self.geometry("900x700")
        self.transient(parent)

        self.project_path = project_path
        self.manifest: Optional[ProjectManifest] = None
        self.modified = False

        self._create_ui()
        self._load_project()

    def _create_ui(self):
        """Build the window UI."""
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="Save", command=self._save_manifest).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Save As...", command=self._save_as).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Reload", command=self._load_project).pack(side=tk.LEFT, padx=2)

        self.status_label = ttk.Label(toolbar, text="", foreground="gray")
        self.status_label.pack(side=tk.RIGHT, padx=10)

        # Tabbed notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create tabs
        self._create_basic_info_tab()
        self._create_schema_tab()
        self._create_llm_settings_tab()
        self._create_systems_tab()
        self._create_dependencies_tab()
        self._create_advanced_tab()

        # Bottom buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(button_frame, text="Close", command=self.destroy).pack(side=tk.RIGHT)

    def _create_basic_info_tab(self):
        """Create the Basic Info tab."""
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="Basic Info")

        # Name
        ttk.Label(tab, text="Project Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(tab, textvariable=self.name_var, width=50).grid(row=0, column=1, sticky=tk.EW, pady=5)

        # Description
        ttk.Label(tab, text="Description:").grid(row=1, column=0, sticky=tk.NW, pady=5)
        self.description_text = tk.Text(tab, height=4, width=50, wrap=tk.WORD)
        self.description_text.grid(row=1, column=1, sticky=tk.EW, pady=5)

        # Author
        ttk.Label(tab, text="Author:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.author_var = tk.StringVar()
        ttk.Entry(tab, textvariable=self.author_var, width=50).grid(row=2, column=1, sticky=tk.EW, pady=5)

        # Version
        ttk.Label(tab, text="Version:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.version_var = tk.StringVar()
        ttk.Entry(tab, textvariable=self.version_var, width=20).grid(row=3, column=1, sticky=tk.W, pady=5)

        # Schema Version (read-only)
        ttk.Label(tab, text="Schema Version:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.schema_version_var = tk.StringVar()
        ttk.Label(tab, textvariable=self.schema_version_var, foreground="gray").grid(row=4, column=1, sticky=tk.W, pady=5)

        # Timestamps (read-only)
        ttk.Label(tab, text="Created:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.created_at_var = tk.StringVar()
        ttk.Label(tab, textvariable=self.created_at_var, foreground="gray").grid(row=5, column=1, sticky=tk.W, pady=5)

        ttk.Label(tab, text="Last Modified:").grid(row=6, column=0, sticky=tk.W, pady=5)
        self.last_modified_var = tk.StringVar()
        ttk.Label(tab, textvariable=self.last_modified_var, foreground="gray").grid(row=6, column=1, sticky=tk.W, pady=5)

        tab.columnconfigure(1, weight=1)

    def _create_schema_tab(self):
        """Create the Schema tab."""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Entity Schemas")

        ttk.Label(
            tab,
            text="Define custom resource fields for entity types:",
            font=("Arial", 10)
        ).pack(anchor=tk.W, pady=(0, 10))

        self.schema_builder = SchemaBuilderWidget(tab, on_change=self._mark_modified)
        self.schema_builder.pack(fill=tk.BOTH, expand=True)

    def _create_llm_settings_tab(self):
        """Create the LLM Settings tab."""
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="LLM Settings")

        # Provider
        ttk.Label(tab, text="LLM Provider:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.llm_provider_var = tk.StringVar()
        providers = ["openrouter", "lmstudio", "ollama", "anthropic", "openai"]
        ttk.Combobox(
            tab,
            textvariable=self.llm_provider_var,
            values=providers,
            state="readonly",
            width=30
        ).grid(row=0, column=1, sticky=tk.W, pady=5)

        # Default Model
        ttk.Label(tab, text="Default Model:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.llm_default_model_var = tk.StringVar()
        ttk.Entry(tab, textvariable=self.llm_default_model_var, width=50).grid(row=1, column=1, sticky=tk.EW, pady=5)

        # Fallback Model
        ttk.Label(tab, text="Fallback Model:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.llm_fallback_model_var = tk.StringVar()
        ttk.Entry(tab, textvariable=self.llm_fallback_model_var, width=50).grid(row=2, column=1, sticky=tk.EW, pady=5)

        # Memory Backend
        ttk.Label(tab, text="Memory Backend:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.memory_backend_var = tk.StringVar()
        ttk.Combobox(
            tab,
            textvariable=self.memory_backend_var,
            values=["chromadb_local", "chromadb_remote"],
            state="readonly",
            width=30
        ).grid(row=3, column=1, sticky=tk.W, pady=5)

        # Memory Collection ID
        ttk.Label(tab, text="Memory Collection ID:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.memory_collection_id_var = tk.StringVar()
        ttk.Entry(tab, textvariable=self.memory_collection_id_var, width=50).grid(row=4, column=1, sticky=tk.EW, pady=5)

        tab.columnconfigure(1, weight=1)

    def _create_systems_tab(self):
        """Create the Systems tab."""
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="Systems")

        ttk.Label(tab, text="Enabled Simulation Systems:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 10))

        self.systems_vars = {}
        for system in ["events", "memory", "relationships", "economy", "combat", "diplomacy"]:
            var = tk.BooleanVar()
            self.systems_vars[system] = var
            ttk.Checkbutton(tab, text=system.capitalize(), variable=var).pack(anchor=tk.W, pady=2)

    def _create_dependencies_tab(self):
        """Create the Dependencies tab."""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="Dependencies")

        ttk.Label(
            tab,
            text="Mod Dependencies (Mod ID → Version):",
            font=("Arial", 10)
        ).pack(anchor=tk.W, pady=(0, 10))

        self.dependency_manager = DependencyManagerWidget(tab, on_change=self._mark_modified)
        self.dependency_manager.pack(fill=tk.BOTH, expand=True)

    def _create_advanced_tab(self):
        """Create the Advanced tab."""
        tab = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab, text="Advanced")

        # Simulation Settings
        sim_frame = ttk.LabelFrame(tab, text="Simulation Settings", padding=10)
        sim_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(sim_frame, text="Snapshot Interval (turns):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.snapshot_interval_var = tk.IntVar()
        ttk.Spinbox(sim_frame, from_=1, to=1000, textvariable=self.snapshot_interval_var, width=10).grid(row=0, column=1, sticky=tk.W, pady=5)

        ttk.Label(sim_frame, text="Tick Duration (seconds):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.tick_duration_var = tk.DoubleVar()
        ttk.Spinbox(sim_frame, from_=0.1, to=60.0, increment=0.1, textvariable=self.tick_duration_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=5)

        ttk.Label(sim_frame, text="Max Concurrent Agents:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.max_concurrent_agents_var = tk.IntVar()
        ttk.Spinbox(sim_frame, from_=1, to=100, textvariable=self.max_concurrent_agents_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=5)

    def _load_project(self):
        """Load project manifest from disk."""
        if not self.project_path:
            # Create new manifest with defaults
            self.manifest = ProjectManifest(name="New Project")
            self.status_label.config(text="New Project (not saved)")
        else:
            manifest_path = self.project_path / "project.json"
            if not manifest_path.exists():
                messagebox.showerror("Error", f"project.json not found in {self.project_path}", parent=self)
                return

            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.manifest = ProjectManifest(**data)
                self.status_label.config(text=f"Loaded: {manifest_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load project.json:\n\n{str(e)}", parent=self)
                return

        self._populate_fields()
        self.modified = False

    def _populate_fields(self):
        """Populate UI fields with manifest data."""
        if not self.manifest:
            return

        # Basic Info
        self.name_var.set(self.manifest.name)
        self.description_text.delete("1.0", tk.END)
        self.description_text.insert("1.0", self.manifest.description)
        self.author_var.set(self.manifest.author)
        self.version_var.set(self.manifest.version)
        self.schema_version_var.set(str(self.manifest.schema_version))
        self.created_at_var.set(str(self.manifest.created_at))
        self.last_modified_var.set(str(self.manifest.last_modified_at))

        # Schema
        self.schema_builder.set_schemas(self.manifest.entity_schemas)

        # LLM Settings
        self.llm_provider_var.set(self.manifest.llm_provider)
        self.llm_default_model_var.set(self.manifest.llm_default_model)
        self.llm_fallback_model_var.set(self.manifest.llm_fallback_model or "")
        self.memory_backend_var.set(self.manifest.memory_backend)
        self.memory_collection_id_var.set(self.manifest.memory_collection_id)

        # Systems
        for system, var in self.systems_vars.items():
            var.set(system in self.manifest.enabled_systems)

        # Dependencies
        self.dependency_manager.set_dependencies(self.manifest.dependencies)

        # Advanced
        self.snapshot_interval_var.set(self.manifest.snapshot_interval)
        self.tick_duration_var.set(self.manifest.tick_duration_seconds)
        self.max_concurrent_agents_var.set(self.manifest.max_concurrent_agents)

    def _mark_modified(self):
        """Mark the project as modified."""
        self.modified = True
        self.status_label.config(text="Modified (unsaved)", foreground="orange")

    def _save_manifest(self):
        """Save the manifest to disk."""
        if not self.project_path:
            self._save_as()
            return

        self._do_save(self.project_path)

    def _save_as(self):
        """Save manifest to a new location."""
        directory = filedialog.askdirectory(title="Select Project Directory", parent=self)
        if not directory:
            return

        self.project_path = Path(directory)
        self._do_save(self.project_path)

    def _do_save(self, path: Path):
        """Perform the actual save operation."""
        try:
            # Build manifest from UI
            from datetime import datetime, UTC

            enabled_systems = [system for system, var in self.systems_vars.items() if var.get()]

            self.manifest = ProjectManifest(
                name=self.name_var.get(),
                description=self.description_text.get("1.0", tk.END).strip(),
                author=self.author_var.get(),
                version=self.version_var.get(),
                schema_version=self.manifest.schema_version if self.manifest else 1,
                created_at=self.manifest.created_at if self.manifest else datetime.now(UTC),
                last_modified_at=datetime.now(UTC),
                entity_schemas=self.schema_builder.get_schemas(),
                enabled_systems=enabled_systems,
                llm_provider=self.llm_provider_var.get(),
                llm_default_model=self.llm_default_model_var.get(),
                llm_fallback_model=self.llm_fallback_model_var.get() or None,
                memory_backend=self.memory_backend_var.get(),
                memory_collection_id=self.memory_collection_id_var.get(),
                snapshot_interval=self.snapshot_interval_var.get(),
                tick_duration_seconds=self.tick_duration_var.get(),
                max_concurrent_agents=self.max_concurrent_agents_var.get(),
                dependencies=self.dependency_manager.get_dependencies()
            )

            # Save to file
            manifest_path = path / "project.json"
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(json.loads(self.manifest.model_dump_json()), f, indent=2)

            self.modified = False
            self.status_label.config(text=f"Saved: {manifest_path}", foreground="green")
            messagebox.showinfo("Success", f"Project saved to:\n{manifest_path}", parent=self)

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save project:\n\n{str(e)}", parent=self)
