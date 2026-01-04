"""TkinterHIL: GUI-based Human-in-the-Loop modal for interactive extraction.

This module implements the HILCallback protocol using Tkinter modals,
allowing users to review, edit, and approve/reject each phase of the
extraction pipeline from within the GUI.
"""

import json
import asyncio
from typing import Optional, Any
from pathlib import Path

import tkinter as tk
from tkinter import ttk

from pyscrai_forge.agents.hil_protocol import (
    HILCallback, HILContext, HILResponse, HILAction
)


class TkinterHIL:
    """Tkinter-based HIL callback handler for GUI extraction workflow.
    
    Creates non-blocking modal dialogs at each pause point, allowing users to:
    - Review prompts and results
    - Edit prompts/results inline
    - Approve/reject/retry/skip/abort phases
    
    Design:
    - Resizable modal (1000x700 initial, min 800x600)
    - Inline text editing with scrollbars
    - Manual approval for MVP
    - Async/await compatible with Tkinter event loop
    """
    
    PHASE_COLORS = {
        "scout": "#2E86AB",
        "analyst": "#A23B72",
        "relationships": "#F18F01"
    }
    
    def __init__(self, parent_window: tk.Tk):
        """Initialize TkinterHIL with parent window reference.
        
        Args:
            parent_window: Root Tkinter window
        """
        self.parent = parent_window
        self.current_response: Optional[HILResponse] = None
        self.modal_open = False
    
    async def callback(self, context: HILContext) -> HILResponse:
        """Main HIL callback - displays modal and waits for user action.
        
        Args:
            context: HILContext with phase info, prompts, results
            
        Returns:
            HILResponse with user's chosen action
        """
        # Create and show modal in main thread
        self.current_response = None
        self.modal_open = True
        
        # Schedule modal creation in main thread
        self.parent.after(0, self._create_modal, context)
        
        # Wait for user response asynchronously
        while self.modal_open:
            await asyncio.sleep(0.1)
        
        return self.current_response or HILResponse(action=HILAction.ABORT)
    
    def _create_modal(self, context: HILContext):
        """Create and display the HIL modal dialog."""
        modal = tk.Toplevel(self.parent)
        modal.title(f"PyScrAI HIL - {context.phase.upper()} Phase")
        modal.geometry("1000x700")
        modal.minsize(800, 600)
        modal.resizable(True, True)
        
        # Force light theme colors for modal
        modal.configure(bg="white")
        
        # Make modal floating on top
        modal.attributes('-topmost', True)
        
        # Center on parent window
        modal.transient(self.parent)
        modal.grab_set()
        
        # Build modal UI
        self._build_modal_ui(modal, context)
        
        # Handle window close (treat as abort)
        def on_closing():
            self.current_response = HILResponse(action=HILAction.ABORT)
            self.modal_open = False
            modal.destroy()
        
        modal.protocol("WM_DELETE_WINDOW", on_closing)
    
    def _build_modal_ui(self, modal: tk.Toplevel, context: HILContext):
        """Build the complete modal UI with all sections."""
        # Color for phase
        phase_color = self.PHASE_COLORS.get(context.phase, "#555555")
        
        # =====================================================================
        # HEADER: Phase info and status
        # =====================================================================
        header = ttk.Frame(modal)
        header.pack(fill=tk.X, padx=15, pady=10)
        
        phase_label = tk.Label(
            header,
            text=f"Phase: {context.phase.upper()}",
            font=("Courier", 14, "bold"),
            fg="white",
            bg=phase_color,
            padx=10,
            pady=5
        )
        phase_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        agent_label = tk.Label(
            header,
            text=f"Agent: {context.agent_name}",
            font=("Courier", 10),
            fg="white",
            bg=phase_color,
            padx=10,
            pady=5
        )
        agent_label.pack(side=tk.LEFT, fill=tk.X)
        
        status_text = "[PRE-EXECUTION]" if context.is_pre_execution else "[POST-EXECUTION]"
        status_label = tk.Label(
            header,
            text=status_text,
            font=("Courier", 10, "bold"),
            fg="white",
            bg=phase_color,
            padx=10,
            pady=5
        )
        status_label.pack(side=tk.RIGHT)
        
        # =====================================================================
        # MAIN CONTENT: Notebook with tabs
        # =====================================================================
        notebook = ttk.Notebook(modal)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Prompts
        prompts_frame = ttk.Frame(notebook)
        notebook.add(prompts_frame, text="Prompts")
        self._build_prompts_section(prompts_frame, context)
        
        # Tab 2: Results (only for post-execution)
        if not context.is_pre_execution and context.results:
            results_frame = ttk.Frame(notebook)
            notebook.add(results_frame, text="Results")
            self._build_results_section(results_frame, context)
        
        # Tab 3: Metadata
        metadata_frame = ttk.Frame(notebook)
        notebook.add(metadata_frame, text="Details")
        self._build_metadata_section(metadata_frame, context)
        
        # =====================================================================
        # ACTION BUTTONS
        # =====================================================================
        button_frame = ttk.Frame(modal)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def approve():
            self.current_response = HILResponse(action=HILAction.APPROVE)
            self.modal_open = False
            modal.destroy()
        
        def edit():
            # For MVP: Edit shows prompts for review then approves
            # In future: inline editing of prompts/results
            self.current_response = HILResponse(
                action=HILAction.APPROVE,  # MVP: Edit just approves with a note
                edited_system_prompt=context.system_prompt,
                edited_user_prompt=context.user_prompt,
                edited_results=context.results
            )
            self.modal_open = False
            modal.destroy()
        
        def retry():
            # Retry: re-run the phase (user may edit prompts first in future)
            self.current_response = HILResponse(action=HILAction.RETRY)
            self.modal_open = False
            modal.destroy()
        
        def skip():
            self.current_response = HILResponse(action=HILAction.SKIP)
            self.modal_open = False
            modal.destroy()
        
        def abort():
            self.current_response = HILResponse(action=HILAction.ABORT)
            self.modal_open = False
            modal.destroy()
        
        # Approve button (primary) - styled
        approve_btn = ttk.Button(button_frame, text="✓ Approve", command=approve)
        approve_btn.pack(side=tk.LEFT, padx=5)
        
        # Edit button - for MVP, same as approve (future: inline editing)
        # Note: Currently stores prompts/results for future inline editor
        edit_btn = ttk.Button(button_frame, text="✎ Edit (MVP: Approve)", command=edit)
        edit_btn.pack(side=tk.LEFT, padx=5)
        
        # Retry button - only works for Scout phase in current version
        retry_text = "↻ Retry" if context.phase == "scout" else "↻ Retry (Scout only)"
        retry_btn = ttk.Button(button_frame, text=retry_text, command=retry)
        retry_btn.pack(side=tk.LEFT, padx=5)
        
        # Skip button
        skip_btn = ttk.Button(button_frame, text="⊘ Skip", command=skip)
        skip_btn.pack(side=tk.LEFT, padx=5)
        
        # Abort button (last)
        abort_btn = ttk.Button(button_frame, text="✕ Abort", command=abort)
        abort_btn.pack(side=tk.RIGHT, padx=5)
    
    def _build_prompts_section(self, parent: ttk.Frame, context: HILContext):
        """Build the prompts display section."""
        parent.configure(style='White.TFrame')
        
        # System Prompt
        system_label = tk.Label(parent, text="System Prompt:", font=("Courier", 10, "bold"), bg="white", fg="black")
        system_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        # Frame for text widget with scrollbar
        system_frame = tk.Frame(parent, bg="white")
        system_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        system_scroll = tk.Scrollbar(system_frame)
        system_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        system_text = tk.Text(
            system_frame,
            height=6,
            width=100,
            font=("Courier", 9),
            wrap=tk.WORD,
            bg="white",
            fg="black",
            insertbackground="black",
            relief=tk.SUNKEN,
            borderwidth=2,
            yscrollcommand=system_scroll.set
        )
        system_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        system_scroll.config(command=system_text.yview)
        
        system_text.insert("1.0", context.system_prompt)
        system_text.config(state=tk.DISABLED)
        
        # User Prompt
        user_label = tk.Label(parent, text="User Prompt:", font=("Courier", 10, "bold"), bg="white", fg="black")
        user_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        # Frame for text widget with scrollbar
        user_frame = tk.Frame(parent, bg="white")
        user_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        user_scroll = tk.Scrollbar(user_frame)
        user_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        user_text = tk.Text(
            user_frame,
            height=6,
            width=100,
            font=("Courier", 9),
            wrap=tk.WORD,
            bg="white",
            fg="black",
            insertbackground="black",
            relief=tk.SUNKEN,
            borderwidth=2,
            yscrollcommand=user_scroll.set
        )
        user_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        user_scroll.config(command=user_text.yview)
        
        user_text.insert("1.0", context.user_prompt)
        user_text.config(state=tk.DISABLED)
    
    def _build_results_section(self, parent: ttk.Frame, context: HILContext):
        """Build the results display section."""
        parent.configure(style='White.TFrame')
        
        results_label = tk.Label(parent, text="Results:", font=("Courier", 10, "bold"), bg="white", fg="black")
        results_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        # Frame for text widget with scrollbar
        results_frame = tk.Frame(parent, bg="white")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        results_scroll = tk.Scrollbar(results_frame)
        results_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        results_text = tk.Text(
            results_frame,
            height=20,
            width=100,
            font=("Courier", 9),
            wrap=tk.WORD,
            bg="white",
            fg="black",
            insertbackground="black",
            relief=tk.SUNKEN,
            borderwidth=2,
            yscrollcommand=results_scroll.set
        )
        results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scroll.config(command=results_text.yview)
        
        # Format results for display
        if context.results:
            try:
                results_for_display = []
                for r in context.results:
                    if hasattr(r, 'model_dump'):
                        # Pydantic model - use model_dump()
                        results_for_display.append(r.model_dump())
                    elif hasattr(r, '__dict__'):
                        # Dataclass or custom object - use __dict__
                        results_for_display.append(r.__dict__)
                    else:
                        # Fallback to string representation
                        results_for_display.append(str(r))
                
                # Try to serialize to JSON
                results_json = json.dumps(results_for_display, indent=2, default=str)
                results_text.insert("1.0", results_json)
            except Exception as e:
                # If JSON fails, just display as string
                for r in context.results:
                    if hasattr(r, 'model_dump'):
                        results_text.insert(tk.END, json.dumps(r.model_dump(), indent=2, default=str))
                    elif hasattr(r, '__dict__'):
                        results_text.insert(tk.END, json.dumps(r.__dict__, indent=2, default=str))
                    else:
                        results_text.insert(tk.END, str(r) + "\n\n")
        
        results_text.config(state=tk.DISABLED)
    
    def _build_metadata_section(self, parent: ttk.Frame, context: HILContext):
        """Build the metadata/details section."""
        parent.configure(style='White.TFrame')
        
        meta_label = tk.Label(parent, text="Phase Details:", font=("Courier", 10, "bold"), bg="white", fg="black")
        meta_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        # Frame for text widget with scrollbar
        meta_frame = tk.Frame(parent, bg="white")
        meta_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        meta_scroll = tk.Scrollbar(meta_frame)
        meta_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        meta_text = tk.Text(
            meta_frame,
            height=20,
            width=100,
            font=("Courier", 9),
            wrap=tk.WORD,
            bg="white",
            fg="black",
            insertbackground="black",
            relief=tk.SUNKEN,
            borderwidth=2,
            yscrollcommand=meta_scroll.set
        )
        meta_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        meta_scroll.config(command=meta_text.yview)
        
        # Format metadata
        meta_info = {
            "Phase": context.phase,
            "Agent": context.agent_name,
            "Status": "PRE-EXECUTION" if context.is_pre_execution else "POST-EXECUTION",
            "Metadata": context.metadata
        }
        meta_json = json.dumps(meta_info, indent=2)
        meta_text.insert("1.0", meta_json)
        meta_text.config(state=tk.DISABLED)
