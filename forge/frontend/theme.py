"""
Forge Frontend Theme and Layout.

Intelligence Platform aesthetic with:
- Left sidebar: Collapsible navigation with phase list
- Header: Menu bar with status indicators
- Right drawer: Terminal-style AI Assistant
- Main content: Dark theme, monospace fonts, minimal icons
- Footer: Status bar with connection info
"""

from __future__ import annotations

from typing import Callable

from nicegui import ui

from forge.frontend.state import get_ui_context, is_project_loaded, set_active_page
from forge.utils.logging import get_logger

logger = get_logger("frontend.theme")


def html(content: str) -> None:
    """Render raw HTML with sanitization disabled.
    
    Wrapper around ui.html() that sets sanitize=False for trusted content.
    Use only with hardcoded/trusted HTML strings.
    """
    ui.html(content, sanitize=False)


# Color palette - Intelligence Platform
COLORS = {
    "bg_dark": "#0a0a0a",
    "bg_panel": "#111111",
    "bg_card": "#1a1a1a",
    "bg_hover": "#222222",
    "accent": "#00b8d4",  # Cyan
    "accent_dim": "#006d80",
    "text": "#e0e0e0",
    "text_dim": "#888888",
    "success": "#00c853",
    "warning": "#ffab00",
    "error": "#ff5252",
    "critical": "#ff1744",
}

# Custom CSS for intelligence platform aesthetic
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600&family=Inter:wght@300;400;500;600&display=swap');
    
    :root {
        --forge-bg: #0a0a0a;
        --forge-panel: #111111;
        --forge-card: #1a1a1a;
        --forge-accent: #00b8d4;
        --forge-accent-dim: #006d80;
        --forge-text: #e0e0e0;
        --forge-text-dim: #888888;
    }
    
    body {
        font-family: 'Inter', -apple-system, sans-serif !important;
        background: var(--forge-bg) !important;
    }
    
    .mono {
        font-family: 'JetBrains Mono', 'Consolas', monospace !important;
    }
    
    .forge-header {
        background: var(--forge-panel) !important;
        border-bottom: 1px solid #333 !important;
    }
    
    .forge-sidebar {
        background: var(--forge-panel) !important;
        border-right: 1px solid #333 !important;
    }
    
    .forge-card {
        background: var(--forge-card) !important;
        border: 1px solid #333 !important;
        border-radius: 4px !important;
    }
    
    .forge-nav-item {
        color: var(--forge-text-dim) !important;
        transition: all 0.15s ease !important;
        border-left: 2px solid transparent !important;
        padding: 8px 16px !important;
    }
    
    .forge-nav-item:hover {
        background: rgba(0, 184, 212, 0.1) !important;
        color: var(--forge-text) !important;
    }
    
    .forge-nav-item.active {
        background: rgba(0, 184, 212, 0.15) !important;
        border-left-color: var(--forge-accent) !important;
        color: var(--forge-accent) !important;
    }
    
    .forge-stat-value {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 2rem !important;
        font-weight: 600 !important;
        color: var(--forge-text) !important;
    }
    
    .forge-badge {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.7rem !important;
        padding: 2px 8px !important;
        border-radius: 2px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }
    
    .forge-badge-online { background: #00c853 !important; color: #000 !important; }
    .forge-badge-active { background: #00b8d4 !important; color: #000 !important; }
    .forge-badge-critical { background: #ff1744 !important; color: #fff !important; }
    .forge-badge-high { background: #ff5252 !important; color: #fff !important; }
    .forge-badge-info { background: #00b8d4 !important; color: #000 !important; }
    
    .forge-terminal {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.8rem !important;
        line-height: 1.5 !important;
        background: #0d0d0d !important;
        color: var(--forge-text-dim) !important;
    }
    
    .forge-input {
        background: #1a1a1a !important;
        border: 1px solid #333 !important;
        color: var(--forge-text) !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    .forge-input:focus {
        border-color: var(--forge-accent) !important;
    }
    
    .forge-btn {
        background: transparent !important;
        border: 1px solid #444 !important;
        color: var(--forge-text-dim) !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.75rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        transition: all 0.15s ease !important;
    }
    
    .forge-btn:hover {
        border-color: var(--forge-accent) !important;
        color: var(--forge-accent) !important;
    }
    
    .forge-btn-primary {
        background: var(--forge-accent) !important;
        border-color: var(--forge-accent) !important;
        color: #000 !important;
    }
    
    .forge-btn-primary:hover {
        background: #00d4f5 !important;
        color: #000 !important;
    }
    
    .section-label {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.65rem !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        color: var(--forge-text-dim) !important;
        margin-bottom: 8px !important;
    }
    
    .forge-footer {
        background: var(--forge-panel) !important;
        border-top: 1px solid #333 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.7rem !important;
        color: var(--forge-text-dim) !important;
    }
</style>
"""

# Pipeline phases - text labels, no emojis
PHASES = [
    {"id": "overview", "num": "", "label": "OVERVIEW", "route": "/dashboard"},
    {"id": "osint", "num": "01", "label": "OSINT", "route": "/osint", "desc": "Extraction"},
    {"id": "humint", "num": "02", "label": "HUMINT", "route": "/humint", "desc": "Entities"},
    {"id": "sigint", "num": "03", "label": "SIGINT", "route": "/sigint", "desc": "Relationships"},
    {"id": "synth", "num": "04", "label": "SYNTH", "route": "/synth", "desc": "Narrative"},  
    {"id": "geoint", "num": "05", "label": "GEOINT", "route": "/geoint", "desc": "Cartography"},
    {"id": "finint", "num": "06", "label": "FININT", "route": "/anvil", "desc": "Finalize"},
]


def inject_styles() -> None:
    """Inject custom CSS into the page."""
    ui.add_head_html(CUSTOM_CSS)


def create_header() -> None:
    """Create the intelligence platform header bar."""
    from forge.frontend.state import get_session
    
    with ui.header().classes("forge-header items-center px-4 py-2"):
        # Logo - simple text, no icons
        ui.html('<span class="mono" style="color: #00b8d4; font-weight: 600; font-size: 1.1rem;">PYSCRAI</span>', sanitize=False)
        ui.html('<span class="mono" style="color: #666; margin: 0 4px;">|</span>', sanitize=False)
        ui.html('<span class="mono" style="color: #888; font-size: 0.9rem;">FORGE</span>', sanitize=False)
        
        # Menu items (placeholders - to be implemented)
        with ui.row().classes("ml-8 gap-4"):
            for item in ["FILE", "VIEW", "DB", "TOOLS"]:
                with ui.element("span").classes("mono").style(
                    "color: #888; font-size: 0.75rem; cursor: pointer; letter-spacing: 0.5px;"
                ).on("click", lambda i=item: ui.notify(f"{i} menu - Coming soon", type="info")):
                    ui.label(item)
        
        ui.space()
        
        # Right side controls
        with ui.row().classes("gap-2"):
            with ui.element("span").classes("mono forge-btn px-3 py-1").style(
                "cursor: pointer;"
            ).on("click", lambda: ui.notify("Config panel - Coming soon", type="info")):
                ui.label("[CONFIG]")
            with ui.element("span").classes("mono forge-btn px-3 py-1").style(
                "cursor: pointer;"
            ).on("click", lambda: ui.notify("Alerts panel - Coming soon", type="info")):
                ui.label("[ALERTS]")


def create_sidebar(active_page: str, collapsed: bool = False) -> ui.element:
    """Create the collapsible navigation sidebar.
    
    Args:
        active_page: Currently active page ID for highlighting
        collapsed: Whether sidebar starts collapsed
    """
    sidebar_width = "60px" if collapsed else "200px"
    
    with ui.left_drawer(value=True).classes("forge-sidebar p-0").props(f"width={200} bordered") as sidebar:
        with ui.column().classes("w-full h-full"):
            # Collapse button at top
            with ui.element("div").classes("px-4 pt-3 pb-2"):
                with ui.element("span").classes(
                    "mono forge-btn px-2 py-1 text-center block"
                ).style("cursor: pointer; font-size: 0.7rem;").on("click", lambda s=sidebar: s.toggle()):
                    ui.label("<< COLLAPSE")
            
            # System nav section
            ui.html('<div class="section-label px-4 pt-2">SYSTEM NAV</div>', sanitize=False)
            
            # Overview item
            overview = PHASES[0]
            is_overview_active = active_page in ["dashboard", "overview", "landing"]
            with ui.element("div").classes(
                f"forge-nav-item cursor-pointer {'active' if is_overview_active else ''}"
            ).on("click", lambda: ui.navigate.to("/dashboard")):
                ui.html(f'<span class="mono" style="font-size: 0.85rem;">{overview["label"]}</span>', sanitize=False)
            
            # Projects item
            with ui.element("div").classes(
                f"forge-nav-item cursor-pointer {'active' if active_page == 'landing' else ''}"
            ).style("padding-left: 24px !important").on("click", lambda: ui.navigate.to("/")):
                ui.html('<span class="mono" style="font-size: 0.8rem; color: #666;">› PROJECTS</span>', sanitize=False)
            
            # Pipeline phases section
            ui.html('<div class="section-label px-4 pt-6">PIPELINE PHASES</div>', sanitize=False)
            
            for phase in PHASES[1:]:  # Skip overview
                is_active = active_page == phase["id"] or (phase["id"] == "finint" and active_page == "anvil")
                with ui.element("div").classes(
                    f"forge-nav-item cursor-pointer {'active' if is_active else ''}"
                ).on("click", lambda r=phase["route"]: ui.navigate.to(r)):
                    with ui.row().classes("items-center gap-2"):
                        ui.html(f'<span class="mono" style="color: #555; font-size: 0.7rem;">{phase["num"]}</span>', sanitize=False)
                        ui.html(f'<span class="mono" style="font-size: 0.85rem;">{phase["label"]}</span>', sanitize=False)
            
            ui.space()
    
    return sidebar


def create_assistant_drawer() -> ui.element:
    """Create the right drawer containing the terminal-style AI Assistant."""
    from forge.frontend.components.assistant import AssistantPanel
    
    with ui.right_drawer(value=False).classes("forge-sidebar p-0").props("width=380 bordered") as drawer:
        AssistantPanel()
    
    return drawer


def create_footer() -> None:
    """Create the status bar footer."""
    from forge.frontend.state import get_session, is_project_loaded
    
    with ui.footer().classes("forge-footer px-4 py-2 items-center"):
        # Project info
        if is_project_loaded():
            try:
                session = get_session()
                if session.project:
                    ui.html(f'<span class="mono">PROJECT: <span style="color: #00b8d4;">{session.project.name.upper()}</span></span>', sanitize=False)
                    ui.html('<span class="mono mx-4" style="color: #333;">|</span>', sanitize=False)
                    stats = session.get_stats()
                    entity_count = stats.get("entity_count", 0)
                    rel_count = stats.get("relationship_count", 0)
                    ui.html(f'<span class="mono">DB: {entity_count} ENTITIES, {rel_count} RELATIONSHIPS</span>', sanitize=False)
            except Exception:
                ui.html('<span class="mono">PROJECT: NONE</span>', sanitize=False)
        else:
            ui.html('<span class="mono">PROJECT: NONE</span>', sanitize=False)
        
        ui.space()
        
        # Connection status
        ui.html('<span style="display: inline-block; width: 6px; height: 6px; background: #00c853; border-radius: 50%; margin-right: 6px;"></span>', sanitize=False)
        ui.html('<span class="mono" style="color: #00c853;">CONNECTED</span>', sanitize=False)
        
        ui.html('<span class="mono mx-4" style="color: #333;">|</span>', sanitize=False)
        ui.html('<span class="mono">v.3.0.1</span>', sanitize=False)


def create_layout(
    content_fn: Callable[[], None],
    active_page: str = "dashboard",
) -> None:
    """Create the full application layout with intelligence platform styling.
    
    Args:
        content_fn: Function that renders the page-specific content
        active_page: ID of the currently active page for nav highlighting
    """
    # Update UI context
    set_active_page(active_page)
    
    # Inject custom styles
    inject_styles()
    
    # Apply dark theme base
    ui.query("body").style(f"background: {COLORS['bg_dark']} !important")
    
    # Create layout components
    create_header()
    create_sidebar(active_page)
    assistant_drawer = create_assistant_drawer()
    create_footer()
    
    # Floating assistant toggle button (minimal style)
    with ui.page_sticky(position="bottom-right", x_offset=20, y_offset=80):
        with ui.button(color="cyan").props("fab-mini").on("click", assistant_drawer.toggle) as btn:
            ui.html('<span style="font-size: 16px;">⌘</span>', sanitize=False)
            btn.tooltip("AI Assistant")
    
    # Main content area
    with ui.column().classes("p-6 w-full"):
        content_fn()
