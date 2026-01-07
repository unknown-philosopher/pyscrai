# pyscrai_forge/harvester/ui/import_dialog.py
"""Import Dialog - Multi-file import with source pool management."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Callable, List, Optional
from ..converters import create_registry, ConversionResult


class ImportDialog(tk.Toplevel):
    """Dialog for importing multiple files into the source data pool."""
    
    def __init__(self, parent, on_import: Optional[Callable] = None, staging_service=None):
        """Initialize the import dialog.
        
        Args:
            parent: Parent window
            on_import: Callback when import is complete (text, metadata, file_path, reset_counters)
            staging_service: Optional StagingService for direct source pool management
        """
        super().__init__(parent)
        self.title("Import Data Files")
        self.geometry("900x700")
        self.transient(parent)
        self.on_import = on_import
        self.staging_service = staging_service

        # Use centralized converter registry
        self.registry = create_registry()

        # Multi-file support
        self.file_queue: List[dict] = []  # List of {path, result, status}
        self.current_preview_index = 0

        self._create_ui()

    def _create_ui(self):
        """Build the dialog UI."""
        # Top bar: File selection with multi-file support
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="Add files to import queue:").pack(side=tk.LEFT)
        ttk.Button(top_frame, text="Add Files...", command=self._browse_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Add Folder...", command=self._browse_folder).pack(side=tk.LEFT)
        
        # Clear queue button
        ttk.Button(top_frame, text="Clear Queue", command=self._clear_queue).pack(side=tk.RIGHT)

        # File queue list
        queue_frame = ttk.LabelFrame(self, text="Import Queue", padding=10)
        queue_frame.pack(fill=tk.X, padx=10, pady=5)

        # Treeview for file queue
        columns = ("filename", "status", "chars", "active")
        self.queue_tree = ttk.Treeview(queue_frame, columns=columns, show="headings", height=6)
        self.queue_tree.heading("filename", text="Filename")
        self.queue_tree.heading("status", text="Status")
        self.queue_tree.heading("chars", text="Characters")
        self.queue_tree.heading("active", text="Active")
        
        self.queue_tree.column("filename", width=350)
        self.queue_tree.column("status", width=100)
        self.queue_tree.column("chars", width=100)
        self.queue_tree.column("active", width=80)
        
        self.queue_tree.pack(fill=tk.X, side=tk.LEFT, expand=True)
        self.queue_tree.bind("<<TreeviewSelect>>", self._on_queue_select)
        self.queue_tree.bind("<Double-1>", self._toggle_active)
        
        queue_scroll = ttk.Scrollbar(queue_frame, orient=tk.VERTICAL, command=self.queue_tree.yview)
        queue_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.queue_tree.config(yscrollcommand=queue_scroll.set)

        # Queue actions
        queue_actions = ttk.Frame(self, padding=(10, 0))
        queue_actions.pack(fill=tk.X)
        
        ttk.Button(queue_actions, text="Remove Selected", command=self._remove_selected).pack(side=tk.LEFT)
        ttk.Button(queue_actions, text="Toggle Active", command=self._toggle_selected_active).pack(side=tk.LEFT, padx=5)
        
        self.queue_count_var = tk.StringVar(value="0 files queued")
        ttk.Label(queue_actions, textvariable=self.queue_count_var).pack(side=tk.RIGHT)

        # Main area: Preview of selected file
        preview_frame = ttk.LabelFrame(self, text="Preview (select file above)", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.preview_text = tk.Text(preview_frame, wrap=tk.WORD)
        self.preview_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.preview_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview_text.config(yscrollcommand=scrollbar.set)

        # Bottom bar: Actions
        action_frame = ttk.Frame(self, padding=10)
        action_frame.pack(fill=tk.X)

        self.status_var = tk.StringVar(value="Ready - Add files to begin")
        ttk.Label(action_frame, textvariable=self.status_var).pack(side=tk.LEFT)

        # Checkbox for resetting ID counters
        self.reset_counters_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            action_frame,
            text="Reset ID Counters",
            variable=self.reset_counters_var
        ).pack(side=tk.LEFT, padx=20)
        
        # Checkbox for auto-extract
        self.auto_extract_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            action_frame,
            text="Extract Entities After Import",
            variable=self.auto_extract_var
        ).pack(side=tk.LEFT, padx=10)

        ttk.Button(action_frame, text="Import All", command=self._process_all).pack(side=tk.RIGHT)
        ttk.Button(action_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def _browse_files(self):
        """Browse for multiple files."""
        formats = [
            ("All Supported", "*.pdf *.html *.htm *.docx *.png *.jpg *.jpeg *.txt *.md"),
            ("PDF Files", "*.pdf"),
            ("Word Files", "*.docx"),
            ("HTML Files", "*.html *.htm"),
            ("Images", "*.png *.jpg *.jpeg"),
            ("Text Files", "*.txt *.md"),
            ("All Files", "*.*")
        ]
        filenames = filedialog.askopenfilenames(parent=self, filetypes=formats)
        if filenames:
            for filename in filenames:
                self._add_file_to_queue(Path(filename))
    
    def _browse_folder(self):
        """Browse for a folder and add all supported files."""
        folder = filedialog.askdirectory(parent=self)
        if folder:
            folder_path = Path(folder)
            supported_exts = {'.pdf', '.html', '.htm', '.docx', '.png', '.jpg', '.jpeg', '.txt', '.md'}
            
            for file_path in folder_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in supported_exts:
                    self._add_file_to_queue(file_path)
    
    def _add_file_to_queue(self, path: Path):
        """Add a file to the import queue."""
        # Check if already in queue
        for item in self.file_queue:
            if item["path"] == path:
                return
        
        self.status_var.set(f"Converting {path.name}...")
        self.update_idletasks()
        
        try:
            # Convert the file
            if path.suffix.lower() in ('.txt', '.md'):
                with open(path, 'r', encoding='utf-8') as f:
                    text = f.read()
                result = ConversionResult(text=text, metadata={})
            else:
                result = self.registry.convert(path)
            
            if result.error:
                status = "Error"
                chars = 0
            else:
                status = "Ready"
                chars = len(result.text)
            
            file_info = {
                "path": path,
                "result": result,
                "status": status,
                "chars": chars,
                "active": True
            }
            self.file_queue.append(file_info)
            
            # Add to treeview
            self.queue_tree.insert("", tk.END, values=(
                path.name,
                status,
                f"{chars:,}",
                "✓" if file_info["active"] else "✗"
            ))
            
            self._update_queue_count()
            self.status_var.set(f"Added {path.name}")
            
        except Exception as e:
            messagebox.showerror("Conversion Error", f"Failed to convert {path.name}: {e}")
            self.status_var.set(f"Error: {e}")
    
    def _clear_queue(self):
        """Clear the file queue."""
        self.file_queue.clear()
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)
        self.preview_text.delete("1.0", tk.END)
        self._update_queue_count()
        self.status_var.set("Queue cleared")
    
    def _remove_selected(self):
        """Remove selected files from queue."""
        selection = self.queue_tree.selection()
        if not selection:
            return
        
        indices_to_remove = []
        for item in selection:
            idx = self.queue_tree.index(item)
            indices_to_remove.append(idx)
            self.queue_tree.delete(item)
        
        # Remove from file_queue in reverse order to preserve indices
        for idx in sorted(indices_to_remove, reverse=True):
            if 0 <= idx < len(self.file_queue):
                del self.file_queue[idx]
        
        self.preview_text.delete("1.0", tk.END)
        self._update_queue_count()
    
    def _toggle_active(self, event=None):
        """Toggle active status on double-click."""
        self._toggle_selected_active()
    
    def _toggle_selected_active(self):
        """Toggle active status for selected files."""
        selection = self.queue_tree.selection()
        if not selection:
            return
        
        for item in selection:
            idx = self.queue_tree.index(item)
            if 0 <= idx < len(self.file_queue):
                self.file_queue[idx]["active"] = not self.file_queue[idx]["active"]
                
                # Update treeview
                file_info = self.file_queue[idx]
                self.queue_tree.item(item, values=(
                    file_info["path"].name,
                    file_info["status"],
                    f"{file_info['chars']:,}",
                    "✓" if file_info["active"] else "✗"
                ))
    
    def _on_queue_select(self, event=None):
        """Show preview of selected file."""
        selection = self.queue_tree.selection()
        if not selection:
            return
        
        idx = self.queue_tree.index(selection[0])
        if 0 <= idx < len(self.file_queue):
            file_info = self.file_queue[idx]
            self.preview_text.delete("1.0", tk.END)
            
            if file_info["result"] and file_info["result"].text:
                self.preview_text.insert("1.0", file_info["result"].text)
            elif file_info["result"] and file_info["result"].error:
                self.preview_text.insert("1.0", f"Error: {file_info['result'].error}")
    
    def _update_queue_count(self):
        """Update the queue count label."""
        total = len(self.file_queue)
        active = sum(1 for f in self.file_queue if f["active"])
        self.queue_count_var.set(f"{active} of {total} files active")

    def _process_all(self):
        """Process all active files in the queue."""
        active_files = [f for f in self.file_queue if f["active"] and f["status"] == "Ready"]
        
        if not active_files:
            messagebox.showwarning("Warning", "No active files to process")
            return
        
        # If staging service is available, save sources to pool
        if self.staging_service:
            self.status_var.set("Saving to source pool...")
            self.update_idletasks()
            
            source_ids = []
            for file_info in active_files:
                try:
                    source_id = self.staging_service.save_source_file(
                        file_path=file_info["path"],
                        text_content=file_info["result"].text,
                        metadata=file_info["result"].metadata,
                        active=True
                    )
                    source_ids.append(source_id)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save {file_info['path'].name}: {e}")
            
            self.status_var.set(f"Saved {len(source_ids)} sources to pool")
        
        # Call the on_import callback if provided
        if self.on_import and self.auto_extract_var.get():
            # Combine all active texts for extraction
            combined_text = "\n\n".join(
                f"--- SOURCE: {f['path'].name} ---\n{f['result'].text}"
                for f in active_files
            )
            
            combined_metadata = {
                "source_count": len(active_files),
                "source_files": [f["path"].name for f in active_files],
                "total_chars": sum(f["chars"] for f in active_files)
            }
            
            reset_counters = self.reset_counters_var.get()
            self.on_import(
                combined_text,
                combined_metadata,
                active_files[0]["path"] if active_files else None,  # Primary file for reference
                reset_counters
            )

        self.destroy()


# Keep backward compatibility with old single-file import
class SingleFileImportDialog(ImportDialog):
    """Legacy single-file import dialog."""
    
    def __init__(self, parent, on_import=None):
        super().__init__(parent, on_import=on_import)
        self.title("Import File")
