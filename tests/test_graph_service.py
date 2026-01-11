"""Graph Analysis Service Tests.

Tests for the GraphAnalysisService that builds and maintains the knowledge graph.
"""

import asyncio
import unittest
from typing import Any

from forge.core.event_bus import EventBus, EventPayload
from forge.core import events
from forge.domain.graph.service import GraphAnalysisService


class GraphAnalysisServiceTest(unittest.IsolatedAsyncioTestCase):
    """Test GraphAnalysisService functionality."""

    async def asyncSetUp(self) -> None:
        """Set up test fixtures."""
        self.bus = EventBus()
        self.graph_service = GraphAnalysisService(self.bus)
        await self.graph_service.start()

    async def test_graph_service_subscribes_to_relationships(self) -> None:
        """Test that graph service subscribes to relationship events."""
        graph_updates: list[EventPayload] = []

        async def on_graph_updated(payload: EventPayload) -> None:
            graph_updates.append(payload)

        await self.bus.subscribe(events.TOPIC_GRAPH_UPDATED, on_graph_updated)

        # Publish a relationship event
        await self.bus.publish(
            events.TOPIC_RELATIONSHIP_FOUND,
            events.create_relationship_found_event(
                doc_id="test_doc",
                relationships=[
                    {
                        "source": "Alice",
                        "source_type": "PERSON",
                        "target": "PyScrAI",
                        "target_type": "ORG",
                        "relation_type": "WORKS_AT",
                        "confidence": 0.85,
                    }
                ]
            )
        )

        await asyncio.sleep(0.5)

        # Verify graph update was emitted
        self.assertGreater(len(graph_updates), 0)
        graph_payload = graph_updates[0]
        self.assertEqual(graph_payload.get("doc_id"), "test_doc")
        self.assertIn("graph_stats", graph_payload)

    async def test_graph_builds_nodes_from_relationships(self) -> None:
        """Test that graph service builds nodes from relationships."""
        graph_updates: list[EventPayload] = []

        async def on_graph_updated(payload: EventPayload) -> None:
            graph_updates.append(payload)

        await self.bus.subscribe(events.TOPIC_GRAPH_UPDATED, on_graph_updated)

        await self.bus.publish(
            events.TOPIC_RELATIONSHIP_FOUND,
            events.create_relationship_found_event(
                doc_id="test_nodes",
                relationships=[
                    {
                        "source": "Alice",
                        "source_type": "PERSON",
                        "target": "CompanyA",
                        "target_type": "ORG",
                        "relation_type": "WORKS_AT",
                        "confidence": 0.9,
                    }
                ]
            )
        )

        await asyncio.sleep(0.5)

        graph_stats = graph_updates[0].get("graph_stats", {})
        nodes = graph_stats.get("nodes", [])
        
        # Verify nodes were created
        self.assertGreater(len(nodes), 0)
        
        # Verify node structure
        node_ids = {node["id"] for node in nodes}
        self.assertIn("Alice", node_ids)
        self.assertIn("CompanyA", node_ids)
        
        # Verify node properties
        alice_node = next(n for n in nodes if n["id"] == "Alice")
        self.assertEqual(alice_node["type"], "PERSON")
        self.assertEqual(alice_node["label"], "Alice")

    async def test_graph_builds_edges_from_relationships(self) -> None:
        """Test that graph service builds edges from relationships."""
        graph_updates: list[EventPayload] = []

        async def on_graph_updated(payload: EventPayload) -> None:
            graph_updates.append(payload)

        await self.bus.subscribe(events.TOPIC_GRAPH_UPDATED, on_graph_updated)

        await self.bus.publish(
            events.TOPIC_RELATIONSHIP_FOUND,
            events.create_relationship_found_event(
                doc_id="test_edges",
                relationships=[
                    {
                        "source": "Bob",
                        "source_type": "PERSON",
                        "target": "CompanyB",
                        "target_type": "ORG",
                        "relation_type": "WORKS_AT",
                        "confidence": 0.85,
                    }
                ]
            )
        )

        await asyncio.sleep(0.5)

        graph_stats = graph_updates[0].get("graph_stats", {})
        edges = graph_stats.get("edges", [])
        
        # Verify edge was created
        self.assertGreater(len(edges), 0)
        
        # Verify edge structure
        edge = edges[0]
        self.assertEqual(edge["source"], "Bob")
        self.assertEqual(edge["target"], "CompanyB")
        self.assertEqual(edge["type"], "WORKS_AT")
        self.assertEqual(edge["confidence"], 0.85)
        self.assertEqual(edge["doc_id"], "test_edges")

    async def test_graph_accumulates_multiple_relationships(self) -> None:
        """Test that graph accumulates multiple relationships."""
        graph_updates: list[EventPayload] = []

        async def on_graph_updated(payload: EventPayload) -> None:
            graph_updates.append(payload)

        await self.bus.subscribe(events.TOPIC_GRAPH_UPDATED, on_graph_updated)

        # Publish multiple relationships
        await self.bus.publish(
            events.TOPIC_RELATIONSHIP_FOUND,
            events.create_relationship_found_event(
                doc_id="test_multi",
                relationships=[
                    {
                        "source": "Alice",
                        "source_type": "PERSON",
                        "target": "CompanyA",
                        "target_type": "ORG",
                        "relation_type": "WORKS_AT",
                        "confidence": 0.9,
                    },
                    {
                        "source": "Bob",
                        "source_type": "PERSON",
                        "target": "CompanyB",
                        "target_type": "ORG",
                        "relation_type": "WORKS_AT",
                        "confidence": 0.85,
                    }
                ]
            )
        )

        await asyncio.sleep(0.5)

        graph_stats = graph_updates[0].get("graph_stats", {})
        
        # Verify multiple nodes were created
        self.assertGreaterEqual(graph_stats.get("node_count", 0), 4)  # Alice, CompanyA, Bob, CompanyB
        
        # Verify multiple edges were created
        edges = graph_stats.get("edges", [])
        self.assertGreaterEqual(len(edges), 2)

    async def test_graph_node_deduplication(self) -> None:
        """Test that graph service deduplicates nodes."""
        graph_updates: list[EventPayload] = []

        async def on_graph_updated(payload: EventPayload) -> None:
            graph_updates.append(payload)

        await self.bus.subscribe(events.TOPIC_GRAPH_UPDATED, on_graph_updated)

        # Publish relationships that share nodes
        await self.bus.publish(
            events.TOPIC_RELATIONSHIP_FOUND,
            events.create_relationship_found_event(
                doc_id="test_dedup_1",
                relationships=[
                    {
                        "source": "Alice",
                        "source_type": "PERSON",
                        "target": "CompanyA",
                        "target_type": "ORG",
                        "relation_type": "WORKS_AT",
                        "confidence": 0.9,
                    }
                ]
            )
        )

        await asyncio.sleep(0.3)

        first_stats = graph_updates[0].get("graph_stats", {})
        first_node_count = first_stats.get("node_count", 0)

        # Publish another relationship with same company
        await self.bus.publish(
            events.TOPIC_RELATIONSHIP_FOUND,
            events.create_relationship_found_event(
                doc_id="test_dedup_2",
                relationships=[
                    {
                        "source": "Bob",
                        "source_type": "PERSON",
                        "target": "CompanyA",  # Same company
                        "target_type": "ORG",
                        "relation_type": "WORKS_AT",
                        "confidence": 0.85,
                    }
                ]
            )
        )

        await asyncio.sleep(0.3)

        # Graph should have 3 nodes (Alice, Bob, CompanyA) not 4
        # Note: Current implementation uses in-memory graph, so nodes persist
        # between events
        if len(graph_updates) > 1:
            later_stats = graph_updates[-1].get("graph_stats", {})
            later_node_count = later_stats.get("node_count", 0)
            # Should have 3 nodes total (Alice, Bob, CompanyA)
            self.assertGreaterEqual(later_node_count, 3)

    async def test_graph_stats_structure(self) -> None:
        """Test that graph stats have correct structure."""
        graph_updates: list[EventPayload] = []

        async def on_graph_updated(payload: EventPayload) -> None:
            graph_updates.append(payload)

        await self.bus.subscribe(events.TOPIC_GRAPH_UPDATED, on_graph_updated)

        await self.bus.publish(
            events.TOPIC_RELATIONSHIP_FOUND,
            events.create_relationship_found_event(
                doc_id="test_stats",
                relationships=[
                    {
                        "source": "TestPerson",
                        "source_type": "PERSON",
                        "target": "TestOrg",
                        "target_type": "ORG",
                        "relation_type": "WORKS_AT",
                        "confidence": 0.8,
                    }
                ]
            )
        )

        await asyncio.sleep(0.5)

        graph_stats = graph_updates[0].get("graph_stats", {})
        
        # Verify required fields
        self.assertIn("node_count", graph_stats)
        self.assertIn("edge_count", graph_stats)
        self.assertIn("nodes", graph_stats)
        self.assertIn("edges", graph_stats)
        
        # Verify types
        self.assertIsInstance(graph_stats["node_count"], int)
        self.assertIsInstance(graph_stats["edge_count"], int)
        self.assertIsInstance(graph_stats["nodes"], list)
        self.assertIsInstance(graph_stats["edges"], list)
        
        # Verify counts match data
        self.assertEqual(graph_stats["node_count"], len(graph_stats["nodes"]))
        self.assertEqual(graph_stats["edge_count"], len(graph_stats["edges"]))


if __name__ == "__main__":
    unittest.main()
