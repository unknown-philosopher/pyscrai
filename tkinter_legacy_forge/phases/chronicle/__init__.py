"""Phase 3: CHRONICLE - Narrative Synthesis with Verification.

The Chronicle phase handles:
- Loading entities and relationships from Loom staging
- Blueprint template selection (sitrep, dossier, etc.)
- Narrative generation via Narrator agent
- Sentence-level fact-checking and highlighting
- Staging output to narrative_report.md

Output artifact: staging/narrative_report.md
"""

from pyscrai_forge.phases.chronicle.ui import ChroniclePanel

__all__ = ["ChroniclePanel"]

