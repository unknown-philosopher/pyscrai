"""
Extraction Phase - Entity and relationship extraction from documents.

This phase handles:
- Document chunking for LLM processing
- LLM-powered entity/relationship extraction
- Sentinel reconciliation for duplicate detection
- Merge workflow for user review
"""

from forge.phases.extraction.chunker import TextChunker, TextChunk
from forge.phases.extraction.extractor import EntityExtractor, ExtractionResult
from forge.phases.extraction.sentinel import (
    Sentinel,
    MergeCandidate,
    MergeDecision,
    SentinelStats,
)
from forge.phases.extraction.orchestrator import (
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
