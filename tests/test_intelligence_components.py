"""Test for intelligence UI components."""

import pytest
from forge.presentation.renderer.registry import render_schema


def test_semantic_profile_component():
    """Test semantic profile rendering."""
    schema = {
        "type": "semantic_profile",
        "props": {
            "entity_id": "PERSON:Alice",
            "summary": "Alice is an experienced researcher at PyScrAI",
            "attributes": ["researcher", "technical", "experienced"],
            "importance": 8,
            "key_relationships": ["WORKS_AT:PyScrAI", "COLLABORATES_WITH:Bob"],
            "confidence": 0.92
        }
    }
    
    component = render_schema(schema)
    assert component is not None


def test_narrative_component():
    """Test narrative rendering."""
    schema = {
        "type": "narrative",
        "props": {
            "doc_id": "doc_123",
            "narrative": """# Main Findings

PyScrAI is an AI research organization focusing on knowledge extraction.

## Key Points
- Advanced NLP capabilities
- GPU-accelerated processing
- Entity relationship analysis

### Team
- Alice works as a lead researcher
- Bob contributes to infrastructure""",
            "entity_count": 3,
            "relationship_count": 5
        }
    }
    
    component = render_schema(schema)
    assert component is not None


def test_graph_analytics_component():
    """Test graph analytics rendering."""
    schema = {
        "type": "graph_analytics",
        "props": {
            "centrality": {
                "most_connected": [
                    {"entity": "PyScrAI", "degree": 0.85},
                    {"entity": "Alice", "degree": 0.72}
                ],
                "bridges": [
                    {"entity": "Alice", "betweenness": 0.65}
                ]
            },
            "communities": [
                {
                    "id": 0,
                    "entities": ["PyScrAI", "Alice", "Bob"],
                    "size": 3
                }
            ],
            "statistics": {
                "num_nodes": 5,
                "num_edges": 8,
                "density": 0.4
            }
        }
    }
    
    component = render_schema(schema)
    assert component is not None


def test_entity_card_component():
    """Test entity card rendering."""
    schema = {
        "type": "entity_card",
        "props": {
            "entity_id": "PERSON:Alice",
            "type": "PERSON",
            "label": "Alice",
            "relationship_count": 5
        }
    }
    
    component = render_schema(schema)
    assert component is not None


def test_unknown_component_fallback():
    """Test that unknown components fall back to card renderer."""
    schema = {
        "type": "unknown_type",
        "title": "Fallback Test",
        "summary": "This should render as a card"
    }
    
    component = render_schema(schema)
    assert component is not None
