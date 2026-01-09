"""
Forge Phases - Pipeline UI and frontend logic.

Each phase uses strict functional naming in code while displaying
UI "lore" labels (OSINT, HUMINT, SIGINT, etc.) to users.
"""

# Phase mapping for UI display
PHASE_LABELS = {
    "p0_extraction": ("OSINT", "Phase 0: Extraction"),
    "p1_entities": ("HUMINT", "Phase 1: Entities"),
    "p2_relationships": ("SIGINT", "Phase 2: Relationships"),
    "p3_narrative": ("SYNTH", "Phase 3: Narrative"),
    "p4_map": ("GEOINT", "Phase 4: Cartography"),
    "p5_finalize": ("ANVIL", "Phase 5: Finalize"),
}

# Lazy imports to avoid circular dependencies
def get_extraction_orchestrator():
    from forge.phases.extraction import ExtractionOrchestrator
    return ExtractionOrchestrator

def get_anvil_orchestrator():
    from forge.phases.anvil import AnvilOrchestrator
    return AnvilOrchestrator

def get_loom_orchestrator():
    from forge.phases.loom import LoomOrchestrator
    return LoomOrchestrator

__all__ = [
    "PHASE_LABELS",
    "get_extraction_orchestrator",
    "get_anvil_orchestrator",
    "get_loom_orchestrator",
]
