"""AG-UI Component Registry - Maps schema types to Flet widgets."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import flet as ft

# Import intelligence components
from forge.presentation.components.intelligence import (
    render_semantic_profile,
    render_narrative,
    render_graph_analytics,
    render_entity_card,
)

# Global event bus reference for button/form actions
_event_bus_ref: Optional[Any] = None


def set_event_bus(event_bus: Any) -> None:
    """Set the event bus reference for component actions."""
    global _event_bus_ref
    _event_bus_ref = event_bus


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


def _render_table(schema: Dict[str, Any]) -> ft.Control:
    """Render a table component.
    
    Expected schema props:
    - columns: List of column definitions with 'key' and 'label'
    - rows: List of row dictionaries
    - sortable: Whether columns are sortable (default: False)
    """
    props = schema.get("props", {})
    columns = props.get("columns", [])
    rows = props.get("rows", [])
    sortable = props.get("sortable", False)
    
    if not columns:
        return ft.Container(
            content=ft.Text("No columns defined", color=ft.Colors.WHITE70),
            padding=12,
        )
    
    # Build data table
    data_rows = []
    for row in rows:
        data_cells = []
        for col in columns:
            key = col.get("key", "")
            value = row.get(key, "")
            data_cells.append(ft.DataCell(ft.Text(str(value), color=ft.Colors.WHITE70)))
        data_rows.append(ft.DataRow(cells=data_cells))
    
    # Build header row
    header_cells = []
    for col in columns:
        label = col.get("label", col.get("key", ""))
        header_cells.append(ft.DataColumn(
            label=ft.Text(label, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE)
        ))
    
    return ft.Container(
        bgcolor="rgba(255,255,255,0.05)",
        padding=12,
        border_radius=8,
        content=ft.DataTable(
            columns=header_cells,
            rows=data_rows,
            border=ft.border.all(1, "rgba(255,255,255,0.1)"),
            border_radius=8,
        ),
    )


def _render_button(schema: Dict[str, Any]) -> ft.Control:
    """Render a button component.
    
    Expected schema props:
    - label: Button text
    - action: Action identifier to emit on click
    - variant: Button variant (primary, secondary, danger)
    - disabled: Whether button is disabled
    - icon: Optional icon name
    """
    props = schema.get("props", {})
    label = props.get("label", "Button")
    action = props.get("action", "")
    variant = props.get("variant", "primary")
    disabled = props.get("disabled", False)
    icon_name = props.get("icon")
    
    # Map variant to Flet button style
    if variant == "primary":
        button_style = ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.CYAN_600,
        )
    elif variant == "danger":
        button_style = ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.RED_600,
        )
    else:  # secondary
        button_style = ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor="rgba(255,255,255,0.1)",
        )
    
    # Create button with optional icon
    button_content = []
    if icon_name:
        try:
            icon = getattr(ft.Icons, icon_name.upper(), ft.Icons.CIRCLE)
            button_content.append(ft.Icon(icon, size=16))
        except AttributeError:
            pass
    
    button_content.append(ft.Text(label))
    
    button = ft.ElevatedButton(
        content=ft.Row(button_content, spacing=8, tight=True),
        style=button_style,
        disabled=disabled,
    )
    
    # Attach click handler if action is provided
    if action and _event_bus_ref:
        def on_click(e):
            """Handle button click synchronously, then dispatch async."""
            payload = props.get("payload", {})
            if _event_bus_ref:
                import asyncio
                asyncio.create_task(_event_bus_ref.publish("user.action", {"action": action, **payload}))
        
        button.on_click = on_click  # type: ignore[assignment]
    
    return button


def _render_input(schema: Dict[str, Any]) -> ft.Control:
    """Render an input component.
    
    Expected schema props:
    - label: Input label
    - placeholder: Placeholder text
    - value: Initial value
    - type: Input type (text, number, password, email)
    - required: Whether input is required
    - multiline: Whether input is multiline
    """
    props = schema.get("props", {})
    label = props.get("label", "")
    placeholder = props.get("placeholder", "")
    value = props.get("value", "")
    input_type = props.get("type", "text")
    required = props.get("required", False)
    multiline = props.get("multiline", False)
    
    if input_type == "number":
        control = ft.TextField(
            label=label,
            hint_text=placeholder if placeholder else None,
            value=str(value) if value is not None else "",
            keyboard_type=ft.KeyboardType.NUMBER,
        )
    elif multiline:
        control = ft.TextField(
            label=label,
            hint_text=placeholder if placeholder else None,
            value=value,
            multiline=True,
            min_lines=3,
            max_lines=10,
        )
    else:
        control = ft.TextField(
            label=label,
            hint_text=placeholder if placeholder else None,
            value=value,
            password=input_type == "password",
            keyboard_type=ft.KeyboardType.EMAIL if input_type == "email" else ft.KeyboardType.TEXT,
        )
    
    return ft.Container(
        content=control,
        padding=ft.padding.only(bottom=8),
    )


def _render_form(schema: Dict[str, Any]) -> ft.Control:
    """Render a form component.
    
    Expected schema props:
    - fields: List of field schemas (each with type: "input")
    - submit_label: Submit button label
    - submit_action: Action to emit on submit
    """
    props = schema.get("props", {})
    fields = props.get("fields", [])
    submit_label = props.get("submit_label", "Submit")
    submit_action = props.get("submit_action", "")
    
    form_controls = []
    for field_schema in fields:
        if field_schema.get("type") == "input":
            form_controls.append(_render_input(field_schema))
    
    # Add submit button with form data collection
    if submit_action and _event_bus_ref:
        form_inputs = []  # Store input field references
        
        # Collect input field references from form controls
        for control in form_controls:
            if isinstance(control, ft.Container) and isinstance(control.content, ft.TextField):
                form_inputs.append(control.content)
        
        def on_submit(e):
            """Handle form submission synchronously, then dispatch async."""
            # Collect form values from all input fields
            form_data = {}
            for i, field in enumerate(form_inputs):
                field_id = field.label or f"field_{i}"
                form_data[field_id] = field.value or ""
            
            # Also check for corrected_value (common in correction workflows)
            if form_inputs and form_inputs[0].value:
                form_data["corrected_value"] = form_inputs[0].value
                form_data["value"] = form_inputs[0].value
            
            # Publish submit action with form data (async dispatch)
            if _event_bus_ref:
                import asyncio
                asyncio.create_task(_event_bus_ref.publish("user.action", {
                    "action": submit_action,
                    "form_data": form_data,
                    **form_data,  # Also include as top-level for convenience
                }))
        
        submit_button = ft.ElevatedButton(
            content=ft.Text(submit_label),
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.CYAN_600,
            ),
            on_click=on_submit,  # type: ignore[assignment]
        )
        form_controls.append(submit_button)
    
    return ft.Container(
        bgcolor="rgba(255,255,255,0.05)",
        padding=16,
        border_radius=8,
        content=ft.Column(form_controls, spacing=12),
    )


def _render_dialog(schema: Dict[str, Any]) -> ft.Control:
    """Render a dialog component (returns a dialog control, not directly rendered).
    
    Expected schema props:
    - title: Dialog title
    - content: Dialog content (text or schema)
    - actions: List of action buttons
    """
    props = schema.get("props", {})
    title = props.get("title", "Dialog")
    content = props.get("content", "")
    actions = props.get("actions", [])
    
    # Build action buttons
    action_buttons = []
    for action_schema in actions:
        if isinstance(action_schema, dict) and action_schema.get("type") == "button":
            action_buttons.append(_render_button(action_schema))
    
    # Create dialog content
    if isinstance(content, str):
        dialog_content = ft.Text(content, color=ft.Colors.WHITE70)
    else:
        # If content is a schema, render it
        dialog_content = render_schema(content) if isinstance(content, dict) else ft.Text(str(content))
    
    return ft.AlertDialog(
        title=ft.Text(title, color=ft.Colors.WHITE),
        content=dialog_content,
        actions=action_buttons if action_buttons else [],
        bgcolor="rgba(30, 30, 30, 0.95)",
    )


def _render_list(schema: Dict[str, Any]) -> ft.Control:
    """Render a list component.
    
    Expected schema props:
    - items: List of item schemas or strings
    - ordered: Whether list is ordered (numbered)
    """
    props = schema.get("props", {})
    items = props.get("items", [])
    ordered = props.get("ordered", False)
    
    list_controls = []
    for i, item in enumerate(items):
        if isinstance(item, str):
            list_controls.append(ft.Text(item, color=ft.Colors.WHITE70))
        elif isinstance(item, dict):
            # Render item as schema
            rendered = render_schema(item)
            list_controls.append(rendered)
        else:
            list_controls.append(ft.Text(str(item), color=ft.Colors.WHITE70))
    
    return ft.Container(
        bgcolor="rgba(255,255,255,0.05)",
        padding=12,
        border_radius=8,
        content=ft.Column(list_controls, spacing=8),
    )


def _render_divider(schema: Dict[str, Any]) -> ft.Control:
    """Render a divider component."""
    props = schema.get("props", {})
    height = props.get("height", 1)
    color = props.get("color", "rgba(255,255,255,0.1)")
    
    return ft.Divider(height=height, color=color)


def _render_spacer(schema: Dict[str, Any]) -> ft.Control:
    """Render a spacer component."""
    props = schema.get("props", {})
    height = props.get("height", 16)
    width = props.get("width", 16)
    
    return ft.Container(width=width, height=height)


# Component registry mapping schema types to render functions
_COMPONENT_REGISTRY: Dict[str, Callable[[Dict[str, Any]], ft.Control]] = {
    # Basic components
    "card": _render_card,
    "kpi_card": _render_kpi_card,
    "text": _render_text,
    "table": _render_table,
    "button": _render_button,
    "input": _render_input,
    "form": _render_form,
    "dialog": _render_dialog,
    "list": _render_list,
    "divider": _render_divider,
    "spacer": _render_spacer,
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
