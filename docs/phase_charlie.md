 This is a significant refactor that consolidates the operational aspects of PyScrAI Forge (Project Management, Graphing, and Ingestion) into a single "Command Center" dashboard, while keeping the Intelligence Dashboard separate.

Here is the plan:

1. **`forge/core/app_controller.py`**: Add state for the collapsible AG-UI panel and update navigation items.
2. **`forge/presentation/controllers/dashboard_controller.py`**: Create a new master controller that merges the logic from `Project`, `Graph`, and `Ingest` controllers into a unified view.
3. **`forge/presentation/layouts/shell.py`**: Wire up the new dashboard, implement the collapsible side panel, and update the navigation rail.

### 1. Update App Controller (`forge/core/app_controller.py`)

I will add the `is_agui_expanded` state and update the navigation menu to just "Dashboard" and "Intel".

```python
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from fletx.core import RxBool, RxDict, RxList, RxStr

from .event_bus import EventBus, EventPayload


class AppController:
    """Bridges the EventBus to reactive SDUI state for the application shell."""

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self._event_bus = event_bus or EventBus()

        # Reactive state exposed to the presentation layer
        self.nav_items: RxList[Dict[str, str]] = RxList(
            [
                # MERGED VIEW: Project + Graph + Ingest
                {"id": "dashboard", "label": "Dashboard", "icon": "dashboard"},
                # EXISTING VIEW: Intelligence Dashboard
                {"id": "intel", "label": "Intel", "icon": "psychology"},
            ]
        )
        self.nav_selected: RxStr = RxStr("dashboard")
        self.status_text: RxStr = RxStr("System Initialized…")
        self.ag_feed: RxList[Dict[str, Any]] = RxList([])
        self.workspace_schemas: RxList[Dict[str, Any]] = RxList([])
        self.is_ready: RxBool = RxBool(False)
        
        # New: Collapsible AG-UI Panel State
        self.is_agui_expanded: RxBool = RxBool(True)

        # Internal flag to prevent duplicate subscriptions
        self._started = False

    @property
    def bus(self) -> EventBus:
        return self._event_bus

    async def start(self) -> None:
        """Wire bus subscriptions once."""
        if self._started:
            return

        await self._event_bus.subscribe("agui.event", self._handle_agui_event)
        await self._event_bus.subscribe("workspace.schema", self._handle_workspace_schema)
        await self._event_bus.subscribe("status.text", self._handle_status_text)
        await self._event_bus.subscribe("nav.select", self._handle_nav_select)

        self._started = True
        self.is_ready.value = True

    async def publish(self, topic: str, payload: EventPayload) -> None:
        """Publish through the shared bus."""
        await self._event_bus.publish(topic, payload)

    async def _handle_agui_event(self, payload: EventPayload) -> None:
        entry = {
            "ts": payload.get("ts", time.time()),
            "level": payload.get("level", "info"),
            "message": payload.get("message", ""),
            "topic": payload.get("topic"),
        }
        self.ag_feed.append(entry)
        # Keep the feed lightweight
        if len(self.ag_feed) > 200:
            self.ag_feed.value = self.ag_feed.value[-200:]

    async def _handle_workspace_schema(self, payload: EventPayload) -> None:
        schema = payload.get("schema")
        if schema:
            self.workspace_schemas.append(schema)

    async def _handle_status_text(self, payload: EventPayload) -> None:
        text = payload.get("text")
        if text:
            self.status_text.value = str(text)

    async def _handle_nav_select(self, payload: EventPayload) -> None:
        selection = payload.get("id")
        if selection:
            self.nav_selected.value = str(selection)

    async def raise_user_action(self, action: str, payload: Optional[EventPayload] = None) -> None:
        """Helper for UI to push user intent into the bus."""
        await self.publish("user.action", {"action": action, **(payload or {})})

    async def emit_schema(self, schema: Dict[str, Any]) -> None:
        """Convenience for domain services to add SDUI components."""
        await self.publish("workspace.schema", {"schema": schema})

    async def push_status(self, text: str) -> None:
        await self.publish("status.text", {"text": text})

    async def push_agui_log(self, message: str, level: str = "info") -> None:
        await self.publish(
            "agui.event",
            {"message": message, "level": level, "ts": time.time()},
        )
    
    def toggle_agui(self) -> None:
        """Toggle the visibility of the AG-UI feed panel."""
        self.is_agui_expanded.value = not self.is_agui_expanded.value

    def clear_workspace(self) -> None:
        """Synchronous helper to reset schemas."""
        self.workspace_schemas.clear()

    def clear_feed(self) -> None:
        self.ag_feed.clear()

    def set_nav_items(self, items: List[Dict[str, str]]) -> None:
        self.nav_items.value = items

    def set_nav_selected(self, nav_id: str) -> None:
        self.nav_selected.value = nav_id

    def ready(self) -> None:
        """Mark controller ready for the UI."""
        self.is_ready.value = True

    def close(self) -> None:
        """Teardown any local state if needed later."""
        self.clear_feed()
        self.workspace_schemas.clear()

```

### 2. Create Dashboard Controller (`forge/presentation/controllers/dashboard_controller.py`)

This file merges the logic from `ProjectController`, `IngestController`, and `GraphController`.

```python
"""
Dashboard Controller - Unified Command Center.
Merges Project Management, Graph View, and Document Ingest.
"""

from __future__ import annotations

import asyncio
import logging
import os
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
            bgcolor="rgba(255,255,255,0.03)",
            border_radius=10,
            padding=10,
            content=ft.Row(
                [
                    ft.Row([
                        ft.Icon(ft.Icons.DASHBOARD, color=ft.Colors.CYAN_400),
                        ft.Text("Mission Control", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ], spacing=10),
                    
                    ft.Container(expand=True),  # Spacer
                    
                    ft.IconButton(
                        icon=ft.Icons.FOLDER_OPEN, tooltip="Open Project",
                        icon_color=ft.Colors.BLUE_400,
                        on_click=lambda e: asyncio.create_task(on_open(e))
                    ),
                    ft.IconButton(
                        icon=ft.Icons.SAVE, tooltip="Save Project",
                        icon_color=ft.Colors.GREEN_400,
                        on_click=lambda e: asyncio.create_task(on_save(e))
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_FOREVER, tooltip="Reset Session",
                        icon_color=ft.Colors.RED_400,
                        on_click=lambda e: asyncio.create_task(on_reset(e))
                    ),
                    ft.IconButton(
                        icon=ft.Icons.SETTINGS, tooltip="Settings",
                        icon_color=ft.Colors.WHITE54,
                        # on_click config handler if needed
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
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
        
        status_text = ft.Text("Ready", size=12, color=ft.Colors.WHITE54)

        async def on_process(e):
            text = doc_input.value
            if not text: return
            
            self._doc_counter += 1
            doc_id = f"doc_{self._doc_counter:04d}"
            
            status_text.value = f"Processing {doc_id}..."
            self.page.update()
            
            await self.app_controller.publish(
                events.TOPIC_DATA_INGESTED,
                events.create_data_ingested_event(doc_id, text.strip())
            )
            
            doc_input.value = ""
            status_text.value = f"✅ Ingested {doc_id}"
            await self.app_controller.push_agui_log(f"Ingested {doc_id}", "info")
            self.page.update()

        return ft.Column(
            [
                ft.Row([
                    ft.Icon(ft.Icons.DESCRIPTION, size=16, color=ft.Colors.CYAN_200),
                    ft.Text("Document Ingest", weight=ft.FontWeight.W_600, color=ft.Colors.CYAN_100),
                ]),
                ft.Container(
                    content=doc_input,
                    expand=True,  # Fill vertical space
                ),
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "Process Intelligence",
                            icon=ft.Icons.AUTO_AWESOME,
                            bgcolor=ft.Colors.CYAN_700,
                            color=ft.Colors.WHITE,
                            on_click=lambda e: asyncio.create_task(on_process(e))
                        ),
                        ft.Container(width=10),
                        status_text,
                    ]
                )
            ],
            expand=True,
            spacing=10
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
            if not has_data: return
            # Generate and open
            html_path = self._generate_graph_html(entities, relationships)
            if html_path:
                url = await self._serve_html(html_path)
                if url:
                    self._open_browser(url)
                    await self.app_controller.push_agui_log("Graph opened in browser", "success")

        # Stats Cards
        def _stat_card(label, value, icon, color):
            return ft.Container(
                bgcolor="rgba(255,255,255,0.05)",
                padding=10, border_radius=5, expand=True,
                content=ft.Column([
                    ft.Icon(icon, color=color, size=16),
                    ft.Text(str(value), size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ft.Text(label, size=10, color=ft.Colors.WHITE54)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            )

        return ft.Column(
            [
                ft.Row([
                    ft.Icon(ft.Icons.HUB, size=16, color=ft.Colors.PURPLE_200),
                    ft.Text("Knowledge Graph", weight=ft.FontWeight.W_600, color=ft.Colors.PURPLE_100),
                ]),
                
                ft.Row([
                    _stat_card("Entities", e_count, ft.Icons.CIRCLE, ft.Colors.BLUE_400),
                    _stat_card("Relations", r_count, ft.Icons.SHARE, ft.Colors.GREEN_400),
                ]),
                
                ft.Container(height=10),
                
                ft.Dropdown(
                    label="Layout", value=self._current_layout,
                    options=[
                        ft.dropdown.Option("force-directed"),
                        ft.dropdown.Option("circular"),
                    ],
                    text_size=12, height=40, content_padding=5,
                    border_color="rgba(255,255,255,0.2)",
                    on_change=lambda e: setattr(self, "_current_layout", e.control.value)
                ),
                
                ft.Container(height=5),
                
                ft.ElevatedButton(
                    "View Interactive Graph",
                    icon=ft.Icons.OPEN_IN_BROWSER,
                    bgcolor=ft.Colors.PURPLE_700,
                    color=ft.Colors.WHITE,
                    width=200, # Full width
                    disabled=not has_data,
                    on_click=lambda e: asyncio.create_task(on_view_graph(e))
                ),
                
                ft.Text(
                    "Visualize connections in browser.",
                    size=11, color=ft.Colors.WHITE30, italic=True
                )
            ],
            spacing=10
        )

    # --- Graph Helpers (Ported from GraphController) ---
    
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

        # Save
        path = Path("data/graph/visualization.html")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(fig.to_html(include_plotlyjs='cdn', full_html=True), encoding='utf-8')
        return path

    async def _serve_html(self, path: Path) -> str:
        # Simple one-shot HTTP server setup (reusing logic from GraphController)
        if self._http_server:
            try: self._http_server.shutdown()
            except: pass
            
        port = 0
        with socket.socket() as s:
            s.bind(('', 0)); port = s.getsockname()[1]

        def run():
            handler = SimpleHTTPRequestHandler
            # Bind directory to handler in a clean way if needed, or just use chdir context
            # For simplicity, we serve from the file's dir
            os.chdir(path.parent) 
            server = HTTPServer(('127.0.0.1', port), handler)
            self._http_server = server
            try: server.serve_forever()
            except: pass

        self._http_server_thread = threading.Thread(target=run, daemon=True)
        self._http_server_thread.start()
        await asyncio.sleep(0.5)
        return f"http://127.0.0.1:{port}/{path.name}"

    def _open_browser(self, url):
        webbrowser.open(url)

```

### 3. Update Shell Layout (`forge/presentation/layouts/shell.py`)

I will update the shell to use the new `DashboardController` and implement the collapsible right panel.

```python
from __future__ import annotations

from typing import List, Optional

import flet as ft

from forge.core.app_controller import AppController
from forge.core.service_registry import get_session_manager
from forge.presentation.renderer import render_schema
# Import the new DashboardController
from forge.presentation.controllers.dashboard_controller import DashboardController


def apply_shell_theme(page: ft.Page) -> None:
    """Apply a dark, high-contrast baseline theme."""
    page.theme = ft.Theme(
        font_family="Space Grotesk",
        color_scheme_seed="#48b0f7",
        visual_density=ft.VisualDensity.COMPACT,
        use_material3=True,
    )
    page.bgcolor = ft.Colors.BLACK
    page.padding = 0


def _nav_destinations(items: List[dict]) -> List[ft.NavigationRailDestination]:
    destinations: List[ft.NavigationRailDestination] = []
    for item in items:
        icon_name = str(item.get("icon", "dashboard")).upper()
        icon = getattr(ft.Icons, icon_name, ft.Icons.DASHBOARD)
        destinations.append(
            ft.NavigationRailDestination(icon=icon, label=item.get("label", ""))
        )
    return destinations


def build_shell(page: ft.Page, controller: AppController) -> ft.View:
    apply_shell_theme(page)

    # Initialize the new Dashboard Controller
    dashboard_controller = DashboardController(controller, page)

    # --- UI primitives ---
    nav_rail = ft.NavigationRail(
        label_type=ft.NavigationRailLabelType.ALL,
        bgcolor="#080b31",  # Dark blue accent
        indicator_color=ft.Colors.BLUE_400,
        min_width=80,
        min_extended_width=180,
        destinations=_nav_destinations(controller.nav_items.value),
        selected_index=0,
    )

    status_text = ft.Text(controller.status_text.value, color=ft.Colors.WHITE70)

    # AG-UI Feed List
    ag_feed = ft.ListView(spacing=8, auto_scroll=True)

    # Main Content Container
    content_container = ft.Container(
        expand=True,
        content=dashboard_controller.build_view(),  # Default to unified dashboard
    )

    # Intelligence Workspace (Scrollable)
    workspace = ft.Column(
        controls=[ft.Text("Awaiting Intel", color=ft.Colors.WHITE70)],
        scroll=ft.ScrollMode.AUTO,
        spacing=12,
    )

    # --- State Sync Handlers ---

    def _sync_nav() -> None:
        nav_rail.destinations = _nav_destinations(controller.nav_items.value)
        ids = [item.get("id") for item in controller.nav_items.value]
        if controller.nav_selected.value in ids:
            nav_rail.selected_index = ids.index(controller.nav_selected.value)
        page.update()

    def _sync_status() -> None:
        status_text.value = controller.status_text.value
        page.update()

    def _sync_feed() -> None:
        ag_feed.controls = [
            ft.Row(
                [
                    ft.Text(entry.get("level", "info").upper(), color=ft.Colors.AMBER_200, size=10, width=40),
                    ft.Text(entry.get("message", ""), color=ft.Colors.WHITE, size=12, expand=True),
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
            for entry in controller.ag_feed.value
        ]
        page.update()

    def _sync_agui_panel() -> None:
        # Toggle visibility/width based on state
        ag_panel_container.visible = controller.is_agui_expanded.value
        page.update()

    def _sync_workspace() -> None:
        if not controller.workspace_schemas.value:
            workspace.controls = [ft.Text("Awaiting Intel", color=ft.Colors.WHITE70)]
        else:
            rendered_components: List[ft.Control] = []
            for schema in controller.workspace_schemas.value:
                try:
                    component = render_schema(schema)
                    rendered_components.append(component)
                except Exception as e:
                    rendered_components.append(
                        ft.Container(
                            bgcolor="rgba(255,0,0,0.1)",
                            padding=12, border_radius=8,
                            content=ft.Text(f"Render error: {str(e)}", color=ft.Colors.RED_300),
                        )
                    )
            workspace.controls = rendered_components
        page.update()

    # --- Navigation Logic ---

    def _on_nav_change(e: ft.ControlEvent) -> None:
        rail = e.control
        if hasattr(rail, 'selected_index'):
            idx = rail.selected_index
            items = controller.nav_items.value
            if 0 <= idx < len(items):
                nav_id = items[idx].get("id", "")
                controller.set_nav_selected(nav_id)
                
                # Switch Views
                if nav_id == "dashboard":
                    # Rebuild dashboard to refresh stats
                    content_container.content = dashboard_controller.build_view()
                
                elif nav_id == "intel":
                    # Show Intelligence Dashboard (Workspace)
                    content_container.content = ft.Container(
                        padding=20,
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.PSYCHOLOGY, size=32, color=ft.Colors.CYAN_300),
                                ft.Text("Intelligence Dashboard", size=24, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
                            ], spacing=12),
                            ft.Divider(color="rgba(255, 255, 255, 0.1)"),
                            workspace,
                        ], spacing=12, scroll=ft.ScrollMode.AUTO)
                    )
        page.update()

    nav_rail.on_change = _on_nav_change

    # --- Listener Bindings ---
    controller.nav_items.listen(_sync_nav)
    controller.nav_selected.listen(_sync_nav)
    controller.status_text.listen(_sync_status)
    controller.ag_feed.listen(_sync_feed)
    controller.workspace_schemas.listen(_sync_workspace)
    controller.is_agui_expanded.listen(_sync_agui_panel)

    # --- Collapsible Panel Definition ---
    ag_panel_container = ft.Container(
        width=300, # Fixed width when open
        padding=12,
        bgcolor="rgba(255,255,255,0.06)",
        border_radius=12,
        animate_opacity=300, # Fade effect
        content=ft.Column(
            [
                ft.Row([
                    ft.Text("AG-UI Feed", weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
                    ft.IconButton(ft.Icons.CLOSE, icon_size=16, on_click=lambda e: controller.toggle_agui())
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(color="rgba(255,255,255,0.1)"),
                ag_feed,
            ],
            spacing=8,
        ),
    )

    # --- Main Layout ---
    chrome = ft.Container(
        expand=True,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=["#0b1224", "#0a0f1c", "#05080f"],
        ),
        content=ft.Row(
            [
                nav_rail,
                ft.VerticalDivider(width=1, color="rgba(255,255,255,0.1)"),
                ft.Container(
                    expand=True,
                    padding=16,
                    content=ft.Column(
                        [
                            # Header Bar
                            ft.Row(
                                [
                                    ft.Row([
                                        ft.Text("PyScrAI Forge", size=18, weight=ft.FontWeight.W_700, color=ft.Colors.WHITE),
                                        status_text,
                                    ], spacing=20),
                                    
                                    # Toggle Button for AG-UI
                                    ft.IconButton(
                                        icon=ft.Icons.VIEW_SIDEBAR,
                                        tooltip="Toggle AG-UI Feed",
                                        icon_color=ft.Colors.CYAN_200,
                                        on_click=lambda e: controller.toggle_agui()
                                    )
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Container(height=8),
                            
                            # Content Area + Right Panel
                            ft.Row(
                                [
                                    ft.Container(
                                        expand=True, # Takes remaining space
                                        content=content_container,
                                        padding=0,
                                        bgcolor="rgba(255,255,255,0.04)",
                                        border_radius=12,
                                    ),
                                    
                                    # The collapsible panel
                                    ag_panel_container, 
                                ],
                                expand=True,
                                spacing=12,
                            ),
                        ],
                        spacing=12,
                    ),
                ),
            ],
            expand=True,
        ),
    )

    # Initial Sync
    _sync_nav()
    _sync_status()
    _sync_feed()
    _sync_workspace()
    _sync_agui_panel()

    return ft.View(
        route="/",
        controls=[chrome],
        bgcolor=ft.Colors.BLACK,
        padding=0,
    )

```

These changes implement the requested unified dashboard layout and the collapsible AG-UI panel while maintaining all existing functionality.