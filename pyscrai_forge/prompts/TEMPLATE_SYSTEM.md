"""
# Prompt Template System

A robust system for managing, organizing, and swapping prompt templates across different genres, project types, and use cases.

## Overview

Prompts are critical to the quality of entity extraction, analysis, and relationship mapping. The template system allows:

- **Easy Editing**: Prompts stored as YAML files, no code changes needed
- **Genre Support**: Pre-built templates for historical, espionage, fictional, etc.
- **Reusability**: Share templates across projects and teams
- **Versioning**: Track prompt iterations and improvements
- **Fallback**: Gracefully falls back to "default" if a genre template doesn't exist
- **Runtime Customization**: Register custom templates at runtime

## Directory Structure

```
pyscrai_forge/prompts/templates/
├── default/           # Default templates (fallback for all genres)
│   ├── scout.yaml
│   ├── analyst.yaml
│   └── relationships.yaml
├── historical/        # Templates optimized for historical texts
│   ├── scout.yaml
│   ├── analyst.yaml
│   └── relationships.yaml
├── espionage/         # Templates for intelligence/espionage content
│   ├── scout.yaml
│   ├── analyst.yaml
│   └── relationships.yaml
└── fictional/         # Templates for fictional narratives
    ├── scout.yaml
    ├── analyst.yaml
    └── relationships.yaml
```

## Template Format (YAML)

Each template file contains system + user prompts plus metadata:

```yaml
name: "Scout Template Name"
description: "What this template does"
version: "1.0"
author: "PyScrAI Team"
tags:
  - scout
  - entity-discovery
  - historical

system_prompt: |
  You are the Scout agent...
  [full system prompt with instructions]

user_prompt_template: |
  [user prompt with {placeholders} for variables]
  TEXT: {text}
  GENRE: {genre}

metadata:
  phases: ["scout"]
  compatible_genres: ["historical", "chronicle"]
  min_tokens: 50
  max_tokens: 3000
```

## Usage

### Basic Usage

```python
from pyscrai_forge.prompts.template_manager import TemplateManager
from pyscrai_forge.agents.scout import ScoutAgent
from pyscrai_core.llm_interface.provider_factory import create_provider_from_env

# Initialize
manager = TemplateManager()
provider, _ = create_provider_from_env()
scout = ScoutAgent(provider, template_manager=manager)

# Use default template
entities = await scout.discover_entities(text, genre="generic")

# Use historical template
entities = await scout.discover_entities(text, genre="historical")

# Use custom template
entities = await scout.discover_entities(text, template_name="my_custom")
```

### List Available Templates

```python
manager = TemplateManager()

# See all templates for scout agent
templates = manager.list_templates("scout")
# Returns: {"default": [...], "historical": [...], "espionage": [...]}
```

### Register Custom Template

```python
from pyscrai_forge.prompts.template_manager import PromptTemplate

template = PromptTemplate(
    name="My Custom Scout",
    description="Customized for my project",
    version="1.0",
    system_prompt="You are...",
    user_prompt_template="Extract from: {text}"
)

manager.register_custom_template("scout", "my_custom", template)

# Now use it
entities = await scout.discover_entities(text, template_name="my_custom")
```

### Export and Adapt Templates

```python
# Export default template to a new file
manager.export_template_to_file("scout", "default", Path("my_scout_template.yaml"))

# Now edit the exported file and use it
custom = manager._load_template(Path("my_scout_template.yaml"))
manager.register_custom_template("scout", "custom", custom)
```

## Template Variables (Placeholders)

Templates can use these variables via `{variable_name}`:

### Scout Templates
- `{text}` - The source text to extract entities from
- `{genre}` - The genre/category of the document

### Analyst Templates
- `{entity_name}` - Name of the entity being analyzed
- `{entity_type}` - Type of entity (actor, polity, location, abstract)
- `{description}` - Current description of the entity
- `{schema_fields}` - Field definitions from project schema
- `{text}` - Source text

### Relationship Templates
- `{entities_list}` - Formatted list of entities to relate
- `{text}` - Source text

## Built-In Genres

### Default
Generic templates that work for any text type. Used as fallback.

### Historical
Optimized for historical documents, chronicles, biographies.
- Handles titles, honorifics, alternative names
- Recognizes kingdoms, empires, dynasties
- Captures military figures and campaigns

### Espionage
Optimized for intelligence reports, surveillance, covert operations.
- Identifies operatives, handlers, agents
- Recognizes intelligence agencies and criminal networks
- Tracks safe houses and operational locations
- Captures organizational hierarchies

### Fictional
(Ready for future implementation)
Optimized for novels, fantasy, sci-fi narratives.

## Adding a New Genre

1. Create a directory: `prompts/templates/{genre_name}/`
2. Create template files:
   - `scout.yaml` - Entity discovery for your genre
   - `analyst.yaml` - Detailed analysis instructions
   - `relationships.yaml` - Relationship mapping rules
3. Test with your content
4. Share or add to main templates

## Best Practices

### Writing Prompts

1. **Be Explicit**: Clearly state what to extract and why
2. **Give Examples**: Show entity types and expected output format
3. **Set Boundaries**: Tell the agent what NOT to do
4. **Format Instructions**: Specify exact JSON structure expected
5. **Test Thoroughly**: Try with representative samples of your content

### Template Maintenance

1. **Version Tracking**: Increment version when you update prompts
2. **Document Changes**: Note what changed and why in metadata
3. **Test After Changes**: Always verify improvements with real data
4. **Backup Original**: Keep previous versions for comparison

### Performance Tips

1. **Token Limits**: Set appropriate min/max_tokens in metadata
2. **Temperature**: Scout uses 0.1 (very deterministic) - usually good
3. **Prompt Length**: Shorter, focused prompts often work better
4. **Examples**: 1-2 good examples > many generic instructions

## Future Enhancements

- [ ] CLI for editing templates
- [ ] Template validation against schema
- [ ] A/B testing different prompts
- [ ] Automatic prompt optimization
- [ ] Template marketplace/sharing
- [ ] Prompt performance analytics
"""
