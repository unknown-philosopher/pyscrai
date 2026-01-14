"""Graph controller for relationship graph visualization."""

from __future__ import annotations

import asyncio
import logging
import socket
import subprocess
import tempfile
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Any, Optional
from collections import defaultdict

import flet as ft

from forge.core.service_registry import get_session_manager

if TYPE_CHECKING:
    from forge.core.app_controller import AppController

logger = logging.getLogger(__name__)


class GraphController:
    """Handles graph visualization UI and interaction."""
    
    # Color mapping for entity types
    ENTITY_COLORS = {
        "PERSON": "#4A90E2",  # Blue
        "ORGANIZATION": "#7ED321",  # Green
        "LOCATION": "#9013FE",  # Purple
        "EVENT": "#F5A623",  # Orange
        "DATE": "#50E3C2",  # Teal
        "MONEY": "#B8E986",  # Light Green
        "PERCENT": "#BD10E0",  # Magenta
        "MISC": "#D0021B",  # Red
    }
    
    DEFAULT_COLOR = "#BDC3C7"  # Gray for unknown types
    
    def __init__(self, app_controller: "AppController", page: ft.Page):
        self.app_controller = app_controller
        self.page = page
        self._current_layout = "force-directed"
        self._filters = {
            "entity_types": [],
            "relationship_types": [],
            "confidence_threshold": 0.0,
        }
        # Cache for graph HTML file
        self._graph_html_path: Optional[Path] = None
        # HTTP server for serving HTML files
        self._http_server: Optional[HTTPServer] = None
        self._http_server_thread: Optional[threading.Thread] = None
    
    def build_view(self) -> ft.Control:
        """Build the graph view UI with controls and graph container."""
        
        # Load graph data
        entities, relationships = self._load_graph_data()
        
        # Apply filters
        filtered_entities, filtered_relationships = self._apply_filters(entities, relationships)
        
        # Calculate stats
        entity_count = len(filtered_entities)
        relationship_count = len(filtered_relationships)
        entity_types = set(e.get("type", "UNKNOWN") for e in filtered_entities)
        relationship_types = set(r.get("type", "UNKNOWN") for r in filtered_relationships)
        
        # Generate graph HTML if we have data
        graph_available = entity_count > 0 and relationship_count > 0
        
        async def on_view_graph(e):
            """Open graph visualization in browser."""
            if not graph_available:
                await self.app_controller.push_agui_log("No graph data available to visualize", "warning")
                return
            
            try:
                html_path = self._generate_and_save_graph(filtered_entities, filtered_relationships)
                if html_path and html_path.exists():
                    # Serve via HTTP server (more reliable than file:// URLs)
                    url = await self._serve_html_file(html_path)
                    if url:
                        if self._open_url_in_browser(url):
                            await self.app_controller.push_agui_log(f"Graph visualization opened in browser", "success")
                        else:
                            await self.app_controller.push_agui_log(f"Could not open browser. URL: {url}", "warning")
                    else:
                        # Fallback to file:// URL
                        file_url = f"file://{html_path.absolute()}"
                        if self._open_url_in_browser(file_url):
                            await self.app_controller.push_agui_log(f"Graph visualization opened in browser", "success")
                        else:
                            await self.app_controller.push_agui_log(f"Could not open browser. File: {html_path}", "warning")
                else:
                    await self.app_controller.push_agui_log("Failed to generate graph visualization", "error")
            except Exception as ex:
                logger.error(f"Error opening graph: {ex}")
                await self.app_controller.push_agui_log(f"Error opening graph: {str(ex)}", "error")
        
        async def on_export_html(e):
            """Export graph as HTML file."""
            if not graph_available:
                await self.app_controller.push_agui_log("No graph data available to export", "warning")
                return
            
            try:
                # For now, just open the graph - in a full implementation, we'd use a file dialog
                await on_view_graph(e)
                await self.app_controller.push_agui_log("Graph exported (opened in browser)", "success")
            except Exception as ex:
                logger.error(f"Error exporting graph: {ex}")
                await self.app_controller.push_agui_log(f"Error exporting graph: {str(ex)}", "error")
        
        async def on_layout_change(e):
            """Change graph layout algorithm."""
            layout_dropdown = e.control
            self._current_layout = layout_dropdown.value
            # Refresh the view (in a full implementation, we'd regenerate the graph)
            await self.app_controller.push_agui_log(f"Layout changed to {self._current_layout}", "info")
            self.page.update()
        
        # Build UI
        header = ft.Row(
            [
                ft.Icon(ft.Icons.ACCOUNT_TREE, size=32, color=ft.Colors.CYAN_300),
                ft.Text("Graph View", size=24, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
            ],
            spacing=12,
        )
        
        # Stats panel
        stats_panel = ft.Container(
            bgcolor="rgba(255, 255, 255, 0.05)",
            padding=16,
            border_radius=8,
            content=ft.Column(  # type: ignore[arg-type]
                [
                    ft.Text("Graph Statistics", size=16, weight=ft.FontWeight.W_600, color=ft.Colors.CYAN_200),
                    ft.Divider(color="rgba(255, 255, 255, 0.1)", height=10),  # type: ignore[call-arg]
                    ft.Row([
                        ft.Column([
                            ft.Text(f"{entity_count}", size=24, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
                            ft.Text("Nodes", size=12, color=ft.Colors.WHITE70),
                        ], spacing=4),
                        ft.VerticalDivider(width=1, color="rgba(255, 255, 255, 0.1)"),
                        ft.Column([
                            ft.Text(f"{relationship_count}", size=24, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
                            ft.Text("Edges", size=12, color=ft.Colors.WHITE70),
                        ], spacing=4),
                        ft.VerticalDivider(width=1, color="rgba(255, 255, 255, 0.1)"),
                        ft.Column([
                            ft.Text(f"{len(entity_types)}", size=24, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
                            ft.Text("Entity Types", size=12, color=ft.Colors.WHITE70),
                        ], spacing=4),
                    ], spacing=20),
                ],
                spacing=8,
            ),
        )
        
        # Controls
        layout_dropdown = ft.Dropdown(
            label="Layout Algorithm",
            value=self._current_layout,
            options=[
                ft.dropdown.Option("force-directed", "Force-Directed"),
                ft.dropdown.Option("circular", "Circular"),
                ft.dropdown.Option("hierarchical", "Hierarchical"),
            ],
            border_color="rgba(255,255,255,0.2)",
            width=200,
        )
        layout_dropdown.on_change = on_layout_change  # type: ignore[assignment]
        
        controls_row = ft.Row(
            [
                ft.ElevatedButton(
                    "View Graph",
                    icon=ft.Icons.OPEN_IN_BROWSER,
                    on_click=lambda e: asyncio.create_task(on_view_graph(e)),
                    bgcolor=ft.Colors.BLUE_700,
                    color=ft.Colors.WHITE,
                    disabled=not graph_available,
                    tooltip="Open interactive graph visualization in browser",
                ),
                ft.ElevatedButton(
                    "Export HTML",
                    icon=ft.Icons.DOWNLOAD,
                    on_click=lambda e: asyncio.create_task(on_export_html(e)),
                    bgcolor=ft.Colors.GREEN_700,
                    color=ft.Colors.WHITE,
                    disabled=not graph_available,
                    tooltip="Export graph as HTML file",
                ),
                layout_dropdown,
            ],
            spacing=10,
            wrap=False,
        )
        
        # Content
        if not graph_available:
            content = ft.Container(
                padding=40,
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.ACCOUNT_TREE, size=64, color=ft.Colors.WHITE54),
                        ft.Text("No Graph Data", size=20, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE70),
                        ft.Text(
                            "Ingest documents to extract entities and relationships, then visualize them here.",
                            size=14,
                            color=ft.Colors.WHITE54,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=12,
                ),
            )
        else:
            content = ft.Container(
                padding=20,
                content=ft.Column(
                    [
                        ft.Text(
                            "Graph visualization will open in your default browser. "
                            "Use the controls above to change layout and export options.",
                            size=14,
                            color=ft.Colors.WHITE70,
                        ),
                        ft.Container(height=20),
                        stats_panel,
                    ],
                    spacing=12,
                ),
            )
        
        return ft.Container(
            padding=20,
            content=ft.Column(  # type: ignore[arg-type]
                [
                    header,
                    ft.Divider(color="rgba(255, 255, 255, 0.1)", height=20),  # type: ignore[call-arg]
                    controls_row,
                    ft.Container(height=20),
                    content,
                ],
                spacing=12,
                scroll=ft.ScrollMode.AUTO,
            ),
        )
    
    def _load_graph_data(self) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Load entities and relationships from database.
        
        Returns:
            Tuple of (entities, relationships) lists
        """
        session_manager = get_session_manager()
        if not session_manager or not session_manager.persistence:
            logger.warning("Session manager or persistence service not available")
            return [], []
        
        try:
            entities = session_manager.persistence.get_all_entities()
            relationships = session_manager.persistence.get_all_relationships()
            return entities, relationships
        except Exception as e:
            logger.error(f"Error loading graph data: {e}")
            return [], []
    
    def _apply_layout(
        self,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        layout_name: str
    ) -> Dict[str, Dict[str, float]]:
        """Apply layout algorithm to calculate node positions.
        
        Args:
            entities: List of entity dictionaries
            relationships: List of relationship dictionaries
            layout_name: Name of layout algorithm
            
        Returns:
            Dictionary mapping entity IDs to position dicts with 'x' and 'y' keys
        """
        try:
            import networkx as nx
        except ImportError:
            logger.error("NetworkX not installed. Cannot compute layout.")
            return {}
        
        if not entities or not relationships:
            return {}
        
        # Build NetworkX graph
        G = nx.DiGraph()
        
        # Add nodes
        entity_ids = set()
        for entity in entities:
            entity_id = entity.get("id")
            if entity_id:
                entity_ids.add(entity_id)
                G.add_node(
                    entity_id,
                    type=entity.get("type", "UNKNOWN"),
                    label=entity.get("label", ""),
                )
        
        # Add edges (only between existing nodes)
        for rel in relationships:
            source = rel.get("source")
            target = rel.get("target")
            if source in entity_ids and target in entity_ids:
                G.add_edge(
                    source,
                    target,
                    type=rel.get("type", "UNKNOWN"),
                    confidence=rel.get("confidence", 0.0),
                )
        
        if G.number_of_nodes() == 0:
            return {}
        
        # Apply layout algorithm
        try:
            if layout_name == "circular":
                pos = nx.circular_layout(G)
            elif layout_name == "hierarchical":
                # Try to use hierarchical layout, fallback to spring if not available
                try:
                    pos = nx.spring_layout(G, k=2, iterations=50)
                except:
                    pos = nx.spring_layout(G)
            else:  # force-directed (default)
                pos = nx.spring_layout(G, k=2, iterations=50)
        except Exception as e:
            logger.warning(f"Error computing {layout_name} layout, using spring: {e}")
            pos = nx.spring_layout(G)
        
        # Convert to dict format
        positions = {}
        for node_id, (x, y) in pos.items():
            positions[node_id] = {"x": float(x), "y": float(y)}
        
        return positions
    
    def _apply_filters(
        self,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Filter nodes/edges by type, confidence, etc.
        
        Args:
            entities: List of entity dictionaries
            relationships: List of relationship dictionaries
            
        Returns:
            Tuple of (filtered_entities, filtered_relationships)
        """
        # For MVP, return all entities and relationships
        # In a full implementation, apply filters based on self._filters
        filtered_entities = entities
        filtered_relationships = relationships
        
        # Apply confidence threshold if set
        if self._filters.get("confidence_threshold", 0.0) > 0.0:
            threshold = self._filters["confidence_threshold"]
            filtered_relationships = [
                r for r in filtered_relationships
                if r.get("confidence", 0.0) >= threshold
            ]
        
        # Filter relationships to only include those between existing entities
        entity_ids = {e.get("id") for e in filtered_entities}
        filtered_relationships = [
            r for r in filtered_relationships
            if r.get("source") in entity_ids and r.get("target") in entity_ids
        ]
        
        return filtered_entities, filtered_relationships
    
    def _open_url_in_browser(self, url: str) -> bool:
        """Open a URL in the default browser.
        
        Args:
            url: URL to open
            
        Returns:
            True if browser was launched successfully, False otherwise
        """
        # Try common browsers in order of preference
        # Format: (command_name, use_app_mode)
        browsers = [
            # Chromium-based browsers (with app mode for cleaner UI)
            ('chromium-browser', True),
            ('chromium', True),
            ('google-chrome', True),
            ('google-chrome-stable', True),
            # Firefox
            ('firefox', False),
            # Epiphany/GNOME Web
            ('epiphany', False),
            ('epiphany-browser', False),
            # xdg-open as last resort
            ('xdg-open', False),
        ]
        
        for browser_name, use_app_mode in browsers:
            try:
                if use_app_mode:
                    # Chromium browsers support --app flag for app-like experience
                    cmd = [browser_name, f'--app={url}']
                else:
                    cmd = [browser_name, url]
                
                # Try to launch the browser
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                return True
            except (FileNotFoundError, OSError):
                continue
        
        # Fallback to webbrowser module (may not work but worth trying)
        try:
            webbrowser.open(url)
            return True
        except Exception:
            pass
        
        return False
    
    def _find_free_port(self) -> int:
        """Find a free port for the HTTP server."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    async def _serve_html_file(self, html_path: Path) -> Optional[str]:
        """Start a simple HTTP server to serve the HTML file.
        
        Args:
            html_path: Path to the HTML file to serve
            
        Returns:
            URL to access the file, or None if server couldn't be started
        """
        try:
            # Stop any existing server
            if self._http_server:
                self._stop_http_server()
            
            # Change to the directory containing the HTML file
            server_dir = html_path.parent
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
            filename = html_path.name
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
    
    def _generate_and_save_graph(
        self,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> Optional[Path]:
        """Generate Plotly graph HTML and save to file.
        
        Args:
            entities: List of entity dictionaries
            relationships: List of relationship dictionaries
            
        Returns:
            Path to saved HTML file, or None if generation failed
        """
        try:
            import plotly.graph_objects as go
            import networkx as nx
        except ImportError as e:
            logger.error(f"Required libraries not available: {e}")
            return None
        
        if not entities or not relationships:
            logger.warning("Cannot generate graph: no entities or relationships")
            return None
        
        # Compute layout
        positions = self._apply_layout(entities, relationships, self._current_layout)
        if not positions:
            logger.warning("Failed to compute graph layout")
            return None
        
        # Build NetworkX graph for edge computation
        G = nx.DiGraph()
        entity_map = {e.get("id"): e for e in entities}
        for entity in entities:
            entity_id = entity.get("id")
            if entity_id and entity_id in positions:
                G.add_node(entity_id)
        
        for rel in relationships:
            source = rel.get("source")
            target = rel.get("target")
            if source in positions and target in positions:
                G.add_edge(source, target)
        
        # Prepare edge traces
        edge_x = []
        edge_y = []
        edge_info = []
        
        for edge in G.edges():
            source, target = edge
            if source in positions and target in positions:
                x0, y0 = positions[source]["x"], positions[source]["y"]
                x1, y1 = positions[target]["x"], positions[target]["y"]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])
                
                # Find relationship info
                rel_info = next((r for r in relationships if r.get("source") == source and r.get("target") == target), None)
                if rel_info:
                    edge_info.append(f"{rel_info.get('type', 'RELATED')} (conf: {rel_info.get('confidence', 0.0):.2f})")
        
        edge_trace = go.Scatter(
            x=edge_x,
            y=edge_y,
            line=dict(width=1.5, color="#888"),
            hoverinfo="none",
            mode="lines",
            showlegend=False,
        )
        
        # Prepare node traces
        node_x = []
        node_y = []
        node_text = []
        node_colors = []
        node_sizes = []
        
        # Calculate node degrees for sizing
        node_degrees = dict(G.degree())  # type: ignore[operator]
        max_degree = max(node_degrees.values()) if node_degrees else 1
        min_size, max_size = 10, 30
        
        for entity in entities:
            entity_id = entity.get("id")
            if entity_id in positions:
                node_x.append(positions[entity_id]["x"])
                node_y.append(positions[entity_id]["y"])
                
                label = entity.get("label", entity_id)
                entity_type = entity.get("type", "UNKNOWN")
                degree = node_degrees.get(entity_id, 0)
                
                node_text.append(f"{label}<br>Type: {entity_type}<br>Connections: {degree}")
                
                # Color by entity type
                color = self.ENTITY_COLORS.get(entity_type, self.DEFAULT_COLOR)
                node_colors.append(color)
                
                # Size by degree
                if max_degree > 0:
                    size = min_size + (max_size - min_size) * (degree / max_degree)
                else:
                    size = min_size
                node_sizes.append(size)
        
        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            text=[entity.get("label", "") for entity in entities if entity.get("id") in positions],
            textposition="top center",
            textfont=dict(size=10, color="white"),
            hovertext=node_text,
            hoverinfo="text",
            marker=dict(
                size=node_sizes,
                color=node_colors,
                line=dict(width=2, color="white"),
                showscale=False,
            ),
            showlegend=False,
        )
        
        # Create figure
        fig = go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                title=dict(
                    text="Relationship Graph",
                    font=dict(size=20, color="white"),
                ),
                showlegend=False,
                hovermode="closest",
                margin=dict(b=20, l=20, r=20, t=60),
                plot_bgcolor="rgba(10, 10, 20, 1)",
                paper_bgcolor="rgba(10, 10, 20, 1)",
                font=dict(color="white"),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                annotations=[
                    dict(
                        text=f"Nodes: {len(node_x)}, Edges: {len(G.edges())}",
                        showarrow=False,
                        xref="paper",
                        yref="paper",
                        x=0.005,
                        y=-0.002,
                        xanchor="left",
                        yanchor="bottom",
                        font=dict(size=12, color="white"),
                    )
                ],
            ),
        )
        
        # Generate HTML
        html_str = fig.to_html(include_plotlyjs="cdn", config={"displayModeBar": True})
        
        # Save to temporary file
        try:
            project_root = Path(__file__).parent.parent.parent.parent
            output_dir = project_root / "data" / "graph"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            html_path = output_dir / "graph_visualization.html"
            html_path.write_text(html_str, encoding="utf-8")
            
            self._graph_html_path = html_path
            logger.info(f"Graph HTML saved to {html_path}")
            return html_path
        except Exception as e:
            logger.error(f"Error saving graph HTML: {e}")
            return None
