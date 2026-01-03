"""Landing page widget for PyScrAI|Forge."""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Callable, Optional
from datetime import datetime, timezone


class LandingPageWidget(ttk.Frame):
    """Landing page shown when no project is loaded."""
    
    def __init__(self, parent, 
                 on_new_project: Callable[[], None],
                 on_open_project: Callable[[], None],
                 on_open_recent: Callable[[Path], None],
                 recent_projects: list = None):
        """
        Initialize landing page.
        
        Args:
            parent: Parent widget
            on_new_project: Callback for New Project button
            on_open_project: Callback for Open Project button
            on_open_recent: Callback for clicking recent project
            recent_projects: List of RecentProject objects
        """
        super().__init__(parent)
        self.on_new_project = on_new_project
        self.on_open_project = on_open_project
        self.on_open_recent = on_open_recent
        self.recent_projects = recent_projects or []
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the landing page UI."""
        # Main container with padding
        main_frame = ttk.Frame(self)
        main_frame.pack(expand=True)
        
        # Title
        title = ttk.Label(main_frame, text="PyScrAI|Forge", 
                 font=("Arial", 28, "bold"))
        title.pack(pady=(40, 10))
        
        subtitle = ttk.Label(main_frame, text="WorldBuilding Model & Component Management",
                font=("Arial", 11), foreground="gray")
        subtitle.pack(pady=(0, 40))
        
        # Attribution line
        attribution = ttk.Label(main_frame, text="Bro. Hamilton |::.| 2026",
                   font=("Arial", 9), foreground="gray")
        attribution.pack(pady=(0, 20))
        
        # Action buttons frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)
        
        # New Project button
        new_btn = tk.Button(btn_frame, text="New Project",
                           command=self.on_new_project,
                           width=18, height=2,
                           font=("Arial", 11),
                           bg="#219124", fg="white",
                           activebackground="#125d15", activeforeground="white",
                           relief=tk.FLAT, cursor="hand2")
        new_btn.pack(side=tk.LEFT, padx=15)
        
        # Open Project button
        open_btn = tk.Button(btn_frame, text="Open Project",
                            command=self.on_open_project,
                            width=18, height=2,
                            font=("Arial", 11),
                            bg="#1D70B4", fg="white",
                            activebackground="#0a4677", activeforeground="white",
                            relief=tk.FLAT, cursor="hand2")
        open_btn.pack(side=tk.LEFT, padx=15)
        
        # Recent projects section
        if self.recent_projects:
            recent_label = ttk.Label(main_frame, text="Recent Projects",
                                    font=("Arial", 13, "bold"))
            recent_label.pack(pady=(50, 15))
            
            # Recent projects frame with border
            recent_container = ttk.Frame(main_frame, relief=tk.SOLID, borderwidth=1)
            recent_container.pack(fill=tk.X, padx=100)
            
            recent_inner = ttk.Frame(recent_container)
            recent_inner.pack(fill=tk.X, padx=10, pady=10)
            
            for proj in self.recent_projects[:5]:
                proj_frame = ttk.Frame(recent_inner)
                proj_frame.pack(fill=tk.X, pady=3)
                
                proj_btn = tk.Button(
                    proj_frame,
                    text=f"• {proj.name}",
                    command=lambda p=proj.path: self.on_open_recent(Path(p)),
                    anchor='w',
                    relief=tk.FLAT,
                    fg="#054F8B",
                    font=("Arial", 10, "underline"),
                    cursor="hand2"
                )
                proj_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
                
                time_label = ttk.Label(proj_frame, 
                                      text=self._format_time(proj.last_opened),
                                      font=("Arial", 9),
                                      foreground="gray")
                time_label.pack(side=tk.RIGHT)
    
    def _format_time(self, dt):
        """Format datetime for display."""
        now = datetime.now(timezone.utc)
        dt_aware = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        diff = now - dt_aware
        
        if diff.days == 0:
            if diff.seconds < 3600:
                mins = diff.seconds // 60
                return f"{mins} minute{'s' if mins != 1 else ''} ago"
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.days == 1:
            return "yesterday"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        elif diff.days < 30:
            weeks = diff.days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        else:
            months = diff.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
