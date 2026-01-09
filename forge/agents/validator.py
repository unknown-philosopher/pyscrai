"""
Validator Agent for Forge 3.0.

Validates data consistency and schema compliance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from forge.agents.base import Agent, AgentRole, AgentResponse
from forge.core.models.entity import EntityType
from forge.utils.logging import get_logger

if TYPE_CHECKING:
    from forge.core.models.entity import Entity
    from forge.core.models.relationship import Relationship

logger = get_logger("agents.validator")


class ValidationSeverity(str, Enum):
    """Severity of a validation issue."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A single validation issue."""
    
    entity_id: str | None
    field: str
    message: str
    severity: ValidationSeverity
    suggestion: str = ""


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    errors: int = 0
    warnings: int = 0
    info: int = 0
    
    def add_issue(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)
        if issue.severity == ValidationSeverity.ERROR:
            self.errors += 1
            self.is_valid = False
        elif issue.severity == ValidationSeverity.WARNING:
            self.warnings += 1
        else:
            self.info += 1


VALIDATOR_SYSTEM_PROMPT = """You are a data validation specialist ensuring data quality and schema compliance.

Your role is to:
1. Validate entity data against expected schemas
2. Check relationship integrity
3. Identify missing required fields
4. Flag invalid or suspicious values
5. Ensure type consistency

VALIDATION RULES:
- All entities must have a name
- Entity types must be valid
- Relationships must reference existing entities
- Strengths must be between -1.0 and 1.0
- Dates should be in valid formats
- Required fields must be present

Report issues with severity:
- ERROR: Must be fixed (data integrity issues)
- WARNING: Should be reviewed (potential issues)
- INFO: Suggestions for improvement
"""


class ValidatorAgent(Agent):
    """Agent for validating data consistency and schema compliance.
    
    Usage:
        validator = ValidatorAgent(state)
        
        # Validate an entity
        result = validator.validate_entity(entity)
        
        # Validate relationships
        result = validator.validate_relationships()
        
        # Full project validation
        result = await validator.validate_project()
    """
    
    role = AgentRole.VALIDATOR
    
    def get_system_prompt(self) -> str:
        return VALIDATOR_SYSTEM_PROMPT
    
    # ========== Synchronous Validation ==========
    
    def validate_entity(
        self,
        entity: "Entity",
        schema: dict | None = None,
    ) -> ValidationResult:
        """Validate an entity against rules and optional schema.
        
        Args:
            entity: Entity to validate
            schema: Optional schema to validate against
            
        Returns:
            ValidationResult with any issues found
        """
        result = ValidationResult(is_valid=True)
        
        # Required fields
        if not entity.name or not entity.name.strip():
            result.add_issue(ValidationIssue(
                entity_id=entity.id,
                field="name",
                message="Entity name is required",
                severity=ValidationSeverity.ERROR,
            ))
        
        if not entity.id:
            result.add_issue(ValidationIssue(
                entity_id=entity.id,
                field="id",
                message="Entity ID is required",
                severity=ValidationSeverity.ERROR,
            ))
        
        # Type validation
        if entity.type not in EntityType:
            result.add_issue(ValidationIssue(
                entity_id=entity.id,
                field="type",
                message=f"Invalid entity type: {entity.type}",
                severity=ValidationSeverity.ERROR,
            ))
        
        # Description quality
        if not entity.description:
            result.add_issue(ValidationIssue(
                entity_id=entity.id,
                field="description",
                message="Entity lacks description",
                severity=ValidationSeverity.WARNING,
                suggestion="Add a description for better context",
            ))
        elif len(entity.description) < 10:
            result.add_issue(ValidationIssue(
                entity_id=entity.id,
                field="description",
                message="Entity description is very short",
                severity=ValidationSeverity.INFO,
            ))
        
        # Schema validation
        if schema:
            result = self._validate_against_schema(entity, schema, result)
        
        return result
    
    def validate_relationship(
        self,
        relationship: "Relationship",
    ) -> ValidationResult:
        """Validate a relationship.
        
        Args:
            relationship: Relationship to validate
            
        Returns:
            ValidationResult with any issues found
        """
        result = ValidationResult(is_valid=True)
        
        # Check source exists
        source = self.state.db.get_entity(relationship.source_id)
        if not source:
            result.add_issue(ValidationIssue(
                entity_id=relationship.id,
                field="source_id",
                message=f"Source entity not found: {relationship.source_id}",
                severity=ValidationSeverity.ERROR,
            ))
        
        # Check target exists
        target = self.state.db.get_entity(relationship.target_id)
        if not target:
            result.add_issue(ValidationIssue(
                entity_id=relationship.id,
                field="target_id",
                message=f"Target entity not found: {relationship.target_id}",
                severity=ValidationSeverity.ERROR,
            ))
        
        # Check self-reference
        if relationship.source_id == relationship.target_id:
            result.add_issue(ValidationIssue(
                entity_id=relationship.id,
                field="target_id",
                message="Relationship references same entity",
                severity=ValidationSeverity.WARNING,
            ))
        
        # Strength validation
        if not -1.0 <= relationship.strength <= 1.0:
            result.add_issue(ValidationIssue(
                entity_id=relationship.id,
                field="strength",
                message=f"Strength {relationship.strength} out of range [-1.0, 1.0]",
                severity=ValidationSeverity.ERROR,
            ))
        
        return result
    
    def _validate_against_schema(
        self,
        entity: "Entity",
        schema: dict,
        result: ValidationResult,
    ) -> ValidationResult:
        """Validate entity against a prefab schema.
        
        Args:
            entity: Entity to validate
            schema: Schema definition
            result: Existing result to append to
            
        Returns:
            Updated ValidationResult
        """
        required_fields = schema.get("required", [])
        field_types = schema.get("fields", {})
        
        for field_name in required_fields:
            if field_name not in entity.attributes:
                result.add_issue(ValidationIssue(
                    entity_id=entity.id,
                    field=field_name,
                    message=f"Required field missing: {field_name}",
                    severity=ValidationSeverity.ERROR,
                ))
        
        for field_name, expected_type in field_types.items():
            if field_name in entity.attributes:
                value = entity.attributes[field_name]
                if not self._check_type(value, expected_type):
                    result.add_issue(ValidationIssue(
                        entity_id=entity.id,
                        field=field_name,
                        message=f"Field '{field_name}' has wrong type. Expected {expected_type}",
                        severity=ValidationSeverity.WARNING,
                    ))
        
        return result
    
    def _check_type(self, value: Any, expected: str) -> bool:
        """Check if a value matches expected type."""
        type_map = {
            "string": str,
            "int": int,
            "float": (int, float),
            "bool": bool,
            "list": list,
            "dict": dict,
        }
        expected_type = type_map.get(expected.lower())
        if expected_type:
            return isinstance(value, expected_type)
        return True  # Unknown type, assume valid
    
    # ========== Batch Validation ==========
    
    def validate_all_entities(self) -> ValidationResult:
        """Validate all entities in the project.
        
        Returns:
            Combined ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        for entity in self.state.db.get_all_entities():
            entity_result = self.validate_entity(entity)
            for issue in entity_result.issues:
                result.add_issue(issue)
        
        self.log(
            f"Validated all entities: "
            f"{result.errors} errors, {result.warnings} warnings"
        )
        
        return result
    
    def validate_all_relationships(self) -> ValidationResult:
        """Validate all relationships in the project.
        
        Returns:
            Combined ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        for entity in self.state.db.get_all_entities():
            relationships = self.state.db.get_relationships_for_entity(entity.id)
            for rel in relationships:
                rel_result = self.validate_relationship(rel)
                for issue in rel_result.issues:
                    result.add_issue(issue)
        
        self.log(
            f"Validated all relationships: "
            f"{result.errors} errors, {result.warnings} warnings"
        )
        
        return result
    
    # ========== LLM-Assisted Validation ==========
    
    async def validate_project(self) -> AgentResponse:
        """Comprehensive LLM-assisted project validation.
        
        Returns:
            Validation assessment response
        """
        # Run synchronous validations
        entity_result = self.validate_all_entities()
        rel_result = self.validate_all_relationships()
        
        stats = self.state.db.get_stats()
        
        # Build summary
        issues_summary = []
        all_issues = entity_result.issues + rel_result.issues
        
        # Group by severity
        errors = [i for i in all_issues if i.severity == ValidationSeverity.ERROR]
        warnings = [i for i in all_issues if i.severity == ValidationSeverity.WARNING]
        
        prompt = f"""Review the validation results for this intelligence project:

PROJECT STATISTICS:
- Total Entities: {stats.get('entity_count', 0)}
- Total Relationships: {stats.get('relationship_count', 0)}

VALIDATION RESULTS:
- Errors: {len(errors)}
- Warnings: {len(warnings)}

TOP ERRORS:
{self._format_issues(errors[:10])}

TOP WARNINGS:
{self._format_issues(warnings[:10])}

Provide a comprehensive validation assessment with:
1. Overall data integrity assessment
2. Critical issues requiring immediate attention
3. Patterns in the issues found
4. Recommended fixes
5. Prevention strategies

Respond in JSON format:
{{
    "integrity_score": <0-100>,
    "critical_issues": ["issue1", "issue2"],
    "patterns": ["pattern1", "pattern2"],
    "recommended_fixes": [
        {{"issue": "description", "fix": "how to fix", "priority": "HIGH|MEDIUM|LOW"}}
    ],
    "prevention_strategies": ["strategy1", "strategy2"],
    "summary": "executive summary"
}}"""

        response = await self._generate_structured(prompt)
        
        # Add validation results to metadata
        response.metadata = {
            "total_errors": len(errors),
            "total_warnings": len(warnings),
            "entity_validation": {
                "is_valid": entity_result.is_valid,
                "errors": entity_result.errors,
                "warnings": entity_result.warnings,
            },
            "relationship_validation": {
                "is_valid": rel_result.is_valid,
                "errors": rel_result.errors,
                "warnings": rel_result.warnings,
            },
        }
        
        return response
    
    def _format_issues(self, issues: list[ValidationIssue]) -> str:
        """Format issues for prompt."""
        if not issues:
            return "None"
        
        lines = []
        for issue in issues:
            lines.append(
                f"- [{issue.severity.value.upper()}] {issue.field}: {issue.message}"
            )
        return "\n".join(lines)
