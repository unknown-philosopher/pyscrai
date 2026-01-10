"""Phase 2: LOOM - Relationship Mapping and Graph Visualization.

The Loom phase handles:
- Loading entities from Foundry staging
- Interactive graph visualization (networkx + Canvas)
- Relationship creation, editing, and inference
- Conflict detection and resolution
- Staging output to graph_staging.json

Output artifact: staging/graph_staging.json
"""

from pyscrai_forge.phases.loom.agent import LoomAgent
from pyscrai_forge.phases.loom.graph_viz import GraphCanvas
from pyscrai_forge.phases.loom.ui import LoomPanel
from pyscrai_forge.phases.loom.clustering import SemanticClusterer
from pyscrai_forge.phases.loom.assistant import LoomAssistant

__all__ = ["LoomAgent", "GraphCanvas", "LoomPanel", "SemanticClusterer", "LoomAssistant"]

