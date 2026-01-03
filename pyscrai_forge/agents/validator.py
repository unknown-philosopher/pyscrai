"""The Validator Agent: Enforces schema consistency and graph integrity."""

import json
from dataclasses import dataclass, field
from pyscrai_core import Entity, Relationship, ProjectManifest

@dataclass
class ValidationReport:
    """Report of validation issues."""
    critical_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        return len(self.critical_errors) == 0

class ValidatorAgent:
    """Validates entities against Project Manifest and checks graph integrity."""

    def validate(
        self, 
        entities: list[Entity], 
        relationships: list[Relationship],
        manifest: ProjectManifest
    ) -> ValidationReport:
        """Run all validation checks."""
        report = ValidationReport()
        
        # 1. Check Graph Integrity (Ghost Nodes)
        entity_ids = {e.id for e in entities}
        for rel in relationships:
            if rel.source_id not in entity_ids:
                report.critical_errors.append(
                    f"Relationship {rel.id} references missing source: {rel.source_id}"
                )
            if rel.target_id not in entity_ids:
                report.critical_errors.append(
                    f"Relationship {rel.id} references missing target: {rel.target_id}"
                )
        
        # 2. Check Schema Compliance
        schemas = manifest.entity_schemas
        for entity in entities:
            e_type = entity.descriptor.entity_type.value
            expected_schema = schemas.get(e_type, {})
            
            # Skip if no schema defined for this type
            if not expected_schema:
                continue
                
            resources = entity.state.resources
            
            for field_name, field_type in expected_schema.items():
                if field_name not in resources:
                    report.warnings.append(
                        f"Entity {entity.id} ({e_type}) missing expected field: {field_name}"
                    )
                else:
                    # Basic type checking could go here (e.g. checking if int matches "int")
                    val = resources[field_name]
                    if val is None:
                        continue # Null is usually allowed as "unknown"
                        
                    # Very basic type check
                    if "float" in field_type and not isinstance(val, (float, int)):
                         report.warnings.append(
                            f"Entity {entity.id} field '{field_name}' expected {field_type}, got {type(val)}"
                        )

        return report

__all__ = ["ValidatorAgent", "ValidationReport"]
