"""Phase 4: CARTOGRAPHY - Spatial Anchoring and Map Placement.

The Cartography phase handles:
- Loading entities from previous phases
- Grid map visualization and editing
- Entity positioning via drag-and-drop
- Region boundary management
- CartographerAgent for position suggestions
- Staging output to spatial_metadata.json

Output artifact: staging/spatial_metadata.json
"""

from pyscrai_forge.phases.cartography.agent import CartographerAgent
from pyscrai_forge.phases.cartography.map_widget import MapCanvas
from pyscrai_forge.phases.cartography.ui import CartographyPanel

__all__ = ["CartographerAgent", "MapCanvas", "CartographyPanel"]

