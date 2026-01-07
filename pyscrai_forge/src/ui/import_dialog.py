# pyscrai_forge/harvester/ui/import_dialog.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from ..converters import create_registry, ConversionResult

class ImportDialog(tk.Toplevel):
    def __init__(self, parent, on_import=None):
        super().__init__(parent)
        self.title("Import File")
        self.geometry("800x600")
        self.transient(parent)
        self.on_import = on_import

        # Use centralized converter registry
        self.registry = create_registry()

        self.extracted_result = None
        self.current_file_path = None

        self._create_ui()

    def _create_ui(self):
        # Top bar: File selection
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(fill=tk.X)

        self.path_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.path_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(top_frame, text="Browse...", command=self._browse_file).pack(side=tk.LEFT)
        ttk.Button(top_frame, text="Convert", command=self._convert_file).pack(side=tk.LEFT, padx=5)

        # Main area: Preview
        preview_frame = ttk.LabelFrame(self, text="Preview", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.preview_text = tk.Text(preview_frame)
        self.preview_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.preview_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview_text.config(yscrollcommand=scrollbar.set)

        # Bottom bar: Actions
        action_frame = ttk.Frame(self, padding=10)
        action_frame.pack(fill=tk.X)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(action_frame, textvariable=self.status_var).pack(side=tk.LEFT)

        # Checkbox for resetting ID counters
        self.reset_counters_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            action_frame,
            text="Reset Component ID Counters",
            variable=self.reset_counters_var
        ).pack(side=tk.LEFT, padx=20)

        ttk.Button(action_frame, text="Process", command=self._process).pack(side=tk.RIGHT)
        ttk.Button(action_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def _on_interactive_toggle(self):
        """Update interactive mode flag when checkbox is toggled."""
        self.interactive_mode = self.interactive_var.get()

    def _browse_file(self):
        formats = [
            ("All Supported", "*.pdf *.html *.htm *.docx *.png *.jpg *.jpeg *.txt"),
            ("PDF Files", "*.pdf"),
            ("Word Files", "*.docx"),
            ("HTML Files", "*.html *.htm"),
            ("Images", "*.png *.jpg *.jpeg"),
            ("Text Files", "*.txt"),
            ("All Files", "*.*")
        ]
        filename = filedialog.askopenfilename(parent=self, filetypes=formats)
        if filename:
            self.path_var.set(filename)
            self._convert_file()

    def _convert_file(self):
        path_str = self.path_var.get()
        if not path_str:
            return

        path = Path(path_str)
        if not path.exists():
            messagebox.showerror("Error", "File does not exist")
            return

        self.status_var.set("Converting...")
        self.update_idletasks()

        try:
            # Handle .txt directly or via registry if we added a TextConverter
            if path.suffix.lower() == '.txt':
                with open(path, 'r', encoding='utf-8') as f:
                    text = f.read()
                self.extracted_result = ConversionResult(text=text, metadata={})
            else:
                self.extracted_result = self.registry.convert(path)

            if self.extracted_result.error:
                 self.preview_text.delete("1.0", tk.END)
                 self.preview_text.insert("1.0", f"Error: {self.extracted_result.error}")
                 self.status_var.set("Conversion Failed")
            else:
                 self.preview_text.delete("1.0", tk.END)
                 self.preview_text.insert("1.0", self.extracted_result.text)
                 self.status_var.set(f"Loaded {len(self.extracted_result.text)} characters")
                 self.current_file_path = path

        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Conversion Error", str(e))

    def _process(self):
        if not self.extracted_result or not self.extracted_result.text:
            messagebox.showwarning("Warning", "No text to process")
            return

        if self.on_import:
            # Pass text, metadata, file path, and reset_counters flag back to caller
            reset_counters = self.reset_counters_var.get()
            self.on_import(
                self.extracted_result.text,
                self.extracted_result.metadata,
                self.current_file_path,
                reset_counters
            )

        self.destroy()
