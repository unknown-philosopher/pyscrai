"""Example demonstrating the intelligence pipeline with UI components.

This shows how the intelligence services automatically generate visualizations
that appear in the AG-UI feed.
"""

import asyncio
from forge.core.event_bus import EventBus
from forge.core import events


async def intelligence_pipeline_example():
    """Demonstrate the full intelligence pipeline with UI visualization."""
    
    # Initialize event bus
    event_bus = EventBus()
    
    # Track visualizations published
    visualizations = []
    
    async def track_visualizations(payload):
        """Track workspace schema events (UI components)."""
        schema = payload.get("schema", {})
        schema_type = schema.get("type")
        if schema_type in ["semantic_profile", "narrative", "graph_analytics", "entity_card"]:
            visualizations.append(schema)
            print(f"\n✨ UI Component Published: {schema_type}")
            print(f"   Title: {schema.get('title')}")
    
    # Subscribe to workspace schema events
    await event_bus.subscribe(events.TOPIC_WORKSPACE_SCHEMA, track_visualizations)
    
    # Simulate the pipeline
    print("=" * 60)
    print("INTELLIGENCE PIPELINE DEMONSTRATION")
    print("=" * 60)
    
    # Step 1: Document ingestion triggers extraction
    print("\n📄 Step 1: Ingesting document...")
    await event_bus.publish(
        events.TOPIC_DATA_INGESTED,
        events.create_data_ingested_event(
            doc_id="doc_001",
            content="Alice is a senior researcher at PyScrAI. She collaborates with Bob on AI projects."
        )
    )
    await asyncio.sleep(0.1)
    
    # Step 2: Entities extracted
    print("\n🔍 Step 2: Extracting entities...")
    await event_bus.publish(
        events.TOPIC_ENTITY_EXTRACTED,
        events.create_entity_extracted_event(
            doc_id="doc_001",
            entities=[
                {"type": "PERSON", "text": "Alice"},
                {"type": "PERSON", "text": "Bob"},
                {"type": "ORG", "text": "PyScrAI"},
            ]
        )
    )
    await asyncio.sleep(0.1)
    
    # Step 3: Relationships found
    print("\n🔗 Step 3: Finding relationships...")
    await event_bus.publish(
        events.TOPIC_RELATIONSHIP_FOUND,
        events.create_relationship_found_event(
            doc_id="doc_001",
            relationships=[
                {"source": "PERSON:Alice", "target": "ORG:PyScrAI", "type": "WORKS_AT", "confidence": 0.95},
                {"source": "PERSON:Alice", "target": "PERSON:Bob", "type": "COLLABORATES_WITH", "confidence": 0.85},
            ]
        )
    )
    await asyncio.sleep(0.1)
    
    # Step 4: Graph updated (this would trigger intelligence services)
    print("\n📊 Step 4: Updating graph...")
    await event_bus.publish(
        events.TOPIC_GRAPH_UPDATED,
        events.create_graph_updated_event(
            doc_id="doc_001",
            graph_stats={
                "nodes": [
                    {"id": "PERSON:Alice", "type": "PERSON", "label": "Alice"},
                    {"id": "PERSON:Bob", "type": "PERSON", "label": "Bob"},
                    {"id": "ORG:PyScrAI", "type": "ORG", "label": "PyScrAI"},
                ],
                "edges": [
                    {"source": "PERSON:Alice", "target": "ORG:PyScrAI", "type": "WORKS_AT", "confidence": 0.95},
                    {"source": "PERSON:Alice", "target": "PERSON:Bob", "type": "COLLABORATES_WITH", "confidence": 0.85},
                ],
            }
        )
    )
    await asyncio.sleep(0.1)
    
    # Step 5: Semantic profile generated (simulating SemanticProfilerService)
    print("\n🧠 Step 5: Generating semantic profile...")
    await event_bus.publish(
        events.TOPIC_WORKSPACE_SCHEMA,
        events.create_workspace_schema_event({
            "type": "semantic_profile",
            "title": "Profile: Alice",
            "props": {
                "entity_id": "PERSON:Alice",
                "summary": "Alice is a senior researcher at PyScrAI, leading AI development projects",
                "attributes": ["researcher", "technical", "leadership", "AI specialist"],
                "importance": 9,
                "key_relationships": ["WORKS_AT:PyScrAI", "COLLABORATES_WITH:Bob"],
                "confidence": 0.92
            }
        })
    )
    await asyncio.sleep(0.1)
    
    # Step 6: Narrative generated (simulating NarrativeSynthesisService)
    print("\n📝 Step 6: Generating narrative...")
    await event_bus.publish(
        events.TOPIC_WORKSPACE_SCHEMA,
        events.create_workspace_schema_event({
            "type": "narrative",
            "title": "Document Narrative",
            "props": {
                "doc_id": "doc_001",
                "narrative": """# Team Structure

## Key Personnel

Alice serves as a senior researcher at PyScrAI, demonstrating strong technical leadership. Her collaboration with Bob indicates a team-based approach to AI project development.

## Organization

PyScrAI emerges as the central organizational entity, employing key researchers and fostering collaborative AI research.

### Evidence Chain
- Alice → WORKS_AT → PyScrAI
- Alice → COLLABORATES_WITH → Bob
""",
                "entity_count": 3,
                "relationship_count": 2
            }
        })
    )
    await asyncio.sleep(0.1)
    
    # Step 7: Graph analytics (simulating AdvancedGraphAnalysisService)
    print("\n📈 Step 7: Running graph analytics...")
    await event_bus.publish(
        events.TOPIC_WORKSPACE_SCHEMA,
        events.create_workspace_schema_event({
            "type": "graph_analytics",
            "title": "Graph Analysis",
            "props": {
                "centrality": {
                    "most_connected": [
                        {"entity": "PERSON:Alice", "degree": 0.67},
                        {"entity": "ORG:PyScrAI", "degree": 0.33},
                    ],
                    "bridges": [
                        {"entity": "PERSON:Alice", "betweenness": 0.80}
                    ],
                },
                "communities": [
                    {
                        "id": 0,
                        "entities": ["PERSON:Alice", "PERSON:Bob", "ORG:PyScrAI"],
                        "size": 3
                    }
                ],
                "statistics": {
                    "num_nodes": 3,
                    "num_edges": 2,
                    "density": 0.33,
                    "is_connected": True,
                    "num_components": 1
                }
            }
        })
    )
    await asyncio.sleep(0.1)
    
    # Step 8: Entity cards for quick overview
    print("\n🃏 Step 8: Generating entity cards...")
    for entity in [
        {"id": "PERSON:Alice", "type": "PERSON", "label": "Alice", "rel_count": 2},
        {"id": "PERSON:Bob", "type": "PERSON", "label": "Bob", "rel_count": 1},
        {"id": "ORG:PyScrAI", "type": "ORG", "label": "PyScrAI", "rel_count": 1},
    ]:
        await event_bus.publish(
            events.TOPIC_WORKSPACE_SCHEMA,
            events.create_workspace_schema_event({
                "type": "entity_card",
                "title": f"{entity['type']}: {entity['label']}",
                "props": {
                    "entity_id": entity['id'],
                    "type": entity['type'],
                    "label": entity['label'],
                    "relationship_count": entity['rel_count']
                }
            })
        )
        await asyncio.sleep(0.05)
    
    # Summary
    print("\n" + "=" * 60)
    print(f"✅ Pipeline Complete!")
    print(f"   Total UI Components Published: {len(visualizations)}")
    print("\n   Component Types:")
    for viz in visualizations:
        print(f"   - {viz['type']}: {viz['title']}")
    print("=" * 60)
    print("\n💡 All visualizations automatically appear in the AG-UI feed!")
    print("   Users see semantic profiles, narratives, and analytics")
    print("   in real-time as documents are processed.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(intelligence_pipeline_example())
