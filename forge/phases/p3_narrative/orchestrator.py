"""
Narrative Orchestrator - Phase 3: SYNTH.

Manages narrative documents and provides semantic search for the Fact Deck.

Responsibilities:
- Save/load Markdown narrative files
- List available narratives
- Query VectorMemory for Fact Deck suggestions (debounced on pause)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.core.models.entity import Entity
    from forge.systems.memory.vector_memory import VectorMemory

logger = get_logger("phases.p3_narrative")


class NarrativeOrchestrator:
    """Orchestrator for Phase 3: Narrative editing and synthesis.
    
    Manages narrative Markdown files and provides semantic search
    for the Fact Deck sidebar.
    """
    
    def __init__(
        self,
        project_path: Path,
        vector_memory: "VectorMemory | None" = None,
    ) -> None:
        """Initialize the NarrativeOrchestrator.
        
        Args:
            project_path: Path to the project directory
            vector_memory: Optional VectorMemory for Fact Deck search
        """
        self.project_path = Path(project_path)
        self.vector_memory = vector_memory
        
        # Ensure narrative directory exists
        self.narrative_dir = self.project_path / "narrative"
        self.narrative_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"NarrativeOrchestrator initialized: {self.narrative_dir}")
    
    # ========== File Management ==========
    
    def list_narratives(self) -> list[str]:
        """List all narrative files in the project.
        
        Returns:
            List of narrative filenames (without path)
        """
        if not self.narrative_dir.exists():
            return []
        
        return sorted([
            f.name for f in self.narrative_dir.glob("*.md")
        ])
    
    def save_narrative(self, filename: str, content: str) -> Path:
        """Save a narrative document.
        
        Args:
            filename: Name of the file (with or without .md extension)
            content: Markdown content to save
            
        Returns:
            Path to the saved file
        """
        # Ensure .md extension
        if not filename.endswith(".md"):
            filename = f"{filename}.md"
        
        # Sanitize filename
        safe_name = "".join(c for c in filename if c.isalnum() or c in "._-")
        if not safe_name.endswith(".md"):
            safe_name = f"{safe_name}.md"
        
        file_path = self.narrative_dir / safe_name
        file_path.write_text(content, encoding="utf-8")
        
        logger.info(f"Saved narrative: {file_path}")
        return file_path
    
    def load_narrative(self, filename: str) -> str:
        """Load a narrative document.
        
        Args:
            filename: Name of the file
            
        Returns:
            Markdown content
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not filename.endswith(".md"):
            filename = f"{filename}.md"
        
        file_path = self.narrative_dir / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Narrative not found: {filename}")
        
        return file_path.read_text(encoding="utf-8")
    
    def delete_narrative(self, filename: str) -> bool:
        """Delete a narrative document.
        
        Args:
            filename: Name of the file
            
        Returns:
            True if deleted, False if not found
        """
        if not filename.endswith(".md"):
            filename = f"{filename}.md"
        
        file_path = self.narrative_dir / filename
        
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted narrative: {filename}")
            return True
        
        return False
    
    def get_narrative_metadata(self, filename: str) -> dict[str, Any]:
        """Get metadata about a narrative file.
        
        Args:
            filename: Name of the file
            
        Returns:
            Dictionary with file metadata
        """
        if not filename.endswith(".md"):
            filename = f"{filename}.md"
        
        file_path = self.narrative_dir / filename
        
        if not file_path.exists():
            return {}
        
        stat = file_path.stat()
        content = file_path.read_text(encoding="utf-8")
        
        # Extract title from first heading
        title = filename
        for line in content.split("\n"):
            if line.startswith("# "):
                title = line[2:].strip()
                break
        
        return {
            "filename": filename,
            "title": title,
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "word_count": len(content.split()),
            "line_count": len(content.split("\n")),
        }
    
    # ========== Fact Deck (Semantic Search) ==========
    
    async def get_fact_deck(
        self,
        paragraph_text: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Get relevant entities for the Fact Deck based on current paragraph.
        
        Uses semantic search against the entity embeddings to find
        relevant entities that could be mentioned or referenced.
        
        Args:
            paragraph_text: Current paragraph or text selection
            top_k: Maximum number of suggestions to return
            
        Returns:
            List of entity suggestions with similarity scores
        """
        if not self.vector_memory:
            logger.warning("VectorMemory not available for Fact Deck")
            return []
        
        if not paragraph_text or len(paragraph_text) < 20:
            return []  # Not enough context
        
        try:
            # Query vector memory for similar entities
            results = await self.vector_memory.find_similar(
                query=paragraph_text,
                top_k=top_k,
            )
            
            # Format results for UI
            suggestions = []
            for entity, similarity in results:
                suggestions.append({
                    "id": entity.id,
                    "name": entity.name,
                    "type": entity.entity_type.value if hasattr(entity.entity_type, "value") else str(entity.entity_type),
                    "description": entity.description,
                    "similarity": similarity,
                    "tags": entity.tags,
                })
            
            logger.debug(f"Fact Deck: {len(suggestions)} suggestions for paragraph")
            return suggestions
            
        except Exception as e:
            logger.error(f"Fact Deck search failed: {e}")
            return []
    
    def get_entity_context(self, entity_id: str) -> dict[str, Any]:
        """Get full context for an entity (for insertion into narrative).
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            Entity details formatted for narrative use
        """
        # This would query the database for full entity details
        # For now, return a placeholder
        return {
            "id": entity_id,
            "snippet": f"[Entity: {entity_id}]",
        }
    
    # ========== Template Utilities ==========
    
    def create_from_template(
        self,
        template_name: str,
        title: str,
        variables: dict[str, Any] | None = None,
    ) -> str:
        """Create a new narrative from a template.
        
        Args:
            template_name: Name of the template (e.g., 'chapter', 'profile')
            title: Title for the new narrative
            variables: Optional variables to substitute
            
        Returns:
            Path to created file
        """
        templates = {
            "chapter": f"""# {title}

## Summary

_Write a brief summary of this chapter._

## Scene 1

...

## Scene 2

...

## Notes

- 
""",
            "profile": f"""# Character Profile: {title}

## Overview

_Brief description._

## Background

_History and origins._

## Personality

_Key traits and motivations._

## Relationships

- 

## Notes

- 
""",
            "location": f"""# Location: {title}

## Overview

_Description of this location._

## Geography

_Physical characteristics._

## Notable Features

- 

## History

_Significant events._

## Current Status

_Present-day state._
""",
            "blank": f"""# {title}

""",
        }
        
        template_content = templates.get(template_name, templates["blank"])
        
        # Simple variable substitution
        if variables:
            for key, value in variables.items():
                template_content = template_content.replace(f"{{{{{key}}}}}", str(value))
        
        # Generate filename
        safe_title = "".join(c for c in title.lower() if c.isalnum() or c == " ")
        filename = safe_title.replace(" ", "_")[:50]
        
        return self.save_narrative(filename, template_content)
