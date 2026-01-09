"""
Relationships Phase Orchestrator.

Coordinates graph visualization and analysis operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from forge.phases.p2_relationships.graph import GraphManager
from forge.phases.p2_relationships.analysis import GraphAnalyzer, GraphMetrics, CentralityScores
from forge.core.models.entity import EntityType
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.app.state import ForgeState

logger = get_logger("p2_relationships")


class RelationshipsView(str, Enum):
    """Current view mode in Relationships."""
    FULL_GRAPH = "full_graph"
    SUBGRAPH = "subgraph"
    TYPE_FILTER = "type_filter"
    COMMUNITY = "community"


@dataclass
class RelationshipsContext:
    """Context for Relationships operations."""
    
    view: RelationshipsView = RelationshipsView.FULL_GRAPH
    center_entity_id: str | None = None
    depth: int = 2
    filter_types: list[EntityType] = field(default_factory=list)
    selected_community: int | None = None
    layout_algorithm: str = "spring"
    show_labels: bool = True
    show_edge_labels: bool = False


class RelationshipsOrchestrator:
    """Orchestrates the Relationships graph visualization phase.
    
    Provides:
    - Graph building and refresh
    - View mode management
    - Analysis operations
    - Layout computation
    - Export capabilities
    
    Usage:
        relationships = RelationshipsOrchestrator(state)
        relationships.build_graph()
        
        # Get full graph data for visualization
        data = relationships.get_visualization_data()
        
        # Focus on an entity
        relationships.focus_on_entity("ACT_123", depth=2)
        data = relationships.get_visualization_data()
        
        # Analyze
        top_nodes = relationships.get_top_central_nodes()
        metrics = relationships.get_metrics()
    """
    
    def __init__(self, state: "ForgeState"):
        """Initialize the orchestrator.
        
        Args:
            state: Application state
        """
        self.state = state
        self.graph_mgr = GraphManager(state)
        self.analyzer = GraphAnalyzer(self.graph_mgr)
        self.context = RelationshipsContext()
        self._communities: list[set[str]] | None = None
    
    def build_graph(self) -> None:
        """Build or rebuild the graph from database."""
        self.graph_mgr.build_graph()
        self.analyzer.invalidate_cache()
        self._communities = None
        logger.info(
            f"Graph built: {self.graph_mgr.node_count} nodes, "
            f"{self.graph_mgr.edge_count} edges"
        )
    
    def refresh(self) -> None:
        """Refresh the graph from database."""
        self.build_graph()
    
    # ========== View Management ==========
    
    def set_view(self, view: RelationshipsView) -> None:
        """Set the current view mode."""
        self.context.view = view
    
    def focus_on_entity(
        self,
        entity_id: str,
        depth: int = 2,
    ) -> None:
        """Focus the view on a specific entity.
        
        Args:
            entity_id: Entity to center on
            depth: Number of hops to include
        """
        self.context.view = RelationshipsView.SUBGRAPH
        self.context.center_entity_id = entity_id
        self.context.depth = depth
    
    def filter_by_types(self, entity_types: list[EntityType]) -> None:
        """Filter view to specific entity types.
        
        Args:
            entity_types: Types to include
        """
        self.context.view = RelationshipsView.TYPE_FILTER
        self.context.filter_types = entity_types
    
    def show_community(self, community_index: int) -> None:
        """Show a specific community.
        
        Args:
            community_index: Index of community to show
        """
        self.context.view = RelationshipsView.COMMUNITY
        self.context.selected_community = community_index
    
    def reset_view(self) -> None:
        """Reset to full graph view."""
        self.context = RelationshipsContext()
    
    # ========== Visualization Data ==========
    
    def get_visualization_data(self) -> dict:
        """Get data for the current view.
        
        Returns:
            Dict with nodes, edges, and layout
        """
        # Get appropriate subgraph based on view
        if self.context.view == RelationshipsView.SUBGRAPH and self.context.center_entity_id:
            G = self.graph_mgr.get_subgraph_around(
                self.context.center_entity_id,
                self.context.depth,
            )
        elif self.context.view == RelationshipsView.TYPE_FILTER and self.context.filter_types:
            G = self.graph_mgr.get_subgraph_for_types(self.context.filter_types)
        elif self.context.view == RelationshipsView.COMMUNITY and self.context.selected_community is not None:
            communities = self.get_communities()
            if 0 <= self.context.selected_community < len(communities):
                node_ids = communities[self.context.selected_community]
                G = self.graph_mgr.graph.subgraph(node_ids).copy()
            else:
                G = self.graph_mgr.graph
        else:
            G = self.graph_mgr.graph
        
        # Compute layout
        import networkx as nx
        if G.number_of_nodes() > 0:
            try:
                layout_func = getattr(nx, f"{self.context.layout_algorithm}_layout")
                positions = layout_func(G)
            except Exception:
                positions = nx.spring_layout(G)
        else:
            positions = {}
        
        # Build node data
        nodes = []
        for node_id, data in G.nodes(data=True):
            pos = positions.get(node_id, (0, 0))
            entity = self.graph_mgr.get_entity(node_id)
            
            node_data = {
                "id": node_id,
                "x": float(pos[0]),
                "y": float(pos[1]),
                "label": data.get("name", node_id),
                "type": data.get("type", "unknown"),
                "description": data.get("description", ""),
            }
            
            # Add centrality if available
            if self.analyzer._centrality_cache:
                node_data["centrality"] = self.analyzer.get_node_centrality(node_id)
            
            nodes.append(node_data)
        
        # Build edge data
        edges = []
        for source, target, data in G.edges(data=True):
            edge_data = {
                "source": source,
                "target": target,
                "type": data.get("type", "related"),
                "strength": data.get("strength", 0.5),
                "label": data.get("description", "") if self.context.show_edge_labels else "",
            }
            edges.append(edge_data)
        
        return {
            "nodes": nodes,
            "edges": edges,
            "view": self.context.view.value,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }
    
    def get_cytoscape_data(self) -> dict:
        """Get data in Cytoscape.js format.
        
        Returns:
            Cytoscape-compatible dict
        """
        return self.graph_mgr.to_cytoscape()
    
    # ========== Analysis ==========
    
    def compute_centrality(self) -> CentralityScores:
        """Compute centrality measures."""
        return self.analyzer.compute_centrality()
    
    def get_top_central_nodes(
        self,
        n: int = 10,
        metric: str = "pagerank",
    ) -> list[tuple[str, float]]:
        """Get the most central nodes.
        
        Args:
            n: Number of nodes to return
            metric: Centrality metric to use
            
        Returns:
            List of (node_id, score) tuples
        """
        return self.analyzer.get_top_central_nodes(n, metric)
    
    def get_metrics(self) -> GraphMetrics:
        """Get overall graph metrics."""
        return self.analyzer.get_metrics()
    
    def find_path(
        self,
        source: str,
        target: str,
    ) -> list[str]:
        """Find shortest path between two nodes.
        
        Args:
            source: Source node ID
            target: Target node ID
            
        Returns:
            List of node IDs in path, or empty if no path
        """
        result = self.analyzer.shortest_path(source, target)
        return result.path if result.exists else []
    
    def get_communities(self) -> list[set[str]]:
        """Get detected communities.
        
        Returns:
            List of node ID sets
        """
        if self._communities is None:
            self._communities = self.analyzer.detect_communities()
        return self._communities
    
    def get_entity_neighbors(
        self,
        entity_id: str,
        direction: str = "both",
    ) -> list[dict]:
        """Get neighbors of an entity with details.
        
        Args:
            entity_id: Entity to get neighbors for
            direction: "in", "out", or "both"
            
        Returns:
            List of neighbor info dicts
        """
        neighbor_ids = self.graph_mgr.get_neighbors(entity_id, direction)
        
        neighbors = []
        for nid in neighbor_ids:
            entity = self.graph_mgr.get_entity(nid)
            if entity:
                neighbors.append({
                    "id": entity.id,
                    "name": entity.name,
                    "type": entity.type.value,
                })
        
        return neighbors
    
    # ========== Stats ==========
    
    def get_stats(self) -> dict[str, Any]:
        """Get Relationships statistics.
        
        Returns:
            Statistics dict
        """
        metrics = self.get_metrics()
        communities = self.get_communities()
        
        return {
            "node_count": metrics.node_count,
            "edge_count": metrics.edge_count,
            "density": metrics.density,
            "is_connected": metrics.is_connected,
            "component_count": metrics.component_count,
            "average_degree": metrics.average_degree,
            "clustering_coefficient": metrics.clustering_coefficient,
            "community_count": len(communities),
            "view": self.context.view.value,
        }
