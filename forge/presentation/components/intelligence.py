"""Intelligence dashboard UI components for PyScrAI Forge.

Provides AG-UI compatible components for semantic profiles, narratives, and graph analytics.
"""

from __future__ import annotations

from typing import Any, Dict

import flet as ft


def render_semantic_profile(schema: Dict[str, Any]) -> ft.Control:
    """Render a semantic profile component.
    
    Expected schema props:
    - entity_id: Entity identifier
    - summary: Brief entity summary
    - attributes: List of key attributes
    - importance: 1-10 importance rating
    - key_relationships: List of important relationship types
    - confidence: 0-1 confidence score
    """
    props = schema.get("props", {})
    entity_id = props.get("entity_id", "Unknown")
    summary = props.get("summary", "No summary available")
    attributes = props.get("attributes", [])
    importance = props.get("importance", 5)
    key_relationships = props.get("key_relationships", [])
    confidence = props.get("confidence", 0.0)
    
    # Importance color based on rating
    if importance >= 8:
        importance_color = ft.Colors.RED_400
    elif importance >= 6:
        importance_color = ft.Colors.ORANGE_400
    elif importance >= 4:
        importance_color = ft.Colors.YELLOW_400
    else:
        importance_color = ft.Colors.GREEN_400
    
    # Build attributes chips
    attribute_chips = []
    for attr in attributes[:8]:  # Limit to 8 attributes
        attribute_chips.append(
            ft.Container(
                content=ft.Text(attr, size=11, color=ft.Colors.WHITE),
                bgcolor="rgba(100, 200, 255, 0.2)",
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                border_radius=12,
            )
        )
    
    # Build relationships list
    relationship_items = []
    for rel in key_relationships[:5]:  # Limit to 5 relationships
        relationship_items.append(
            ft.Row(
                [
                    ft.Icon(ft.Icons.ARROW_RIGHT, size=14, color=ft.Colors.CYAN_400),
                    ft.Text(rel, size=12, color=ft.Colors.WHITE70),
                ],
                spacing=4,
            )
        )
    
    return ft.Container(
        content=ft.Column(
            [
                # Header with entity ID and importance
                ft.Row(
                    [
                        ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=24, color=ft.Colors.CYAN_400),
                        ft.Text(
                            entity_id,
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.WHITE,
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Text(
                                f"★ {importance}",
                                size=14,
                                weight=ft.FontWeight.W_700,
                                color=ft.Colors.BLACK,
                            ),
                            bgcolor=importance_color,
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            border_radius=8,
                        ),
                    ],
                    spacing=8,
                ),
                # Summary
                ft.Container(
                    content=ft.Text(
                        summary,
                        size=13,
                        color=ft.Colors.WHITE70,
                        italic=True,
                    ),
                    padding=ft.padding.only(top=8, bottom=8),
                ),
                # Attributes
                ft.Column(
                    [
                        ft.Text(
                            "Attributes",
                            size=12,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.CYAN_400,
                        ),
                        ft.Row(
                            attribute_chips,
                            wrap=True,
                            spacing=6,
                        ),
                    ],
                    spacing=6,
                ) if attributes else ft.Container(),
                # Key Relationships
                ft.Column(
                    [
                        ft.Text(
                            "Key Relationships",
                            size=12,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.CYAN_400,
                        ),
                        ft.Column(relationship_items, spacing=4),
                    ],
                    spacing=6,
                ) if key_relationships else ft.Container(),
                # Confidence footer
                ft.Row(
                    [
                        ft.Icon(ft.Icons.VERIFIED, size=14, color=ft.Colors.GREEN_400),
                        ft.Text(
                            f"Confidence: {confidence:.0%}",
                            size=11,
                            color=ft.Colors.WHITE60,
                        ),
                    ],
                    spacing=4,
                ),
            ],
            spacing=12,
        ),
        bgcolor="rgba(255, 255, 255, 0.05)",
        padding=16,
        border_radius=12,
        border=ft.border.all(1, "rgba(100, 200, 255, 0.3)"),
    )


def render_narrative(schema: Dict[str, Any]) -> ft.Control:
    """Render a narrative component.
    
    Expected schema props:
    - doc_id: Document identifier
    - narrative: Markdown-formatted narrative text
    - entity_count: Number of entities
    - relationship_count: Number of relationships
    """
    props = schema.get("props", {})
    doc_id = props.get("doc_id", "Unknown")
    narrative = props.get("narrative", "No narrative available")
    entity_count = props.get("entity_count", 0)
    relationship_count = props.get("relationship_count", 0)
    
    # Parse narrative for basic markdown support
    narrative_lines = []
    for line in narrative.split("\n"):
        line = line.strip()
        if not line:
            continue
        
        # Headers
        if line.startswith("### "):
            narrative_lines.append(
                ft.Text(
                    line[4:],
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=ft.Colors.CYAN_400,
                )
            )
        elif line.startswith("## "):
            narrative_lines.append(
                ft.Text(
                    line[3:],
                    size=16,
                    weight=ft.FontWeight.W_700,
                    color=ft.Colors.CYAN_300,
                )
            )
        elif line.startswith("# "):
            narrative_lines.append(
                ft.Text(
                    line[2:],
                    size=18,
                    weight=ft.FontWeight.W_700,
                    color=ft.Colors.CYAN_200,
                )
            )
        # List items
        elif line.startswith("- "):
            narrative_lines.append(
                ft.Row(
                    [
                        ft.Text("•", color=ft.Colors.CYAN_400, size=14),
                        ft.Text(line[2:], color=ft.Colors.WHITE70, size=13, expand=True),
                    ],
                    spacing=8,
                )
            )
        # Regular text
        else:
            narrative_lines.append(
                ft.Text(line, color=ft.Colors.WHITE70, size=13)
            )
    
    return ft.Container(
        bgcolor="rgba(255, 255, 255, 0.05)",
        padding=16,
        border_radius=12,
        border=ft.border.all(1, "rgba(150, 100, 255, 0.3)"),
        content=ft.Column(
            [
                # Header
                ft.Row(
                    [
                        ft.Icon(ft.Icons.DESCRIPTION, size=24, color=ft.Colors.PURPLE_300),
                        ft.Column(
                            [
                                ft.Text(
                                    "Document Narrative",
                                    size=16,
                                    weight=ft.FontWeight.W_600,
                                    color=ft.Colors.WHITE,
                                ),
                                ft.Text(
                                    f"ID: {doc_id[:16]}..." if len(doc_id) > 16 else f"ID: {doc_id}",
                                    size=11,
                                    color=ft.Colors.WHITE60,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                    spacing=8,
                ),
                
                ft.Divider(height=1, color="rgba(255, 255, 255, 0.1)"),
                
                # Stats
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Icon(ft.Icons.ACCOUNT_BOX, size=16, color=ft.Colors.CYAN_400),
                                    ft.Text(f"{entity_count} entities", size=12, color=ft.Colors.WHITE70),
                                ],
                                spacing=4,
                            ),
                            bgcolor="rgba(100, 200, 255, 0.1)",
                            padding=8,
                            border_radius=8,
                        ),
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Icon(ft.Icons.LINK, size=16, color=ft.Colors.ORANGE_400),
                                    ft.Text(f"{relationship_count} relationships", size=12, color=ft.Colors.WHITE70),
                                ],
                                spacing=4,
                            ),
                            bgcolor="rgba(255, 150, 100, 0.1)",
                            padding=8,
                            border_radius=8,
                        ),
                    ],
                    spacing=8,
                ),
                
                ft.Divider(height=1, color="rgba(255, 255, 255, 0.1)"),
                
                # Narrative content
                ft.Container(
                    content=ft.Column(
                        narrative_lines,
                        spacing=8,
                    ),
                    height=300,
                    padding=ft.padding.only(right=8),
                ),
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        ),
    )


def render_graph_analytics(schema: Dict[str, Any]) -> ft.Control:
    """Render a graph analytics component.
    
    Expected schema props:
    - centrality: Dict with most_connected, bridges, influential lists
    - communities: List of community dicts with entities and size
    - statistics: Dict with num_nodes, num_edges, density, etc.
    """
    props = schema.get("props", {})
    centrality = props.get("centrality", {})
    communities = props.get("communities", [])
    statistics = props.get("statistics", {})
    
    # Build centrality metrics
    most_connected = centrality.get("most_connected", [])[:5]
    bridges = centrality.get("bridges", [])[:5]
    
    # Statistics
    num_nodes = statistics.get("num_nodes", 0)
    num_edges = statistics.get("num_edges", 0)
    density = statistics.get("density", 0.0)
    
    # Build connected nodes list
    connected_items = []
    for item in most_connected:
        entity = item.get("entity", "")
        degree = item.get("degree", 0)
        connected_items.append(
            ft.Row(
                [
                    ft.Container(
                        content=ft.Text(f"{degree:.2f}", size=11, color=ft.Colors.BLACK),
                        bgcolor=ft.Colors.CYAN_400,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        border_radius=4,
                    ),
                    ft.Text(entity, size=12, color=ft.Colors.WHITE70, expand=True),
                ],
                spacing=8,
            )
        )
    
    # Build bridges list
    bridge_items = []
    for item in bridges:
        entity = item.get("entity", "")
        betweenness = item.get("betweenness", 0)
        bridge_items.append(
            ft.Row(
                [
                    ft.Container(
                        content=ft.Text(f"{betweenness:.2f}", size=11, color=ft.Colors.BLACK),
                        bgcolor=ft.Colors.ORANGE_400,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        border_radius=4,
                    ),
                    ft.Text(entity, size=12, color=ft.Colors.WHITE70, expand=True),
                ],
                spacing=8,
            )
        )
    
    # Build communities list
    community_items = []
    for i, comm in enumerate(communities[:3]):  # Top 3 communities
        size = comm.get("size", 0)
        entities = comm.get("entities", [])[:5]  # First 5 entities
        community_items.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            f"Community {i+1} ({size} members)",
                            size=11,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.GREEN_400,
                        ),
                        ft.Text(
                            ", ".join(entities),
                            size=11,
                            color=ft.Colors.WHITE60,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                    spacing=4,
                ),
                bgcolor="rgba(100, 255, 100, 0.1)",
                padding=8,
                border_radius=6,
            )
        )
    
    return ft.Container(
        bgcolor="rgba(255, 255, 255, 0.05)",
        padding=16,
        border_radius=12,
        border=ft.border.all(1, "rgba(100, 255, 150, 0.3)"),
        content=ft.Column(
            [
                # Header
                ft.Row(
                    [
                        ft.Icon(ft.Icons.ANALYTICS, size=24, color=ft.Colors.GREEN_400),
                        ft.Text(
                            "Graph Analytics",
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.WHITE,
                        ),
                    ],
                    spacing=8,
                ),
                
                # Statistics cards
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("Nodes", size=11, color=ft.Colors.WHITE60),
                                    ft.Text(str(num_nodes), size=20, weight=ft.FontWeight.W_700, color=ft.Colors.CYAN_400),
                                ],
                                spacing=2,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            bgcolor="rgba(100, 200, 255, 0.1)",
                            padding=12,
                            border_radius=8,
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("Edges", size=11, color=ft.Colors.WHITE60),
                                    ft.Text(str(num_edges), size=20, weight=ft.FontWeight.W_700, color=ft.Colors.ORANGE_400),
                                ],
                                spacing=2,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            bgcolor="rgba(255, 150, 100, 0.1)",
                            padding=12,
                            border_radius=8,
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("Density", size=11, color=ft.Colors.WHITE60),
                                    ft.Text(f"{density:.2%}", size=20, weight=ft.FontWeight.W_700, color=ft.Colors.GREEN_400),
                                ],
                                spacing=2,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            bgcolor="rgba(100, 255, 100, 0.1)",
                            padding=12,
                            border_radius=8,
                            expand=True,
                        ),
                    ],
                    spacing=8,
                ),
                
                # Most Connected
                ft.Column(
                    [
                        ft.Text(
                            "Most Connected Nodes",
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.CYAN_400,
                        ),
                        ft.Column(connected_items, spacing=4),
                    ],
                    spacing=6,
                ) if connected_items else ft.Container(),
                
                # Bridges
                ft.Column(
                    [
                        ft.Text(
                            "Bridge Nodes",
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.ORANGE_400,
                        ),
                        ft.Column(bridge_items, spacing=4),
                    ],
                    spacing=6,
                ) if bridge_items else ft.Container(),
                
                # Communities
                ft.Column(
                    [
                        ft.Text(
                            "Communities",
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.GREEN_400,
                        ),
                        ft.Column(community_items, spacing=6),
                    ],
                    spacing=6,
                ) if community_items else ft.Container(),
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        ),
    )


def render_entity_card(schema: Dict[str, Any]) -> ft.Control:
    """Render an entity card component.
    
    Expected schema props:
    - entity_id: Entity identifier
    - type: Entity type (PERSON, ORG, etc.)
    - label: Entity label/name
    - relationship_count: Number of relationships
    """
    props = schema.get("props", {})
    entity_id = props.get("entity_id", "Unknown")
    entity_type = props.get("type", "UNKNOWN")
    label = props.get("label", entity_id)
    relationship_count = props.get("relationship_count", 0)
    
    # Type badge color
    type_colors = {
        "PERSON": ft.Colors.BLUE_400,
        "ORG": ft.Colors.PURPLE_400,
        "ORGANIZATION": ft.Colors.PURPLE_400,
        "LOCATION": ft.Colors.GREEN_400,
        "GPE": ft.Colors.GREEN_400,
        "DATE": ft.Colors.ORANGE_400,
        "EVENT": ft.Colors.RED_400,
    }
    type_color = type_colors.get(entity_type, ft.Colors.GREY_400)
    
    return ft.Container(
        bgcolor="rgba(255, 255, 255, 0.05)",
        padding=12,
        border_radius=8,
        border=ft.border.all(1, "rgba(255, 255, 255, 0.1)"),
        content=ft.Row(
            [
                ft.Icon(ft.Icons.CIRCLE, size=8, color=type_color),
                ft.Column(
                    [
                        ft.Text(label, size=14, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
                        ft.Row(
                            [
                                ft.Container(
                                    content=ft.Text(entity_type, size=10, color=ft.Colors.BLACK),
                                    bgcolor=type_color,
                                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                    border_radius=4,
                                ),
                                ft.Text(
                                    f"{relationship_count} links",
                                    size=11,
                                    color=ft.Colors.WHITE60,
                                ),
                            ],
                            spacing=8,
                        ),
                    ],
                    spacing=4,
                    expand=True,
                ),
            ],
            spacing=8,
        ),
    )
