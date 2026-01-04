# pyscrai_forge/harvester/ui/dialogs/project_wizard.py
"""Multi-step wizard for creating new projects."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from pyscrai_core import ProjectManifest
import json
from datetime import datetime, UTC



class ProjectWizardDialog(tk.Toplevel):
    """Wizard for creating new PyScrAI projects."""

    def __init__(self, parent, on_complete=None):
        """
        Initialize the project wizard.

        Args:
            parent: Parent window
            on_complete: Callback function(project_path) called when wizard completes
        """
        super().__init__(parent)
        self.title("New Project Wizard")
        self.geometry("700x600")
        self.transient(parent)
        self.grab_set()

        self.on_complete = on_complete
        self.current_step = 0
        self.project_data = {}

        self._create_ui()
        self._show_step(0)

    def _create_ui(self):
        """Build the wizard UI."""
        # Header
        header_frame = ttk.Frame(self, relief=tk.RAISED, borderwidth=1)
        header_frame.pack(fill=tk.X)

        self.step_label = ttk.Label(
            header_frame,
            text="Step 1 of 4: Project Identity",
            font=("Arial", 12, "bold"),
            padding=15
        )
        self.step_label.pack()

        # Content area
        self.content_frame = ttk.Frame(self, padding=20)
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # Button bar
        button_frame = ttk.Frame(self, padding=10)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.back_button = ttk.Button(button_frame, text="< Back", command=self._go_back)
        self.back_button.pack(side=tk.LEFT)

        self.next_button = ttk.Button(button_frame, text="Next >", command=self._go_next)
        self.next_button.pack(side=tk.RIGHT, padx=5)

        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self.destroy)
        self.cancel_button.pack(side=tk.RIGHT)

    def _show_step(self, step: int):
        """Show the specified step."""
        self.current_step = step

        # Update header
        titles = [
            "Step 1 of 4: Project Identity",
            "Step 2 of 4: Entity Schemas",
            "Step 3 of 4: LLM Configuration",
            "Step 4 of 4: Review & Create"
        ]
        self.step_label.config(text=titles[step])

        # Update buttons
        self.back_button.config(state=tk.NORMAL if step > 0 else tk.DISABLED)

        if step == 3:  # Last step
            self.next_button.config(text="Create Project")
        else:
            self.next_button.config(text="Next >")

        # Clear content area
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Show appropriate step content
        if step == 0:
            self._create_step_identity()
        elif step == 1:
            self._create_step_schemas()
        elif step == 2:
            self._create_step_llm()
        elif step == 3:
            self._create_step_review()

    def _create_step_identity(self):
        """Step 1: Project Identity."""
        ttk.Label(
            self.content_frame,
            text="Enter basic information about your project:",
            font=("Arial", 10)
        ).pack(anchor=tk.W, pady=(0, 15))

        # Project Name
        ttk.Label(self.content_frame, text="Project Name:").pack(anchor=tk.W, pady=5)
        self.name_var = tk.StringVar(value=self.project_data.get("name", ""))
        ttk.Entry(self.content_frame, textvariable=self.name_var, width=50).pack(anchor=tk.W, pady=(0, 10))

        # Description
        ttk.Label(self.content_frame, text="Description:").pack(anchor=tk.W, pady=5)
        self.description_text = tk.Text(self.content_frame, height=4, width=50, wrap=tk.WORD)
        self.description_text.pack(anchor=tk.W, pady=(0, 10))
        if "description" in self.project_data:
            self.description_text.insert("1.0", self.project_data["description"])

        # Author
        ttk.Label(self.content_frame, text="Author:").pack(anchor=tk.W, pady=5)
        self.author_var = tk.StringVar(value=self.project_data.get("author", ""))
        ttk.Entry(self.content_frame, textvariable=self.author_var, width=50).pack(anchor=tk.W, pady=(0, 10))

        # Template Selection
        ttk.Label(self.content_frame, text="Template:").pack(anchor=tk.W, pady=5)
        self.template_var = tk.StringVar(value=self.project_data.get("template", ""))
        templates = self._get_available_templates()
        self.template_dropdown = ttk.Combobox(
            self.content_frame,
            textvariable=self.template_var,
            values=templates,
            state="readonly",
            width=50
        )
        self.template_dropdown.pack(anchor=tk.W, pady=(0, 10))

        # Project Location
        ttk.Label(self.content_frame, text="Project Location:").pack(anchor=tk.W, pady=5)

        location_frame = ttk.Frame(self.content_frame)
        location_frame.pack(anchor=tk.W, pady=(0, 10))

        self.location_var = tk.StringVar(value=self.project_data.get("location", ""))
        ttk.Entry(location_frame, textvariable=self.location_var, width=40).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(location_frame, text="Browse...", command=self._browse_location).pack(side=tk.LEFT)

    def _get_available_templates(self):
        """Return a list of available template directory names from the templates directory."""
        import os
        # Find project root (assume this file is always 4 levels below root)
        current = os.path.abspath(os.path.dirname(__file__))
        for _ in range(4):
            current = os.path.dirname(current)
        templates_dir = os.path.join(current, 'pyscrai_forge', 'prompts', 'templates')
        try:
            templates = [d for d in os.listdir(templates_dir) if os.path.isdir(os.path.join(templates_dir, d))]
            return sorted(templates)
        except Exception:
            return []

    def _browse_location(self):
        """Browse for project location."""
        directory = filedialog.askdirectory(title="Select Project Location", parent=self)
        if directory:
            self.location_var.set(directory)

    def _create_step_schemas(self):
        """Step 2: Entity Schemas."""
        ttk.Label(
            self.content_frame,
            text="Define custom resource fields for entity types (optional):",
            font=("Arial", 10)
        ).pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(
            self.content_frame,
            text="You can skip this step and add schemas later.",
            foreground="gray"
        ).pack(anchor=tk.W, pady=(0, 10))

        # Schema builder
        from ..widgets.schema_builder import SchemaBuilderWidget
        schemas = self.project_data.get("schemas", {})
        self.schema_builder = SchemaBuilderWidget(self.content_frame, schemas=schemas)
        self.schema_builder.pack(fill=tk.BOTH, expand=True)

    def _create_step_llm(self):
        """Step 3: LLM Configuration."""
        ttk.Label(
            self.content_frame,
            text="Configure LLM provider settings:",
            font=("Arial", 10)
        ).pack(anchor=tk.W, pady=(0, 15))

        # Provider
        ttk.Label(self.content_frame, text="LLM Provider:").pack(anchor=tk.W, pady=5)
        self.llm_provider_var = tk.StringVar(value=self.project_data.get("llm_provider", "openrouter"))
        providers = ["openrouter", "lmstudio", "ollama", "anthropic", "openai"]
        ttk.Combobox(
            self.content_frame,
            textvariable=self.llm_provider_var,
            values=providers,
            state="readonly",
            width=30
        ).pack(anchor=tk.W, pady=(0, 10))

        # Default Model
        ttk.Label(self.content_frame, text="Default Model:").pack(anchor=tk.W, pady=5)
        self.llm_default_model_var = tk.StringVar(value=self.project_data.get("llm_default_model", ""))
        ttk.Entry(self.content_frame, textvariable=self.llm_default_model_var, width=50).pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(
            self.content_frame,
            text="(e.g., 'anthropic/claude-sonnet-4-20250514' for OpenRouter)",
            foreground="gray",
            font=("Arial", 8)
        ).pack(anchor=tk.W)

    def _create_step_review(self):
        """Step 4: Review & Create."""
        ttk.Label(
            self.content_frame,
            text="Review your project configuration:",
            font=("Arial", 10, "bold")
        ).pack(anchor=tk.W, pady=(0, 15))

        # Collect all data
        self._collect_step_data()

        # Display summary
        summary_text = tk.Text(self.content_frame, height=20, width=60, wrap=tk.WORD)
        summary_text.pack(fill=tk.BOTH, expand=True)

        summary = f"""Project Name: {self.project_data.get('name', 'N/A')}
Author: {self.project_data.get('author', 'N/A')}
Location: {self.project_data.get('location', 'N/A')}

Description:
{self.project_data.get('description', 'N/A')}

LLM Provider: {self.project_data.get('llm_provider', 'openrouter')}
Default Model: {self.project_data.get('llm_default_model', 'Not specified')}

Entity Schemas: {len(self.project_data.get('schemas', {}))} type(s) defined

The wizard will create:
• project.json (manifest)
• world.db (database)
• Standard directory structure
"""

        summary_text.insert("1.0", summary)
        summary_text.config(state=tk.DISABLED)

    def _collect_step_data(self):
        """Collect data from the current step."""
        if self.current_step == 0:
            self.project_data["name"] = self.name_var.get().strip()
            self.project_data["description"] = self.description_text.get("1.0", tk.END).strip()
            self.project_data["author"] = self.author_var.get().strip()
            self.project_data["location"] = self.location_var.get().strip()
            self.project_data["template"] = self.template_var.get() if self.template_var.get() else None
        elif self.current_step == 1:
            self.project_data["schemas"] = self.schema_builder.get_schemas()
        elif self.current_step == 2:
            self.project_data["llm_provider"] = self.llm_provider_var.get()
            self.project_data["llm_default_model"] = self.llm_default_model_var.get().strip()

    def _validate_step(self) -> bool:
        """Validate current step data."""
        self._collect_step_data()

        if self.current_step == 0:
            if not self.project_data.get("name"):
                messagebox.showerror("Validation Error", "Project name is required.", parent=self)
                return False

            if not self.project_data.get("location"):
                messagebox.showerror("Validation Error", "Project location is required.", parent=self)
                return False

            # Check if location exists
            location = Path(self.project_data["location"])
            if not location.exists():
                if not messagebox.askyesno(
                    "Create Directory",
                    f"Directory does not exist:\n{location}\n\nCreate it?",
                    parent=self
                ):
                    return False

        return True

    def _go_back(self):
        """Go to previous step."""
        if self.current_step > 0:
            self._collect_step_data()
            self._show_step(self.current_step - 1)

    def _go_next(self):
        """Go to next step or finish."""
        if not self._validate_step():
            return

        if self.current_step < 3:
            self._show_step(self.current_step + 1)
        else:
            self._create_project()

    def _create_project(self):
        """Create the project."""
        try:
            # Create project directory
            project_path = Path(self.project_data["location"]) / self.project_data["name"]

            if project_path.exists():
                if not messagebox.askyesno(
                    "Directory Exists",
                    f"Directory already exists:\n{project_path}\n\nUse it anyway?",
                    parent=self
                ):
                    return
            else:
                project_path.mkdir(parents=True)

            # Create subdirectories
            (project_path / "assets").mkdir(exist_ok=True)
            (project_path / "data").mkdir(exist_ok=True)
            (project_path / "logs").mkdir(exist_ok=True)

            # Create manifest
            manifest = ProjectManifest(
                name=self.project_data["name"],
                description=self.project_data.get("description", ""),
                author=self.project_data.get("author", ""),
                version="0.1.0",
                entity_schemas=self.project_data.get("schemas", {}),
                llm_provider=self.project_data.get("llm_provider", "openrouter"),
                llm_default_model=self.project_data.get("llm_default_model", ""),
                template=self.project_data.get("template"),
                created_at=datetime.now(UTC),
                last_modified_at=datetime.now(UTC)
            )

            # Save manifest
            manifest_path = project_path / "project.json"
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(json.loads(manifest.model_dump_json()), f, indent=2)

            # Initialize database
            from pyscrai_forge.src.storage import init_harvester_tables
            db_path = project_path / "world.db"
            init_harvester_tables(db_path)

            messagebox.showinfo(
                "Success",
                f"Project created successfully!\n\nLocation: {project_path}",
                parent=self
            )

            if self.on_complete:
                self.on_complete(project_path)

            self.destroy()

        except Exception as e:
            messagebox.showerror("Create Error", f"Failed to create project:\n\n{str(e)}", parent=self)
