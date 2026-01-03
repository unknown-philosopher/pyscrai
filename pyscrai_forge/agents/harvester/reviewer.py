"""The forge Agent: Orchestrates the Harvester loop and manages HIL."""

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from pyscrai_core import Entity, Relationship
from .validator import ValidationReport

@dataclass
class ReviewPacket:
    """The data bundle sent to the UI for human review."""
    entities: list[dict]
    relationships: list[dict]
    validation_report: dict
    source_text_snippet: str = ""
    status: str = "pending" # pending, approved, rejected

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str, indent=2)

class ReviewerAgent:
    """
    Orchestrates the Human-in-the-Loop process.
    
    In a CLI context, this might prompt via stdout.
    In a GUI context, this saves a 'Packet' to disk for the GUI to load.
    """

    def create_review_packet(
        self, 
        entities: list[Entity], 
        relationships: list[Relationship],
        report: ValidationReport,
        source_text: str = ""
    ) -> ReviewPacket:
        """Create a packet for the UI to consume."""
        
        # Convert entities to dicts (using pydantic)
        ent_dicts = []
        for e in entities:
            d = json.loads(e.model_dump_json())
            # Flatten descriptor for easier UI handling? 
            # forge UI expects specific structure, let's keep it robust.
            # We will rely on Pydantic's structure.
            ent_dicts.append(d)

        rel_dicts = [json.loads(r.model_dump_json()) for r in relationships]
        
        return ReviewPacket(
            entities=ent_dicts,
            relationships=rel_dicts,
            validation_report=asdict(report),
            source_text_snippet=source_text[:500] + "..." if len(source_text) > 500 else source_text
        )

    def save_packet(self, packet: ReviewPacket, path: Path | str) -> None:
        """Save packet to disk."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(packet.to_json())
            
    def load_packet(self, path: Path | str) -> ReviewPacket:
        """Load packet from disk."""
        with open(path, "r", encoding="utf-8") as f:
             data = json.load(f)
             # Basic reconstruction (omitted for brevity, assume UI handles dicts)
             return ReviewPacket(**data)
