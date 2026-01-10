# pyscrai_forge/harvester/ui/windows/file_browser.py
"""Project directory structure viewer."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Optional
import os


class FileBrowserWindow(tk.Toplevel):
    """Window for browsing project directory structure."""

    def __init__(self, parent, project_path: Optional[Path] = None):
        """
        Initialize the file browser.

        Args:
            parent: Parent window
            project_path: Path to project directory
        """
        super().__init__(parent)
        self.title("File Browser")
        self.geometry("900x600")
        self.transient(parent)

        self.project_path = project_path
        self.current_file: Optional[Path] = None

        self._create_ui()

        if project_path:
            self._load_directory()

    def _create_ui(self):
        """Build the window UI."""
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="Open Project...", command=self._select_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Refresh", command=self._load_directory).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="New Folder", command=self._create_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Delete", command=self._delete_item).pack(side=tk.LEFT, padx=2)

        self.path_label = ttk.Label(toolbar, text="No project loaded", foreground="gray")
        self.path_label.pack(side=tk.LEFT, padx=20)

        # Main paned window
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left: Directory tree
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Directory Structure", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))

        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(tree_frame, selectmode=tk.BROWSE)
        self.tree.heading("#0", text="Files")

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.config(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_tree_double_click)

        # Right: File preview
        right_frame = ttk.Frame(paned, width=400)
        paned.add(right_frame, weight=2)

        ttk.Label(right_frame, text="File Preview", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))

        preview_frame = ttk.Frame(right_frame)
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.preview_text = tk.Text(preview_frame, wrap=tk.NONE, state=tk.DISABLED)
        self.preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        preview_scroll_y = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.preview_text.yview)
        preview_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview_text.config(yscrollcommand=preview_scroll_y.set)

        preview_scroll_x = ttk.Scrollbar(right_frame, orient=tk.HORIZONTAL, command=self.preview_text.xview)
        preview_scroll_x.pack(fill=tk.X)
        self.preview_text.config(xscrollcommand=preview_scroll_x.set)

        # File info label
        self.info_label = ttk.Label(right_frame, text="", foreground="gray")
        self.info_label.pack(anchor=tk.W, pady=5)

        # Close button
        ttk.Button(self, text="Close", command=self.destroy).pack(pady=5)

    def _select_project(self):
        """Select a project directory."""
        directory = filedialog.askdirectory(title="Select Project Directory", parent=self)
        if directory:
            self.project_path = Path(directory)
            self._load_directory()

    def _load_directory(self):
        """Load the project directory into the tree."""
        if not self.project_path or not self.project_path.exists():
            messagebox.showwarning("No Project", "Please select a project directory first.", parent=self)
            return

        # Clear tree
        self.tree.delete(*self.tree.get_children())

        # Update label
        self.path_label.config(text=str(self.project_path))

        # Build tree
        root_node = self.tree.insert("", tk.END, text=self.project_path.name, open=True)
        self.tree.item(root_node, tags=("directory",))
        self._add_directory_contents(root_node, self.project_path)

    def _add_directory_contents(self, parent_node, directory: Path):
        """Recursively add directory contents to tree."""
        try:
            items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))

            for item in items:
                # Skip hidden files and __pycache__
                if item.name.startswith(".") or item.name == "__pycache__":
                    continue

                if item.is_dir():
                    node = self.tree.insert(parent_node, tk.END, text=f"{item.name}/", tags=("directory",))
                    # Add placeholder for lazy loading
                    self.tree.insert(node, tk.END, text="Loading...")
                else:
                    size_kb = item.stat().st_size / 1024
                    display_name = f"{item.name} ({size_kb:.1f} KB)"
                    self.tree.insert(parent_node, tk.END, text=display_name, tags=("file",))

        except PermissionError:
            self.tree.insert(parent_node, tk.END, text="[Permission Denied]", tags=("error",))

    def _on_tree_select(self, event):
        """Handle tree selection."""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        self._load_preview(item)

    def _on_tree_double_click(self, event):
        """Handle double-click to expand directories."""
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        tags = self.tree.item(item, "tags")

        if "directory" in tags:
            # Expand/collapse directory
            if self.tree.item(item, "open"):
                self.tree.item(item, open=False)
            else:
                # Lazy load on first expand
                children = self.tree.get_children(item)
                if len(children) == 1 and self.tree.item(children[0], "text") == "Loading...":
                    self.tree.delete(children[0])
                    path = self._get_item_path(item)
                    if path:
                        self._add_directory_contents(item, path)

                self.tree.item(item, open=True)

    def _get_item_path(self, item) -> Optional[Path]:
        """Get the full path for a tree item."""
        if not self.project_path:
            return None

        # Build path from tree hierarchy
        parts = []
        current = item

        while current:
            text = self.tree.item(current, "text")
            # Strip size info from files
            if "(" in text and "KB)" in text:
                text = text[:text.rfind("(")].strip()
            # Strip trailing slash from directories
            text = text.rstrip("/")

            parts.insert(0, text)
            parent = self.tree.parent(current)
            if not parent:
                break
            current = parent

        # Remove root name
        if parts and parts[0] == self.project_path.name:
            parts.pop(0)

        return self.project_path / Path(*parts) if parts else self.project_path

    def _load_preview(self, item):
        """Load file preview."""
        path = self._get_item_path(item)
        if not path or not path.exists():
            return

        self.current_file = path

        # Clear preview
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)

        if path.is_dir():
            self.preview_text.insert("1.0", f"Directory: {path.name}\n\nDouble-click to expand/collapse")
            self.info_label.config(text="")
        else:
            # Show file info
            size_bytes = path.stat().st_size
            size_str = f"{size_bytes / 1024:.1f} KB" if size_bytes >= 1024 else f"{size_bytes} bytes"
            self.info_label.config(text=f"File: {path.name} | Size: {size_str}")

            # Try to preview text files
            if path.suffix.lower() in [".txt", ".md", ".json", ".py", ".yaml", ".yml", ".toml", ".cfg", ".ini"]:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read(100000)  # Limit to 100KB
                        self.preview_text.insert("1.0", content)
                except Exception as e:
                    self.preview_text.insert("1.0", f"Error reading file:\n{str(e)}")
            else:
                self.preview_text.insert("1.0", f"Binary file: {path.suffix}\n\n(No preview available)")

        self.preview_text.config(state=tk.DISABLED)

    def _create_folder(self):
        """Create a new folder in the selected directory."""
        if not self.project_path:
            messagebox.showwarning("No Project", "Please select a project directory first.", parent=self)
            return

        selection = self.tree.selection()
        if not selection:
            parent_path = self.project_path
        else:
            parent_path = self._get_item_path(selection[0])
            if parent_path and not parent_path.is_dir():
                parent_path = parent_path.parent

        # Prompt for folder name
        dialog = tk.Toplevel(self)
        dialog.title("Create Folder")
        dialog.geometry("400x120")
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text="Folder name:").pack(pady=10)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=40)
        name_entry.pack(pady=5)
        name_entry.focus()

        def create():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Folder name is required.", parent=dialog)
                return

            new_path = parent_path / name
            if new_path.exists():
                messagebox.showerror("Error", f"'{name}' already exists.", parent=dialog)
                return

            try:
                new_path.mkdir()
                self._load_directory()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=dialog)

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Create", command=create).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT)

    def _delete_item(self):
        """Delete the selected file or folder."""
        selection = self.tree.selection()
        if not selection:
            return

        path = self._get_item_path(selection[0])
        if not path or not path.exists():
            return

        if path == self.project_path:
            messagebox.showwarning("Cannot Delete", "Cannot delete the project root.", parent=self)
            return

        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete '{path.name}'?\n\nThis action cannot be undone.",
            parent=self
        ):
            return

        try:
            if path.is_dir():
                import shutil
                shutil.rmtree(path)
            else:
                path.unlink()

            self._load_directory()
        except Exception as e:
            messagebox.showerror("Delete Error", str(e), parent=self)
