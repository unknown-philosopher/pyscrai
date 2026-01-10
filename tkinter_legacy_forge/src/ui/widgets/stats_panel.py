# pyscrai_forge/harvester/ui/widgets/stats_panel.py
"""Statistics display panel for database explorer."""

import tkinter as tk
from tkinter import ttk
from typing import Dict, List
from collections import Counter


class StatsPanelWidget(ttk.Frame):
    """Widget for displaying database statistics."""

    def __init__(self, parent):
        """Initialize the stats panel widget."""
        super().__init__(parent)
        self._create_ui()

    def _create_ui(self):
        """Build the widget UI."""
        # Title
        title_label = ttk.Label(self, text="Statistics", font=("Arial", 11, "bold"))
        title_label.pack(anchor=tk.W, pady=(0, 10))

        # Scrollable frame for stats
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)

        self.stats_frame = ttk.Frame(canvas)
        self.stats_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.stats_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Initial empty state
        self._show_empty_state()

    def _show_empty_state(self):
        """Show empty state message."""
        for widget in self.stats_frame.winfo_children():
            widget.destroy()

        ttk.Label(
            self.stats_frame,
            text="No data loaded",
            foreground="gray"
        ).pack(pady=20)

    def update_stats(self, entities: List, relationships: List):
        """
        Update statistics with entity and relationship data.

        Args:
            entities: List of Entity objects
            relationships: List of Relationship objects
        """
        # Clear previous stats
        for widget in self.stats_frame.winfo_children():
            widget.destroy()

        # Overall counts
        overall_frame = ttk.LabelFrame(self.stats_frame, text="Overall", padding=10)
        overall_frame.pack(fill=tk.X, pady=5)

        ttk.Label(overall_frame, text=f"Total Entities: {len(entities)}").pack(anchor=tk.W)
        ttk.Label(overall_frame, text=f"Total Relationships: {len(relationships)}").pack(anchor=tk.W)

        # Entity type breakdown
        entity_types = Counter()
        for entity in entities:
            if hasattr(entity, "descriptor") and hasattr(entity.descriptor, "entity_type"):
                entity_types[entity.descriptor.entity_type.value] += 1

        if entity_types:
            entity_frame = ttk.LabelFrame(self.stats_frame, text="Entities by Type", padding=10)
            entity_frame.pack(fill=tk.X, pady=5)

            for entity_type, count in sorted(entity_types.items()):
                ttk.Label(entity_frame, text=f"{entity_type}: {count}").pack(anchor=tk.W)

        # Relationship type breakdown
        rel_types = Counter()
        for rel in relationships:
            if hasattr(rel, "relationship_type"):
                rel_types[rel.relationship_type.value] += 1

        if rel_types:
            rel_frame = ttk.LabelFrame(self.stats_frame, text="Relationships by Type", padding=10)
            rel_frame.pack(fill=tk.X, pady=5)

            for rel_type, count in sorted(rel_types.items()):
                ttk.Label(rel_frame, text=f"{rel_type}: {count}").pack(anchor=tk.W)

        # Validation stats (if available)
        entities_with_issues = 0
        entities_with_warnings = 0

        for entity in entities:
            # Check for validation issues (this is a placeholder - real validation would come from ValidatorAgent)
            if not hasattr(entity, "descriptor") or not entity.descriptor.name:
                entities_with_issues += 1

        if entities_with_issues > 0 or entities_with_warnings > 0:
            validation_frame = ttk.LabelFrame(self.stats_frame, text="Validation", padding=10)
            validation_frame.pack(fill=tk.X, pady=5)

            if entities_with_issues > 0:
                ttk.Label(
                    validation_frame,
                    text=f"Entities with errors: {entities_with_issues}",
                    foreground="red"
                ).pack(anchor=tk.W)

            if entities_with_warnings > 0:
                ttk.Label(
                    validation_frame,
                    text=f"Entities with warnings: {entities_with_warnings}",
                    foreground="orange"
                ).pack(anchor=tk.W)

    def clear(self):
        """Clear statistics and show empty state."""
        self._show_empty_state()
