"""
Graph Manager for Loom Phase.

NetworkX-based graph representation of entities and relationships.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterator
from dataclasses import dataclass, field

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    nx = None

from forge.core.models.entity import Entity, EntityType
from forge.core.models.relationship import Relationship, RelationType
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.app.state import ForgeState

logger = get_logger("loom.graph")


@dataclass
class NodeData:
    """Data associated with a graph node."""
    
    entity_id: str
    name: str
    entity_type: EntityType
    description: str = ""
    attributes: dict = field(default_factory=dict)
    
    @classmethod
    def from_entity(cls, entity: Entity) -> "NodeData":
        return cls(
            entity_id=entity.id,
            name=entity.name,
            entity_type=entity.entity_type,
            description=entity.description,
            attributes=entity.attributes.copy(),
        )


@dataclass
class EdgeData:
    """Data associated with a graph edge."""
    
    relationship_id: str
    relation_type: RelationType
    description: str = ""
    strength: float = 0.5
    attributes: dict = field(default_factory=dict)
    
    @classmethod
    def from_relationship(cls, relationship: Relationship) -> "EdgeData":
        return cls(
            relationship_id=relationship.id,
            relation_type=relationship.relationship_type,
            description=relationship.description,
            strength=relationship.strength,
            attributes=relationship.attributes.copy(),
        )


class GraphManager:
    """Manages NetworkX graph representation of the world.
    
    Provides:
    - Graph construction from entities/relationships
    - Node/edge operations
    - Subgraph extraction
    - Layout computation
    
    Usage:
        graph_mgr = GraphManager(state)
        graph_mgr.build_graph()
        
        # Get graph
        G = graph_mgr.graph
        
        # Get neighbors
        neighbors = graph_mgr.get_neighbors("ACT_123")
        
        # Get subgraph
        subgraph = graph_mgr.get_subgraph_around("ACT_123", depth=2)
    """
    
    def __init__(self, state: "ForgeState"):
        """Initialize the graph manager.
        
        Args:
            state: Application state
        """
        if not HAS_NETWORKX:
            raise ImportError("NetworkX is required for Loom phase. Install with: pip install networkx")
        
        self.state = state
        self._graph: Any = nx.DiGraph()
        self._entity_map: dict[str, Entity] = {}
        self._relationship_map: dict[str, Relationship] = {}
    
    @property
    def graph(self) -> Any:
        """Get the NetworkX graph."""
        return self._graph
    
    @property
    def node_count(self) -> int:
        """Get number of nodes in graph."""
        return self._graph.number_of_nodes()
    
    @property
    def edge_count(self) -> int:
        """Get number of edges in graph."""
        return self._graph.number_of_edges()
    
    def build_graph(self) -> None:
        """Build the graph from database entities and relationships."""
        self._graph.clear()
        self._entity_map.clear()
        self._relationship_map.clear()
        
        # Add all entities as nodes
        for entity in self.state.db.get_all_entities():
            self.add_entity(entity)
        
        # Add all relationships as edges
        for entity in self._entity_map.values():
            relationships = self.state.db.get_relationships_for_entity(entity.id)
            for rel in relationships:
                if rel.id not in self._relationship_map:
                    self.add_relationship(rel)
        
        logger.info(
            f"Built graph: {self.node_count} nodes, {self.edge_count} edges"
        )
    
    def add_entity(self, entity: Entity) -> None:
        """Add an entity as a node.
        
        Args:
            entity: Entity to add
        """
        node_data = NodeData.from_entity(entity)
        self._graph.add_node(
            entity.id,
            **{
                "name": node_data.name,
                "type": node_data.entity_type.value,
                "description": node_data.description,
                "attributes": node_data.attributes,
            }
        )
        self._entity_map[entity.id] = entity
    
    def add_relationship(self, relationship: Relationship) -> None:
        """Add a relationship as an edge.
        
        Args:
            relationship: Relationship to add
        """
        # Ensure both endpoints exist
        if relationship.source_id not in self._graph:
            logger.warning(f"Source node missing: {relationship.source_id}")
            return
        if relationship.target_id not in self._graph:
            logger.warning(f"Target node missing: {relationship.target_id}")
            return
        
        edge_data = EdgeData.from_relationship(relationship)
        self._graph.add_edge(
            relationship.source_id,
            relationship.target_id,
            **{
                "id": edge_data.relationship_id,
                "type": edge_data.relation_type.value,
                "description": edge_data.description,
                "strength": edge_data.strength,
                "weight": 1.0 - abs(edge_data.strength),  # For path algorithms
                "attributes": edge_data.attributes,
            }
        )
        self._relationship_map[relationship.id] = relationship
    
    def remove_entity(self, entity_id: str) -> None:
        """Remove an entity node and its edges.
        
        Args:
            entity_id: ID of entity to remove
        """
        if entity_id in self._graph:
            self._graph.remove_node(entity_id)
            self._entity_map.pop(entity_id, None)
    
    def remove_relationship(self, relationship_id: str) -> None:
        """Remove a relationship edge.
        
        Args:
            relationship_id: ID of relationship to remove
        """
        rel = self._relationship_map.get(relationship_id)
        if rel:
            self._graph.remove_edge(rel.source_id, rel.target_id)
            del self._relationship_map[relationship_id]
    
    # ========== Node Queries ==========
    
    def get_node_data(self, entity_id: str) -> dict | None:
        """Get data for a node.
        
        Args:
            entity_id: Node ID
            
        Returns:
            Node data dict or None
        """
        if entity_id in self._graph:
            return dict(self._graph.nodes[entity_id])
        return None
    
    def get_entity(self, entity_id: str) -> Entity | None:
        """Get the entity for a node.
        
        Args:
            entity_id: Node ID
            
        Returns:
            Entity or None
        """
        return self._entity_map.get(entity_id)
    
    def get_neighbors(
        self,
        entity_id: str,
        direction: str = "both",
    ) -> list[str]:
        """Get neighboring node IDs.
        
        Args:
            entity_id: Center node ID
            direction: "in", "out", or "both"
            
        Returns:
            List of neighbor IDs
        """
        if entity_id not in self._graph:
            return []
        
        if direction == "in":
            return list(self._graph.predecessors(entity_id))
        elif direction == "out":
            return list(self._graph.successors(entity_id))
        else:
            preds = set(self._graph.predecessors(entity_id))
            succs = set(self._graph.successors(entity_id))
            return list(preds | succs)
    
    def get_nodes_by_type(self, entity_type: EntityType) -> list[str]:
        """Get all node IDs of a given type.
        
        Args:
            entity_type: Type to filter by
            
        Returns:
            List of node IDs
        """
        type_val = entity_type.value
        return [
            node_id for node_id, data in self._graph.nodes(data=True)
            if data.get("type") == type_val
        ]
    
    # ========== Subgraphs ==========
    
    def get_subgraph_around(
        self,
        entity_id: str,
        depth: int = 1,
    ) -> Any:
        """Get a subgraph centered on an entity.
        
        Args:
            entity_id: Center node ID
            depth: How many hops to include
            
        Returns:
            Subgraph as DiGraph
        """
        if entity_id not in self._graph:
            return nx.DiGraph()
        
        # BFS to collect nodes within depth
        nodes = {entity_id}
        frontier = {entity_id}
        
        for _ in range(depth):
            next_frontier = set()
            for node in frontier:
                neighbors = self.get_neighbors(node, direction="both")
                for neighbor in neighbors:
                    if neighbor not in nodes:
                        nodes.add(neighbor)
                        next_frontier.add(neighbor)
            frontier = next_frontier
        
        return self._graph.subgraph(nodes).copy()
    
    def get_subgraph_for_types(
        self,
        entity_types: list[EntityType],
    ) -> Any:
        """Get a subgraph containing only certain entity types.
        
        Args:
            entity_types: Types to include
            
        Returns:
            Filtered subgraph
        """
        type_vals = {t.value for t in entity_types}
        nodes = [
            node_id for node_id, data in self._graph.nodes(data=True)
            if data.get("type") in type_vals
        ]
        return self._graph.subgraph(nodes).copy()
    
    # ========== Layout ==========
    
    def compute_layout(
        self,
        algorithm: str = "spring",
        **kwargs: Any,
    ) -> dict[str, tuple[float, float]]:
        """Compute node positions for visualization.
        
        Args:
            algorithm: Layout algorithm ("spring", "circular", "kamada_kawai", etc.)
            **kwargs: Additional arguments for the layout function
            
        Returns:
            Dict mapping node IDs to (x, y) positions
        """
        if self.node_count == 0:
            return {}
        
        layout_funcs = {
            "spring": nx.spring_layout,
            "circular": nx.circular_layout,
            "kamada_kawai": nx.kamada_kawai_layout,
            "shell": nx.shell_layout,
            "spectral": nx.spectral_layout,
            "random": nx.random_layout,
        }
        
        layout_func = layout_funcs.get(algorithm, nx.spring_layout)
        
        try:
            pos = layout_func(self._graph, **kwargs)
            return {node: (float(x), float(y)) for node, (x, y) in pos.items()}
        except Exception as e:
            logger.warning(f"Layout computation failed: {e}")
            return nx.random_layout(self._graph)
    
    # ========== Export ==========
    
    def to_dict(self) -> dict:
        """Export graph to dictionary format.
        
        Returns:
            Dict with nodes and edges
        """
        return {
            "nodes": [
                {"id": n, **data}
                for n, data in self._graph.nodes(data=True)
            ],
            "edges": [
                {"source": u, "target": v, **data}
                for u, v, data in self._graph.edges(data=True)
            ],
        }
    
    def to_cytoscape(self) -> dict:
        """Export graph in Cytoscape.js format.
        
        Returns:
            Cytoscape-compatible dict
        """
        elements = []
        
        # Add nodes
        for node_id, data in self._graph.nodes(data=True):
            elements.append({
                "data": {"id": node_id, **data},
                "group": "nodes",
            })
        
        # Add edges
        for source, target, data in self._graph.edges(data=True):
            elements.append({
                "data": {
                    "source": source,
                    "target": target,
                    **data,
                },
                "group": "edges",
            })
        
        return {"elements": elements}
