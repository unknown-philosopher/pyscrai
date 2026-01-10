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

from forge.legacy_nicegui.state import get_ui_context, is_project_loaded, set_active_page
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

# CSS is now loaded from external file

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
    """Inject custom CSS from external file into the page."""
    from pathlib import Path
    
    css_path = Path(__file__).parent / "static" / "style.css"
    if css_path.exists():
        css_content = css_path.read_text(encoding="utf-8")
        ui.add_head_html(f"<style>{css_content}</style>")
    else:
        logger.warning(f"CSS file not found at {css_path}")


def create_header(sidebar: ui.element | None = None, assistant_drawer: ui.element | None = None) -> None:
    """Create the intelligence platform header bar.
    
    Args:
        sidebar: Optional sidebar element to toggle when clicking PyScrAI logo
        assistant_drawer: Optional assistant drawer element to toggle
    """
    from forge.legacy_nicegui.state import get_session
    
    with ui.header().classes("forge-header items-center px-4 py-2"):
        # Logo - clickable to toggle sidebar
        with ui.element("div").classes("flex items-center cursor-pointer").style(
            "user-select: none;"
        ).on("click", lambda: sidebar.toggle() if sidebar else None):
            ui.html('<span class="mono" style="color: #00b8d4; font-weight: 600; font-size: 1.1rem;">PyScrAI</span>', sanitize=False)
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
        with ui.row().classes("gap-2 items-center"):
            # Assistant button removed - now in drawer header
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
            # System nav section
            ui.html('<div class="section-label px-4 pt-4">SYSTEM NAV</div>', sanitize=False)
            
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
    from forge.legacy_nicegui.components.assistant import AssistantPanel
    
    with ui.right_drawer(value=False).classes("forge-sidebar p-0").props("width=380 bordered") as drawer:
        # Assistant panel content
        AssistantPanel()
    
    # Toggle button - fixed position relative to viewport (top-right, same location as drawer controls)
    # Positioned absolutely so it stays in place whether drawer is open or closed
    # This replaces the native x/- controls
    with ui.element("div").classes("fixed").style(
        "top: 8px; right: 8px; z-index: 1001;"
    ):
        with ui.button(color="amber").props("round dense size=sm").on(
            "click", drawer.toggle
        ) as btn:
            ui.html('<span style="font-size: 12px;">⌘</span>', sanitize=False)
            btn.tooltip("Toggle AI Assistant")
    
    return drawer


def create_footer() -> None:
    """Create the status bar footer."""
    from forge.legacy_nicegui.state import get_session, is_project_loaded
    
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
    
    # Create layout components - order matters for header references
    sidebar = create_sidebar(active_page)
    assistant_drawer = create_assistant_drawer()
    create_header(sidebar=sidebar, assistant_drawer=assistant_drawer)
    create_footer()
    
    # Main content area
    with ui.column().classes("p-6 w-full"):
        content_fn()
