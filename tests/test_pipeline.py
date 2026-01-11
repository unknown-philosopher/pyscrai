"""Quick test of the document extraction pipeline."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from forge.core.event_bus import EventBus, EventPayload
from forge.core import events
from forge.domain.extraction.service import DocumentExtractionService
from forge.domain.resolution.service import EntityResolutionService
from forge.domain.graph.service import GraphAnalysisService
from forge.infrastructure.persistence.duckdb_service import DuckDBPersistenceService



async def on_entity_extracted(payload: EventPayload):
    """Handler to verify entity extraction works."""
    print(f"\n✅ ENTITY EXTRACTION SUCCESS!")
    print(f"   Document ID: {payload.get('doc_id')}")
    print(f"   Entities Found: {len(payload.get('entities', []))}")
    for entity in payload.get('entities', []):
        print(f"     - {entity.get('type')}: {entity.get('text')}")

async def on_relationship_found(payload: EventPayload):
    """Handler to verify relationship detection works."""
    print(f"\n✅ RELATIONSHIP DETECTION SUCCESS!")
    print(f"   Document ID: {payload.get('doc_id')}")
    print(f"   Relationships Found: {len(payload.get('relationships', []))}")
    for rel in payload.get('relationships', []):
        print(f"     - {rel.get('source')} ({rel.get('source_type')}) "
              f"→ [{rel.get('relation_type')}] → "
              f"{rel.get('target')} ({rel.get('target_type')})")
        print(f"       Confidence: {rel.get('confidence', 0):.2%}")


async def on_graph_updated(payload: EventPayload):
    """Handler to verify graph analysis works."""
    print(f"\n✅ GRAPH ANALYSIS SUCCESS!")
    print(f"   Document ID: {payload.get('doc_id')}")
    graph_stats = payload.get('graph_stats', {})
    print(f"   Knowledge Graph Stats:")
    print(f"     - Nodes: {graph_stats.get('node_count', 0)}")
    print(f"     - Edges: {graph_stats.get('edge_count', 0)}")


async def main():
    print("🧪 Testing Full Intelligence Pipeline\n")
    
    # Initialize event bus
    bus = EventBus()
    
    # Start extraction service
    extraction_service = DocumentExtractionService(bus)
    await extraction_service.start()
    print("📦 DocumentExtractionService started")

    # Start entity resolution service
    resolution_service = EntityResolutionService(bus)
    await resolution_service.start()
    print("📦 EntityResolutionService started")

    # Start graph analysis service
    graph_service = GraphAnalysisService(bus)
    await graph_service.start()
    print("📦 GraphAnalysisService started")

    # Start persistence service
    persistence_service = DuckDBPersistenceService(bus, db_path=":memory:")
    await persistence_service.start()
    print("📦 DuckDBPersistenceService started")

    # Subscribe to all pipeline events
    await bus.subscribe(events.TOPIC_ENTITY_EXTRACTED, on_entity_extracted)
    await bus.subscribe(events.TOPIC_RELATIONSHIP_FOUND, on_relationship_found)
    await bus.subscribe(events.TOPIC_GRAPH_UPDATED, on_graph_updated)
    print("👂 Listening for entity, relationship, and graph events\n")
    
    # Publish test document
    test_doc = {
        "doc_id": "test_001",
        "content": "Alice works at PyScrAI, a company focused on AI research.",
    }
    
    print(f"📄 Publishing test document: {test_doc['doc_id']}")
    print(f"   Content: {test_doc['content']}\n")
    
    await bus.publish(
        events.TOPIC_DATA_INGESTED,
        events.create_data_ingested_event(
            doc_id=test_doc["doc_id"],
            content=test_doc["content"]
        )
    )
    
    # Wait for async processing
    print("⏳ Waiting for extraction to complete...")
    await asyncio.sleep(2)
    
    # Verify persistence
    print("\n📊 DATABASE VERIFICATION:")
    entity_count = persistence_service.get_entity_count()
    relationship_count = persistence_service.get_relationship_count()
    print(f"   Entities in DB: {entity_count}")
    print(f"   Relationships in DB: {relationship_count}")
    
    if entity_count > 0:
        print("\n   Stored Entities:")
        for entity in persistence_service.get_all_entities():
            print(f"     - {entity['label']} ({entity['type']})")
    
    if relationship_count > 0:
        print("\n   Stored Relationships:")
        for rel in persistence_service.get_all_relationships():
            print(f"     - {rel['source']} → [{rel['type']}] → {rel['target']} (confidence: {rel['confidence']:.2%})")
    
    # Clean up
    persistence_service.close()
    
    print("\n✨ Pipeline test complete!")


if __name__ == "__main__":
    asyncio.run(main())
