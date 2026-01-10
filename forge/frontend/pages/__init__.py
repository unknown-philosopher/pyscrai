"""
Forge Frontend Pages.

Each page corresponds to a phase in the Intelligence Pipeline:
- Landing: Project selection
- Dashboard: Overview and stats
- OSINT: Extraction & Sentinel triage
- HUMINT: Entity management
- SIGINT: Relationship/graph analysis
- SYNTH: Narrative editing
- GEOINT: Cartography/mapping
- ANVIL: Finalization & export
"""

from forge.frontend.pages import (
    anvil,
    dashboard,
    geoint,
    humint,
    landing,
    osint,
    sigint,
    synth,
)

__all__ = [
    "landing",
    "dashboard",
    "osint",
    "humint",
    "sigint",
    "synth",
    "geoint",
    "anvil",
]
