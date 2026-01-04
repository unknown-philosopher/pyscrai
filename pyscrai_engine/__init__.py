"""PyScrAI Engine - Simulation runtime for PyScrAI worlds.

The Engine is responsible for executing simulations of worlds created in the Forge.
It processes intentions, applies events, manages agents, and generates narrative.

Core Components:
- SimulationEngine: Main simulation loop and state management
- TurnProcessor: Turn resolution pipeline (intentions → events → state changes)
- IntentionValidator: Validates intentions against world state and rules
- EventApplier: Applies events to entity state (only mutation point)

Usage:
    from pyscrai_engine import SimulationEngine
    
    engine = SimulationEngine(project_path)
    engine.initialize()
    engine.run(max_turns=100)
"""

from .engine import SimulationEngine
from .turn_processor import TurnProcessor
from .intention_validator import IntentionValidator
from .event_applier import EventApplier

__version__ = "0.1.0"

__all__ = [
    "SimulationEngine",
    "TurnProcessor",
    "IntentionValidator",
    "EventApplier",
]
