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
                 get_forge_manager: Optional[Callable[[], Any]] = None,
                 on_go_to_foundry: Optional[Callable[[], None]] = None,
                 on_go_to_loom: Optional[Callable[[], None]] = None,
                 on_go_to_chronicle: Optional[Callable[[], None]] = None,
                 on_go_to_cartography: Optional[Callable[[], None]] = None,
                 on_go_to_anvil: Optional[Callable[[], None]] = None):
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
        self.on_go_to_foundry = on_go_to_foundry
        self.on_go_to_loom = on_go_to_loom
        self.on_go_to_chronicle = on_go_to_chronicle
        self.on_go_to_cartography = on_go_to_cartography
        self.on_go_to_anvil = on_go_to_anvil
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the dashboard UI."""
        # Build overview directly (no tabs)
        self._build_overview_tab(self)
    
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
        
        # Pipeline phase buttons
        phase_frame = ttk.LabelFrame(main_container, text="Pipeline Phases", padding=15)
        phase_frame.pack(fill=tk.X, pady=(0, 20))
        
        # First row of buttons
        row1 = ttk.Frame(phase_frame)
        row1.pack(fill=tk.X, pady=(0, 10))
        
        edit_entities_btn = ttk.Button(
            row1,
            text="🔨 Edit Entities",
            command=self.on_edit_components,  # Goes to Foundry
            width=18,
            cursor="hand2"
        )
        edit_entities_btn.pack(side=tk.LEFT, padx=8)
        
        edit_relationships_btn = ttk.Button(
            row1,
            text="🕸️ Edit Relationships",
            command=self._on_edit_relationships,  # Goes to Loom
            width=18,
            cursor="hand2"
        )
        edit_relationships_btn.pack(side=tk.LEFT, padx=8)
        
        narrative_btn = ttk.Button(
            row1,
            text="📖 Narrative",
            command=self._on_narrative,  # Goes to Chronicle
            width=18,
            cursor="hand2"
        )
        narrative_btn.pack(side=tk.LEFT, padx=8)
        
        # Second row of buttons
        row2 = ttk.Frame(phase_frame)
        row2.pack(fill=tk.X)
        
        spatial_btn = ttk.Button(
            row2,
            text="🗺️ Spatial Editor",
            command=self._on_spatial_editor,  # Goes to Cartography
            width=18,
            cursor="hand2"
        )
        spatial_btn.pack(side=tk.LEFT, padx=8)
        
        finalize_btn = ttk.Button(
            row2,
            text="⚒️ Finalize",
            command=self._on_finalize,  # Goes to Anvil
            width=18,
            cursor="hand2"
        )
        finalize_btn.pack(side=tk.LEFT, padx=8)
        
        browse_db_btn = ttk.Button(
            row2,
            text="🗄️ Browse Database",
            command=self.on_browse_db,
            width=18,
            cursor="hand2"
        )
        browse_db_btn.pack(side=tk.LEFT, padx=8)
        
        # Three-column layout for stats, activity, and quick info
        bottom_frame = ttk.Frame(main_container)
        bottom_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        
        # Left column - Project Statistics
        stats_frame = ttk.LabelFrame(bottom_frame, text="Project Statistics", padding=15)
        stats_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self._load_project_stats(stats_frame)
        
        # Middle column - Recent Activity
        activity_frame = ttk.LabelFrame(bottom_frame, text="Recent Imports", padding=15)
        activity_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self._load_recent_imports(activity_frame)
        
        # Right column - Quick Info
        info_frame = ttk.LabelFrame(bottom_frame, text="Quick Info", padding=15)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        self._load_quick_info(info_frame)
        
        # Bottom actions
        bottom_action_frame = ttk.Frame(main_container)
        bottom_action_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(bottom_action_frame, text="⚙️ Project Settings",
                  command=self.on_settings).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(bottom_action_frame, text="📂 Browse Files",
                  command=self.on_browse_files).pack(side=tk.LEFT)
    
    def _on_edit_relationships(self):
        """Navigate to Loom phase."""
        if self.on_go_to_loom:
            self.on_go_to_loom()
        elif self.on_edit_components:
            # Fallback - try to go to component editor which should redirect
            self.on_edit_components()
    
    def _on_narrative(self):
        """Navigate to Chronicle phase."""
        if self.on_go_to_chronicle:
            self.on_go_to_chronicle()
    
    def _on_spatial_editor(self):
        """Navigate to Cartography phase."""
        if self.on_go_to_cartography:
            self.on_go_to_cartography()
    
    def _on_finalize(self):
        """Navigate to Anvil phase."""
        if self.on_go_to_anvil:
            self.on_go_to_anvil()
    
    
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
    
    def _load_quick_info(self, parent):
        """Load and display quick project information."""
        try:
            from pyscrai_forge.src import storage
            from datetime import datetime
            from pathlib import Path
            
            db_path = self.project_path / "world.db"
            
            # Database status
            if db_path.exists():
                db_size = db_path.stat().st_size / 1024  # KB
                ttk.Label(parent, 
                         text=f"Database: {db_size:.1f} KB",
                         font=("Arial", 10)).pack(anchor='w', pady=(0, 5))
            else:
                ttk.Label(parent, 
                         text="Database: Not initialized",
                         font=("Arial", 10),
                         foreground="gray").pack(anchor='w', pady=(0, 5))
            
            # Project path info
            path_parts = Path(self.project_path).parts
            if len(path_parts) > 3:
                short_path = "..." + "/".join(path_parts[-2:])
            else:
                short_path = str(self.project_path)
            
            ttk.Label(parent,
                     text=f"Path: {short_path}",
                     font=("Arial", 9),
                     foreground="gray",
                     wraplength=200).pack(anchor='w', pady=(0, 10))
            
            # Template info
            if self.manifest.template:
                ttk.Label(parent,
                         text=f"Template: {self.manifest.template}",
                         font=("Arial", 10)).pack(anchor='w', pady=(0, 5))
            
            # LLM provider info
            if self.manifest.llm_provider:
                ttk.Label(parent,
                         text=f"LLM: {self.manifest.llm_provider}",
                         font=("Arial", 10)).pack(anchor='w', pady=(0, 5))
                if self.manifest.llm_default_model:
                    ttk.Label(parent,
                             text=f"Model: {self.manifest.llm_default_model[:20]}...",
                             font=("Arial", 9),
                             foreground="gray").pack(anchor='w')
            
        except Exception as e:
            ttk.Label(parent, text=f"Error: {str(e)}",
                     font=("Arial", 9),
                     foreground="red").pack(anchor='w')
