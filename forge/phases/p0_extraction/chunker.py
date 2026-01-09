"""
Text Chunker for Extraction Phase.

Splits source documents into overlapping chunks for LLM processing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator


# ============================================================================
# Chunk Data Structure
# ============================================================================


@dataclass
class TextChunk:
    """A chunk of text extracted from a source document.
    
    Attributes:
        content: The text content of the chunk
        index: Zero-based index of this chunk in the document
        start_char: Starting character position in original document
        end_char: Ending character position in original document
        source_name: Name of the source document
        overlap_start: Number of characters that overlap with previous chunk
        overlap_end: Number of characters that overlap with next chunk
        metadata: Additional metadata about the chunk
    """
    
    content: str
    index: int
    start_char: int
    end_char: int
    source_name: str = ""
    overlap_start: int = 0
    overlap_end: int = 0
    metadata: dict = field(default_factory=dict)
    
    @property
    def char_count(self) -> int:
        """Get the character count of this chunk."""
        return len(self.content)
    
    @property
    def word_count(self) -> int:
        """Approximate word count."""
        return len(self.content.split())
    
    @property
    def unique_content(self) -> str:
        """Get content excluding overlap regions."""
        start = self.overlap_start if self.overlap_start else 0
        end = -self.overlap_end if self.overlap_end else None
        return self.content[start:end]
    
    def get_context_summary(self) -> str:
        """Get a summary for context in prompts."""
        return (
            f"Chunk {self.index + 1} of '{self.source_name}' "
            f"(chars {self.start_char}-{self.end_char})"
        )


# ============================================================================
# Chunker
# ============================================================================


class TextChunker:
    """Splits text into overlapping chunks for LLM processing.
    
    Uses a token-approximation based on character count (1 token ≈ 4 chars).
    Attempts to break at sentence or paragraph boundaries when possible.
    
    Usage:
        chunker = TextChunker(chunk_size=2500, overlap=500)
        for chunk in chunker.chunk_text(document, source_name="report.txt"):
            print(f"Chunk {chunk.index}: {chunk.word_count} words")
    """
    
    # Approximate characters per token
    CHARS_PER_TOKEN = 4
    
    # Patterns for finding good break points
    PARAGRAPH_PATTERN = re.compile(r'\n\s*\n')
    SENTENCE_PATTERN = re.compile(r'(?<=[.!?])\s+')
    
    def __init__(
        self,
        chunk_size: int = 2500,
        overlap: int = 500,
        min_chunk_size: int = 100,
    ):
        """Initialize the chunker.
        
        Args:
            chunk_size: Target chunk size in tokens
            overlap: Overlap between chunks in tokens
            min_chunk_size: Minimum chunk size in tokens
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size
        
        # Convert to characters
        self.chunk_chars = chunk_size * self.CHARS_PER_TOKEN
        self.overlap_chars = overlap * self.CHARS_PER_TOKEN
        self.min_chars = min_chunk_size * self.CHARS_PER_TOKEN
    
    def chunk_text(
        self,
        text: str,
        source_name: str = "",
    ) -> Iterator[TextChunk]:
        """Split text into overlapping chunks.
        
        Args:
            text: The text to chunk
            source_name: Name of the source document
            
        Yields:
            TextChunk objects
        """
        if not text.strip():
            return
        
        text_len = len(text)
        
        # If text is smaller than one chunk, return as single chunk
        if text_len <= self.chunk_chars:
            yield TextChunk(
                content=text,
                index=0,
                start_char=0,
                end_char=text_len,
                source_name=source_name,
            )
            return
        
        chunk_index = 0
        current_pos = 0
        
        while current_pos < text_len:
            # Calculate chunk boundaries
            chunk_start = current_pos
            chunk_end = min(current_pos + self.chunk_chars, text_len)
            
            # Try to find a good break point
            if chunk_end < text_len:
                chunk_end = self._find_break_point(text, chunk_start, chunk_end)
            
            # Extract chunk content
            content = text[chunk_start:chunk_end]
            
            # Calculate overlap info
            overlap_start = self.overlap_chars if chunk_index > 0 else 0
            overlap_end = self.overlap_chars if chunk_end < text_len else 0
            
            yield TextChunk(
                content=content,
                index=chunk_index,
                start_char=chunk_start,
                end_char=chunk_end,
                source_name=source_name,
                overlap_start=overlap_start,
                overlap_end=overlap_end,
            )
            
            # Move position forward (minus overlap)
            current_pos = chunk_end - self.overlap_chars
            if current_pos <= chunk_start:
                current_pos = chunk_end  # Prevent infinite loop
            
            chunk_index += 1
    
    def _find_break_point(
        self,
        text: str,
        start: int,
        target_end: int,
    ) -> int:
        """Find a good break point near the target end position.
        
        Prefers paragraph breaks, then sentence breaks, then word breaks.
        
        Args:
            text: Full text
            start: Start of chunk
            target_end: Target end position
            
        Returns:
            Adjusted end position
        """
        # Look for break points in the last 20% of the chunk
        search_start = start + int((target_end - start) * 0.8)
        search_region = text[search_start:target_end]
        
        # Try paragraph break first
        para_matches = list(self.PARAGRAPH_PATTERN.finditer(search_region))
        if para_matches:
            # Use the last paragraph break
            match = para_matches[-1]
            return search_start + match.end()
        
        # Try sentence break
        sent_matches = list(self.SENTENCE_PATTERN.finditer(search_region))
        if sent_matches:
            # Use the last sentence break
            match = sent_matches[-1]
            return search_start + match.end()
        
        # Fall back to word break
        last_space = search_region.rfind(' ')
        if last_space != -1:
            return search_start + last_space + 1
        
        # No good break found, use target
        return target_end
    
    def estimate_chunk_count(self, text: str) -> int:
        """Estimate number of chunks for a text.
        
        Args:
            text: The text to estimate
            
        Returns:
            Estimated number of chunks
        """
        if not text.strip():
            return 0
        
        text_len = len(text)
        
        if text_len <= self.chunk_chars:
            return 1
        
        # Account for overlap
        effective_chunk = self.chunk_chars - self.overlap_chars
        return max(1, (text_len + effective_chunk - 1) // effective_chunk)
    
    def get_stats(self, text: str) -> dict:
        """Get chunking statistics for a text.
        
        Args:
            text: The text to analyze
            
        Returns:
            Dict with statistics
        """
        chunks = list(self.chunk_text(text, "analysis"))
        
        return {
            "total_chars": len(text),
            "total_words": len(text.split()),
            "estimated_tokens": len(text) // self.CHARS_PER_TOKEN,
            "chunk_count": len(chunks),
            "avg_chunk_chars": sum(c.char_count for c in chunks) / len(chunks) if chunks else 0,
            "avg_chunk_words": sum(c.word_count for c in chunks) / len(chunks) if chunks else 0,
        }
