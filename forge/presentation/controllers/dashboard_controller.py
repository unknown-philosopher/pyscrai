"""
Dashboard Controller - Unified Command Center.
Merges Project Management, Graph View, and Document Ingest.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import subprocess
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import flet as ft

from forge.core import events
from forge.core.service_registry import get_session_manager

# Optional Tkinter for file dialogs
try:
    import tkinter as tk
    from tkinter import filedialog, simpledialog
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    tk: Any = None
    filedialog: Any = None
    simpledialog: Any = None

if TYPE_CHECKING:
    from forge.core.app_controller import AppController

logger = logging.getLogger(__name__)


class DashboardController:
    """Unified controller for the main dashboard."""

    # Graph Color Mapping
    ENTITY_COLORS = {
        "PERSON": "#4A90E2", "ORGANIZATION": "#7ED321", "LOCATION": "#9013FE",
        "EVENT": "#F5A623", "DATE": "#50E3C2", "MONEY": "#B8E986",
        "PERCENT": "#BD10E0", "MISC": "#D0021B",
    }
    DEFAULT_COLOR = "#BDC3C7"

    def __init__(self, app_controller: AppController, page: ft.Page):
        self.app_controller = app_controller
        self.page = page
        self._doc_counter = 0
        
        # Graph State
        self._current_layout = "force-directed"
        self._graph_html_path: Optional[Path] = None
        self._http_server: Optional[HTTPServer] = None
        self._http_server_thread: Optional[threading.Thread] = None
        
        # Selected file for processing
        self._selected_file: Optional[Path] = None

    def build_view(self) -> ft.Control:
        """Build the unified dashboard view."""
        
        # --- Section 1: Project Management Buttons (without header) ---
        project_buttons = self._build_project_buttons()
        
        # --- Section 2: Analyze Data Button (renamed from Select Data) ---
        analyze_data_button = self._build_analyze_data_button()
        
        # --- Section 3: Graph View (Right/Side Area) ---
        graph_section = self._build_graph_panel()

        # Layout Assembly
        return ft.Container(
            padding=ft.padding.only(left=20, right=20, top=16, bottom=16),
            expand=True,
            content=ft.Column(
                [
                    # Row 1: PyScrAI Header
                    ft.Row([
                        ft.Icon(ft.Icons.DASHBOARD, color="#48b0f7", size=26),
                        ft.Text("PyScrAI", size=22, weight=ft.FontWeight.W_700, color="#E8F1F8"),
                    ], spacing=12),
                    
                    # Row 2: Divider beneath header
                    ft.Divider(color="rgba(255, 255, 255, 0.12)", height=14),
                    
                    # Row 3: Main Content Area
                    ft.Row(
                        [
                            # Left Column: Project Management + Buttons + Analyze Data
                            ft.Container(
                                expand=2,
                                alignment=ft.Alignment(-1.0, -1.0),
                                content=ft.Column(
                                    [
                                        # Project Management header (no icon)
                                        ft.Text("Project Management", size=16, weight=ft.FontWeight.W_600, color="#B8C5D0"),
                                        ft.Container(height=14),
                                        
                                        # Project buttons (New, Open, Save)
                                        project_buttons,
                                        ft.Container(height=18),
                                        
                                        # Analyze Data button
                                        analyze_data_button,
                                    ],
                                    spacing=0,
                                ),
                            ),
                            
                            ft.VerticalDivider(width=1, color="rgba(255, 255, 255, 0.12)"),
                            
                            # Right Column: Graph & Stats
                            ft.Container(
                                expand=1,
                                content=graph_section,
                            )
                        ],
                        expand=True,
                        spacing=20,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    ),
                ],
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
                alignment=ft.MainAxisAlignment.START,
            )
        )

    # =========================================================================
    # PROJECT MANAGEMENT LOGIC
    # =========================================================================
    
    def _build_project_buttons(self) -> ft.Control:
        """Build just the project management buttons (New, Open, Save) without header."""
        
        async def on_new_project(e):
            """Open dialog to create a new project."""
            if not TKINTER_AVAILABLE:
                await self.app_controller.push_agui_log("Tkinter required for file dialogs", "error")
                return
            
            # Get project name
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            # Simple dialog for project name
            project_name = simpledialog.askstring(
                "New Project",
                "Enter project name:",
                parent=root
            )
            root.destroy()
            
            if not project_name:
                return
            
            # Get storage directory (default: /data/projects)
            project_root = Path(__file__).parent.parent.parent.parent
            default_dir = project_root / "data" / "projects"
            default_dir.mkdir(parents=True, exist_ok=True)
            
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            storage_dir = filedialog.askdirectory(
                title="Select Project Storage Directory",
                initialdir=str(default_dir)
            )
            root.destroy()
            
            if not storage_dir:
                return
            
            # Create project directory and database file
            project_dir = Path(storage_dir) / project_name
            project_dir.mkdir(parents=True, exist_ok=True)
            db_path = project_dir / f"{project_name}.duckdb"
            
            # Initialize new DuckDB database
            import duckdb
            conn = duckdb.connect(str(db_path))
            # Let the persistence service create schema when opened
            conn.close()
            
            await self.app_controller.push_agui_log(f"Created new project: {project_name}", "success")
            
            # Open the new project
            sm = get_session_manager()
            if sm:
                await sm.open_project(str(db_path))
        
        async def on_save(e):
            sm = get_session_manager()
            if not sm: return
            if not TKINTER_AVAILABLE:
                await self.app_controller.push_agui_log("Tkinter required for file dialogs", "error")
                return
                
            root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
            path = filedialog.asksaveasfilename(
                title="Save Project", defaultextension=".duckdb",
                filetypes=[("DuckDB", "*.duckdb")], initialfile="project.duckdb"
            )
            root.destroy()
            
            if path:
                await sm.save_project(path)

        async def on_open(e):
            sm = get_session_manager()
            if not sm: return
            if not TKINTER_AVAILABLE: return
            
            root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
            path = filedialog.askopenfilename(
                title="Open Project", filetypes=[("DuckDB", "*.duckdb")]
            )
            root.destroy()
            
            if path:
                await sm.open_project(path)

        return ft.Row(
            [
                ft.OutlinedButton(
                    "New",
                    icon=ft.Icons.ADD,
                    icon_color="#B8C5D0",
                    tooltip="Create New Project",
                    style=ft.ButtonStyle(
                        color="#E8F1F8",
                    ),
                    on_click=lambda e: asyncio.create_task(on_new_project(e))
                ),
                ft.OutlinedButton(
                    "Open",
                    icon=ft.Icons.FOLDER_OPEN,
                    icon_color="#B8C5D0",
                    tooltip="Open Project",
                    style=ft.ButtonStyle(
                        color="#E8F1F8",
                    ),
                    on_click=lambda e: asyncio.create_task(on_open(e))
                ),
                ft.OutlinedButton(
                    "Save",
                    icon=ft.Icons.SAVE,
                    icon_color="#B8C5D0",
                    tooltip="Save Project",
                    style=ft.ButtonStyle(
                        color="#E8F1F8",
                    ),
                    on_click=lambda e: asyncio.create_task(on_save(e))
                ),
            ],
            spacing=8,
        )
    
    def _build_project_controls(self) -> ft.Control:
        
        async def on_new_project(e):
            """Open dialog to create a new project."""
            if not TKINTER_AVAILABLE:
                await self.app_controller.push_agui_log("Tkinter required for file dialogs", "error")
                return
            
            # Get project name
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            # Simple dialog for project name
            project_name = simpledialog.askstring(
                "New Project",
                "Enter project name:",
                parent=root
            )
            root.destroy()
            
            if not project_name:
                return
            
            # Get storage directory (default: /data/projects)
            project_root = Path(__file__).parent.parent.parent.parent
            default_dir = project_root / "data" / "projects"
            default_dir.mkdir(parents=True, exist_ok=True)
            
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            storage_dir = filedialog.askdirectory(
                title="Select Project Storage Directory",
                initialdir=str(default_dir)
            )
            root.destroy()
            
            if not storage_dir:
                return
            
            # Create project directory and database file
            project_dir = Path(storage_dir) / project_name
            project_dir.mkdir(parents=True, exist_ok=True)
            db_path = project_dir / f"{project_name}.duckdb"
            
            # Initialize new DuckDB database
            import duckdb
            conn = duckdb.connect(str(db_path))
            # Let the persistence service create schema when opened
            conn.close()
            
            await self.app_controller.push_agui_log(f"Created new project: {project_name}", "success")
            
            # Open the new project
            sm = get_session_manager()
            if sm:
                await sm.open_project(str(db_path))
        
        async def on_save(e):
            sm = get_session_manager()
            if not sm: return
            if not TKINTER_AVAILABLE:
                await self.app_controller.push_agui_log("Tkinter required for file dialogs", "error")
                return
                
            root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
            path = filedialog.asksaveasfilename(
                title="Save Project", defaultextension=".duckdb",
                filetypes=[("DuckDB", "*.duckdb")], initialfile="project.duckdb"
            )
            root.destroy()
            
            if path:
                await sm.save_project(path)

        async def on_open(e):
            sm = get_session_manager()
            if not sm: return
            if not TKINTER_AVAILABLE: return
            
            root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
            path = filedialog.askopenfilename(
                title="Open Project", filetypes=[("DuckDB", "*.duckdb")]
            )
            root.destroy()
            
            if path:
                await sm.open_project(path)

        return ft.Container(
            bgcolor="rgba(255,255,255,0.02)",
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            content=ft.Row(
                [
                    ft.Row([
                        ft.Icon(ft.Icons.DASHBOARD, color=ft.Colors.CYAN_300, size=20),
                        ft.Text("Project Management", size=18, weight=ft.FontWeight.W_500, color=ft.Colors.WHITE70),
                    ], spacing=8),
                    
                    ft.Container(expand=True),  # Spacer
                    
                    # Minimalist action buttons
                    ft.OutlinedButton(
                        "New",
                        icon=ft.Icons.ADD,
                        icon_color=ft.Colors.WHITE70,
                        tooltip="Create New Project",
                        style=ft.ButtonStyle(
                            text_style=ft.TextStyle(color=ft.Colors.WHITE70),
                        ),
                        on_click=lambda e: asyncio.create_task(on_new_project(e))
                    ),
                    ft.OutlinedButton(
                        "Open",
                        icon=ft.Icons.FOLDER_OPEN,
                        icon_color=ft.Colors.WHITE70,
                        tooltip="Open Project",
                        style=ft.ButtonStyle(
                            text_style=ft.TextStyle(color=ft.Colors.WHITE70),
                        ),
                        on_click=lambda e: asyncio.create_task(on_open(e))
                    ),
                    ft.OutlinedButton(
                        "Save",
                        icon=ft.Icons.SAVE,
                        icon_color=ft.Colors.WHITE70,
                        tooltip="Save Project",
                        style=ft.ButtonStyle(
                            text_style=ft.TextStyle(color=ft.Colors.WHITE70),
                        ),
                        on_click=lambda e: asyncio.create_task(on_save(e))
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                spacing=8,
            )
        )

    # =========================================================================
    # ANALYZE DATA BUTTON (formerly Select Data)
    # =========================================================================

    def _build_analyze_data_button(self) -> ft.Control:
        """Build the Analyze Data button (renamed from Select Data) with file selection and processing."""
        # Selected file display
        selected_file_text = ft.Text(
            "No file selected",
            size=12,
            color="#8A9BA8",
            weight=ft.FontWeight.W_400,
            italic=True
        )
        
        def _read_file_content(file_path: Path) -> str:
            """Read content from supported file formats."""
            suffix = file_path.suffix.lower()
            
            if suffix == '.txt':
                return file_path.read_text(encoding='utf-8')
            elif suffix == '.pdf':
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(file_path)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    return text
                except ImportError:
                    logger.error("pypdf not available for PDF reading")
                    return ""
                except Exception as e:
                    logger.error(f"Error reading PDF: {e}")
                    return ""
            else:
                # Try to read as text for other formats
                try:
                    return file_path.read_text(encoding='utf-8')
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {e}")
                    return ""
        
        async def on_analyze_data(e):
            """Open file picker to select a data file, then process it."""
            if not TKINTER_AVAILABLE:
                await self.app_controller.push_agui_log("Tkinter required for file dialogs", "error")
                return
            
            project_root = Path(__file__).parent.parent.parent.parent
            default_dir = project_root / "data"
            default_dir.mkdir(parents=True, exist_ok=True)
            
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            # Support multiple formats: .txt and .pdf
            file_path = filedialog.askopenfilename(
                title="Select Data File",
                initialdir=str(default_dir),
                filetypes=[
                    ("Text files", "*.txt"),
                    ("PDF files", "*.pdf"),
                    ("All supported", "*.txt *.pdf"),
                    ("All files", "*.*")
                ]
            )
            root.destroy()
            
            if not file_path:
                return
            
            self._selected_file = Path(file_path)
            selected_file_text.value = f"Selected: {self._selected_file.name}"
            selected_file_text.color = "#B8C5D0"
            selected_file_text.italic = False
            self.page.update()
            await self.app_controller.push_agui_log(f"Selected file: {self._selected_file.name}", "info")
            
            # Automatically process the selected file
            self._doc_counter += 1
            doc_id = f"doc_{self._doc_counter:04d}"
            
            selected_file_text.value = f"Processing {self._selected_file.name}..."
            selected_file_text.color = "#48b0f7"
            self.page.update()
            
            try:
                # Read file content
                text = _read_file_content(self._selected_file)
                if not text:
                    await self.app_controller.push_agui_log(f"Could not read content from {self._selected_file.name}", "error")
                    selected_file_text.value = "No file selected"
                    selected_file_text.color = "#8A9BA8"
                    selected_file_text.italic = True
                    self.page.update()
                    return
                
                # Publish ingestion event
                await self.app_controller.publish(
                    events.TOPIC_DATA_INGESTED,
                    events.create_data_ingested_event(doc_id, text.strip())
                )
                
                # Reset selection after processing
                processed_filename = self._selected_file.name
                self._selected_file = None
                selected_file_text.value = "No file selected"
                selected_file_text.color = "#8A9BA8"
                selected_file_text.italic = True
                await self.app_controller.push_agui_log(f"Processed {doc_id} from {processed_filename}", "success")
                self.page.update()
                
            except Exception as ex:
                logger.error(f"Error processing file: {ex}", exc_info=True)
                await self.app_controller.push_agui_log(f"Error processing file: {str(ex)}", "error")
                selected_file_text.value = "No file selected"
                selected_file_text.color = "#8A9BA8"
                selected_file_text.italic = True
                self.page.update()

        return ft.Column(
            [
                ft.OutlinedButton(
                    "Analyze Data",
                    icon=ft.Icons.ANALYTICS,
                    icon_color="#B8C5D0",
                    tooltip="Select and analyze a data file (.txt, .pdf)",
                    style=ft.ButtonStyle(
                        color="#E8F1F8",
                    ),
                    expand=True,
                    on_click=lambda e: asyncio.create_task(on_analyze_data(e))
                ),
                ft.Container(height=10),
                selected_file_text,
            ],
            spacing=0,
        )

    def _build_ingest_panel(self) -> ft.Control:
        # Selected file display and Process button (will be created in async functions)
        selected_file_text = ft.Text(
            "No file selected",
            size=12,
            color=ft.Colors.WHITE54,
            weight=ft.FontWeight.W_400
        )
        
        process_button = ft.OutlinedButton(
            "Process",
            icon=ft.Icons.PLAY_ARROW,
            icon_color=ft.Colors.CYAN_300,
            tooltip="Process selected file and extract intelligence",
            style=ft.ButtonStyle(
                text_style=ft.TextStyle(color=ft.Colors.CYAN_300),
            ),
            disabled=True,  # Disabled until file is selected
            on_click=lambda e: asyncio.create_task(on_process(e))
        )
        
        def _read_file_content(file_path: Path) -> str:
            """Read content from supported file formats."""
            suffix = file_path.suffix.lower()
            
            if suffix == '.txt':
                return file_path.read_text(encoding='utf-8')
            elif suffix == '.pdf':
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(file_path)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    return text
                except ImportError:
                    logger.error("pypdf not available for PDF reading")
                    return ""
                except Exception as e:
                    logger.error(f"Error reading PDF: {e}")
                    return ""
            else:
                # Try to read as text for other formats
                try:
                    return file_path.read_text(encoding='utf-8')
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {e}")
                    return ""
        
        async def on_select_data(e):
            """Open file picker to select a data file."""
            if not TKINTER_AVAILABLE:
                await self.app_controller.push_agui_log("Tkinter required for file dialogs", "error")
                return
            
            project_root = Path(__file__).parent.parent.parent.parent
            default_dir = project_root / "data"
            default_dir.mkdir(parents=True, exist_ok=True)
            
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            # Support multiple formats: .txt and .pdf
            file_path = filedialog.askopenfilename(
                title="Select Data File",
                initialdir=str(default_dir),
                filetypes=[
                    ("Text files", "*.txt"),
                    ("PDF files", "*.pdf"),
                    ("All supported", "*.txt *.pdf"),
                    ("All files", "*.*")
                ]
            )
            root.destroy()
            
            if file_path:
                self._selected_file = Path(file_path)
                selected_file_text.value = f"Selected: {self._selected_file.name}"
                selected_file_text.color = ft.Colors.WHITE70
                process_button.disabled = False
                self.page.update()
                await self.app_controller.push_agui_log(f"Selected file: {self._selected_file.name}", "info")
        
        async def on_process(e):
            if not self._selected_file or not self._selected_file.exists():
                await self.app_controller.push_agui_log("No file selected", "warning")
                return
            
            self._doc_counter += 1
            doc_id = f"doc_{self._doc_counter:04d}"
            
            # Disable button during processing
            process_button.disabled = True
            selected_file_text.value = f"Processing {self._selected_file.name}..."
            selected_file_text.color = ft.Colors.CYAN_300
            self.page.update()
            
            try:
                # Read file content
                text = _read_file_content(self._selected_file)
                if not text:
                    await self.app_controller.push_agui_log(f"Could not read content from {self._selected_file.name}", "error")
                    process_button.disabled = False
                    self.page.update()
                    return
                
                # Publish ingestion event
                await self.app_controller.publish(
                    events.TOPIC_DATA_INGESTED,
                    events.create_data_ingested_event(doc_id, text.strip())
                )
                
                # Reset selection after processing
                processed_filename = self._selected_file.name if self._selected_file else 'file'
                self._selected_file = None
                selected_file_text.value = "No file selected"
                selected_file_text.color = ft.Colors.WHITE54
                process_button.disabled = True
                await self.app_controller.push_agui_log(f"Processed {doc_id} from {processed_filename}", "success")
                self.page.update()
                
            except Exception as ex:
                logger.error(f"Error processing file: {ex}", exc_info=True)
                await self.app_controller.push_agui_log(f"Error processing file: {str(ex)}", "error")
                process_button.disabled = False
                self.page.update()

        return ft.Column(
            [
                ft.Row([
                    ft.Icon(ft.Icons.ANALYTICS, size=18, color=ft.Colors.WHITE70),
                    ft.Text("Analyze Data", size=14, weight=ft.FontWeight.W_500, color=ft.Colors.WHITE70),
                ], spacing=8),
                ft.Container(height=8),
                
                # Process button directly under header
                ft.Container(
                    content=process_button,
                    padding=0,
                ),
                ft.Container(height=8),
                
                # Select Data button
                ft.OutlinedButton(
                    "Select Data",
                    icon=ft.Icons.UPLOAD_FILE,
                    icon_color=ft.Colors.WHITE70,
                    tooltip="Select a data file to analyze (.txt, .pdf)",
                    style=ft.ButtonStyle(
                        text_style=ft.TextStyle(color=ft.Colors.WHITE70),
                    ),
                    expand=True,
                    on_click=lambda e: asyncio.create_task(on_select_data(e))
                ),
                ft.Container(height=8),
                
                # Selected file display
                selected_file_text,
            ],
            expand=True,
            spacing=0
        )

    # =========================================================================
    # GRAPH LOGIC
    # =========================================================================

    def _build_graph_panel(self) -> ft.Control:
        # Simplified Graph View integrated into dashboard
        
        # Load Stats (Safe loading)
        entities, relationships = [], []
        sm = get_session_manager()
        if sm and sm.persistence:
            try:
                entities = sm.persistence.get_all_entities()
                relationships = sm.persistence.get_all_relationships()
            except Exception: pass
            
        e_count = len(entities)
        r_count = len(relationships)
        has_data = e_count > 0

        async def on_view_graph(e):
            if not has_data: 
                await self.app_controller.push_agui_log("No graph data available", "warning")
                return
            try:
                # Generate and open
                html_path = self._generate_graph_html(entities, relationships)
                if not html_path:
                    await self.app_controller.push_agui_log("Failed to generate graph", "error")
                    return
                
                url = await self._serve_html(html_path)
                if not url:
                    await self.app_controller.push_agui_log("Failed to start HTTP server", "error")
                    return
                
                if self._open_browser(url):
                    await self.app_controller.push_agui_log("Graph opened in browser", "success")
                else:
                    await self.app_controller.push_agui_log(f"Could not open browser. URL: {url}", "warning")
            except Exception as ex:
                logger.error(f"Error opening graph: {ex}", exc_info=True)
                await self.app_controller.push_agui_log(f"Error opening graph: {str(ex)}", "error")

        # Minimalist Stats Cards
        def _stat_card(label, value, icon, color):
            return ft.Container(
                bgcolor="rgba(255,255,255,0.025)",
                padding=ft.padding.symmetric(horizontal=14, vertical=12),
                border_radius=8,
                border=ft.border.all(1, "rgba(255,255,255,0.1)"),
                expand=True,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(icon, color=color, size=16),
                        ft.Text(str(value), size=20, weight=ft.FontWeight.W_700, color="#E8F1F8"),
                    ], spacing=8, alignment=ft.MainAxisAlignment.START),
                    ft.Text(label, size=11, color="#8A9BA8", weight=ft.FontWeight.W_500)
                ], spacing=6, horizontal_alignment=ft.CrossAxisAlignment.START)
            )

        return ft.Column(
            [
                ft.Row([
                    _stat_card("Entities", e_count, ft.Icons.CIRCLE, "#48b0f7"),
                    ft.Container(width=10),
                    _stat_card("Relations", r_count, ft.Icons.SHARE, "#4ECDC4"),
                ], spacing=0),
                
                ft.Container(height=18),
                
                # Divider with "Knowledge Graph" header
                ft.Column([
                    ft.Text("Knowledge Graph", size=14, weight=ft.FontWeight.W_600, color="#B8C5D0"),
                    ft.Divider(color="rgba(255, 255, 255, 0.12)", height=1),
                ], spacing=6),
                
                ft.Container(height=10),
                
                self._create_layout_dropdown(),
                
                ft.Container(height=14),
                
                ft.OutlinedButton(
                    "View Graph",
                    icon=ft.Icons.OPEN_IN_BROWSER,
                    icon_color="#B8C5D0",
                    tooltip="Open interactive graph visualization",
                    style=ft.ButtonStyle(
                        color="#E8F1F8",
                    ),
                    expand=True,
                    disabled=not has_data,
                    on_click=lambda e: asyncio.create_task(on_view_graph(e))
                ),
            ],
            spacing=0
        )

    # --- Graph Helpers (Ported from GraphController) ---
    
    def _create_layout_dropdown(self) -> ft.Dropdown:
        """Create layout dropdown with proper event handler."""
        def on_layout_change(e):
            self._current_layout = e.control.value
        
        dropdown = ft.Dropdown(
            label="Layout", 
            value=self._current_layout,
            options=[
                ft.dropdown.Option("force-directed"),
                ft.dropdown.Option("circular"),
            ],
            text_size=13, 
            height=40, 
            content_padding=ft.padding.symmetric(horizontal=10, vertical=8),
            border_color="rgba(255,255,255,0.15)",
            bgcolor="rgba(255,255,255,0.02)",
            color="#E8F1F8",
            label_style=ft.TextStyle(color="#B8C5D0", size=12),
        )
        dropdown.on_change = on_layout_change  # type: ignore[assignment]
        return dropdown
    
    def _generate_graph_html(self, entities, relationships) -> Optional[Path]:
        try:
            import plotly.graph_objects as go
            import networkx as nx
        except ImportError:
            return None

        # Build NetworkX Graph for Layout
        G = nx.DiGraph()
        valid_ids = set()
        
        for e in entities:
            eid = e.get("id")
            if eid: 
                valid_ids.add(eid)
                G.add_node(eid, **e)
                
        for r in relationships:
            src, tgt = r.get("source"), r.get("target")
            if src in valid_ids and tgt in valid_ids:
                G.add_edge(src, tgt, **r)

        if not G.nodes: return None

        # Calculate Layout
        if self._current_layout == "circular":
            pos = nx.circular_layout(G)
        else:
            pos = nx.spring_layout(G, k=0.5, iterations=50)

        # Create Plotly Traces
        edge_x, edge_y = [], []
        node_x, node_y, node_text, node_color = [], [], [], []

        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none', mode='lines')

        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            data = G.nodes[node]
            label = data.get("label", node)
            etype = data.get("type", "UNKNOWN")
            node_text.append(f"{label} ({etype})")
            node_color.append(self.ENTITY_COLORS.get(etype, self.DEFAULT_COLOR))

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            text=[G.nodes[n].get("label", n) for n in G.nodes()],
            textposition="top center",
            hovertext=node_text,
            marker=dict(size=10, color=node_color, line_width=2))

        fig = go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                title="Knowledge Graph",
                showlegend=False,
                margin=dict(b=0,l=0,r=0,t=40),
                paper_bgcolor='rgba(10,15,30,1)',
                plot_bgcolor='rgba(10,15,30,1)',
                font=dict(color='white'),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
            )
        )

        # Save to absolute path
        try:
            project_root = Path(__file__).parent.parent.parent.parent
            output_dir = project_root / "data" / "graph"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            html_path = output_dir / "visualization.html"
            html_path.write_text(fig.to_html(include_plotlyjs='cdn', full_html=True), encoding='utf-8')
            logger.info(f"Graph HTML saved to {html_path}")
            return html_path
        except Exception as e:
            logger.error(f"Error saving graph HTML: {e}")
            return None

    def _find_free_port(self) -> int:
        """Find a free port for the HTTP server."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    async def _serve_html(self, path: Path) -> Optional[str]:
        """Start a simple HTTP server to serve the HTML file.
        
        Args:
            path: Path to the HTML file to serve
            
        Returns:
            URL to access the file, or None if server couldn't be started
        """
        try:
            # Stop any existing server
            if self._http_server:
                self._stop_http_server()
            
            # Change to the directory containing the HTML file
            server_dir = path.parent
            port = self._find_free_port()
            
            # Create handler class with directory bound
            def make_handler(directory: str):
                class Handler(SimpleHTTPRequestHandler):
                    def __init__(self, *args, **kwargs):
                        super().__init__(*args, directory=directory, **kwargs)
                    
                    def log_message(self, format, *args):
                        # Suppress server logs
                        pass
                return Handler
            
            Handler = make_handler(str(server_dir))
            self._http_server = HTTPServer(('127.0.0.1', port), Handler)
            server = self._http_server  # Capture for nested function
            
            def run_server():
                try:
                    server.serve_forever()  # type: ignore[union-attr]
                except Exception:
                    pass  # Server stopped
            
            self._http_server_thread = threading.Thread(target=run_server, daemon=True)
            self._http_server_thread.start()
            
            # Give the server a moment to start
            await asyncio.sleep(0.1)
            
            # Build URL
            filename = path.name
            url = f"http://127.0.0.1:{port}/{filename}"
            return url
        except Exception as e:
            logger.warning(f"Could not start HTTP server: {e}")
            return None
    
    def _stop_http_server(self):
        """Stop the HTTP server if it's running."""
        if self._http_server:
            try:
                self._http_server.shutdown()
                self._http_server.server_close()
            except Exception:
                pass
            self._http_server = None
        if self._http_server_thread and self._http_server_thread.is_alive():
            self._http_server_thread.join(timeout=1.0)
        self._http_server_thread = None

    def _open_browser(self, url: str) -> bool:
        """Open a URL in the default browser with improved error handling."""
        logger.info(f"Attempting to open browser with URL: {url}")
        
        # On Linux/WSL2, xdg-open is the most reliable method
        # Try xdg-open first (works with default browser)
        try:
            result = subprocess.run(
                ['xdg-open', url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                check=False
            )
            if result.returncode == 0:
                logger.info("Successfully opened browser using xdg-open")
                return True
            else:
                logger.debug(f"xdg-open returned code {result.returncode}: {result.stderr.decode()}")
        except FileNotFoundError:
            logger.debug("xdg-open not found, trying other methods")
        except subprocess.TimeoutExpired:
            logger.warning("xdg-open timed out")
        except Exception as e:
            logger.debug(f"xdg-open failed: {e}")
        
        # Try webbrowser module (cross-platform, uses default browser)
        try:
            webbrowser.open(url)
            logger.info("Successfully opened browser using webbrowser module")
            return True
        except Exception as e:
            logger.warning(f"webbrowser.open failed: {e}")
        
        # Fallback: Try specific browsers
        browsers = [
            ('chromium-browser', False),
            ('chromium', False),
            ('google-chrome', False),
            ('google-chrome-stable', False),
            ('firefox', False),
        ]
        
        for browser_name, use_app_mode in browsers:
            try:
                if use_app_mode:
                    cmd = [browser_name, f'--app={url}']
                else:
                    cmd = [browser_name, url]
                
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                logger.info(f"Successfully launched {browser_name}")
                return True
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.debug(f"Failed to launch {browser_name}: {e}")
                continue
        
        logger.error(f"All browser opening methods failed for URL: {url}")
        return False
