"""Phase 3: CHRONICLE - Narrative Synthesis UI Panel.

This module provides the main UI panel for the Chronicle phase,
which handles narrative generation with blueprint templates
and fact-checking visualization.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk
from typing import TYPE_CHECKING, Callable, List, Optional

if TYPE_CHECKING:
    from pyscrai_core import Entity, Relationship


# Built-in narrative blueprint templates
BLUEPRINT_TEMPLATES = {
    "sitrep": {
        "name": "Situation Report",
        "description": "Military-style briefing on current state",
        "structure": [
            "## Current Situation",
            "## Key Players",
            "## Recent Developments", 
            "## Threats & Opportunities",
            "## Recommended Actions"
        ],
        "focus": "factions,events,conflicts"
    },
    "dossier": {
        "name": "Character Dossier",
        "description": "Detailed profile on a specific character",
        "structure": [
            "## Basic Information",
            "## Background",
            "## Known Associates",
            "## Notable Activities",
            "## Assessment"
        ],
        "focus": "characters,relationships"
    },
    "gazetteer": {
        "name": "Location Gazetteer",
        "description": "Geographic/location overview",
        "structure": [
            "## Overview",
            "## Geography",
            "## Notable Features",
            "## Inhabitants",
            "## History"
        ],
        "focus": "locations,regions"
    },
    "timeline": {
        "name": "Timeline Chronicle",
        "description": "Chronological event summary",
        "structure": [
            "## Early History",
            "## Key Events",
            "## Recent Developments",
            "## Current Status"
        ],
        "focus": "events,dates"
    },
    "faction_brief": {
        "name": "Faction Brief",
        "description": "Organization/faction analysis",
        "structure": [
            "## Organization Overview",
            "## Leadership",
            "## Membership",
            "## Goals & Methods",
            "## Alliances & Enemies"
        ],
        "focus": "factions,organizations"
    }
}


class ChroniclePanel(ttk.Frame):
    """Main panel for the Chronicle phase - Narrative Synthesis.
    
    Features:
    - Blueprint template selector
    - Focus entity/topic selector
    - Narrative generation with NarratorAgent
    - Fact-check highlighting
    - Export to staging
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        project_path: Optional[Path] = None,
        callbacks: Optional[dict[str, Callable]] = None,
        **kwargs
    ):
        """Initialize the Chronicle panel.
        
        Args:
            parent: Parent widget
            project_path: Path to the current project
            callbacks: Dictionary of callback functions
        """
        super().__init__(parent, **kwargs)
        
        self.project_path = project_path
        self.callbacks = callbacks or {}
        
        # Data
        self.entities: List["Entity"] = []
        self.relationships: List["Relationship"] = []
        self.current_narrative: str = ""
        self.fact_check_results: List[dict] = []
        
        # UI components
        self.narrative_text: Optional[scrolledtext.ScrolledText] = None
        self.entity_listbox: Optional[tk.Listbox] = None
        self.fact_check_tree: Optional[ttk.Treeview] = None
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        """Build the Chronicle phase UI."""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        ttk.Label(
            header_frame,
            text="Phase 3: CHRONICLE",
            font=("Segoe UI", 16, "bold")
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            header_frame,
            text="Narrative Synthesis with Verification",
            font=("Segoe UI", 11),
            foreground="gray"
        ).pack(side=tk.LEFT, padx=(15, 0))
        
        # Main content - horizontal split
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left: Controls and entity reference
        left_frame = ttk.Frame(main_paned, width=300)
        left_frame.pack_propagate(False)
        main_paned.add(left_frame, weight=0)
        
        self._build_controls_panel(left_frame)
        
        # Center: Narrative text
        center_frame = ttk.Frame(main_paned)
        main_paned.add(center_frame, weight=2)
        
        self._build_narrative_panel(center_frame)
        
        # Right: Fact-check results
        right_frame = ttk.Frame(main_paned, width=280)
        right_frame.pack_propagate(False)
        main_paned.add(right_frame, weight=0)
        
        self._build_factcheck_panel(right_frame)
        
        # Bottom action bar
        self._build_action_bar()
    
    def _build_controls_panel(self, parent: ttk.Frame) -> None:
        """Build the controls and entity reference panel."""
        # Blueprint selector
        blueprint_frame = ttk.LabelFrame(parent, text="Blueprint Template", padding=10)
        blueprint_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.blueprint_var = tk.StringVar(value="sitrep")
        
        for bp_id, bp_info in BLUEPRINT_TEMPLATES.items():
            rb = ttk.Radiobutton(
                blueprint_frame,
                text=bp_info["name"],
                value=bp_id,
                variable=self.blueprint_var,
                command=self._on_blueprint_change
            )
            rb.pack(anchor=tk.W)
        
        # Blueprint description
        self.blueprint_desc = ttk.Label(
            blueprint_frame,
            text=BLUEPRINT_TEMPLATES["sitrep"]["description"],
            font=("Segoe UI", 9, "italic"),
            foreground="gray",
            wraplength=250
        )
        self.blueprint_desc.pack(anchor=tk.W, pady=(10, 0))
        
        # Focus input
        focus_frame = ttk.LabelFrame(parent, text="Focus Topic/Entity", padding=10)
        focus_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.focus_entry = ttk.Entry(focus_frame)
        self.focus_entry.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(
            focus_frame,
            text="Enter a topic, entity name, or leave blank for overview",
            font=("Segoe UI", 8),
            foreground="gray",
            wraplength=250
        ).pack(anchor=tk.W)
        
        # Entity reference list
        entity_frame = ttk.LabelFrame(parent, text="Entity Reference", padding=10)
        entity_frame.pack(fill=tk.BOTH, expand=True)
        
        list_frame = ttk.Frame(entity_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.entity_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE, font=("Segoe UI", 9))
        entity_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.entity_listbox.yview)
        self.entity_listbox.configure(yscrollcommand=entity_scroll.set)
        
        self.entity_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        entity_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Double-click to set focus
        self.entity_listbox.bind("<Double-1>", self._on_entity_double_click)
        
        # Generate button
        ttk.Button(
            parent,
            text="Generate Narrative",
            command=self._on_generate
        ).pack(fill=tk.X, pady=10)
    
    def _build_narrative_panel(self, parent: ttk.Frame) -> None:
        """Build the narrative text panel."""
        # Header
        header = ttk.Frame(parent)
        header.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(header, text="Generated Narrative", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        
        ttk.Button(
            header,
            text="Copy",
            command=self._on_copy_narrative,
            width=8
        ).pack(side=tk.RIGHT)
        
        ttk.Button(
            header,
            text="Clear",
            command=self._on_clear_narrative,
            width=8
        ).pack(side=tk.RIGHT, padx=5)
        
        # Text area with markdown-style highlighting
        text_frame = ttk.Frame(parent)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.narrative_text = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="white",
            selectbackground="#264f78"
        )
        self.narrative_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for highlighting
        self.narrative_text.tag_configure("heading", font=("Segoe UI", 12, "bold"), foreground="#569cd6")
        self.narrative_text.tag_configure("entity", foreground="#4ec9b0", underline=True)
        self.narrative_text.tag_configure("verified", background="#1e3a1e")  # Green tint
        self.narrative_text.tag_configure("unverified", background="#3a1e1e")  # Red tint
        self.narrative_text.tag_configure("uncertain", background="#3a3a1e")  # Yellow tint
    
    def _build_factcheck_panel(self, parent: ttk.Frame) -> None:
        """Build the fact-check results panel."""
        # Header
        header = ttk.Frame(parent)
        header.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(header, text="Fact Check", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        
        ttk.Button(
            header,
            text="Run",
            command=self._on_run_factcheck,
            width=6
        ).pack(side=tk.RIGHT)
        
        # Stats
        self.factcheck_stats = ttk.Label(
            parent,
            text="No fact-check performed",
            font=("Segoe UI", 9),
            foreground="gray"
        )
        self.factcheck_stats.pack(anchor=tk.W, pady=(0, 5))
        
        # Results tree
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.fact_check_tree = ttk.Treeview(
            tree_frame,
            columns=("status", "claim"),
            show="headings",
            selectmode=tk.BROWSE
        )
        
        self.fact_check_tree.heading("status", text="Status")
        self.fact_check_tree.heading("claim", text="Claim")
        
        self.fact_check_tree.column("status", width=60)
        self.fact_check_tree.column("claim", width=180)
        
        # Status colors
        self.fact_check_tree.tag_configure("verified", foreground="#55ff55")
        self.fact_check_tree.tag_configure("unverified", foreground="#ff5555")
        self.fact_check_tree.tag_configure("uncertain", foreground="#ffff55")
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.fact_check_tree.yview)
        self.fact_check_tree.configure(yscrollcommand=scrollbar.set)
        
        self.fact_check_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Selection highlights in narrative
        self.fact_check_tree.bind("<<TreeviewSelect>>", self._on_factcheck_select)
    
    def _build_action_bar(self) -> None:
        """Build the bottom action bar."""
        action_frame = ttk.Frame(self)
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Left: Phase info
        ttk.Label(
            action_frame,
            text=f"Project: {self.project_path.name if self.project_path else 'None'}",
            font=("Segoe UI", 9, "italic"),
            foreground="gray"
        ).pack(side=tk.LEFT)
        
        # Right: Action buttons
        ttk.Button(
            action_frame,
            text="← Back to Loom",
            command=self.callbacks.get("go_to_loom", lambda: None)
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            action_frame,
            text="Proceed to Cartography →",
            command=self._on_proceed_to_cartography
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Separator(action_frame, orient=tk.VERTICAL).pack(side=tk.RIGHT, padx=10, fill=tk.Y, pady=2)
        
        ttk.Button(
            action_frame,
            text="Save to Staging",
            command=self._on_save_staging
        ).pack(side=tk.RIGHT, padx=5)
    
    def set_data(
        self,
        entities: List["Entity"],
        relationships: List["Relationship"]
    ) -> None:
        """Set the data to display.
        
        Args:
            entities: List of Entity objects
            relationships: List of Relationship objects
        """
        self.entities = entities
        self.relationships = relationships
        self._refresh_entity_list()
    
    def _refresh_entity_list(self) -> None:
        """Refresh the entity reference list."""
        if not self.entity_listbox:
            return
        
        self.entity_listbox.delete(0, tk.END)
        
        for entity in self.entities:
            name = entity.descriptor.name if hasattr(entity, "descriptor") else entity.id
            entity_type = ""
            if hasattr(entity, "descriptor") and hasattr(entity.descriptor, "entity_type"):
                entity_type = entity.descriptor.entity_type.value if hasattr(entity.descriptor.entity_type, "value") else ""
            
            display = f"[{entity_type[:3].upper()}] {name}" if entity_type else name
            self.entity_listbox.insert(tk.END, display)
    
    def _on_blueprint_change(self) -> None:
        """Handle blueprint selection change."""
        bp_id = self.blueprint_var.get()
        bp_info = BLUEPRINT_TEMPLATES.get(bp_id, {})
        self.blueprint_desc.configure(text=bp_info.get("description", ""))
    
    def _on_entity_double_click(self, event) -> None:
        """Handle double-click on entity to set as focus."""
        selection = self.entity_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        if 0 <= idx < len(self.entities):
            entity = self.entities[idx]
            name = entity.descriptor.name if hasattr(entity, "descriptor") else entity.id
            self.focus_entry.delete(0, tk.END)
            self.focus_entry.insert(0, name)
    
    def _on_generate(self) -> None:
        """Generate narrative using NarratorAgent."""
        if not self.entities:
            messagebox.showinfo("No Data", "No entities available. Please complete the Loom phase first.")
            return
        
        blueprint_id = self.blueprint_var.get()
        focus = self.focus_entry.get().strip()
        
        # Build context for narrative
        blueprint = BLUEPRINT_TEMPLATES.get(blueprint_id, {})
        
        # For now, generate a placeholder narrative
        # TODO: Wire to NarratorAgent via TaskQueue
        
        narrative = self._generate_placeholder_narrative(blueprint, focus)
        
        self.narrative_text.configure(state=tk.NORMAL)
        self.narrative_text.delete("1.0", tk.END)
        self.narrative_text.insert("1.0", narrative)
        self._apply_narrative_highlighting()
        self.current_narrative = narrative
        
        messagebox.showinfo(
            "Narrative Generated",
            f"Generated {blueprint.get('name', 'narrative')} with {len(self.entities)} entities.\n\n"
            "Full LLM generation requires connection setup."
        )
    
    def _generate_placeholder_narrative(self, blueprint: dict, focus: str) -> str:
        """Generate a placeholder narrative from available data."""
        lines = []
        
        # Title
        lines.append(f"# {blueprint.get('name', 'Narrative Report')}")
        if focus:
            lines.append(f"*Focus: {focus}*")
        lines.append("")
        
        # Add structure sections
        for section in blueprint.get("structure", []):
            lines.append(section)
            lines.append("")
            
            # Add some entity info for relevant sections
            if "Players" in section or "Characters" in section or "Associates" in section:
                chars = [e for e in self.entities if hasattr(e, "descriptor") and 
                        hasattr(e.descriptor, "entity_type") and
                        e.descriptor.entity_type.value in ("character", "person")]
                for char in chars[:5]:
                    lines.append(f"- **{char.descriptor.name}**: {getattr(char.descriptor, 'description', 'No description')[:100]}...")
                lines.append("")
                
            elif "Location" in section or "Geography" in section:
                locs = [e for e in self.entities if hasattr(e, "descriptor") and 
                       hasattr(e.descriptor, "entity_type") and
                       e.descriptor.entity_type.value in ("location", "place")]
                for loc in locs[:5]:
                    lines.append(f"- **{loc.descriptor.name}**: {getattr(loc.descriptor, 'description', 'No description')[:100]}...")
                lines.append("")
                
            elif "Organization" in section or "Faction" in section:
                orgs = [e for e in self.entities if hasattr(e, "descriptor") and 
                       hasattr(e.descriptor, "entity_type") and
                       e.descriptor.entity_type.value in ("organization", "faction")]
                for org in orgs[:5]:
                    lines.append(f"- **{org.descriptor.name}**: {getattr(org.descriptor, 'description', 'No description')[:100]}...")
                lines.append("")
        
        # Summary
        lines.append("---")
        lines.append(f"*Generated from {len(self.entities)} entities and {len(self.relationships)} relationships.*")
        
        return "\n".join(lines)
    
    def _apply_narrative_highlighting(self) -> None:
        """Apply syntax highlighting to the narrative."""
        if not self.narrative_text:
            return
        
        content = self.narrative_text.get("1.0", tk.END)
        
        # Highlight headings
        import re
        for match in re.finditer(r'^#+\s+.+$', content, re.MULTILINE):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.narrative_text.tag_add("heading", start, end)
        
        # Highlight entity names
        for entity in self.entities:
            if hasattr(entity, "descriptor") and hasattr(entity.descriptor, "name"):
                name = entity.descriptor.name
                start_idx = "1.0"
                while True:
                    pos = self.narrative_text.search(name, start_idx, stopindex=tk.END)
                    if not pos:
                        break
                    end_pos = f"{pos}+{len(name)}c"
                    self.narrative_text.tag_add("entity", pos, end_pos)
                    start_idx = end_pos
    
    def _on_copy_narrative(self) -> None:
        """Copy narrative to clipboard."""
        if self.narrative_text:
            content = self.narrative_text.get("1.0", tk.END)
            self.clipboard_clear()
            self.clipboard_append(content)
            messagebox.showinfo("Copied", "Narrative copied to clipboard.")
    
    def _on_clear_narrative(self) -> None:
        """Clear the narrative text."""
        if self.narrative_text:
            self.narrative_text.configure(state=tk.NORMAL)
            self.narrative_text.delete("1.0", tk.END)
            self.current_narrative = ""
    
    def _on_run_factcheck(self) -> None:
        """Run fact-checking on the narrative."""
        if not self.current_narrative:
            messagebox.showinfo("No Narrative", "Generate a narrative first.")
            return
        
        # TODO: Wire to NarratorAgent fact-check via TaskQueue
        messagebox.showinfo(
            "Fact Check",
            "Fact-checking will verify claims against entity data.\n\n"
            "This feature requires LLM connection."
        )
    
    def _on_factcheck_select(self, event) -> None:
        """Handle fact-check result selection to highlight in narrative."""
        # Could highlight the relevant sentence in the narrative
        pass
    
    def _on_save_staging(self) -> None:
        """Save narrative to staging."""
        if not self.project_path:
            messagebox.showwarning("No Project", "Please load a project first.")
            return
        
        if not self.current_narrative:
            messagebox.showinfo("No Narrative", "Generate a narrative first.")
            return
        
        try:
            from pyscrai_forge.src.staging import StagingService
            
            staging = StagingService(self.project_path)
            artifact_path = staging.save_narrative_staging(
                narrative_text=self.current_narrative,
                blueprint_name=self.blueprint_var.get(),
                focus=self.focus_entry.get().strip(),
                fact_check_results=self.fact_check_results,
                metadata={"phase": "chronicle"}
            )
            
            messagebox.showinfo("Staging Saved", f"Narrative saved to:\n{artifact_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save staging: {e}")
    
    def _on_proceed_to_cartography(self) -> None:
        """Proceed to Cartography phase."""
        # Auto-save if we have a narrative
        if self.current_narrative and self.project_path:
            try:
                from pyscrai_forge.src.staging import StagingService
                staging = StagingService(self.project_path)
                staging.save_narrative_staging(
                    self.current_narrative,
                    blueprint_name=self.blueprint_var.get(),
                    focus=self.focus_entry.get().strip()
                )
            except Exception:
                pass  # Don't block navigation on staging failure
        
        go_to_cartography = self.callbacks.get("go_to_cartography")
        if go_to_cartography:
            go_to_cartography()

