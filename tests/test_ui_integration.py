"""
Test script to demonstrate intelligence UI integration.
Publishes sample events to trigger intelligence visualizations.
"""

import asyncio
import time
from forge.core.event_bus import EventBus
from forge.core import events

async def main():
    """Publish sample events to trigger intelligence UI components."""
    bus = EventBus()
    
    print("=" * 60)
    print("INTELLIGENCE UI INTEGRATION TEST")
    print("=" * 60)
    
    # Wait a bit for services to initialize
    await asyncio.sleep(2)
    
    # 1. Publish document ingestion event
    print("\n📄 Step 1: Publishing document ingestion event...")
    await bus.publish(
        events.TOPIC_DATA_INGESTED,
        events.create_data_ingested_event(
            doc_id="test_doc_001",
            content="""
            Alice Smith is a software engineer at TechCorp.
            She works closely with Bob Jones, the senior architect.
            Together they built the PyScrAI system for document analysis.
            Alice specializes in AI and machine learning.
            Bob has 15 years of experience in distributed systems.
            """
        )
    )
    await asyncio.sleep(1)
    
    # 2. Publish entity extraction event
    print("\n🔍 Step 2: Publishing entity extraction event...")
    await bus.publish(
        events.TOPIC_ENTITY_EXTRACTED,
        events.create_entity_extracted_event(
            doc_id="test_doc_001",
            entities=[
                {
                    "entity_id": "e001",
                    "entity_name": "Alice Smith",
                    "entity_type": "PERSON",
                    "attributes": {
                        "role": "Software Engineer",
                        "company": "TechCorp",
                        "specialization": "AI and Machine Learning"
                    }
                },
                {
                    "entity_id": "e002",
                    "entity_name": "Bob Jones",
                    "entity_type": "PERSON",
                    "attributes": {
                        "role": "Senior Architect",
                        "experience": "15 years",
                        "expertise": "Distributed Systems"
                    }
                },
                {
                    "entity_id": "e003",
                    "entity_name": "TechCorp",
                    "entity_type": "ORGANIZATION",
                    "attributes": {
                        "type": "Technology Company"
                    }
                },
                {
                    "entity_id": "e004",
                    "entity_name": "PyScrAI",
                    "entity_type": "PRODUCT",
                    "attributes": {
                        "purpose": "Document Analysis",
                        "type": "Software System"
                    }
                }
            ]
        )
    )
    await asyncio.sleep(1)
    
    # 3. Publish relationship events
    print("\n🔗 Step 3: Publishing relationship events...")
    
    relationships = [
        {
            "source_entity": "Alice Smith",
            "target_entity": "TechCorp",
            "relationship_type": "WORKS_AT"
        },
        {
            "source_entity": "Bob Jones",
            "target_entity": "TechCorp",
            "relationship_type": "WORKS_AT"
        },
        {
            "source_entity": "Alice Smith",
            "target_entity": "Bob Jones",
            "relationship_type": "WORKS_WITH"
        },
        {
            "source_entity": "Alice Smith",
            "target_entity": "PyScrAI",
            "relationship_type": "BUILT"
        },
        {
            "source_entity": "Bob Jones",
            "target_entity": "PyScrAI",
            "relationship_type": "BUILT"
        }
    ]
    
    for rel in relationships:
        await bus.publish(
            events.TOPIC_RELATIONSHIP_FOUND,
            {
                "doc_id": "test_doc_001",
                "relationship": rel
            }
        )
        await asyncio.sleep(0.2)
    
    # 4. Publish graph updated event to trigger intelligence services
    print("\n📊 Step 4: Publishing graph update event...")
    await bus.publish(
        events.TOPIC_GRAPH_UPDATED,
        {
            "doc_id": "test_doc_001",
            "entity_count": 4,
            "relationship_count": 5
        }
    )
    
    print("\n" + "=" * 60)
    print("✅ Events published!")
    print("Intelligence services should now:")
    print("  1. Generate semantic profiles")
    print("  2. Create document narratives")
    print("  3. Analyze graph structure")
    print("  4. Display visualizations in the UI")
    print("=" * 60)
    
    # Keep running to see the results
    print("\nKeep the main application running to see the visualizations!")
    await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
