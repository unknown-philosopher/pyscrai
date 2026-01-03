"""Project dashboard widget for PyScrAI|Forge."""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Callable
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
                 on_browse_files: Callable[[], None]):
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
        """
        super().__init__(parent)
        self.project_path = project_path
        self.manifest = manifest
        self.on_import = on_import
        self.on_edit_components = on_edit_components
        self.on_browse_db = on_browse_db
        self.on_settings = on_settings
        self.on_browse_files = on_browse_files
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the dashboard UI."""
        # Main container with padding
        main_container = ttk.Frame(self)
        main_container.pack(expand=True, fill=tk.BOTH, padx=40, pady=20)
        
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
        action_frame.pack(pady=30)
        
        # Import Data button
        import_frame = self._create_action_button(
            action_frame, "📥 Import\nData", self.on_import, "#4CAF50"
        )
        import_frame.pack(side=tk.LEFT, padx=15)
        
        # Edit Components button
        edit_frame = self._create_action_button(
            action_frame, "✏️ Edit\nComponents", self.on_edit_components, "#2196F3"
        )
        edit_frame.pack(side=tk.LEFT, padx=15)
        
        # Browse Database button
        db_frame = self._create_action_button(
            action_frame, "🗄️ Browse\nDatabase", self.on_browse_db, "#FF9800"
        )
        db_frame.pack(side=tk.LEFT, padx=15)
        
        # Stats panel
        stats_frame = ttk.LabelFrame(main_container, text="Quick Stats", padding=15)
        stats_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        self._load_stats(stats_frame)
        
        # Recent imports
        recent_frame = ttk.LabelFrame(main_container, text="Recent Imports", padding=15)
        recent_frame.pack(fill=tk.X, pady=(0, 20))
        
        self._load_recent_imports(recent_frame)
        
        # Bottom actions
        bottom_frame = ttk.Frame(main_container)
        bottom_frame.pack(fill=tk.X)
        
        ttk.Button(bottom_frame, text="⚙️ Project Settings",
                  command=self.on_settings).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(bottom_frame, text="📂 Browse Files",
                  command=self.on_browse_files).pack(side=tk.LEFT)
    
    def _create_action_button(self, parent, text, command, color):
        """Create a styled action button."""
        frame = tk.Frame(parent, bg=color, relief=tk.RAISED, borderwidth=2)
        
        btn = tk.Button(frame, text=text,
                       command=command,
                       width=12, height=4,
                       font=("Arial", 11),
                       bg=color, fg="white",
                       activebackground=self._darken_color(color),
                       activeforeground="white",
                       relief=tk.FLAT, cursor="hand2")
        btn.pack(padx=2, pady=2)
        
        return frame
    
    def _darken_color(self, hex_color):
        """Darken a hex color by 20%."""
        # Simple darkening - multiply RGB values by 0.8
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r, g, b = int(r * 0.8), int(g * 0.8), int(b * 0.8)
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def _load_stats(self, parent):
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
