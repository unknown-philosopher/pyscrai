"""Phase 5: ANVIL - Finalization and Continuity.

The Anvil phase handles:
- Loading all staging artifacts
- Diff viewing (staging vs canon database)
- Semantic duplicate detection via embeddings
- Merge/Reject/Branch conflict resolution
- Provenance tracking to attribute_history table
- Final commit to world.db

Output: Committed changes to world.db with full provenance
"""

from pyscrai_forge.phases.anvil.ui import AnvilPanel
from pyscrai_forge.phases.anvil.merger import SmartMergeEngine, MergeAction, MergeConflict
from pyscrai_forge.phases.anvil.provenance import ProvenanceTracker

__all__ = ["AnvilPanel", "SmartMergeEngine", "MergeAction", "MergeConflict", "ProvenanceTracker"]

