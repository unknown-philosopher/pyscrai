"""Reusable Treeview column sorting utility.

Provides clickable column headers with sort indicators for Tkinter Treeview widgets.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional


class TreeviewSorter:
    """Adds sortable column functionality to Tkinter Treeview widgets.
    
    Features:
    - Click column headers to sort
    - Visual sort indicators (↑ ↓)
    - Toggle between ascending/descending
    - Preserves row tags during sort
    - Extensible for custom sort functions
    
    Example:
        >>> tree = ttk.Treeview(parent, columns=("name", "age"))
        >>> sorter = TreeviewSorter(tree)
        >>> sorter.enable_sorting("name", sort_key=lambda item: item[0])
        >>> sorter.enable_sorting("age", sort_key=lambda item: int(item[1]))
    """
    
    def __init__(self, treeview: ttk.Treeview):
        """Initialize the sorter for a treeview.
        
        Args:
            treeview: The Treeview widget to add sorting to
        """
        self.treeview = treeview
        self.sort_column: Optional[str] = None
        self.sort_reverse: bool = False
        self.sort_functions: dict[str, Callable] = {}
        self.original_headings: dict[str, str] = {}
        self.column_commands: dict[str, Callable] = {}
        
        # Store original headings
        for col in self.treeview["columns"]:
            self.original_headings[col] = self.treeview.heading(col, "text")
    
    def enable_sorting(
        self,
        column: str,
        sort_key: Optional[Callable[[tuple], any]] = None,
        default_reverse: bool = False
    ) -> None:
        """Enable sorting for a specific column.
        
        Args:
            column: Column identifier
            sort_key: Optional function to extract sort value from row tuple.
                     If None, uses the column value directly.
            default_reverse: Default sort direction for this column
        """
        if column not in self.treeview["columns"]:
            return
        
        # Store sort function
        if sort_key:
            self.sort_functions[column] = sort_key
        else:
            # Default: use column value directly
            # Get column index (accounting for #0 being the tree column)
            columns = list(self.treeview["columns"])
            try:
                col_index = columns.index(column)
                self.sort_functions[column] = lambda item, idx=col_index: item[idx] if idx < len(item) else ""
            except ValueError:
                # Column not found, use string comparison
                self.sort_functions[column] = lambda item: ""
        
        # Create command function for this column
        def make_sort_command(col: str):
            return lambda: self._sort_by_column(col)
        
        sort_command = make_sort_command(column)
        self.column_commands[column] = sort_command
        
        # Bind click event to column header
        self.treeview.heading(
            column,
            command=sort_command,
            text=self.original_headings.get(column, column)
        )
        
        # Set default sort if specified
        if default_reverse:
            self.sort_column = column
            self.sort_reverse = default_reverse
            self._update_header_indicator(column)
    
    def _sort_by_column(self, column: str) -> None:
        """Sort treeview by the specified column.
        
        Args:
            column: Column to sort by
        """
        # Toggle reverse if clicking the same column
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        
        # Get all items with their values and tags
        items = []
        for item_id in self.treeview.get_children():
            values = self.treeview.item(item_id, "values")
            tags = self.treeview.item(item_id, "tags")
            items.append((item_id, values, tags))
        
        # Sort items
        sort_key_func = self.sort_functions.get(column)
        if sort_key_func:
            try:
                items.sort(
                    key=lambda x: sort_key_func(x[1]) if x[1] else "",
                    reverse=self.sort_reverse
                )
            except (TypeError, ValueError):
                # Fallback to string comparison if sort fails
                items.sort(
                    key=lambda x: str(sort_key_func(x[1]) if x[1] else "").lower(),
                    reverse=self.sort_reverse
                )
        else:
            # Fallback: sort by column index
            col_index = list(self.treeview["columns"]).index(column)
            items.sort(
                key=lambda x: str(x[1][col_index] if col_index < len(x[1]) and x[1][col_index] else "").lower(),
                reverse=self.sort_reverse
            )
        
        # Re-insert items in sorted order
        for item_id, values, tags in items:
            self.treeview.move(item_id, "", "end")
            # Preserve tags
            if tags:
                self.treeview.item(item_id, tags=tags)
        
        # Update header indicators
        self._update_all_headers()
    
    def _update_all_headers(self) -> None:
        """Update all column headers to show current sort state."""
        for col in self.treeview["columns"]:
            self._update_header_indicator(col)
    
    def _update_header_indicator(self, column: str) -> None:
        """Update a single column header with sort indicator.
        
        Args:
            column: Column to update
        """
        original_text = self.original_headings.get(column, column)
        
        if self.sort_column == column:
            indicator = " ↓" if self.sort_reverse else " ↑"
            new_text = original_text + indicator
        else:
            new_text = original_text
        
        # Update heading text while preserving command
        # Use stored command instead of trying to retrieve it
        sort_command = self.column_commands.get(column)
        if sort_command:
            self.treeview.heading(
                column,
                text=new_text,
                command=sort_command
            )
        else:
            # Fallback: just update text if no command stored
            self.treeview.heading(column, text=new_text)
    
    def enable_sorting_for_all_columns(
        self,
        sort_functions: Optional[dict[str, Callable]] = None
    ) -> None:
        """Enable sorting for all columns at once.
        
        Args:
            sort_functions: Optional dict mapping column names to sort functions.
                          If not provided, uses default string sorting.
        """
        sort_functions = sort_functions or {}
        
        for col in self.treeview["columns"]:
            sort_func = sort_functions.get(col)
            self.enable_sorting(col, sort_key=sort_func)
    
    def reset_sort(self) -> None:
        """Reset sort to original order and clear indicators."""
        self.sort_column = None
        self.sort_reverse = False
        self._update_all_headers()
        
        # Re-insert items in original order (by item ID)
        items = []
        for item_id in self.treeview.get_children():
            values = self.treeview.item(item_id, "values")
            tags = self.treeview.item(item_id, "tags")
            items.append((item_id, values, tags))
        
        # Sort by item ID to restore original order
        items.sort(key=lambda x: x[0])
        
        for item_id, values, tags in items:
            self.treeview.move(item_id, "", "end")
            if tags:
                self.treeview.item(item_id, tags=tags)

