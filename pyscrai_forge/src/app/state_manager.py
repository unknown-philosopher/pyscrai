"""State management for PyScrAI|Forge application.

Handles UI state transitions and state-specific UI building.
"""

from __future__ import annotations

import tkinter as tk
from enum import Enum
from pathlib import Path
from tkinter import ttk
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from pyscrai_core import ProjectManifest
    from pyscrai_forge.src.user_config import UserConfig
    from pyscrai_forge.src.ui.widgets.landing_page import LandingPageWidget
    from pyscrai_forge.src.ui.widgets.project_dashboard import ProjectDashboardWidget


class AppState(Enum):
    """Application states for UI navigation.
    
    PyScrAI 2.0 introduces a sequential pipeline with 5 phases:
    - PHASE_FOUNDRY: Entity extraction and staging
    - PHASE_LOOM: Relationship mapping and graph visualization
    - PHASE_CHRONICLE: Narrative synthesis with verification
    - PHASE_CARTOGRAPHY: Spatial anchoring and map placement
    - PHASE_ANVIL: Merge, conflict resolution, and finalization
    """
    LANDING = "landing"
    DASHBOARD = "dashboard"
    COMPONENT_EDITOR = "component_editor"  # Legacy, maps to PHASE_FOUNDRY
    
    # PyScrAI 2.0 Pipeline Phases
    PHASE_FOUNDRY = "phase_foundry"
    PHASE_LOOM = "phase_loom"
    PHASE_CHRONICLE = "phase_chronicle"
    PHASE_CARTOGRAPHY = "phase_cartography"
    PHASE_ANVIL = "phase_anvil"


# Phase ordering for navigation
PHASE_STATES = [
    AppState.PHASE_FOUNDRY,
    AppState.PHASE_LOOM,
    AppState.PHASE_CHRONICLE,
    AppState.PHASE_CARTOGRAPHY,
    AppState.PHASE_ANVIL,
]


def get_next_phase_state(current: AppState) -> AppState | None:
    """Get the next phase state, or None if at end."""
    if current not in PHASE_STATES:
        return None
    idx = PHASE_STATES.index(current)
    if idx < len(PHASE_STATES) - 1:
        return PHASE_STATES[idx + 1]
    return None


def get_previous_phase_state(current: AppState) -> AppState | None:
    """Get the previous phase state, or None if at start."""
    if current not in PHASE_STATES:
        return None
    idx = PHASE_STATES.index(current)
    if idx > 0:
        return PHASE_STATES[idx - 1]
    return None


def is_phase_state(state: AppState) -> bool:
    """Check if a state is a pipeline phase."""
    return state in PHASE_STATES


class AppStateManager:
    """Manages UI state transitions and state-specific UI building."""
    
    def __init__(
        self,
        root: tk.Tk,
        main_container: tk.Frame,
        status_bar: ttk.Label,
        callbacks: dict[str, Callable],
    ):
        """Initialize state manager.
        
        Args:
            root: Main Tk window
            main_container: Container frame for state-specific UI
            status_bar: Status bar label to update
            callbacks: Dictionary of callback functions for UI actions
        """
        self.root = root
        self.main_container = main_container
        self.status_bar = status_bar
        self.callbacks = callbacks
        
        self.current_state: AppState = AppState.LANDING
        
        # UI components that persist across states
        self.validation_frame: Optional[tk.Frame] = None
        self.validation_label: Optional[tk.Label] = None
        self.entities_tree: Optional[ttk.Treeview] = None
        self.relationships_tree: Optional[ttk.Treeview] = None
        
        # State-specific data (passed from main app)
        self.project_path: Optional[Path] = None
        self.db_path: Optional[Path] = None
        self.manifest: Optional["ProjectManifest"] = None
        self.user_config: Optional["UserConfig"] = None
    
    def set_project_data(
        self,
        project_path: Optional[Path],
        db_path: Optional[Path],
        manifest: Optional["ProjectManifest"],
        user_config: Optional["UserConfig"],
    ):
        """Update project-related data.
        
        Args:
            project_path: Path to current project
            db_path: Path to database file
            manifest: Project manifest
            user_config: User configuration
        """
        self.project_path = project_path
        self.db_path = db_path
        self.manifest = manifest
        self.user_config = user_config
    
    def transition_to(self, new_state: AppState) -> None:
        """Transition to a new UI state.
        
        Args:
            new_state: Target state to transition to
        """
        self.current_state = new_state
        
        # Clear main container
        if self.main_container:
            for widget in self.main_container.winfo_children():
                widget.destroy()
        
        # Hide/show validation frame based on state
        if self.validation_frame:
            if new_state == AppState.COMPONENT_EDITOR:
                self.validation_frame.pack(fill=tk.X, padx=5, pady=5, before=self.main_container)
            else:
                self.validation_frame.pack_forget()
        
        # Build state-specific UI
        if new_state == AppState.LANDING:
            self._build_landing_page()
        elif new_state == AppState.DASHBOARD:
            self._build_dashboard()
        elif new_state == AppState.COMPONENT_EDITOR:
            # Legacy: redirect to PHASE_FOUNDRY
            self._build_phase_foundry()
        elif new_state == AppState.PHASE_FOUNDRY:
            self._build_phase_foundry()
        elif new_state == AppState.PHASE_LOOM:
            self._build_phase_loom()
        elif new_state == AppState.PHASE_CHRONICLE:
            self._build_phase_chronicle()
        elif new_state == AppState.PHASE_CARTOGRAPHY:
            self._build_phase_cartography()
        elif new_state == AppState.PHASE_ANVIL:
            self._build_phase_anvil()
        
        # Update status bar
        self.update_status_bar()
    
    def _build_landing_page(self) -> None:
        """Build the landing page state."""
        from pyscrai_forge.src.ui.widgets.landing_page import LandingPageWidget
        
        landing = LandingPageWidget(
            self.main_container,
            on_new_project=self.callbacks.get("new_project"),
            on_open_project=self.callbacks.get("open_project"),
            on_open_recent=self.callbacks.get("open_recent"),
            recent_projects=self.user_config.recent_projects if self.user_config else []
        )
        landing.pack(fill=tk.BOTH, expand=True)
    
    def _build_dashboard(self) -> None:
        """Build the project dashboard state."""
        if not self.project_path or not self.manifest:
            # Fallback to landing if no project
            self.transition_to(AppState.LANDING)
            return
        
        from pyscrai_forge.src.ui.widgets.project_dashboard import ProjectDashboardWidget
        
        # Create a factory function for ForgeManager
        def get_forge_manager():
            """Create and return a configured ForgeManager instance."""
            try:
                from pyscrai_forge.agents.manager import ForgeManager
                from pyscrai_core.llm_interface import create_provider
                import os
                
                # Get provider settings from project manifest
                manifest = self.manifest
                provider_name = manifest.llm_provider
                
                # Get API key from environment
                env_key_map = {
                    "openrouter": "OPENROUTER_API_KEY",
                    "cherry": "CHERRY_API_KEY", 
                    "lm_studio": "LM_STUDIO_API_KEY",
                    "lm_proxy": "LM_PROXY_API_KEY",
                }
                
                api_key = os.getenv(env_key_map.get(provider_name, "OPENROUTER_API_KEY"))
                if not api_key:
                    raise ValueError(f"No API key found for {provider_name}")
                
                # Create provider
                provider = create_provider(
                    provider_name,
                    api_key=api_key,
                    base_url=manifest.llm_base_url,
                    timeout=60.0
                )
                
                # Set default model
                if hasattr(provider, 'default_model'):
                    provider.default_model = manifest.llm_default_model
                
                # Create ForgeManager
                return ForgeManager(provider, self.project_path)
            except Exception as e:
                # Return None if ForgeManager can't be created
                return None
        
        dashboard = ProjectDashboardWidget(
            self.main_container,
            project_path=self.project_path,
            manifest=self.manifest,
            on_import=self.callbacks.get("import_file"),
            on_edit_components=self.callbacks.get("edit_components"),
            on_browse_db=self.callbacks.get("browse_db"),
            on_settings=self.callbacks.get("project_settings"),
            on_browse_files=self.callbacks.get("browse_files"),
            get_forge_manager=get_forge_manager,
            on_go_to_foundry=lambda: self.transition_to(AppState.PHASE_FOUNDRY),
            on_go_to_loom=lambda: self.transition_to(AppState.PHASE_LOOM),
            on_go_to_chronicle=lambda: self.transition_to(AppState.PHASE_CHRONICLE),
            on_go_to_cartography=lambda: self.transition_to(AppState.PHASE_CARTOGRAPHY),
            on_go_to_anvil=lambda: self.transition_to(AppState.PHASE_ANVIL)
        )
        dashboard.pack(fill=tk.BOTH, expand=True)
    
    def _build_component_editor(self) -> None:
        """Build the component editor state (entity/relationship editing)."""
        # Top: Validation Summary Banner
        if not self.validation_frame:
            self.validation_frame = ttk.Frame(self.root, height=40)
            self.validation_label = ttk.Label(
                self.validation_frame,
                text="No Packet Loaded",
                font=("Arial", 10)
            )
            self.validation_label.pack(side=tk.LEFT, padx=10)
        self.validation_frame.pack(fill=tk.X, padx=5, pady=5, before=self.main_container)

        # Main paned window (split view)
        paned = ttk.PanedWindow(self.main_container, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left: Entities panel
        entities_frame = ttk.Frame(paned)
        paned.add(entities_frame, weight=2)
        
        ttk.Label(entities_frame, text="Entities", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        # Entities toolbar
        entities_toolbar = ttk.Frame(entities_frame)
        entities_toolbar.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(
            entities_toolbar,
            text="Load Data...",
            command=self.callbacks.get("load_data_file")
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            entities_toolbar,
            text="Add Entity",
            command=self.callbacks.get("add_entity")
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            entities_toolbar,
            text="Delete Selected",
            command=self.callbacks.get("delete_selected_entity")
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            entities_toolbar,
            text="Refine Components",
            command=self.callbacks.get("refine_components")
        ).pack(side=tk.LEFT, padx=2)
        
        # Back to Dashboard button (if project loaded)
        if self.project_path:
            ttk.Button(
                entities_toolbar,
                text="← Back to Dashboard",
                command=lambda: self.callbacks.get("transition_to_dashboard")()
            ).pack(side=tk.RIGHT, padx=2)
        
        # Entities treeview
        entities_tree_frame = ttk.Frame(entities_frame)
        entities_tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.entities_tree = ttk.Treeview(
            entities_tree_frame,
            columns=("id", "type", "name", "issues"),
            show="headings",
            selectmode=tk.EXTENDED,
        )
        self.entities_tree.heading("id", text="ID")
        self.entities_tree.heading("type", text="Type")
        self.entities_tree.heading("name", text="Name")
        self.entities_tree.heading("issues", text="Validation Issues")
        
        self.entities_tree.column("id", width=150)
        self.entities_tree.column("type", width=80)
        self.entities_tree.column("name", width=150)
        self.entities_tree.column("issues", width=200)

        # Tag configuration for coloring rows with issues
        self.entities_tree.tag_configure("error", background="#550000", foreground="white")
        self.entities_tree.tag_configure("warning", background="#554400", foreground="white")
        
        entities_scroll = ttk.Scrollbar(
            entities_tree_frame,
            orient=tk.VERTICAL,
            command=self.entities_tree.yview
        )
        self.entities_tree.configure(yscrollcommand=entities_scroll.set)
        
        self.entities_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        entities_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.entities_tree.bind("<Double-1>", lambda e: self.callbacks.get("edit_entity")())
        
        # Enable column sorting
        from pyscrai_forge.src.ui.widgets.treeview_sorter import TreeviewSorter
        self.entities_sorter = TreeviewSorter(self.entities_tree)
        # Enable sorting for all columns with default string sorting
        self.entities_sorter.enable_sorting_for_all_columns()
        
        # Right: Relationships panel
        relationships_frame = ttk.Frame(paned)
        paned.add(relationships_frame, weight=1)
        
        ttk.Label(relationships_frame, text="Relationships", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        # Relationships toolbar
        rel_toolbar = ttk.Frame(relationships_frame)
        rel_toolbar.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(
            rel_toolbar,
            text="Add Relationship",
            command=self.callbacks.get("add_relationship")
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            rel_toolbar,
            text="Delete Selected",
            command=self.callbacks.get("delete_selected_relationship")
        ).pack(side=tk.LEFT, padx=2)
        
        # Relationships treeview
        rel_tree_frame = ttk.Frame(relationships_frame)
        rel_tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.relationships_tree = ttk.Treeview(
            rel_tree_frame,
            columns=("source", "target", "type", "issues"),
            show="headings",
            selectmode=tk.EXTENDED,
        )
        self.relationships_tree.heading("source", text="Source")
        self.relationships_tree.heading("target", text="Target")
        self.relationships_tree.heading("type", text="Type")
        self.relationships_tree.heading("issues", text="Issues")
        
        self.relationships_tree.column("source", width=120)
        self.relationships_tree.column("target", width=120)
        self.relationships_tree.column("type", width=100)
        self.relationships_tree.column("issues", width=150)

        self.relationships_tree.tag_configure("error", background="#550000", foreground="white")
        
        rel_scroll = ttk.Scrollbar(
            rel_tree_frame,
            orient=tk.VERTICAL,
            command=self.relationships_tree.yview
        )
        self.relationships_tree.configure(yscrollcommand=rel_scroll.set)
        
        self.relationships_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        rel_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.relationships_tree.bind("<Double-1>", lambda e: self.callbacks.get("edit_relationship")())
        
        # Enable column sorting
        from pyscrai_forge.src.ui.widgets.treeview_sorter import TreeviewSorter
        self.relationships_sorter = TreeviewSorter(self.relationships_tree)
        # Enable sorting for all columns with default string sorting
        self.relationships_sorter.enable_sorting_for_all_columns()
        
        # Bottom: Action Bar
        action_frame = ttk.Frame(self.main_container)
        action_frame.pack(fill=tk.X, padx=5, pady=10)
        
        project_label = ttk.Label(
            action_frame,
            text=f"Target Project: {self.project_path or 'None (Required to Commit)'}",
            font=("Arial", 9, "italic"),
        )
        project_label.pack(side=tk.LEFT, padx=5)
        
        commit_button = ttk.Button(
            action_frame,
            text="Approve & Commit to Database",
            command=self.callbacks.get("commit_to_db"),
            state=tk.NORMAL if self.db_path else tk.DISABLED,
        )
        commit_button.pack(side=tk.RIGHT, padx=5)
    
    def _build_phase_foundry(self) -> None:
        """Build Phase 1: FOUNDRY - Entity Extraction and Staging.
        
        Uses the dedicated FoundryPanel widget with:
        - Entity staging to JSON (not direct DB)
        - Phase navigation buttons
        - Integration with StagingService
        """
        try:
            from pyscrai_forge.phases.foundry.ui import FoundryPanel
            
            self.foundry_panel = FoundryPanel(
                self.main_container,
                project_path=self.project_path,
                callbacks=self.callbacks
            )
            self.foundry_panel.pack(fill=tk.BOTH, expand=True)
            
            # Wire up the treeview references for data manager compatibility
            self.entities_tree = self.foundry_panel.entities_tree
            self.relationships_tree = self.foundry_panel.relationships_tree
            
        except ImportError:
            # Fallback to legacy component editor if FoundryPanel not available
            self._build_component_editor()
    
    def _build_phase_loom(self) -> None:
        """Build Phase 2: LOOM - Relationship Mapping.
        
        Uses the dedicated LoomPanel widget with:
        - Interactive node-link graph (networkx + tk.Canvas)
        - Relationship editor panel
        - Conflict detection alerts
        """
        try:
            from pyscrai_forge.phases.loom.ui import LoomPanel
            
            self.loom_panel = LoomPanel(
                self.main_container,
                project_path=self.project_path,
                callbacks=self.callbacks
            )
            self.loom_panel.pack(fill=tk.BOTH, expand=True)
            
        except ImportError:
            # Fallback to placeholder if LoomPanel not available
            placeholder = ttk.Frame(self.main_container)
            placeholder.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            ttk.Label(placeholder, text="Phase 2: LOOM", font=("Arial", 18, "bold")).pack(pady=10)
            ttk.Label(placeholder, text="Relationship Mapping & Graph Visualization", font=("Arial", 12)).pack(pady=5)
            ttk.Label(placeholder, text="[LoomPanel not available - check imports]", font=("Arial", 10, "italic"), foreground="red").pack(pady=20)
            
            nav_frame = ttk.Frame(placeholder)
            nav_frame.pack(pady=20)
            ttk.Button(nav_frame, text="← Back to Foundry", command=lambda: self.transition_to(AppState.PHASE_FOUNDRY)).pack(side=tk.LEFT, padx=10)
            ttk.Button(nav_frame, text="Proceed to Chronicle →", command=lambda: self.transition_to(AppState.PHASE_CHRONICLE)).pack(side=tk.LEFT, padx=10)
    
    def _build_phase_chronicle(self) -> None:
        """Build Phase 3: CHRONICLE - Narrative Synthesis.
        
        Uses the dedicated ChroniclePanel widget with:
        - Blueprint template selector
        - Narrative generation with fact-checking
        - Entity reference panel
        """
        try:
            from pyscrai_forge.phases.chronicle.ui import ChroniclePanel
            
            self.chronicle_panel = ChroniclePanel(
                self.main_container,
                project_path=self.project_path,
                callbacks=self.callbacks
            )
            self.chronicle_panel.pack(fill=tk.BOTH, expand=True)
            
        except ImportError:
            # Fallback to placeholder
            placeholder = ttk.Frame(self.main_container)
            placeholder.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            ttk.Label(placeholder, text="Phase 3: CHRONICLE", font=("Arial", 18, "bold")).pack(pady=10)
            ttk.Label(placeholder, text="Narrative Synthesis with Verification", font=("Arial", 12)).pack(pady=5)
            ttk.Label(placeholder, text="[ChroniclePanel not available - check imports]", font=("Arial", 10, "italic"), foreground="red").pack(pady=20)
            
            nav_frame = ttk.Frame(placeholder)
            nav_frame.pack(pady=20)
            ttk.Button(nav_frame, text="← Back to Loom", command=lambda: self.transition_to(AppState.PHASE_LOOM)).pack(side=tk.LEFT, padx=10)
            ttk.Button(nav_frame, text="Proceed to Cartography →", command=lambda: self.transition_to(AppState.PHASE_CARTOGRAPHY)).pack(side=tk.LEFT, padx=10)
    
    def _build_phase_cartography(self) -> None:
        """Build Phase 4: CARTOGRAPHY - Spatial Anchoring.
        
        Uses the dedicated CartographyPanel widget with:
        - Grid map canvas
        - Entity placement via drag-and-drop
        - Region management
        """
        try:
            from pyscrai_forge.phases.cartography.ui import CartographyPanel
            
            self.cartography_panel = CartographyPanel(
                self.main_container,
                project_path=self.project_path,
                callbacks=self.callbacks
            )
            self.cartography_panel.pack(fill=tk.BOTH, expand=True)
            
        except ImportError:
            # Fallback to placeholder
            placeholder = ttk.Frame(self.main_container)
            placeholder.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            ttk.Label(placeholder, text="Phase 4: CARTOGRAPHY", font=("Arial", 18, "bold")).pack(pady=10)
            ttk.Label(placeholder, text="Spatial Anchoring & Map Placement", font=("Arial", 12)).pack(pady=5)
            ttk.Label(placeholder, text="[CartographyPanel not available - check imports]", font=("Arial", 10, "italic"), foreground="red").pack(pady=20)
            
            nav_frame = ttk.Frame(placeholder)
            nav_frame.pack(pady=20)
            ttk.Button(nav_frame, text="← Back to Chronicle", command=lambda: self.transition_to(AppState.PHASE_CHRONICLE)).pack(side=tk.LEFT, padx=10)
            ttk.Button(nav_frame, text="Proceed to Anvil →", command=lambda: self.transition_to(AppState.PHASE_ANVIL)).pack(side=tk.LEFT, padx=10)
    
    def _build_phase_anvil(self) -> None:
        """Build Phase 5: ANVIL - Finalization & Continuity.
        
        Uses the dedicated AnvilPanel widget with:
        - Diff viewer (staging vs canon)
        - Semantic duplicate detection
        - Merge/Reject/Branch controls
        - Provenance tracking
        """
        try:
            from pyscrai_forge.phases.anvil.ui import AnvilPanel
            
            self.anvil_panel = AnvilPanel(
                self.main_container,
                project_path=self.project_path,
                callbacks=self.callbacks
            )
            self.anvil_panel.pack(fill=tk.BOTH, expand=True)
            
        except ImportError:
            # Fallback to placeholder
            placeholder = ttk.Frame(self.main_container)
            placeholder.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            ttk.Label(placeholder, text="Phase 5: ANVIL", font=("Arial", 18, "bold")).pack(pady=10)
            ttk.Label(placeholder, text="Finalization & Continuity", font=("Arial", 12)).pack(pady=5)
            ttk.Label(placeholder, text="[AnvilPanel not available - check imports]", font=("Arial", 10, "italic"), foreground="red").pack(pady=20)
            
            nav_frame = ttk.Frame(placeholder)
            nav_frame.pack(pady=20)
            ttk.Button(nav_frame, text="← Back to Cartography", command=lambda: self.transition_to(AppState.PHASE_CARTOGRAPHY)).pack(side=tk.LEFT, padx=10)
            ttk.Button(nav_frame, text="Return to Dashboard", command=lambda: self.transition_to(AppState.DASHBOARD)).pack(side=tk.LEFT, padx=10)
    
    def update_status_bar(self) -> None:
        """Update the status bar with current project info."""
        if not self.status_bar:
            return
        
        if self.project_path and self.db_path:
            try:
                from pyscrai_forge.src import storage
                if self.db_path.exists():
                    entities = storage.load_all_entities(self.db_path)
                    relationships = storage.load_all_relationships(self.db_path)
                    status = (
                        f"Project: {self.project_path.name} | "
                        f"DB: {len(entities)} entities, {len(relationships)} relationships"
                    )
                else:
                    status = f"Project: {self.project_path.name} | DB: Not initialized"
            except Exception:
                status = f"Project: {self.project_path.name}"
        else:
            status = "No project loaded"
        
        self.status_bar.config(text=status)
    
    def update_window_title(self) -> None:
        """Update the window title based on current project."""
        if self.project_path and self.manifest:
            self.root.title(f"PyScrAI|Forge - {self.manifest.name}")
        else:
            self.root.title("PyScrAI|Forge")
    
    def update_validation_status(self, validation_report: dict) -> None:
        """Update validation status banner.
        
        Args:
            validation_report: Validation report dictionary
        """
        if not self.validation_frame or not self.validation_label:
            return
        
        crit = len(validation_report.get("critical_errors", []))
        warn = len(validation_report.get("warnings", []))
        
        # In dark mode/themed mode, we change text color instead of background
        msg = "Validation Passed"
        
        if crit > 0:
            # Error state
            self.validation_label.config(text=f"Validation: {crit} Critical Errors", foreground="#ff5555") # Bright Red text
        elif warn > 0:
            # Warning state
            self.validation_label.config(text=f"Validation: {warn} Warnings", foreground="#ffaa00") # Gold text
        else:
            # Valid state
            self.validation_label.config(text="Validation Passed", foreground="#55ff55") # Bright Green text

