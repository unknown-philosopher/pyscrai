"""PyScrAI 2.0 Pipeline Phases.

This package contains the 5 phases of the Sequential Intelligence Pipeline:

1. FOUNDRY: Entity extraction and staging
2. LOOM: Relationship mapping and graph visualization  
3. CHRONICLE: Narrative synthesis with verification
4. CARTOGRAPHY: Spatial anchoring and map placement
5. ANVIL: Merge, conflict resolution, and finalization

Each phase produces staging artifacts that flow to the next phase:
- entities_staging.json (Foundry)
- graph_staging.json (Loom)
- narrative_report.md (Chronicle)
- spatial_metadata.json (Cartography)
- world.db (Anvil - final output)
"""

from pyscrai_forge.phases import foundry
from pyscrai_forge.phases import loom
from pyscrai_forge.phases import chronicle
from pyscrai_forge.phases import cartography
from pyscrai_forge.phases import anvil

__all__ = [
    "foundry",
    "loom", 
    "chronicle",
    "cartography",
    "anvil",
]

