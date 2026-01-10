"""
Theme System - Tactical Dark Mode.

Intelligence Platform aesthetic with tactical dark theme.
"""

from __future__ import annotations

from typing import Any

import flet as ft

# ============================================================================
# Color Palette - Intelligence Platform
# ============================================================================

COLORS = {
    "bg_dark": "#0a0a0a",
    "bg_panel": "#111111",
    "bg_card": "#1a1a1a",
    "bg_hover": "#222222",
    "accent": "#00b8d4",  # Cyan
    "accent_dim": "#006d80",
    "text": "#e0e0e0",
    "text_dim": "#888888",
    "text_muted": "#555555",
    "success": "#00c853",
    "warning": "#ffab00",
    "error": "#ff5252",
    "critical": "#ff1744",
    "border": "#333333",
    "border_light": "#444444",
}

# Pipeline phases - text labels
PHASES = [
    {"id": "overview", "num": "", "label": "OVERVIEW", "route": "/dashboard", "icon": "dashboard"},
    {"id": "osint", "num": "01", "label": "OSINT", "route": "/osint", "desc": "Extraction", "icon": "search"},
    {"id": "humint", "num": "02", "label": "HUMINT", "route": "/humint", "desc": "Entities", "icon": "people"},
    {"id": "sigint", "num": "03", "label": "SIGINT", "route": "/sigint", "desc": "Relationships", "icon": "hub"},
    {"id": "synth", "num": "04", "label": "SYNTH", "route": "/synth", "desc": "Narrative", "icon": "description"},
    {"id": "geoint", "num": "05", "label": "GEOINT", "route": "/geoint", "desc": "Cartography", "icon": "map"},
    {"id": "finint", "num": "06", "label": "FININT", "route": "/anvil", "desc": "Finalize", "icon": "check_circle"},
]


# ============================================================================
# Theme Configuration
# ============================================================================

def get_theme() -> ft.Theme:
    """Get the tactical dark theme for Flet.
    
    Returns:
        Configured Flet Theme object
    """
    return ft.Theme(
        color_scheme_seed=COLORS["accent"],
        color_scheme=ft.ColorScheme(
            primary=COLORS["accent"],
            on_primary="#000000",
            secondary=COLORS["accent_dim"],
            surface=COLORS["bg_panel"],
            on_surface=COLORS["text"],
            error=COLORS["error"],
            on_error="#ffffff",
        ),
        text_theme=ft.TextTheme(
            body_large=ft.TextStyle(
                font_family="Inter",
                color=COLORS["text"],
            ),
            body_medium=ft.TextStyle(
                font_family="Inter",
                color=COLORS["text"],
            ),
            label_large=ft.TextStyle(
                font_family="JetBrains Mono",
                color=COLORS["text"],
            ),
        ),
    )


# ============================================================================
# Reusable Style Functions
# ============================================================================

def mono_text(
    text: str,
    size: float = 12,
    color: str | None = None,
    weight: ft.FontWeight = ft.FontWeight.NORMAL,
) -> ft.Text:
    """Create monospace text with JetBrains Mono font.
    
    Args:
        text: Text content
        size: Font size in pixels
        color: Text color (defaults to text color)
        weight: Font weight
        
    Returns:
        Styled Text widget
    """
    return ft.Text(
        text,
        font_family="JetBrains Mono",
        size=size,
        color=color or COLORS["text"],
        weight=weight,
    )


def mono_label(
    label: str,
    size: float = 10,
    color: str | None = None,
) -> ft.Text:
    """Create uppercase monospace label (section headers).
    
    Args:
        label: Label text
        size: Font size in pixels
        color: Text color (defaults to dim text)
        
    Returns:
        Styled Text widget
    """
    return mono_text(
        label.upper(),
        size=size,
        color=color or COLORS["text_dim"],
    )


def forge_card(
    content: list[ft.Control] | ft.Control | None = None,
    padding: int = 16,
    **kwargs: Any,
) -> ft.Container:
    """Create a forge-styled card container.
    
    Args:
        content: Card content (Control or list of Controls)
        padding: Internal padding
        **kwargs: Additional Container properties
        
    Returns:
        Styled Container widget
    """
    return ft.Container(
        content=content,
        bgcolor=COLORS["bg_card"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=4,
        padding=padding,
        **kwargs,
    )


def forge_button(
    text: str,
    on_click: Any = None,
    primary: bool = False,
    icon: str | None = None,
    **kwargs: Any,
) -> ft.ElevatedButton:
    """Create a forge-styled button.
    
    Args:
        text: Button text
        on_click: Click handler
        primary: Use primary (accent) styling
        icon: Optional icon name
        **kwargs: Additional ElevatedButton properties
        
    Returns:
        Styled ElevatedButton widget
    """
    bgcolor = COLORS["accent"] if primary else None
    color = "#000000" if primary else COLORS["text_dim"]
    border_color = COLORS["accent"] if primary else COLORS["border_light"]
    
    return ft.ElevatedButton(
        content=text.upper(),
        icon=icon,
        on_click=on_click,
        bgcolor=bgcolor,
        color=color,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=4),
            side=ft.BorderSide(1, border_color),
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
        ),
        **kwargs,
    )


def forge_badge(
    text: str,
    severity: str = "info",
) -> ft.Container:
    """Create a forge-styled badge.
    
    Args:
        text: Badge text
        severity: Badge severity (info, success, warning, error, active)
        
    Returns:
        Styled Container widget
    """
    severity_colors = {
        "info": (COLORS["accent"], "#000000"),
        "success": (COLORS["success"], "#000000"),
        "warning": (COLORS["warning"], "#000000"),
        "error": (COLORS["error"], "#ffffff"),
        "active": (COLORS["accent"], "#000000"),
        "critical": (COLORS["critical"], "#ffffff"),
    }
    
    bgcolor, text_color = severity_colors.get(severity, (COLORS["text_dim"], COLORS["bg_dark"]))
    
    return ft.Container(
        content=mono_text(text.upper(), size=10, color=text_color),
        bgcolor=bgcolor,
        padding=ft.padding.symmetric(horizontal=8, vertical=2),
        border_radius=2,
    )


def forge_input(
    label: str | None = None,
    hint_text: str | None = None,
    value: str | None = None,
    multiline: bool = False,
    on_change: Any = None,
    **kwargs: Any,
) -> ft.TextField:
    """Create a forge-styled text input.
    
    Args:
        label: Input label
        hint_text: Placeholder text
        value: Initial value
        multiline: Enable multi-line input
        on_change: Change handler
        **kwargs: Additional TextField properties
        
    Returns:
        Styled TextField widget
    """
    return ft.TextField(
        label=label,
        hint_text=hint_text,
        value=value,
        multiline=multiline,
        on_change=on_change,
        bgcolor=COLORS["bg_card"],
        border_color=COLORS["border"],
        focused_border_color=COLORS["accent"],
        color=COLORS["text"],
        cursor_color=COLORS["accent"],
        font_family="JetBrains Mono",
        **kwargs,
    )


def forge_select(
    label: str | None = None,
    options: list[ft.dropdown.Option] | list[str] | None = None,
    value: str | None = None,
    on_change: Any = None,
    **kwargs: Any,
) -> ft.Dropdown:
    """Create a forge-styled dropdown select.
    
    Args:
        label: Select label
        options: List of options (strings or Option objects)
        value: Initial value
        on_change: Change handler
        **kwargs: Additional Dropdown properties
        
    Returns:
        Styled Dropdown widget
    """
    # Convert string options to Option objects
    if options and isinstance(options[0], str):
        options = [ft.dropdown.Option(opt) for opt in options]
    
    return ft.Dropdown(
        label=label,
        options=options or [],
        value=value,
        on_change=on_change,
        bgcolor=COLORS["bg_card"],
        border_color=COLORS["border"],
        focused_border_color=COLORS["accent"],
        color=COLORS["text"],
        **kwargs,
    )


def terminal_snackbar(
    message: str,
    severity: str = "info",
) -> ft.SnackBar:
    """Create a terminal-style snackbar notification.
    
    Args:
        message: Notification message
        severity: Severity level (info, success, warning, error)
        
    Returns:
        Styled SnackBar widget
    """
    severity_colors = {
        "info": COLORS["text_dim"],
        "success": COLORS["success"],
        "warning": COLORS["warning"],
        "error": COLORS["error"],
    }
    
    color = severity_colors.get(severity, COLORS["text_dim"])
    prefix = {
        "info": "[INFO]",
        "success": "[OK]",
        "warning": "[WARN]",
        "error": "[ERROR]",
    }.get(severity, "[INFO]")
    
    return ft.SnackBar(
        content=ft.Row(
            controls=[
                mono_text(f"{prefix} ", size=11, color=color),
                mono_text(message, size=11, color=COLORS["text"]),
            ],
        ),
        bgcolor=COLORS["bg_panel"],
        border=ft.border.all(1, COLORS["border"]),
        border_radius=4,
        behavior=ft.SnackBarBehavior.FLOATING,
    )


def show_terminal_toast(
    page: ft.Page,
    message: str,
    severity: str = "info",
) -> None:
    """Show a terminal-style toast notification.
    
    Args:
        page: Flet page instance
        message: Notification message
        severity: Severity level
    """
    snackbar = terminal_snackbar(message, severity)
    page.overlay.append(snackbar)
    snackbar.open = True
    page.update()
    
    # Auto-close after 3 seconds
    def close_snackbar():
        import asyncio
        asyncio.sleep(3)
        snackbar.open = False
        page.update()


# ============================================================================
# Navigation Icons
# ============================================================================

# Use string-based Material Icon names (Flet supports these)
NAV_ICONS = {
    "overview": "dashboard",
    "dashboard": "dashboard",
    "osint": "search",
    "humint": "people",
    "sigint": "hub",
    "synth": "description",
    "geoint": "map",
    "anvil": "check_circle",
    "finint": "check_circle",
}
