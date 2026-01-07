"""Project dashboard widget for PyScrAI|Forge."""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Callable, Optional, Any
from pyscrai_core import ProjectManifest


class ProjectDashboardWidget(ttk.Frame):
    """Dashboard shown when project is loaded."""
    
    def __init__(self, parent,
                 project_path: Path,
                 manifest: ProjectManifest,
                 on_import: Callable[[], None],
                 on_edit_components: Callable[[], None],
                 on_browse_db: Callable[[], None],
                 on_settings: Callable[[], None],
                 on_browse_files: Callable[[], None],
                 get_forge_manager: Optional[Callable[[], Any]] = None):
        """
        Initialize project dashboard.
        
        Args:
            parent: Parent widget
            project_path: Path to project directory
            manifest: Project manifest
            on_import: Callback for Import Data button
            on_edit_components: Callback for Edit Components button
            on_browse_db: Callback for Browse Database button
            on_settings: Callback for Project Settings button
            on_browse_files: Callback for Browse Files button
            get_forge_manager: Optional callback to get configured ForgeManager
        """
        super().__init__(parent)
        self.project_path = project_path
        self.manifest = manifest
        self.on_import = on_import
        self.on_edit_components = on_edit_components
        self.on_browse_db = on_browse_db
        self.on_settings = on_settings
        self.on_browse_files = on_browse_files
        self.get_forge_manager = get_forge_manager
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the dashboard UI with tabs."""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Overview tab (original dashboard content)
        overview_frame = ttk.Frame(self.notebook)
        self.notebook.add(overview_frame, text="📊 Overview")
        self._build_overview_tab(overview_frame)
        
        # Narrative Generator tab (only if ForgeManager is available)
        if self.get_forge_manager:
            narrative_frame = ttk.Frame(self.notebook)
            self.notebook.add(narrative_frame, text="📖 Narrative")
            self._build_narrative_tab(narrative_frame)
    
    def _build_overview_tab(self, parent):
        """Build the original overview content."""
        # Main container with padding
        main_container = ttk.Frame(parent)
        main_container.pack(expand=True, fill=tk.BOTH, padx=20, pady=10)
        
        # Project info card
        info_frame = ttk.LabelFrame(main_container, text="Project Information", padding=15)
        info_frame.pack(fill=tk.X, pady=(0, 20))
        
        name_label = ttk.Label(info_frame, text=f"📁 {self.manifest.name}",
                              font=("Arial", 14, "bold"))
        name_label.pack(anchor='w', pady=(0, 5))
        
        if self.manifest.description:
            desc_label = ttk.Label(info_frame, text=self.manifest.description,
                                  wraplength=700, font=("Arial", 10))
            desc_label.pack(anchor='w', pady=(0, 5))
        
        path_label = ttk.Label(info_frame, text=f"Location: {self.project_path}",
                              font=("Arial", 8), foreground="gray")
        path_label.pack(anchor='w')
        
        # Quick action buttons
        action_frame = ttk.Frame(main_container)
        action_frame.pack(pady=20)
        
        # Import Data button
        import_btn = ttk.Button(
            action_frame,
            text="📥 Import Data",
            command=self.on_import,
            width=20,
            style="Accent.TButton",
            cursor="hand2"
        )
        import_btn.pack(side=tk.LEFT, padx=15)
        
        # Edit Components button
        edit_btn = ttk.Button(
            action_frame,
            text="✏️ Edit Components",
            command=self.on_edit_components,
            width=20,
            cursor="hand2"
        )
        edit_btn.pack(side=tk.LEFT, padx=15)
        
        # Browse Database button
        browse_btn = ttk.Button(
            action_frame,
            text="🗄️ Browse Database",
            command=self.on_browse_db,
            width=20,
            cursor="hand2"
        )
        browse_btn.pack(side=tk.LEFT, padx=15)
        
        # Two-column layout for project stats and recent activity  
        bottom_frame = ttk.Frame(main_container)
        bottom_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        
        # Left column - Project Statistics
        stats_frame = ttk.LabelFrame(bottom_frame, text="Project Statistics", padding=15)
        stats_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self._load_project_stats(stats_frame)
        
        # Right column - Recent Activity
        activity_frame = ttk.LabelFrame(bottom_frame, text="Recent Imports", padding=15)
        activity_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        self._load_recent_imports(activity_frame)
        
        # Bottom actions
        bottom_action_frame = ttk.Frame(main_container)
        bottom_action_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(bottom_action_frame, text="⚙️ Project Settings",
                  command=self.on_settings).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(bottom_action_frame, text="📂 Browse Files",
                  command=self.on_browse_files).pack(side=tk.LEFT)
    
    def _build_narrative_tab(self, parent):
        """Build the narrative generator tab."""
        try:
            from pyscrai_forge.src.ui.widgets.narrative_panel import NarrativeGeneratorWidget
            
            narrative_widget = NarrativeGeneratorWidget(
                parent,
                self.project_path,
                self.manifest,
                self.get_forge_manager
            )
            narrative_widget.pack(fill=tk.BOTH, expand=True)
            
        except Exception as e:
            # Fallback if narrative widget can't be created
            error_frame = ttk.Frame(parent)
            error_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            ttk.Label(error_frame, text="📖 Narrative Generator",
                     font=("Arial", 16, "bold")).pack(anchor='w', pady=(0, 10))
            
            ttk.Label(error_frame, text="❌ Narrative generation is not available.",
                     font=("Arial", 12), foreground="red").pack(anchor='w', pady=(0, 5))
            
            ttk.Label(error_frame, text=f"Error: {str(e)}",
                     font=("Arial", 10), foreground="gray").pack(anchor='w')
    
    def _load_project_stats(self, parent):
        """Load and display database statistics."""
        try:
            from pyscrai_forge.src import storage
            db_path = self.project_path / "world.db"
            
            if not db_path.exists():
                ttk.Label(parent, text="Database not initialized yet. Import some data to get started!",
                         foreground="gray").pack(anchor='w')
                return
            
            entities = storage.load_all_entities(db_path)
            relationships = storage.load_all_relationships(db_path)
            
            # Count by type
            type_counts = {}
            for e in entities:
                t = e.descriptor.entity_type.value if hasattr(e.descriptor, 'entity_type') else "unknown"
                type_counts[t] = type_counts.get(t, 0) + 1
            
            # Total entities
            total_label = ttk.Label(parent, 
                                   text=f"• {len(entities)} Total Entities",
                                   font=("Arial", 11, "bold"))
            total_label.pack(anchor='w', pady=(0, 5))
            
            # By type
            for entity_type, count in sorted(type_counts.items()):
                type_label = ttk.Label(parent,
                                      text=f"    ◦ {count} {entity_type.title()}{'s' if count != 1 else ''}",
                                      font=("Arial", 10))
                type_label.pack(anchor='w', pady=1)
            
            # Relationships
            rel_label = ttk.Label(parent,
                                 text=f"• {len(relationships)} Relationships",
                                 font=("Arial", 11, "bold"))
            rel_label.pack(anchor='w', pady=(10, 0))
            
        except Exception as e:
            error_label = ttk.Label(parent, text=f"Error loading stats: {str(e)}",
                                   foreground="red")
            error_label.pack(anchor='w')
    
    def _load_recent_imports(self, parent):
        """Load and display recent import files."""
        data_dir = self.project_path / "data"
        
        if not data_dir.exists() or not any(data_dir.glob("entity_components_*.json")):
            ttk.Label(parent, text="No imports yet. Use 'Import Data' to get started!",
                     foreground="gray").pack(anchor='w')
            return
        
        files = sorted(data_dir.glob("entity_components_*.json"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
        
        for i, f in enumerate(files[:3]):
            ttk.Label(parent, text=f"• {f.name}",
                     font=("Arial", 9)).pack(anchor='w', pady=2)
