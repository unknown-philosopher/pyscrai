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
    from tkinter import filedialog
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    tk: Any = None
    filedialog: Any = None

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

    def build_view(self) -> ft.Control:
        """Build the unified dashboard view."""
        
        # --- Section 1: Project Management (Top Bar) ---
        project_section = self._build_project_controls()
        
        # --- Section 2: Document Ingest (Left/Main Area) ---
        ingest_section = self._build_ingest_panel()
        
        # --- Section 3: Graph View (Right/Side Area) ---
        graph_section = self._build_graph_panel()

        # Layout Assembly
        return ft.Container(
            padding=20,
            content=ft.Column(
                [
                    # Row 1: Project Header & Controls
                    project_section,
                    ft.Divider(color="rgba(255, 255, 255, 0.1)", height=20),
                    
                    # Row 2: Main Content Area
                    ft.Row(
                        [
                            # Left Column: Ingest (2/3 width)
                            ft.Container(
                                expand=2,
                                content=ingest_section,
                            ),
                            
                            ft.VerticalDivider(width=1, color="rgba(255, 255, 255, 0.1)"),
                            
                            # Right Column: Graph & Stats (1/3 width)
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
                spacing=10,
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            )
        )

    # =========================================================================
    # PROJECT MANAGEMENT LOGIC
    # =========================================================================
    
    def _build_project_controls(self) -> ft.Control:
        
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

        async def on_reset(e):
            sm = get_session_manager()
            if sm: await sm.clear_session()

        return ft.Container(
            bgcolor="rgba(255,255,255,0.02)",
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            content=ft.Row(
                [
                    ft.Row([
                        ft.Icon(ft.Icons.DASHBOARD, color=ft.Colors.CYAN_300, size=20),
                        ft.Text("Mission Control", size=18, weight=ft.FontWeight.W_500, color=ft.Colors.WHITE70),
                    ], spacing=8),
                    
                    ft.Container(expand=True),  # Spacer
                    
                    # Minimalist action buttons
                    ft.OutlinedButton(
                        "Open",
                        icon=ft.Icons.FOLDER_OPEN,
                        icon_color=ft.Colors.WHITE70,
                        tooltip="Open Project",
                        style=ft.ButtonStyle(
                            color=ft.Colors.WHITE70,
                            overlay_color=ft.Colors.WHITE10,
                        ),
                        on_click=lambda e: asyncio.create_task(on_open(e))
                    ),
                    ft.OutlinedButton(
                        "Save",
                        icon=ft.Icons.SAVE,
                        icon_color=ft.Colors.WHITE70,
                        tooltip="Save Project",
                        style=ft.ButtonStyle(
                            color=ft.Colors.WHITE70,
                            overlay_color=ft.Colors.WHITE10,
                        ),
                        on_click=lambda e: asyncio.create_task(on_save(e))
                    ),
                    ft.OutlinedButton(
                        "Reset",
                        icon=ft.Icons.REFRESH,
                        icon_color=ft.Colors.WHITE70,
                        tooltip="Reset Session",
                        style=ft.ButtonStyle(
                            color=ft.Colors.WHITE70,
                            overlay_color=ft.Colors.WHITE10,
                        ),
                        on_click=lambda e: asyncio.create_task(on_reset(e))
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                spacing=8,
            )
        )

    # =========================================================================
    # INGEST LOGIC
    # =========================================================================

    def _build_ingest_panel(self) -> ft.Control:
        doc_input = ft.TextField(
            label="Input Document",
            hint_text="Paste text here to begin extraction...",
            multiline=True,
            min_lines=15,
            expand=True,
            bgcolor="rgba(0,0,0,0.2)",
            border_color="rgba(100, 200, 255, 0.2)",
            text_size=13,
        )
        
        status_text = ft.Text("Ready", size=11, color=ft.Colors.WHITE38, weight=ft.FontWeight.W_400)

        async def on_process(e):
            text = doc_input.value
            if not text: return
            
            self._doc_counter += 1
            doc_id = f"doc_{self._doc_counter:04d}"
            
            status_text.value = f"Processing {doc_id}..."
            status_text.color = ft.Colors.CYAN_300
            self.page.update()
            
            await self.app_controller.publish(
                events.TOPIC_DATA_INGESTED,
                events.create_data_ingested_event(doc_id, text.strip())
            )
            
            doc_input.value = ""
            status_text.value = f"Processed {doc_id}"
            status_text.color = ft.Colors.WHITE38
            await self.app_controller.push_agui_log(f"Ingested {doc_id}", "info")
            self.page.update()

        return ft.Column(
            [
                ft.Row([
                    ft.Icon(ft.Icons.DESCRIPTION, size=18, color=ft.Colors.WHITE70),
                    ft.Text("Document Ingest", size=14, weight=ft.FontWeight.W_500, color=ft.Colors.WHITE70),
                ], spacing=8),
                ft.Container(height=8),
                ft.Container(
                    content=doc_input,
                    expand=True,  # Fill vertical space
                ),
                ft.Container(height=12),
                ft.Row(
                    [
                        ft.OutlinedButton(
                            "Process",
                            icon=ft.Icons.PLAY_ARROW,
                            icon_color=ft.Colors.CYAN_300,
                            tooltip="Process document and extract intelligence",
                            style=ft.ButtonStyle(
                                color=ft.Colors.CYAN_300,
                                overlay_color=ft.Colors.CYAN_900,
                                side=ft.BorderSide(1, ft.Colors.CYAN_300),
                            ),
                            on_click=lambda e: asyncio.create_task(on_process(e))
                        ),
                        ft.Container(width=12),
                        status_text,
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
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
                bgcolor="rgba(255,255,255,0.03)",
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                border_radius=6,
                border=ft.border.all(1, "rgba(255,255,255,0.1)"),
                expand=True,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(icon, color=color, size=14),
                        ft.Text(str(value), size=18, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
                    ], spacing=6, alignment=ft.MainAxisAlignment.START),
                    ft.Text(label, size=11, color=ft.Colors.WHITE54, weight=ft.FontWeight.W_400)
                ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.START)
            )

        return ft.Column(
            [
                ft.Row([
                    ft.Icon(ft.Icons.HUB, size=18, color=ft.Colors.WHITE70),
                    ft.Text("Knowledge Graph", size=14, weight=ft.FontWeight.W_500, color=ft.Colors.WHITE70),
                ], spacing=8),
                ft.Container(height=12),
                
                ft.Row([
                    _stat_card("Entities", e_count, ft.Icons.CIRCLE, ft.Colors.CYAN_300),
                    ft.Container(width=8),
                    _stat_card("Relations", r_count, ft.Icons.SHARE, ft.Colors.CYAN_300),
                ], spacing=0),
                
                ft.Container(height=16),
                
                self._create_layout_dropdown(),
                
                ft.Container(height=12),
                
                ft.OutlinedButton(
                    "View Graph",
                    icon=ft.Icons.OPEN_IN_BROWSER,
                    icon_color=ft.Colors.WHITE70,
                    tooltip="Open interactive graph visualization",
                    style=ft.ButtonStyle(
                        color=ft.Colors.WHITE70,
                        overlay_color=ft.Colors.WHITE10,
                        side=ft.BorderSide(1, "rgba(255,255,255,0.2)"),
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
            text_size=12, 
            height=36, 
            content_padding=ft.padding.symmetric(horizontal=8, vertical=6),
            border_color="rgba(255,255,255,0.15)",
            bgcolor="rgba(255,255,255,0.02)",
            color=ft.Colors.WHITE70,
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
