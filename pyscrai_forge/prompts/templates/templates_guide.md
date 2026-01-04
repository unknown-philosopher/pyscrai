Here is a single, practical, and concise document that condenses all the key information from the template system documentation:

---

# PyScrAI|Forge Prompt Template System – Practical Guide

## Overview

A production-ready template system manages prompts and entity schemas for different genres and agent types. Prompts and schemas are stored as YAML files, enabling non-technical editing, versioning, and extensibility. The system supports runtime registration, caching, and graceful fallback to defaults.

## Core Components

### 1. TemplateManager (`template_manager.py`)
- Loads, caches, and manages prompt and schema templates.
- Supports runtime custom template registration.
- Provides fallback: custom → genre → default.
- Key methods:
  - `get_template(agent_type, genre, custom_name=None)`
  - `get_schema(genre, custom_name=None)`
  - `register_custom_template(agent_type, name, template)`
  - `register_custom_schema(name, schema)`
  - `reload_cache()`
  - `export_prompt_template_to_file()`
  - `export_schema_to_file()`

### 2. PromptTemplate (dataclass)
- Holds: name, description, version, system_prompt, user_prompt_template, metadata.
- Method: `render(**kwargs)` for safe variable substitution.

### 3. SchemaTemplate (dataclass)
- Holds: name, description, version, genre, schemas, metadata.
- Methods: `get_schema(type)`, `get_all_schemas()`

## Directory Structure

```
pyscrai_forge/prompts/templates/
├── default/
│   ├── scout.yaml
│   ├── analyst.yaml
│   ├── relationships.yaml
│   └── schema.yaml
├── historical/
│   ├── scout.yaml
│   └── schema.yaml
├── espionage/
│   ├── scout.yaml
│   └── schema.yaml
└── fictional/   # Placeholder
```

## Template Format

### Prompt Template (YAML)
```yaml
name: "Scout Template"
description: "Entity discovery template"
version: "1.0"
system_prompt: "You are an entity discovery agent..."
user_prompt_template: |
  Analyze this {genre} text for entities:
  {text}
metadata:
  tags: ["entity-discovery"]
  compatible_genres: ["default", "historical"]
```

### Schema Template (YAML)
```yaml
name: "Historical Entity Schemas"
description: "Entity field definitions for historical texts"
version: "1.0"
genre: "historical"
schemas:
  actor:
    name: "Full name or regnal name"
    birth_date: "Birth year or period"
    death_date: "Death year or period"
    title: "Royal title, rank, or honorific"
    accomplishments: "Notable deeds and achievements"
metadata:
  compatible_genres: ["historical"]
  entity_types: ["actor", "polity", "location", "abstract"]
```

## Usage Examples

### Load and Render a Template
```python
from pyscrai_forge.prompts.template_manager import TemplateManager

manager = TemplateManager()
template = manager.get_template("scout", genre="historical")
system, user = template.render(text="The Battle of Hastings...", genre="historical")
```

### Load Entity Schema
```python
schema = manager.get_schema(genre="espionage")
actor_fields = schema.get_schema("actor")
```

### Register Custom Template
```python
from pyscrai_forge.prompts.template_manager import PromptTemplate

custom = PromptTemplate(
    name="My Custom Scout",
    description="Specialized template",
    version="1.0",
    system_prompt="You are a custom entity finder...",
    user_prompt_template="Find entities in: {text}",
    metadata={"tags": ["custom"]}
)
manager.register_custom_template("scout", "my_template", custom)
template = manager.get_template("scout", custom_name="my_template")
```

## Integration Example: Scout Agent

```python
class ScoutAgent:
    def __init__(self, provider, template_manager=None):
        self.template_manager = template_manager or TemplateManager()
    async def discover_entities(self, text, genre):
        template = self.template_manager.get_template("scout", genre=genre)
        system, user = template.render(text=text, genre=genre)
        response = await self.provider.complete_simple(system_prompt=system, prompt=user)
        return self._parse_entities(response)
```

## Key Features

- **YAML-based templates**: Easy editing, versioning, and sharing.
- **Genre-based selection**: Optimized prompts and schemas for each genre.
- **Fallback mechanism**: Defaults ensure reliability.
- **Safe variable rendering**: Only provided variables are substituted.
- **Runtime extensibility**: Register custom templates/schemas without file changes.
- **Caching**: Fast access after first load.
- **Export/import**: Save templates to files for editing or sharing.

## Adding New Genres or Agent Types

- Create a new directory under `templates/` (e.g., `fictional/`).
- Add `{agent_type}.yaml` and `schema.yaml` files.
- Use immediately via `get_template()` and `get_schema()`.

## Performance

| Operation              | Time   | Notes                |
|------------------------|--------|----------------------|
| First template load    | 5-10ms | YAML parsing         |
| Cached template load   | <1ms   | In-memory retrieval  |
| Variable rendering     | <1ms   | String formatting    |
| LLM inference          | 1-30s  | Network + processing |

## Troubleshooting

- **Template not found**: Falls back to default genre.
- **Unrendered variables**: Placeholders remain for later rendering.
- **Cache issues**: Use `reload_cache()` to refresh from disk.

## Next Steps

- Integrate with Analyst and Relationships agents.
- Add more genres (fictional, fantasy, sci-fi).
- Build CLI/GUI tools for template management.
- Add analytics and versioning.

---

This guide provides all practical details for using, extending, and integrating the PyScrAI|Forge template system. For further details, see the full documentation files in the workspace.