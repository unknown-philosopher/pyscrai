"""Narrative generator widget for PyScrAI|Forge."""

import tkinter as tk
import asyncio
import threading
from tkinter import ttk, messagebox, scrolledtext, filedialog
from pathlib import Path
from typing import Callable, Optional, Dict, Any
from pyscrai_core import ProjectManifest


class NarrativeGeneratorWidget(ttk.Frame):
    """Widget for generating narratives from project entities."""
    
    def __init__(self, parent,
                 project_path: Path,
                 manifest: ProjectManifest,
                 get_forge_manager: Callable[[], Any]):
        """
        Initialize narrative generator.
        
        Args:
            parent: Parent widget
            project_path: Path to project directory
            manifest: Project manifest
            get_forge_manager: Function that returns configured ForgeManager instance
        """
        super().__init__(parent)
        self.project_path = project_path
        self.manifest = manifest
        self.get_forge_manager = get_forge_manager
        
        # State variables
        self.is_generating = tk.BooleanVar(value=False)
        self.generated_narrative = tk.StringVar()
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the narrative generator UI."""
        # Main container with padding
        main_container = ttk.Frame(self)
        main_container.pack(expand=True, fill=tk.BOTH, padx=20, pady=15)
        
        # Title and description
        title_frame = ttk.Frame(main_container)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(title_frame, text="📖 Narrative Generator",
                               font=("Arial", 16, "bold"))
        title_label.pack(anchor='w')
        
        desc_label = ttk.Label(title_frame, 
                              text="Generate data-driven narratives from your project entities with fact-checking.",
                              font=("Arial", 10), foreground="gray")
        desc_label.pack(anchor='w', pady=(5, 0))
        
        # Controls frame
        controls_frame = ttk.LabelFrame(main_container, text="Generation Settings", padding=15)
        controls_frame.pack(fill=tk.X, pady=(0, 20))
        
        # First row: Mode and Entity Filter
        row1_frame = ttk.Frame(controls_frame)
        row1_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Mode selector
        mode_frame = ttk.Frame(row1_frame)
        mode_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        ttk.Label(mode_frame, text="Narrative Mode:").pack(anchor='w')
        self.mode_var = tk.StringVar(value="auto")
        mode_combo = ttk.Combobox(
            mode_frame,
            textvariable=self.mode_var,
            values=["auto", "sitrep", "story", "dossier", "summary"],
            state="readonly",
            width=15
        )
        mode_combo.pack(anchor='w', pady=(2, 0))
        
        # Entity filter
        filter_frame = ttk.Frame(row1_frame)
        filter_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(filter_frame, text="Entity Filter:").pack(anchor='w')
        self.filter_var = tk.StringVar(value="all")
        filter_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.filter_var,
            values=["all", "actor", "polity", "location"],
            state="readonly",
            width=15
        )
        filter_combo.pack(anchor='w', pady=(2, 0))
        
        # Second row: Focus input
        row2_frame = ttk.Frame(controls_frame)
        row2_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(row2_frame, text="Focus (optional):").pack(anchor='w')
        self.focus_var = tk.StringVar()
        focus_entry = ttk.Entry(row2_frame, textvariable=self.focus_var, width=50)
        focus_entry.pack(anchor='w', fill=tk.X, pady=(2, 0))
        
        # Generate button
        button_frame = ttk.Frame(controls_frame)
        button_frame.pack(fill=tk.X)
        
        self.generate_button = ttk.Button(
            button_frame,
            text="🎭 Generate Narrative",
            command=self._on_generate_clicked,
            style="Accent.TButton",
            cursor="hand2"
        )
        self.generate_button.pack(side=tk.LEFT)
        
        # Progress indicator (initially hidden)
        self.progress_frame = ttk.Frame(button_frame)
        self.progress_label = ttk.Label(self.progress_frame, text="Generating narrative...", 
                                       font=("Arial", 9), foreground="blue")
        self.progress_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Output frame
        output_frame = ttk.LabelFrame(main_container, text="Generated Narrative", padding=10)
        output_frame.pack(fill=tk.BOTH, expand=True)
        
        # Narrative text display
        text_frame = ttk.Frame(output_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.narrative_text = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            height=15,
            font=("Arial", 11),
            state=tk.DISABLED
        )
        self.narrative_text.pack(fill=tk.BOTH, expand=True)
        
        # Action buttons for output
        action_frame = ttk.Frame(output_frame)
        action_frame.pack(fill=tk.X)
        
        self.copy_button = ttk.Button(
            action_frame,
            text="📋 Copy to Clipboard",
            command=self._copy_to_clipboard,
            state=tk.DISABLED
        )
        self.copy_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.save_button = ttk.Button(
            action_frame,
            text="💾 Save to File",
            command=self._save_to_file,
            state=tk.DISABLED
        )
        self.save_button.pack(side=tk.LEFT)
    
    def _on_generate_clicked(self):
        """Handle generate button click."""
        if self.is_generating.get():
            return
        
        # Get settings
        mode = self.mode_var.get() if self.mode_var.get() != "auto" else None
        entity_filter = self.filter_var.get() if self.filter_var.get() != "all" else None
        focus = self.focus_var.get().strip() or None
        
        # Start generation in background thread
        self._start_generation(mode, entity_filter, focus)
    
    def _start_generation(self, mode: Optional[str], entity_filter: Optional[str], focus: Optional[str]):
        """Start narrative generation in background thread."""
        self.is_generating.set(True)
        
        # Update UI state
        self.generate_button.config(state=tk.DISABLED)
        self.progress_frame.pack(side=tk.LEFT, padx=(10, 0))
        self.narrative_text.config(state=tk.NORMAL)
        self.narrative_text.delete(1.0, tk.END)
        self.narrative_text.insert(tk.END, "Generating narrative...\n\nThis may take a moment as the AI:\n• Loads project entities\n• Generates initial narrative\n• Fact-checks against source data\n• Refines if needed")
        self.narrative_text.config(state=tk.DISABLED)
        
        def run_async_generation():
            """Run async generation in thread."""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(self._generate_narrative(mode, entity_filter, focus))
                
                # Update UI on main thread
                self.after(0, lambda: self._on_generation_complete(result, None))
            except Exception as e:
                # Handle error on main thread
                self.after(0, lambda: self._on_generation_complete(None, str(e)))
            finally:
                loop.close()
        
        # Start in background thread
        thread = threading.Thread(target=run_async_generation, daemon=True)
        thread.start()
    
    async def _generate_narrative(self, mode: Optional[str], entity_filter: Optional[str], focus: Optional[str]) -> str:
        """Async narrative generation."""
        try:
            manager = self.get_forge_manager()
            if not manager:
                raise ValueError("Could not create ForgeManager")
            
            result = await manager.generate_project_narrative(
                mode=mode,
                focus=focus,
                entity_filter=entity_filter
            )
            return result
        except Exception as e:
            raise Exception(f"Generation failed: {e}")
    
    def _on_generation_complete(self, result: Optional[str], error: Optional[str]):
        """Handle generation completion on main thread."""
        self.is_generating.set(False)
        
        # Update UI state
        self.generate_button.config(state=tk.NORMAL)
        self.progress_frame.pack_forget()
        
        # Update text display
        self.narrative_text.config(state=tk.NORMAL)
        self.narrative_text.delete(1.0, tk.END)
        
        if error:
            self.narrative_text.insert(tk.END, f"❌ Error generating narrative:\n\n{error}")
            self.narrative_text.config(state=tk.DISABLED)
            self.copy_button.config(state=tk.DISABLED)
            self.save_button.config(state=tk.DISABLED)
        elif result:
            self.narrative_text.insert(tk.END, result)
            self.narrative_text.config(state=tk.DISABLED)
            self.copy_button.config(state=tk.NORMAL)
            self.save_button.config(state=tk.NORMAL)
            self.generated_narrative.set(result)
        else:
            self.narrative_text.insert(tk.END, "❓ No narrative was generated.")
            self.narrative_text.config(state=tk.DISABLED)
            self.copy_button.config(state=tk.DISABLED)
            self.save_button.config(state=tk.DISABLED)
    
    def _copy_to_clipboard(self):
        """Copy narrative to clipboard."""
        narrative = self.generated_narrative.get()
        if narrative:
            self.clipboard_clear()
            self.clipboard_append(narrative)
            messagebox.showinfo("Copied", "Narrative copied to clipboard!")
    
    def _save_to_file(self):
        """Save narrative to file."""
        narrative = self.generated_narrative.get()
        if not narrative:
            return
        
        # Get suggested filename
        project_name = self.manifest.name.replace(" ", "_").lower()
        mode = self.mode_var.get()
        suggested_name = f"{project_name}_narrative_{mode}.txt"
        
        file_path = filedialog.asksaveasfilename(
            title="Save Narrative",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("Markdown files", "*.md"), ("All files", "*.*")],
            initialname=suggested_name
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(narrative)
                messagebox.showinfo("Saved", f"Narrative saved to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file:\n{e}")
