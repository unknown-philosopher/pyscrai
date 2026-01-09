"""
Phase 0: Extraction (UI: OSINT) - Entity and relationship extraction from documents.

This phase handles:
- Document chunking for LLM processing
- LLM-powered entity/relationship extraction
- Sentinel reconciliation for duplicate detection
- Merge workflow for user review
"""

from forge.phases.p0_extraction.chunker import TextChunker, TextChunk
from forge.phases.p0_extraction.extractor import EntityExtractor, ExtractionResult
from forge.phases.p0_extraction.sentinel import (
    Sentinel,
    MergeCandidate,
    MergeDecision,
    SentinelStats,
)
from forge.phases.p0_extraction.orchestrator import (
    ExtractionOrchestrator,
    ExtractionStatus,
    ExtractionProgress,
    ExtractionSummary,
)

__all__ = [
    # Chunking
    "TextChunker",
    "TextChunk",
    # Extraction
    "EntityExtractor",
    "ExtractionResult",
    # Sentinel
    "Sentinel",
    "MergeCandidate",
    "MergeDecision",
    "SentinelStats",
    # Orchestrator
    "ExtractionOrchestrator",
    "ExtractionStatus",
    "ExtractionProgress",
    "ExtractionSummary",
]
