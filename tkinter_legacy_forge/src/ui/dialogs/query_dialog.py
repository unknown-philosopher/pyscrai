# pyscrai_forge/harvester/ui/dialogs/query_dialog.py
"""SQL query dialog for database explorer."""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from pathlib import Path
from typing import Optional, List, Tuple


class QueryDialog(tk.Toplevel):
    """Dialog for executing SQL queries against the database."""

    def __init__(self, parent, db_path: Path):
        """
        Initialize the query dialog.

        Args:
            parent: Parent window
            db_path: Path to the SQLite database
        """
        super().__init__(parent)
        self.title("SQL Query")
        self.geometry("800x600")
        self.transient(parent)

        self.db_path = db_path

        self._create_ui()

    def _create_ui(self):
        """Build the dialog UI."""
        # Query input
        input_frame = ttk.LabelFrame(self, text="Query", padding=10)
        input_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.query_text = tk.Text(input_frame, height=8, wrap=tk.WORD)
        self.query_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        query_scroll = ttk.Scrollbar(input_frame, orient=tk.VERTICAL, command=self.query_text.yview)
        query_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.query_text.config(yscrollcommand=query_scroll.set)

        # Example queries
        examples_text = (
            "SELECT * FROM entities LIMIT 10;\n"
            "SELECT COUNT(*) FROM relationships;\n"
            "SELECT * FROM entities WHERE json_extract(data, '$.descriptor.entity_type') = 'actor';"
        )
        self.query_text.insert("1.0", examples_text)

        # Execute button
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Button(button_frame, text="Execute", command=self._execute_query).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear Results", command=self._clear_results).pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(button_frame, text="", foreground="gray")
        self.status_label.pack(side=tk.LEFT, padx=10)

        # Results
        results_frame = ttk.LabelFrame(self, text="Results", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.results_tree = ttk.Treeview(results_frame, show="tree headings")
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        results_scroll_y = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        results_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_tree.config(yscrollcommand=results_scroll_y.set)

        results_scroll_x = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.results_tree.xview)
        results_scroll_x.pack(fill=tk.X, padx=10)
        self.results_tree.config(xscrollcommand=results_scroll_x.set)

        # Close button
        ttk.Button(self, text="Close", command=self.destroy).pack(pady=5)

    def _execute_query(self):
        """Execute the SQL query."""
        query = self.query_text.get("1.0", tk.END).strip()
        if not query:
            messagebox.showwarning("No Query", "Please enter a SQL query.", parent=self)
            return

        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Execute query
            cursor.execute(query)

            # Fetch results
            if cursor.description:  # SELECT query
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()

                self._display_results(columns, rows)
                self.status_label.config(text=f"✓ {len(rows)} rows returned", foreground="green")
            else:  # Non-SELECT query
                conn.commit()
                self.status_label.config(text=f"✓ Query executed (rows affected: {cursor.rowcount})", foreground="green")
                self._clear_results()

            conn.close()

        except sqlite3.Error as e:
            messagebox.showerror("SQL Error", str(e), parent=self)
            self.status_label.config(text="✗ Error", foreground="red")
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)
            self.status_label.config(text="✗ Error", foreground="red")

    def _display_results(self, columns: List[str], rows: List[Tuple]):
        """Display query results in the treeview."""
        # Clear existing
        self.results_tree.delete(*self.results_tree.get_children())

        # Configure columns
        self.results_tree["columns"] = columns
        self.results_tree["show"] = "headings"

        for col in columns:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=150)

        # Insert rows
        for row in rows:
            # Truncate long values for display
            display_row = [str(val)[:100] + "..." if len(str(val)) > 100 else str(val) for val in row]
            self.results_tree.insert("", tk.END, values=display_row)

    def _clear_results(self):
        """Clear the results treeview."""
        self.results_tree.delete(*self.results_tree.get_children())
        self.results_tree["columns"] = ()
        self.status_label.config(text="")
