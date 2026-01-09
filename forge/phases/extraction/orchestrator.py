"""
Extraction Phase Orchestrator for Forge 3.0.

Coordinates the full extraction workflow: chunking, extraction,
and Sentinel reconciliation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Callable, Any
from pathlib import Path

from forge.phases.extraction.chunker import TextChunker, TextChunk
from forge.phases.extraction.extractor import EntityExtractor, ExtractionResult
from forge.phases.extraction.sentinel import Sentinel, SentinelStats
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.app.state import ForgeState
    from forge.core.models.entity import Entity
    from forge.core.models.relationship import Relationship

logger = get_logger("extraction")


# ============================================================================
# Extraction Status
# ============================================================================


class ExtractionStatus(str, Enum):
    """Status of extraction workflow."""
    IDLE = "idle"
    CHUNKING = "chunking"
    EXTRACTING = "extracting"
    RECONCILING = "reconciling"
    PENDING_REVIEW = "pending_review"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ExtractionProgress:
    """Progress tracking for extraction workflow."""
    
    status: ExtractionStatus = ExtractionStatus.IDLE
    total_chunks: int = 0
    processed_chunks: int = 0
    current_chunk: int = 0
    error_message: str | None = None
    
    @property
    def progress_percent(self) -> float:
        if self.total_chunks == 0:
            return 0.0
        return (self.processed_chunks / self.total_chunks) * 100


@dataclass
class ExtractionSummary:
    """Summary of extraction results."""
    
    source_name: str
    total_chunks: int
    successful_chunks: int
    failed_chunks: int
    total_entities: int
    total_relationships: int
    pending_merges: int
    auto_merges: int
    sentinel_stats: SentinelStats | None = None


# ============================================================================
# Extraction Orchestrator
# ============================================================================


class ExtractionOrchestrator:
    """Orchestrates the full extraction workflow.
    
    Workflow:
    1. Chunk source document(s) into overlapping segments
    2. Extract entities/relationships from each chunk via LLM
    3. Feed results into Sentinel for reconciliation
    4. Present merge candidates for user review
    5. Commit resolved entities to world.db
    
    Usage:
        orchestrator = ExtractionOrchestrator(state)
        
        # Run extraction
        summary = await orchestrator.extract_from_file("document.txt")
        
        # Review merges
        for candidate in orchestrator.sentinel.get_pending_merges():
            orchestrator.sentinel.approve_merge(candidate)
        
        # Commit to database
        orchestrator.commit_to_database()
    """
    
    def __init__(
        self,
        state: "ForgeState",
        chunk_size: int = 2500,
        chunk_overlap: int = 500,
        similarity_threshold: float = 0.85,
        auto_merge_threshold: float = 0.95,
    ):
        """Initialize the orchestrator.
        
        Args:
            state: Application state
            chunk_size: Token size per chunk
            chunk_overlap: Overlap between chunks
            similarity_threshold: Threshold for merge candidates
            auto_merge_threshold: Threshold for automatic merging
        """
        self.state = state
        
        # Initialize components
        self.chunker = TextChunker(
            chunk_size=chunk_size,
            overlap=chunk_overlap,
        )
        
        self.extractor = EntityExtractor(
            llm_provider=state.llm,
            model=state.config.llm.model,
            max_entities_per_chunk=state.config.extraction.max_entities_per_chunk,
        )
        
        self.sentinel = Sentinel(
            vector_memory=state.memory,
            similarity_threshold=similarity_threshold,
            auto_merge_threshold=auto_merge_threshold,
        )
        
        # Progress tracking
        self.progress = ExtractionProgress()
        self._progress_callbacks: list[Callable[[ExtractionProgress], None]] = []
        
        # Results
        self._extraction_results: list[ExtractionResult] = []
    
    def add_progress_callback(
        self,
        callback: Callable[[ExtractionProgress], None],
    ) -> None:
        """Add a progress callback.
        
        Args:
            callback: Function to call on progress updates
        """
        self._progress_callbacks.append(callback)
    
    def _update_progress(
        self,
        status: ExtractionStatus | None = None,
        **kwargs: Any,
    ) -> None:
        """Update progress and notify callbacks.
        
        Args:
            status: New status (optional)
            **kwargs: Fields to update
        """
        if status is not None:
            self.progress.status = status
        
        for key, value in kwargs.items():
            if hasattr(self.progress, key):
                setattr(self.progress, key, value)
        
        for callback in self._progress_callbacks:
            try:
                callback(self.progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
    
    async def extract_from_text(
        self,
        text: str,
        source_name: str = "document",
        context: str = "",
    ) -> ExtractionSummary:
        """Extract entities and relationships from text.
        
        Args:
            text: Text content to extract from
            source_name: Name for the source document
            context: Optional context about the project
            
        Returns:
            Extraction summary
        """
        try:
            # Phase 1: Chunking
            self._update_progress(status=ExtractionStatus.CHUNKING)
            logger.info(f"Chunking document: {source_name}")
            
            chunks = list(self.chunker.chunk_text(text, source_name))
            self._update_progress(
                total_chunks=len(chunks),
                processed_chunks=0,
            )
            
            logger.info(f"Created {len(chunks)} chunks from '{source_name}'")
            
            # Phase 2: Extraction
            self._update_progress(status=ExtractionStatus.EXTRACTING)
            
            successful = 0
            failed = 0
            
            for i, chunk in enumerate(chunks):
                self._update_progress(current_chunk=i + 1)
                
                result = await self.extractor.extract_from_chunk(chunk, context)
                self._extraction_results.append(result)
                
                if result.success:
                    successful += 1
                    # Feed to Sentinel
                    self.sentinel.ingest_result(result)
                else:
                    failed += 1
                    logger.warning(
                        f"Chunk {i + 1} extraction failed: {result.error}"
                    )
                
                self._update_progress(processed_chunks=i + 1)
            
            # Phase 3: Check for pending merges
            pending_merges = self.sentinel.get_pending_merges()
            
            if pending_merges:
                self._update_progress(status=ExtractionStatus.PENDING_REVIEW)
                logger.info(f"Extraction complete. {len(pending_merges)} merges pending review.")
            else:
                self._update_progress(status=ExtractionStatus.COMPLETE)
                logger.info("Extraction complete. No merges pending review.")
            
            # Build summary
            stats = self.sentinel.get_stats()
            
            return ExtractionSummary(
                source_name=source_name,
                total_chunks=len(chunks),
                successful_chunks=successful,
                failed_chunks=failed,
                total_entities=stats.total_entities,
                total_relationships=stats.total_relationships,
                pending_merges=stats.pending_merges,
                auto_merges=stats.auto_merges,
                sentinel_stats=stats,
            )
            
        except Exception as e:
            self._update_progress(
                status=ExtractionStatus.ERROR,
                error_message=str(e),
            )
            logger.error(f"Extraction error: {e}", exc_info=True)
            raise
    
    async def extract_from_file(
        self,
        file_path: str | Path,
        context: str = "",
    ) -> ExtractionSummary:
        """Extract from a file.
        
        Args:
            file_path: Path to the source file
            context: Optional extraction context
            
        Returns:
            Extraction summary
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Source file not found: {file_path}")
        
        text = file_path.read_text(encoding="utf-8")
        return await self.extract_from_text(
            text,
            source_name=file_path.name,
            context=context,
        )
    
    async def extract_from_staging(
        self,
        context: str = "",
    ) -> list[ExtractionSummary]:
        """Extract from all source documents in staging.
        
        Args:
            context: Optional extraction context
            
        Returns:
            List of extraction summaries
        """
        source_files = self.state.files.list_source_documents()
        summaries = []
        
        for source_file in source_files:
            try:
                summary = await self.extract_from_file(source_file, context)
                summaries.append(summary)
            except Exception as e:
                logger.error(f"Failed to extract from {source_file}: {e}")
        
        return summaries
    
    def commit_to_database(self) -> tuple[int, int]:
        """Commit resolved entities and relationships to the database.
        
        Returns:
            Tuple of (entities_saved, relationships_saved)
        """
        entities = self.sentinel.get_resolved_entities()
        relationships = self.sentinel.get_resolved_relationships()
        
        # Save entities
        for entity in entities:
            self.state.db.save_entity(entity)
        
        # Save relationships
        for relationship in relationships:
            self.state.db.save_relationship(relationship)
        
        # Log events
        for event in self.sentinel.get_events():
            self.state.db.log_event(event)
        
        self.state.mark_dirty()
        
        logger.info(
            f"Committed to database: {len(entities)} entities, "
            f"{len(relationships)} relationships"
        )
        
        return len(entities), len(relationships)
    
    def save_staging(self) -> Path:
        """Save current extraction state to staging.
        
        Returns:
            Path to the staging file
        """
        data = self.sentinel.to_staging_dict()
        return self.state.files.write_staging_json("extraction_staging.json", data)
    
    def reset(self) -> None:
        """Reset the orchestrator for a new extraction."""
        self.sentinel.clear()
        self._extraction_results.clear()
        self.progress = ExtractionProgress()
