"""Reusable Progress Dialog for PyScrAI|Forge.

This module provides a standardized progress dialog that can be used
across all phases (Foundry, Loom, etc.) for consistent UX.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable


class ProgressDialog:
    """A reusable, centered progress dialog with animation.
    
    Features:
    - Centered on parent window
    - Animated progress bar
    - Customizable title and messages
    - Provider/model info display
    - Thread-safe update methods
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        title: str,
        message: str = "Processing...",
        status: Optional[str] = None,
        detail: Optional[str] = None,
        width: int = 400,
        height: int = 150
    ):
        """Initialize the progress dialog.
        
        Args:
            parent: Parent widget to center dialog on
            title: Dialog title (will have "..." appended if not present)
            message: Main progress message
            status: Optional status line (e.g., "Provider: X | Model: Y")
            detail: Optional detail line (e.g., "Processing 10 entities...")
            width: Dialog width in pixels
            height: Dialog height in pixels
        """
        self.parent = parent
        self.width = width
        self.height = height
        
        # Ensure title ends with "..."
        if not title.endswith("..."):
            title = title + "..."
        
        # Create dialog window
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry(f"{width}x{height}")
        self.window.transient(parent)
        self.window.grab_set()
        self.window.resizable(False, False)
        
        # Center on parent
        self._center_on_parent()
        
        # Create widgets
        self._create_widgets(message, status, detail)
        
        # Ensure dialog is visible
        self.window.update()
        self.window.update_idletasks()
    
    def _center_on_parent(self):
        """Center the dialog on the parent window."""
        self.window.update_idletasks()
        try:
            parent_x = self.parent.winfo_x()
            parent_y = self.parent.winfo_y()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
            
            x = parent_x + (parent_width - self.width) // 2
            y = parent_y + (parent_height - self.height) // 2
            
            self.window.geometry(f"+{x}+{y}")
        except (tk.TclError, AttributeError):
            # Fallback to screen center if parent info unavailable
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()
            x = (screen_width - self.width) // 2
            y = (screen_height - self.height) // 2
            self.window.geometry(f"+{x}+{y}")
    
    def _create_widgets(self, message: str, status: Optional[str], detail: Optional[str]):
        """Create and layout the dialog widgets."""
        # Progress label (main message)
        self.progress_label = tk.Label(
            self.window,
            text=message,
            font=("Segoe UI", 11),
            pady=20
        )
        self.progress_label.pack()
        
        # Status label (provider/model info)
        if status:
            self.status_label = tk.Label(
                self.window,
                text=status,
                font=("Segoe UI", 9),
                fg="gray"
            )
            self.status_label.pack()
        else:
            self.status_label = None
        
        # Progress bar style
        style = ttk.Style()
        style.configure("pyscrai.Horizontal.TProgressbar", thickness=20)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            self.window,
            mode="indeterminate",
            style="pyscrai.Horizontal.TProgressbar",
            length=300
        )
        self.progress_bar.pack(pady=10)
        self.progress_bar.start(50)
        
        # Detail label (additional info)
        if detail:
            self.detail_label = tk.Label(
                self.window,
                text=detail,
                font=("Segoe UI", 9),
                fg="gray"
            )
            self.detail_label.pack(pady=(5, 10))
        else:
            self.detail_label = None
    
    def update_message(self, message: str):
        """Update the main progress message.
        
        Args:
            message: New message text
        """
        try:
            self.progress_label.config(text=message)
            self.window.update()
        except (tk.TclError, AttributeError):
            pass
    
    def update_status(self, status: str):
        """Update the status line.
        
        Args:
            status: New status text
        """
        try:
            if self.status_label:
                self.status_label.config(text=status)
            self.window.update()
        except (tk.TclError, AttributeError):
            pass
    
    def update_detail(self, detail: str):
        """Update the detail line.
        
        Args:
            detail: New detail text
        """
        try:
            if self.detail_label:
                self.detail_label.config(text=detail)
            self.window.update()
        except (tk.TclError, AttributeError):
            pass
    
    def update_all(self, message: Optional[str] = None, status: Optional[str] = None, detail: Optional[str] = None):
        """Update multiple fields at once.
        
        Args:
            message: Optional new message
            status: Optional new status
            detail: Optional new detail
        """
        try:
            if message is not None:
                self.update_message(message)
            if status is not None:
                self.update_status(status)
            if detail is not None:
                self.update_detail(detail)
        except (tk.TclError, AttributeError):
            pass
    
    def close(self):
        """Close and destroy the dialog."""
        try:
            self.progress_bar.stop()
            self.window.destroy()
        except (tk.TclError, AttributeError):
            pass
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - automatically closes dialog."""
        self.close()


def run_with_progress(
    parent: tk.Widget,
    title: str,
    work_func: Callable,
    message: str = "Processing...",
    status: Optional[str] = None,
    detail: Optional[str] = None,
    on_complete: Optional[Callable] = None,
    on_error: Optional[Callable] = None
):
    """Run a function with a progress dialog.
    
    This is a convenience function that creates a progress dialog,
    runs work_func in a background thread, and handles cleanup.
    
    Args:
        parent: Parent widget
        title: Dialog title
        work_func: Function to run (will be called in background thread)
        message: Initial progress message
        status: Optional status line
        detail: Optional detail line
        on_complete: Optional callback when work completes (receives result)
        on_error: Optional callback when work fails (receives exception)
    
    Returns:
        The progress dialog instance (for manual control if needed)
    """
    import threading
    
    dialog = ProgressDialog(parent, title, message, status, detail)
    
    def finish_work():
        """Run work and handle completion."""
        try:
            result = work_func()
            dialog.close()
            if on_complete:
                parent.after(0, lambda: on_complete(result))
        except Exception as e:
            dialog.close()
            if on_error:
                parent.after(0, lambda: on_error(e))
            else:
                raise
    
    # Run in background thread
    thread = threading.Thread(target=finish_work, daemon=True)
    thread.start()
    
    return dialog
