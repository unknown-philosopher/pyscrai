"""
Reusable UI Components for Forge Frontend.

Provides styled components with consistent cyberpunk/intelligence platform aesthetic.
"""

from __future__ import annotations

from typing import Any

from nicegui import ui


def ForgeMetricCard(label: str, value: str | int, subtext: str = "", icon: str = "circle") -> ui.element:
    """Create a metric card with label, value, and optional subtext.
    
    Args:
        label: Metric label (e.g., "ENTITIES")
        value: Main metric value
        subtext: Optional subtext below value (e.g., "+12 this session")
        icon: Material icon name (default: "circle")
        
    Returns:
        UI element container
    """
    with ui.card().classes("bg-gray-900 border border-gray-800 p-4 gap-2 min-w-[200px]") as card:
        with ui.row().classes("items-center justify-between w-full"):
            ui.html(
                f'<span class="mono" style="color: #555; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px;">{label}</span>',
                sanitize=False
            )
            ui.icon(icon, size="xs").classes("text-cyan-500")
        
        ui.html(
            f'<div class="mono" style="color: #00b8d4; font-size: 2rem; font-weight: 600; margin: 8px 0;">{value}</div>',
            sanitize=False
        )
        
        if subtext:
            ui.html(
                f'<span class="mono" style="color: #444; font-size: 0.65rem;">{subtext}</span>',
                sanitize=False
            )
    
    return card


def ForgeButton(
    label: str,
    icon: str | None = None,
    primary: bool = False,
    on_click: Any = None,
    **kwargs: Any,
) -> ui.element:
    """Create a styled button with consistent Forge theme.
    
    Args:
        label: Button label text
        icon: Optional material icon name
        primary: If True, use primary (cyan) styling, otherwise secondary
        on_click: Click handler function
        **kwargs: Additional props to pass to button
        
    Returns:
        Button element
    """
    if primary:
        # Primary button (cyan background)
        classes = "px-4 py-2 rounded cursor-pointer"
        style = (
            "background: #00b8d4; color: #000; font-family: 'JetBrains Mono', monospace; "
            "font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; "
            "transition: all 0.15s ease; border: none;"
        )
        hover_style = "background: #00d4f5;"
    else:
        # Secondary button (outlined)
        classes = "px-4 py-2 rounded cursor-pointer border"
        style = (
            "background: transparent; border: 1px solid #444; color: #888; "
            "font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; "
            "text-transform: uppercase; letter-spacing: 0.5px; transition: all 0.15s ease;"
        )
        hover_style = "border-color: #00b8d4; color: #00b8d4;"
    
    with ui.element("div").classes(classes).style(style).on("click", on_click) as btn:
        if icon:
            ui.icon(icon, size="sm").classes("mr-2")
        ui.html(f'<span class="mono">{label}</span>', sanitize=False)
        
        # Add hover effect via style
        btn.style(f"{style}").on("mouseenter", lambda: btn.style(f"{style}{hover_style}"))
        btn.on("mouseleave", lambda: btn.style(style))
    
    return btn


def ForgeCard(content_fn: Any = None, **kwargs: Any) -> ui.element:
    """Create a styled card container with Forge theme.
    
    Args:
        content_fn: Optional function to render content inside card
        **kwargs: Additional props (classes, style, etc.)
        
    Returns:
        Card element
    """
    classes = kwargs.pop("classes", "") + " forge-card"
    style = kwargs.pop("style", "") + " background: #1a1a1a; border: 1px solid #333; border-radius: 4px;"
    
    with ui.card().classes(classes).style(style, **kwargs) as card:
        if content_fn:
            content_fn()
    
    return card


def render_metric_card(label: str, value: str | int, subtext: str = "", icon: str = "circle") -> None:
    """Render a metric card (convenience function for inline usage).
    
    Args:
        label: Metric label
        value: Main metric value
        subtext: Optional subtext
        icon: Material icon name
    """
    ForgeMetricCard(label, value, subtext, icon)
