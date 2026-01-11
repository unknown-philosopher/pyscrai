"""
AdvancedGraphAnalysisService for PyScrAI Forge.

Provides graph analytics using NetworkX and relationship inference using LLM.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

from forge.core.event_bus import EventBus, EventPayload
from forge.core import events
from forge.infrastructure.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class AdvancedGraphAnalysisService:
    """Service for advanced graph analytics and relationship inference."""
    
    def __init__(
        self,
        event_bus: EventBus,
        llm_provider: LLMProvider,
        db_connection,  # DuckDB connection
    ):
        """Initialize the advanced graph analysis service.
        
        Args:
            event_bus: Event bus for subscribing to events
            llm_provider: LLM provider for relationship inference
            db_connection: DuckDB connection for querying graph data
        """
        self.event_bus = event_bus
        self.llm_provider = llm_provider
        self.db_conn = db_connection
        
        # Cache analysis results
        self._analysis_cache: Dict[str, Dict[str, Any]] = {}
        
    async def start(self):
        """Start the service and subscribe to events."""
        logger.info("Starting AdvancedGraphAnalysisService")
        
        # Subscribe to graph updated events
        await self.event_bus.subscribe(events.TOPIC_GRAPH_UPDATED, self.handle_graph_updated)
        
        logger.info("AdvancedGraphAnalysisService started")
    
    async def handle_graph_updated(self, payload: EventPayload):
        """Handle graph updated events by running analytics."""
        doc_id = payload.get("doc_id", "unknown")
        
        # Run comprehensive analysis
        await self.analyze_graph(doc_id)
    
    async def analyze_graph(self, doc_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Run comprehensive graph analysis.
        
        Args:
            doc_id: Optional document ID to scope analysis
            
        Returns:
            Analysis results dictionary
        """
        cache_key = doc_id or "global"
        
        # Check cache
        if cache_key in self._analysis_cache:
            return self._analysis_cache[cache_key]
        
        # Get graph data
        entities, relationships = self._get_graph_data(doc_id)
        
        if not entities or not relationships:
            logger.warning(f"Insufficient graph data for analysis (entities: {len(entities)}, relationships: {len(relationships)})")
            return None
        
        # Build NetworkX graph
        graph = self._build_networkx_graph(entities, relationships)
        
        # Compute metrics
        analysis = {
            "centrality": self._compute_centrality(graph),
            "communities": self._detect_communities(graph),
            "statistics": self._compute_statistics(graph),
        }
        
        # Infer missing relationships
        inferred = await self._infer_relationships(entities, relationships)
        if inferred:
            analysis["inferred_relationships"] = inferred
        
        # Cache results
        self._analysis_cache[cache_key] = analysis
        
        # Emit analysis event
        await self.event_bus.publish(
            events.TOPIC_GRAPH_ANALYSIS,
            {
                "doc_id": doc_id,
                "analysis": analysis,
            }
        )
        
        # Emit AG-UI event
        await self.event_bus.publish(
            events.TOPIC_AGUI_EVENT,
            events.create_agui_event(
                f"📈 Completed graph analysis: {len(entities)} entities, {len(relationships)} relationships",
                level="info"
            )
        )
        
        return analysis
    
    def _get_graph_data(self, doc_id: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Get entities and relationships from database."""
        entities = []
        relationships = []
        
        if not self.db_conn:
            return entities, relationships
        
        try:
            # Get entities
            if doc_id:
                # Get entities involved in relationships for this doc
                entity_results = self.db_conn.execute("""
                    SELECT DISTINCT e.id, e.type, e.label
                    FROM entities e
                    JOIN relationships r ON e.id = r.source OR e.id = r.target
                    WHERE r.doc_id = ?
                """, (doc_id,)).fetchall()
            else:
                entity_results = self.db_conn.execute("""
                    SELECT id, type, label
                    FROM entities
                """).fetchall()
            
            for row in entity_results:
                entities.append({
                    "id": row[0],
                    "type": row[1],
                    "label": row[2],
                })
            
            # Get relationships
            if doc_id:
                rel_results = self.db_conn.execute("""
                    SELECT source, target, type, confidence
                    FROM relationships
                    WHERE doc_id = ?
                """, (doc_id,)).fetchall()
            else:
                rel_results = self.db_conn.execute("""
                    SELECT source, target, type, confidence
                    FROM relationships
                """).fetchall()
            
            for row in rel_results:
                relationships.append({
                    "source": row[0],
                    "target": row[1],
                    "type": row[2],
                    "confidence": row[3],
                })
        
        except Exception as e:
            logger.error(f"Error fetching graph data: {e}")
        
        return entities, relationships
    
    def _build_networkx_graph(
        self,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ):
        """Build a NetworkX graph from entities and relationships."""
        try:
            import networkx as nx
        except ImportError:
            logger.error("NetworkX not installed. Run: pip install networkx")
            return None
        
        # Create directed graph
        G = nx.DiGraph()
        
        # Add nodes
        for entity in entities:
            G.add_node(
                entity["id"],
                type=entity["type"],
                label=entity["label"]
            )
        
        # Add edges
        for rel in relationships:
            G.add_edge(
                rel["source"],
                rel["target"],
                type=rel["type"],
                confidence=rel["confidence"]
            )
        
        return G
    
    def _compute_centrality(self, graph) -> Dict[str, Any]:
        """Compute centrality metrics for the graph."""
        if graph is None:
            return {}
        
        try:
            import networkx as nx
            
            # Degree centrality
            degree_centrality = nx.degree_centrality(graph)
            most_connected = sorted(
                [(node, score) for node, score in degree_centrality.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            # Betweenness centrality (bridges)
            betweenness = nx.betweenness_centrality(graph)
            bridges = sorted(
                [(node, score) for node, score in betweenness.items() if score > 0],
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            # PageRank
            pagerank = nx.pagerank(graph)
            influential = sorted(
                [(node, score) for node, score in pagerank.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            return {
                "most_connected": [{"entity": node, "degree": score} for node, score in most_connected],
                "bridges": [{"entity": node, "betweenness": score} for node, score in bridges],
                "influential": [{"entity": node, "pagerank": score} for node, score in influential],
            }
        
        except Exception as e:
            logger.error(f"Error computing centrality: {e}")
            return {}
    
    def _detect_communities(self, graph) -> List[Dict[str, Any]]:
        """Detect communities in the graph."""
        if graph is None:
            return []
        
        try:
            import networkx as nx
            
            # Convert to undirected for community detection
            undirected = graph.to_undirected()
            
            # Use Louvain community detection
            try:
                from networkx.algorithms import community
                communities = community.louvain_communities(undirected)
            except (ImportError, AttributeError):
                # Fallback to simple connected components
                communities = list(nx.connected_components(undirected))
            
            # Format results
            result = []
            for i, comm in enumerate(communities[:10]):  # Top 10 communities
                if len(comm) >= 2:  # Only include communities with 2+ nodes
                    result.append({
                        "id": i,
                        "entities": list(comm)[:20],  # Limit to 20 entities
                        "size": len(comm),
                    })
            
            return result
        
        except Exception as e:
            logger.error(f"Error detecting communities: {e}")
            return []
    
    def _compute_statistics(self, graph) -> Dict[str, Any]:
        """Compute basic graph statistics."""
        if graph is None:
            return {}
        
        try:
            import networkx as nx
            
            return {
                "num_nodes": graph.number_of_nodes(),
                "num_edges": graph.number_of_edges(),
                "density": nx.density(graph),
                "is_connected": nx.is_weakly_connected(graph),
                "num_components": nx.number_weakly_connected_components(graph),
            }
        
        except Exception as e:
            logger.error(f"Error computing statistics: {e}")
            return {}
    
    async def _infer_relationships(
        self,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Infer missing relationships using LLM.
        
        Looks for entities that are mentioned together but lack direct relationships.
        """
        # Build adjacency for quick lookup
        adjacency = defaultdict(set)
        for rel in relationships:
            adjacency[rel["source"]].add(rel["target"])
            adjacency[rel["target"]].add(rel["source"])
        
        # Find entity pairs that might be related but aren't connected
        candidates = []
        entity_ids = [e["id"] for e in entities]
        
        for i, entity1 in enumerate(entities[:20]):  # Limit to first 20 for performance
            for entity2 in entities[i+1:20]:
                # Skip if already connected
                if entity2["id"] in adjacency[entity1["id"]]:
                    continue
                
                # Check if they have common neighbors (potential transitive relationship)
                neighbors1 = adjacency[entity1["id"]]
                neighbors2 = adjacency[entity2["id"]]
                common = neighbors1 & neighbors2
                
                if len(common) >= 2:  # At least 2 common neighbors
                    candidates.append((entity1, entity2, list(common)))
        
        # Infer relationships for top candidates
        inferred = []
        for entity1, entity2, common_neighbors in candidates[:5]:  # Top 5 candidates
            relationship = await self._infer_relationship_with_llm(
                entity1, entity2, common_neighbors
            )
            if relationship:
                inferred.append(relationship)
                
                # Emit inferred relationship event
                await self.event_bus.publish(
                    events.TOPIC_INFERRED_RELATIONSHIP,
                    relationship
                )
        
        return inferred
    
    async def _infer_relationship_with_llm(
        self,
        entity1: Dict[str, Any],
        entity2: Dict[str, Any],
        common_neighbors: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to infer a relationship between two entities.
        
        Args:
            entity1: First entity
            entity2: Second entity
            common_neighbors: List of common neighbor entity IDs
            
        Returns:
            Inferred relationship dictionary or None
        """
        prompt = f"""You are an expert knowledge graph analyst. Two entities are connected through common neighbors, suggesting they may have a direct relationship.

Entity 1: {entity1['label']} ({entity1['type']})
Entity 2: {entity2['label']} ({entity2['type']})
Common connections: {', '.join(common_neighbors[:5])}

Analyze these entities and determine if there is a plausible direct relationship between them. If yes, provide:
1. The relationship type (e.g., WORKS_WITH, INFLUENCED_BY, PART_OF, etc.)
2. A confidence score (0.0 to 1.0)
3. Brief justification

Respond in JSON format:
{{
  "exists": true/false,
  "type": "RELATIONSHIP_TYPE",
  "confidence": 0.0-1.0,
  "justification": "brief explanation"
}}

Respond with ONLY the JSON, no additional text."""
        
        try:
            # Get available models
            models = await self.llm_provider.list_models()
            model = models[0].id if models else self.llm_provider.default_model or ""
            
            response = await self.llm_provider.complete(
                messages=[{"role": "user", "content": prompt}],
                model=model,
                max_tokens=200,
                temperature=0.3,
            )
            
            # Parse JSON response
            content = ""
            if "choices" in response and response["choices"]:
                content = response["choices"][0].get("message", {}).get("content", "")
            result = json.loads(content.strip())
            
            if result.get("exists") and result.get("confidence", 0) >= 0.5:
                return {
                    "source": entity1["id"],
                    "target": entity2["id"],
                    "type": result["type"],
                    "confidence": result["confidence"],
                    "justification": result.get("justification", ""),
                    "inferred": True,
                }
            
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inferring relationship with LLM: {e}")
            return None
