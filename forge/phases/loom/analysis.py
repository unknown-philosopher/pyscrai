"""
Graph Analysis for Loom Phase.

Provides network analysis metrics and algorithms.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    nx = None

from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.phases.loom.graph import GraphManager

logger = get_logger("loom.analysis")


@dataclass
class CentralityScores:
    """Centrality metrics for nodes."""
    
    degree: dict[str, float] = field(default_factory=dict)
    betweenness: dict[str, float] = field(default_factory=dict)
    closeness: dict[str, float] = field(default_factory=dict)
    eigenvector: dict[str, float] = field(default_factory=dict)
    pagerank: dict[str, float] = field(default_factory=dict)


@dataclass
class GraphMetrics:
    """Overall graph metrics."""
    
    node_count: int = 0
    edge_count: int = 0
    density: float = 0.0
    is_connected: bool = False
    component_count: int = 0
    average_degree: float = 0.0
    clustering_coefficient: float = 0.0
    diameter: int | None = None


@dataclass
class PathResult:
    """Result of a path finding operation."""
    
    source: str
    target: str
    path: list[str]
    length: int
    exists: bool = True
    
    @property
    def edge_count(self) -> int:
        return max(0, len(self.path) - 1)


class GraphAnalyzer:
    """Provides network analysis capabilities.
    
    Supports:
    - Centrality measures (degree, betweenness, closeness, etc.)
    - Path finding
    - Community detection
    - Graph metrics
    
    Usage:
        analyzer = GraphAnalyzer(graph_manager)
        
        # Get centrality
        scores = analyzer.compute_centrality()
        top_nodes = analyzer.get_top_central_nodes(n=10)
        
        # Find paths
        path = analyzer.shortest_path("ACT_1", "ACT_2")
        
        # Get metrics
        metrics = analyzer.get_metrics()
    """
    
    def __init__(self, graph_manager: "GraphManager"):
        """Initialize the analyzer.
        
        Args:
            graph_manager: Graph manager instance
        """
        if not HAS_NETWORKX:
            raise ImportError("NetworkX required for graph analysis")
        
        self.graph_mgr = graph_manager
        self._centrality_cache: CentralityScores | None = None
    
    @property
    def graph(self) -> Any:
        """Get the underlying graph."""
        return self.graph_mgr.graph
    
    def invalidate_cache(self) -> None:
        """Invalidate cached computations."""
        self._centrality_cache = None
    
    # ========== Centrality ==========
    
    def compute_centrality(self, force: bool = False) -> CentralityScores:
        """Compute centrality measures for all nodes.
        
        Args:
            force: Force recomputation even if cached
            
        Returns:
            CentralityScores with all measures
        """
        if self._centrality_cache and not force:
            return self._centrality_cache
        
        G = self.graph
        
        if G.number_of_nodes() == 0:
            self._centrality_cache = CentralityScores()
            return self._centrality_cache
        
        scores = CentralityScores()
        
        # Degree centrality
        try:
            scores.degree = dict(nx.degree_centrality(G))
        except Exception as e:
            logger.warning(f"Degree centrality failed: {e}")
        
        # Betweenness centrality
        try:
            scores.betweenness = dict(nx.betweenness_centrality(G))
        except Exception as e:
            logger.warning(f"Betweenness centrality failed: {e}")
        
        # Closeness centrality
        try:
            scores.closeness = dict(nx.closeness_centrality(G))
        except Exception as e:
            logger.warning(f"Closeness centrality failed: {e}")
        
        # Eigenvector centrality (may fail on some graphs)
        try:
            scores.eigenvector = dict(nx.eigenvector_centrality(G, max_iter=500))
        except Exception as e:
            logger.debug(f"Eigenvector centrality failed: {e}")
        
        # PageRank
        try:
            scores.pagerank = dict(nx.pagerank(G))
        except Exception as e:
            logger.warning(f"PageRank failed: {e}")
        
        self._centrality_cache = scores
        return scores
    
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
        scores = self.compute_centrality()
        
        metric_map = {
            "degree": scores.degree,
            "betweenness": scores.betweenness,
            "closeness": scores.closeness,
            "eigenvector": scores.eigenvector,
            "pagerank": scores.pagerank,
        }
        
        score_dict = metric_map.get(metric, scores.pagerank)
        
        if not score_dict:
            return []
        
        sorted_nodes = sorted(
            score_dict.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        
        return sorted_nodes[:n]
    
    def get_node_centrality(self, entity_id: str) -> dict[str, float]:
        """Get all centrality scores for a specific node.
        
        Args:
            entity_id: Node ID
            
        Returns:
            Dict of metric name to score
        """
        scores = self.compute_centrality()
        
        return {
            "degree": scores.degree.get(entity_id, 0.0),
            "betweenness": scores.betweenness.get(entity_id, 0.0),
            "closeness": scores.closeness.get(entity_id, 0.0),
            "eigenvector": scores.eigenvector.get(entity_id, 0.0),
            "pagerank": scores.pagerank.get(entity_id, 0.0),
        }
    
    # ========== Paths ==========
    
    def shortest_path(
        self,
        source: str,
        target: str,
    ) -> PathResult:
        """Find the shortest path between two nodes.
        
        Args:
            source: Source node ID
            target: Target node ID
            
        Returns:
            PathResult with path information
        """
        G = self.graph
        
        if source not in G or target not in G:
            return PathResult(
                source=source,
                target=target,
                path=[],
                length=0,
                exists=False,
            )
        
        try:
            path = nx.shortest_path(G, source, target)
            return PathResult(
                source=source,
                target=target,
                path=path,
                length=len(path),
                exists=True,
            )
        except nx.NetworkXNoPath:
            return PathResult(
                source=source,
                target=target,
                path=[],
                length=0,
                exists=False,
            )
    
    def all_shortest_paths(
        self,
        source: str,
        target: str,
    ) -> list[list[str]]:
        """Find all shortest paths between two nodes.
        
        Args:
            source: Source node ID
            target: Target node ID
            
        Returns:
            List of paths
        """
        G = self.graph
        
        if source not in G or target not in G:
            return []
        
        try:
            return list(nx.all_shortest_paths(G, source, target))
        except nx.NetworkXNoPath:
            return []
    
    def paths_through_node(
        self,
        node: str,
        max_paths: int = 100,
    ) -> list[tuple[str, str]]:
        """Find paths that go through a specific node.
        
        Args:
            node: Node that paths must traverse
            max_paths: Maximum paths to return
            
        Returns:
            List of (source, target) pairs
        """
        G = self.graph
        
        if node not in G:
            return []
        
        predecessors = list(G.predecessors(node))
        successors = list(G.successors(node))
        
        paths = []
        for pred in predecessors:
            for succ in successors:
                if pred != succ:
                    paths.append((pred, succ))
                    if len(paths) >= max_paths:
                        return paths
        
        return paths
    
    # ========== Graph Metrics ==========
    
    def get_metrics(self) -> GraphMetrics:
        """Compute overall graph metrics.
        
        Returns:
            GraphMetrics with statistics
        """
        G = self.graph
        
        if G.number_of_nodes() == 0:
            return GraphMetrics()
        
        metrics = GraphMetrics(
            node_count=G.number_of_nodes(),
            edge_count=G.number_of_edges(),
        )
        
        # Density
        try:
            metrics.density = nx.density(G)
        except Exception:
            pass
        
        # Connectivity (for directed graphs, use weak connectivity)
        try:
            metrics.is_connected = nx.is_weakly_connected(G)
            metrics.component_count = nx.number_weakly_connected_components(G)
        except Exception:
            pass
        
        # Average degree
        try:
            metrics.average_degree = sum(dict(G.degree()).values()) / G.number_of_nodes()
        except Exception:
            pass
        
        # Clustering coefficient (convert to undirected)
        try:
            U = G.to_undirected()
            metrics.clustering_coefficient = nx.average_clustering(U)
        except Exception:
            pass
        
        # Diameter (only if connected)
        if metrics.is_connected and metrics.node_count < 1000:
            try:
                U = G.to_undirected()
                metrics.diameter = nx.diameter(U)
            except Exception:
                pass
        
        return metrics
    
    # ========== Community Detection ==========
    
    def detect_communities(self) -> list[set[str]]:
        """Detect communities in the graph.
        
        Returns:
            List of sets, each containing node IDs in a community
        """
        G = self.graph
        
        if G.number_of_nodes() == 0:
            return []
        
        try:
            # Convert to undirected for community detection
            U = G.to_undirected()
            
            # Use Louvain algorithm if available, fall back to greedy modularity
            try:
                from networkx.algorithms.community import louvain_communities
                communities = louvain_communities(U)
            except (ImportError, AttributeError):
                from networkx.algorithms.community import greedy_modularity_communities
                communities = list(greedy_modularity_communities(U))
            
            return [set(c) for c in communities]
            
        except Exception as e:
            logger.warning(f"Community detection failed: {e}")
            return []
    
    def get_node_community(self, entity_id: str) -> set[str] | None:
        """Get the community containing a specific node.
        
        Args:
            entity_id: Node to find
            
        Returns:
            Set of nodes in the same community, or None
        """
        communities = self.detect_communities()
        
        for community in communities:
            if entity_id in community:
                return community
        
        return None
