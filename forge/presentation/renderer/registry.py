"""AG-UI Component Registry - Maps schema types to Flet widgets."""

from __future__ import annotations

from typing import Any, Callable, Dict

import flet as ft

# Import intelligence components
from forge.presentation.components.intelligence import (
    render_semantic_profile,
    render_narrative,
    render_graph_analytics,
    render_entity_card,
)


def _render_card(schema: Dict[str, Any]) -> ft.Control:
    """Render a basic card component."""
    title = schema.get("title", "Component")
    summary = schema.get("summary") or schema.get("type", "schema")
    props = schema.get("props", {})

    content = ft.Column(
        [
            ft.Text(title, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
            ft.Text(str(summary), color=ft.Colors.WHITE70),
        ],
        spacing=4,
    )

    # Add additional content from props if available
    if "content" in props:
        content.controls.append(ft.Text(str(props["content"]), color=ft.Colors.WHITE60))

    return ft.Container(
        bgcolor="rgba(255,255,255,0.05)",
        padding=12,
        border_radius=8,
        content=content,
    )


def _render_kpi_card(schema: Dict[str, Any]) -> ft.Control:
    """Render a KPI card component."""
    title = schema.get("title", "KPI")
    props = schema.get("props", {})
    value = props.get("value", 0)
    unit = props.get("unit", "")

    return ft.Container(
        bgcolor="rgba(255,255,255,0.05)",
        padding=16,
        border_radius=8,
        content=ft.Column(
            [
                ft.Text(title, size=12, color=ft.Colors.WHITE70),
                ft.Row(
                    [
                        ft.Text(
                            f"{value}{unit}",
                            size=24,
                            weight=ft.FontWeight.W_700,
                            color=ft.Colors.CYAN_ACCENT,
                        ),
                    ]
                ),
            ],
            spacing=4,
        ),
    )


def _render_text(schema: Dict[str, Any]) -> ft.Control:
    """Render a text component."""
    props = schema.get("props", {})
    text = props.get("text", "")
    color = props.get("color", ft.Colors.WHITE70)
    size = props.get("size", 14)

    return ft.Text(text, color=color, size=size)


# Component registry mapping schema types to render functions
_COMPONENT_REGISTRY: Dict[str, Callable[[Dict[str, Any]], ft.Control]] = {
    "card": _render_card,
    "kpi_card": _render_kpi_card,
    "text": _render_text,
    # Intelligence components
    "semantic_profile": render_semantic_profile,
    "narrative": render_narrative,
    "graph_analytics": render_graph_analytics,
    "entity_card": render_entity_card,
}


def register_component(type_name: str, render_fn: Callable[[Dict[str, Any]], ft.Control]) -> None:
    """Register a new component type with its render function.

    Args:
        type_name: The schema type name (e.g., "graph", "table")
        render_fn: Function that takes a schema dict and returns a Flet Control
    """
    _COMPONENT_REGISTRY[type_name] = render_fn


def render_schema(schema: Dict[str, Any]) -> ft.Control:
    """Render a schema dict into a Flet widget.

    Args:
        schema: Schema dictionary with at least a "type" field

    Returns:
        A Flet Control widget

    Raises:
        ValueError: If the schema type is not registered
    """
    schema_type = schema.get("type", "card")

    if schema_type not in _COMPONENT_REGISTRY:
        # Fallback to card renderer for unknown types
        return _render_card(schema)

    render_fn = _COMPONENT_REGISTRY[schema_type]
    return render_fn(schema)
