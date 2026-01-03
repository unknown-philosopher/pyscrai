"""The Harvester Orchestrator (Manager).

This module ties together the Scout, Analyst, Validator, and forge agents
into a cohesive extraction pipeline.
"""

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from pyscrai_core import ProjectManifest, Relationship
# Changed import to avoid circular dependency
from pyscrai_core import RelationshipType
from pyscrai_forge.src.prompts.harvester_prompts import Genre, get_relationship_prompt

from .scout import ScoutAgent
from .analyst import AnalystAgent
from .validator import ValidatorAgent
from .reviewer import ReviewerAgent

if TYPE_CHECKING:
    from pyscrai_core.llm_interface import LLMProvider


class HarvesterOrchestrator:
    """Manages the lifecycle of extracting a world from text."""

    def __init__(self, provider: "LLMProvider", manifest: ProjectManifest, model: Optional[str] = None):
        self.provider = provider
        self.manifest = manifest
        # Prefer an explicit model, otherwise fall back to provider default if available
        self.model = model or getattr(provider, "default_model", None)
        
        # Initialize Squad
        self.scout = ScoutAgent(provider, model=self.model)
        self.analyst = AnalystAgent(provider, model=self.model)
        self.validator = ValidatorAgent()
        self.reviewer = ReviewerAgent()

    async def run_harvester(
        self, 
        text: str, 
        genre: Genre = Genre.GENERIC,
        output_path: Optional[Path] = None
    ) -> str:
        """
        Run the full extraction pipeline.
        
        Returns:
            Path to the generated Review Packet (JSON).
        """
        print(f"--- [Phase 1] Scouting ({len(text)} chars) ---")
        stubs = await self.scout.discover_entities(text, genre)
        print(f"Found {len(stubs)} potential entities.")

        # Dedup stubs (simple by ID)
        seen_ids = set()
        unique_stubs = []
        for stub in stubs:
            if stub.id not in seen_ids:
                unique_stubs.append(stub)
                seen_ids.add(stub.id)
        
        print(f"--- [Phase 2] Analyzing {len(unique_stubs)} entities ---")
        # Parallel analysis
        tasks = []
        for stub in unique_stubs:
            schema = self.manifest.entity_schemas.get(stub.entity_type.value, {})
            tasks.append(self.analyst.analyze_entity(stub, text, schema))
        
        enriched_entities = await asyncio.gather(*tasks)
        print("Analysis complete.")

        print("--- [Phase 3] Mapping Relationships ---")
        # Batch entities for relationship prompt if too many? 
        # For now, simple single pass.
        relationships = await self._extract_relationships(text, enriched_entities, genre)
        print(f"Found {len(relationships)} relationships.")

        print("--- [Phase 4] Validation ---")
        report = self.validator.validate(enriched_entities, relationships, self.manifest)
        if not report.is_valid:
            print(f"Validation Errors: {len(report.critical_errors)}")
        else:
            print("Validation Passed.")

        print("--- [Phase 5] Creating Review Packet ---")
        packet = self.reviewer.create_review_packet(
            enriched_entities, 
            relationships, 
            report, 
            text
        )
        
        if output_path is None:
            output_path = Path("review_packet.json")
            
        self.reviewer.save_packet(packet, output_path)
        print(f"Review Packet saved to: {output_path}")
        
        return str(output_path)

    async def _extract_relationships(self, text: str, entities: list, genre: Genre):
        """Helper to extract relationships using the prompt system."""
        # Convert entities to dicts for prompt
        # We need strict ID matching.
        ent_dicts = []
        for e in entities:
             ent_dicts.append({
                 "id": e.id,
                 "name": e.descriptor.name,
                 "entity_type": e.descriptor.entity_type.value,
                 "description": e.descriptor.bio
             })
             
        system_prompt, user_prompt = get_relationship_prompt(text, ent_dicts, genre)
        
        try:
            response = await self.provider.complete_simple(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                model=self.model,
            )
            
            # Parse response
            # Reuse parsing logic? Or basic regex
            import re
            cleaned = response.strip()
            if "```json" in cleaned:
                cleaned = re.search(r"```json\s*(.*?)\s*```", cleaned, re.DOTALL).group(1)
            elif "```" in cleaned:
                cleaned = re.search(r"```\s*(.*?)\s*```", cleaned, re.DOTALL).group(1)
                
            data = json.loads(cleaned)
            rels_raw = data.get("relationships", [])
            
            rels = []
            for r in rels_raw:
                try:
                    rel_type_str = r.get("relationship_type", "custom").lower()
                    try:
                        rt = RelationshipType(rel_type_str)
                    except ValueError:
                        rt = RelationshipType.CUSTOM
                        
                    rels.append(Relationship(
                        id=r.get("id"),
                        source_id=r.get("source_id"),
                        target_id=r.get("target_id"),
                        relationship_type=rt,
                        strength=float(r.get("strength", 0.0)),
                        description=r.get("description", "")
                    ))
                except Exception:
                    continue
            return rels

        except Exception as e:
            print(f"Relationship extraction failed: {e}")
            return []
