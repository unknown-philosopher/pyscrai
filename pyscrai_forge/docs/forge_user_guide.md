# PyScrAI|Forge User & Developer Guide

This comprehensive guide covers both usage and development of PyScrAI|Forge, the creation toolkit for PyScrAI worldbuilding projects. It includes GUI and CLI workflows, project management, and extensibility for developers.

## Table of Contents

### For Users
1. [Prerequisites](#prerequisites)
2. [Launching the Application](#launching-the-application)
3. [GUI Overview](#gui-overview)
   - [Landing Page](#landing-page)
   - [Project Dashboard](#project-dashboard)
   - [Active Work Views](#active-work-views)
4. [CLI Harvester](#cli-harvester)
   - [Basic Usage](#basic-usage)
   - [Arguments & Options](#arguments--options)
5. [Project Management](#project-management)
   - [Creating Projects](#creating-projects)
   - [Defining Schemas](#defining-schemas)
   - [Database Operations](#database-operations)
6. [Complete Workflow Example](#complete-workflow-example)
7. [Troubleshooting & Tips](#troubleshooting--tips)

### For Developers
8. [Architecture Overview](#architecture-overview)
9. [Extending Agents](#extending-agents)
10. [UI Customization](#ui-customization)
11. [Schema Design](#schema-design)
12. [LLM Provider Integration](#llm-provider-integration)
13. [Best Practices](#best-practices)

---

## Prerequisites

- Python 3.10+
- Install dependencies:
  ```bash
  pip install -e .
  ```
- Set up your `.env` file in the project root for LLM provider API keys:
  ```env
  OPENROUTER_API_KEY=your_key_here
  DEFAULT_PROVIDER=openrouter
  # Optional: Set a specific model
  OPENROUTER_DEFAULT_MODEL=anthropic/claude-3-haiku
  ```

---

## Launching the Application

### GUI (Recommended)
Launch the main application with:
```bash
forge gui
```
This opens the 3-state UI: Landing Page, Project Dashboard, and Active Work Views.

### CLI Harvester
Run the Harvester pipeline from the command line:
```bash
forge process <your_text_file.txt> --genre <genre> --output <output.json>
```

---

## GUI Overview

### Landing Page
- Shown when no project is loaded.
- Options: **New Project**, **Open Project**, recent projects list, and quick start tips.

### Project Dashboard
- Shown after loading/creating a project.
- Displays project info, quick actions (Import Data, Edit Components, Browse Database), recent imports, and entity/relationship stats.

### Active Work Views
- **Component Editor**: Edit entities and relationships in a schema-aware tree/table view.
- **Database Explorer**: Browse and query the underlying SQLite world database.
- **Import Dialog**: Import and extract data from text, PDF, DOCX, HTML, or image files (OCR supported).
- **Validation Banner**: Always visible, shows status (Valid, Warnings, Critical Errors).

#### Key GUI Features
- **Tabbed Entity Editor**: Edit Descriptor, Cognitive, Spatial, and State (resources) for each entity. State tab adapts to your project schema.
- **Relationship Editor**: Edit source/target, type, strength, and visibility for relationships.
- **Validation**: Issues are highlighted; resolve critical errors before committing.
- **Commit to Database**: Save approved entities/relationships to your project's world.db.

---

## CLI Harvester

The CLI Harvester extracts entities and relationships from unstructured text using a multi-agent pipeline.

### Basic Usage
```bash
forge process ./my_lore.txt --genre fantasy --output ./my_review.json --project ./my_project/
```

### Arguments & Options
- **file** (Argument, Required): Path to input file. Supports `.txt`, `.pdf`, `.html`, `.docx`, `.png/.jpg` (OCR).
- **--genre / -g**: Document genre (`fantasy`, `scifi`, `historical`, `modern`, `generic`).
- **--model / -m**: Override the default LLM model.
- **--output / -o**: Output path for the review packet JSON.
- **--project / -p**: Path to a project directory (loads custom schema from `project.json`).

---

## Complete Workflow Example

1. **Create or Open a Project**
   - Use the GUI's Landing Page to create or open a project.
2. **Import & Extract Data**
   - Use the GUI's Import dialog or run the CLI Harvester to process your text/lore files.
3. **Review & Edit**
   - Use the Component Editor and Relationship Editor to correct and enrich extracted data.
   - Validation Banner will guide you to fix issues.
4. **Commit to Database**
   - Approve and commit data to your project's world.db for use in simulation.

---

## Project Management

### Creating Projects

Projects in PyScrAI|Forge are self-contained directories containing:
- `project.json` - Project manifest with metadata and entity schemas
- `world.db` - SQLite database storing entities, relationships, and components
- `data/` - Review packets and imported files
- Other project-specific files

**Via GUI:**
1. Launch `forge gui`
2. Click **New Project** on the Landing Page
3. Fill in project name, description, author, and version
4. Define entity schemas (see [Defining Schemas](#defining-schemas))
5. Save to create the project directory

**Via Project Manager:**
- Use the Project Manager window to create, edit, and validate projects
- Access via Dashboard → **Manage Project** button

### Defining Schemas

Entity schemas define the structure of `StateComponent.resources_json` for each entity type. They are project-specific and stored in `project.json`.

**Schema Format:**
```json
{
  "entity_schemas": {
    "polity": {
      "treasury": "float",
      "stability": "float",
      "population": "int"
    },
    "actor": {
      "health": "float",
      "mana": "float",
      "sanity": "float"
    },
    "location": {
      "defense_rating": "int",
      "capacity": "int"
    }
  }
}
```

**Supported Types:**
- `"float"` - Floating point numbers
- `"int"` - Integers
- `"str"` - Strings
- `"bool"` - Boolean values

**Via GUI:**
- Use the Project Manager's schema builder interface
- Add/remove fields per entity type
- Validation ensures type consistency

**Via Manual Edit:**
- Edit `project.json` directly (not recommended for beginners)
- Use Project Manager to validate after manual edits

### Database Operations

The `world.db` SQLite database stores all committed entities and relationships.

**Database Explorer:**
- Browse entities by type (Actor, Polity, Location, etc.)
- Filter and search across all components
- Batch operations (delete, export, etc.)
- View relationships graph

**Commit Workflow:**
1. Import/extract data via Harvester
2. Review and edit in Component Editor
3. Resolve validation errors (critical errors block commits)
4. Click **Commit to Database** to persist changes

**Backup & Export:**
- Project directories are self-contained
- Copy entire project folder to backup
- Export data via Database Explorer's batch operations

---

## Troubleshooting & Tips

- **Missing .env or API Key**: Ensure your `.env` is set up with the correct provider and key.
- **File Not Found**: Double-check file paths and extensions.
- **Schema Issues**: Edit your `project.json` to define or update your world schema.
- **GUI Not Launching**: Make sure you are running `forge gui` from an environment where the package is installed (`pip install -e .`).
- **Validation Errors**: Critical errors must be resolved before committing. Warnings are informational.
- **Database Locked**: Ensure no other process is accessing `world.db`. Close other Forge instances.
- **For More**: See [Harvester Agents Guide](harvester_agents.md), [Completed Dev Plans](dev_plans/completed/), [Tkinter Guides](dev_plans/tkinter_dev/), and the [Current Dev Blueprint](dev_plans/phase_1-3.md).

---

## Architecture Overview

PyScrAI|Forge is built on top of `pyscrai_core`, which provides the ECS foundation. The Forge adds:

**Core Components:**
- **Harvester Pipeline**: Multi-agent extraction system (Scout → Analyst → Validator → forge)
- **GUI Framework**: Tkinter-based 3-state UI with modular windows and widgets
- **Project Management**: Schema-aware project creation and validation
- **Database Integration**: SQLite persistence with foreign key validation

**Key Modules:**
- `pyscrai_forge/agents/` - Agent implementations (Scout, Analyst, Validator, forge, Manager)
- `pyscrai_forge/src/ui/` - GUI components (windows, widgets, dialogs)
- `pyscrai_forge/src/prompts/` - LLM prompt templates
- `pyscrai_forge/src/converters/` - File format converters (PDF, DOCX, HTML, OCR)

**Data Flow:**
1. **Input** → Text/PDF/DOCX/HTML/Image files
2. **Harvester** → Extracts entities and relationships using LLM agents
3. **Review Packet** → JSON structure for GUI consumption
4. **Component Editor** → Human review and editing
5. **Validation** → Schema and graph consistency checks
6. **Database** → Committed to `world.db` for simulation use

---

## Extending Agents

The Harvester pipeline is designed for extensibility. To add a new agent:

### 1. Create Agent Class

Create a new file in `pyscrai_forge/agents/` (e.g., `cartographer.py`):

```python
from typing import TYPE_CHECKING
from pyscrai_core import Entity, SpatialComponent

if TYPE_CHECKING:
    from pyscrai_core.llm_interface import LLMProvider

class CartographerAgent:
    """Generates spatial coordinates for locations."""
    
    def __init__(self, provider: "LLMProvider", model: str | None = None):
        self.provider = provider
        self.model = model
    
    async def map_entity(self, entity: Entity, context: str) -> SpatialComponent:
        """Extract or generate spatial data."""
        # Your agent logic here
        # Use self.provider.complete_simple() for LLM calls
        pass
```

### 2. Integrate into Manager

Edit `pyscrai_forge/agents/manager.py`:

```python
from .cartographer import CartographerAgent

class HarvesterOrchestrator:
    def __init__(self, ...):
        # ... existing initialization ...
        self.cartographer = CartographerAgent(provider, model=self.model)
    
    async def run_harvester(self, ...):
        # ... existing pipeline ...
        # Add your agent call:
        for entity in entities:
            entity.spatial = await self.cartographer.map_entity(entity, text)
```

### 3. Agent Best Practices

- **Schema Awareness**: Agents should respect `ProjectManifest.entity_schemas`
- **Error Handling**: Always handle LLM failures gracefully (return defaults, log errors)
- **Temperature Settings**: Use low temperature (0.1) for consistency, higher (0.7) for creativity
- **No Hallucination**: If data isn't in the text, leave fields blank/null
- **Async/Await**: All agent methods should be async for parallel execution

See [Harvester Agents Guide](harvester_agents.md) for detailed agent role descriptions.

---

## UI Customization

The GUI is built with Tkinter and organized into modular components.

### Widget Structure

- `pyscrai_forge/src/ui/widgets/` - Reusable UI components
- `pyscrai_forge/src/ui/windows/` - Full window implementations
- `pyscrai_forge/src/ui/dialogs/` - Modal dialogs

### Adding a New Window

1. Create a new file in `pyscrai_forge/src/ui/windows/`:

```python
import tkinter as tk
from tkinter import ttk

class MyCustomWindow(tk.Toplevel):
    def __init__(self, parent, project_controller):
        super().__init__(parent)
        self.project_controller = project_controller
        self.title("My Custom Window")
        self._build_ui()
    
    def _build_ui(self):
        # Your UI code here
        pass
```

2. Register in the main application (typically in the dashboard or menu system)

### Schema-Aware Widgets

Use `pyscrai_forge/src/ui/schema_widgets.py` for type-aware input widgets:
- Automatically validates based on schema types
- Provides appropriate input controls (spinbox for numbers, text for strings)
- Integrates with `ProjectManifest.entity_schemas`

### UI Best Practices

- **3-State UI**: Respect the Landing Page → Dashboard → Work View flow
- **Validation Banner**: Always show validation status when editing
- **Project Context**: Pass `ProjectController` to windows for schema access
- **Error Handling**: Use dialogs for user-facing errors
- **Responsive Layout**: Use `grid` or `pack` consistently, consider window resizing

See [Tkinter Development Guides](dev_plans/tkinter_dev/) for detailed UI development tips.

---

## Schema Design

Entity schemas define the "stats" or "resources" for each entity type in your world.

### Design Principles

1. **Project-Specific**: Each project can have different schemas (fantasy vs sci-fi)
2. **Type Safety**: Use appropriate types (`float` for continuous values, `int` for discrete)
3. **Semantic Clarity**: Field names should be self-explanatory
4. **Extensibility**: Add fields as your world evolves (schema migrations supported)

### Example Schemas

**Fantasy World:**
```json
{
  "polity": {
    "treasury": "float",
    "stability": "float",
    "magic_reserves": "float"
  },
  "actor": {
    "health": "float",
    "mana": "float",
    "sanity": "float",
    "level": "int"
  }
}
```

**Sci-Fi World:**
```json
{
  "polity": {
    "credits": "float",
    "tech_level": "int",
    "hull_integrity": "float"
  },
  "actor": {
    "health": "float",
    "energy": "float",
    "cyberware_rating": "int"
  }
}
```

### Schema Migration

When updating schemas:
1. Use Project Manager to edit schemas (validates changes)
2. Existing entities retain old fields (backward compatible)
3. New entities use updated schema
4. Consider data migration scripts for bulk updates

---

## LLM Provider Integration

PyScrAI|Forge uses `pyscrai_core/llm_interface` for LLM integration.

### Using Existing Providers

**OpenRouter (Default):**
```python
from pyscrai_core.llm_interface import create_provider, ProviderType

provider = create_provider(ProviderType.OPENROUTER)
# Uses OPENROUTER_API_KEY from .env
```

**Local LLM:**
```python
provider = create_provider(ProviderType.LOCAL)
# Configure local endpoint in .env
```

### Adding a New Provider

1. Create provider class in `pyscrai_core/llm_interface/`:

```python
from .base import LLMProvider, LLMClient

class MyCustomProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = MyCustomClient(api_key)
    
    async def complete_simple(self, prompt: str, model: str, **kwargs) -> str:
        # Implement LLM call
        pass
```

2. Register in `provider_factory.py`:
```python
class ProviderType(str, Enum):
    # ... existing types ...
    MY_CUSTOM = "my_custom"

def create_provider(provider_type: ProviderType, **kwargs) -> LLMProvider:
    # ... existing cases ...
    elif provider_type == ProviderType.MY_CUSTOM:
        return MyCustomProvider(**kwargs)
```

3. Update `.env` configuration as needed

### Provider Interface

All providers must implement `LLMProvider` protocol:
- `complete_simple()` - Basic text completion
- `complete_chat()` - Multi-turn conversations
- `get_available_models()` - List supported models

See `pyscrai_core/llm_interface/base.py` for the full interface.

---

## Best Practices

### For Worldbuilders

- **Start Simple**: Begin with basic schemas, add complexity as needed
- **Iterate**: Use the review/edit cycle to refine extracted data
- **Validate Early**: Fix critical errors before committing large batches
- **Backup Projects**: Copy project folders regularly
- **Use Genres**: Set appropriate genre flags for better extraction

### For Developers

- **Follow ECS Principles**: Components hold data, Entities are facades
- **Schema Awareness**: Always check `ProjectManifest.entity_schemas`
- **Error Handling**: Graceful degradation when LLMs fail
- **Async/Await**: Use async for all I/O operations
- **Type Hints**: Maintain type annotations for IDE support
- **Testing**: Test agents with various input formats and edge cases

### Code Organization

- **Agents**: One agent per file, clear single responsibility
- **UI**: Separate windows, widgets, and dialogs
- **Prompts**: Centralize in `src/prompts/` for easy iteration
- **Converters**: One converter per file format

### Performance

- **Parallel Analysis**: Analyst runs in parallel for multiple entities
- **Lazy Loading**: Load project data on demand
- **Database Indexing**: SQLite indexes on entity IDs and types
- **Caching**: Cache LLM responses when appropriate

---

For more information, see:
- [Harvester Agents Guide](harvester_agents.md) - Detailed agent documentation
- [Current Dev Blueprint](dev_plans/phase_1-3.md) - Development roadmap
- [Tkinter Guides](dev_plans/tkinter_dev/) - UI development tips
- [Completed Dev Plans](dev_plans/completed/) - Feature retrospectives

---
