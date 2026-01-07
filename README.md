# PyScrAI|Forge 2.0

**Sequential Intelligence Pipeline for Worldbuilding & Entity Management**

PyScrAI|Forge 2.0 transforms worldbuilding into a structured 5-phase pipeline: extract entities, map relationships, generate narratives, anchor spatially, and merge into a canonical database with full provenance tracking.

## Features

- **5-Phase Sequential Pipeline**: Foundry → Loom → Chronicle → Cartography → Anvil
- **Interactive Graph Visualization**: Networkx-powered relationship mapping with drag-and-drop
- **Narrative Generation**: Blueprint templates with fact-checking
- **Spatial Mapping**: Grid-based entity placement with region management
- **Smart Merge Engine**: Semantic duplicate detection with conflict resolution
- **Provenance Tracking**: Complete attribute history audit trail
- **Staging Isolation**: Phase artifacts flow through JSON/MD files before final commit

## Project Structure

```
pyscrai/
├── pyscrai_core/              # Core data models and services
│   ├── models.py              # Entity, Relationship models
│   ├── memory_service.py      # Semantic search (sqlite-vec/FTS5 fallback)
│   └── llm_interface/         # LLM provider abstractions
│
├── pyscrai_forge/             # Main application
│   ├── phases/                # Pipeline phases
│   │   ├── foundry/           # Phase 1: Entity extraction
│   │   ├── loom/              # Phase 2: Relationship mapping
│   │   ├── chronicle/         # Phase 3: Narrative synthesis
│   │   ├── cartography/       # Phase 4: Spatial anchoring
│   │   └── anvil/             # Phase 5: Merge & finalization
│   │
│   ├── agents/                # LLM agents (Scout, Analyst, Narrator)
│   ├── src/
│   │   ├── app/               # Application controllers
│   │   │   ├── main_app.py    # Three-pane UI layout
│   │   │   ├── state_manager.py
│   │   │   ├── task_queue.py  # Async task execution
│   │   │   └── project_migrator.py  # v1→v2 migration
│   │   ├── staging.py         # Staging artifact management
│   │   └── ui/                # UI components
│   └── prompts/               # Template system
│
└── data/projects/             # Project data directory
    └── <project>/
        ├── project.json       # Project manifest
        ├── world.db           # Canonical database
        └── staging/           # Phase artifacts
            ├── entities_staging.json
            ├── graph_staging.json
            ├── narrative_report.md
            └── spatial_metadata.json
```

## Quickstart

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd pyscrai

# Install dependencies
pip install -e .

# Set up environment variables
cp .env.example .env
# Edit .env with your LLM API keys (OPENROUTER_API_KEY, etc.)
```

### Run the Application

```bash
# Launch PyScrAI|Forge GUI
forge

# Or run directly
python -m pyscrai_forge.src.__main__
```

### Basic Workflow

1. **Create/Open Project**: File → New Project or Open Project
2. **Phase 1 - Foundry**: Import documents → Extract entities → Save to staging
3. **Phase 2 - Loom**: Load staging → Visualize graph → Add relationships → Save
4. **Phase 3 - Chronicle**: Select blueprint → Generate narrative → Fact-check
5. **Phase 4 - Cartography**: Place entities on map → Define regions → Save
6. **Phase 5 - Anvil**: Review conflicts → Resolve merges → Commit to world.db

## Pipeline Phases

### Phase 1: FOUNDRY
- **Input**: Documents (PDF, TXT, DOCX)
- **Process**: Scout/Analyst agents extract entities
- **Output**: `staging/entities_staging.json`
- **UI**: Entity editor with validation

### Phase 2: LOOM
- **Input**: Entities from Foundry
- **Process**: Interactive graph visualization, relationship inference
- **Output**: `staging/graph_staging.json`
- **UI**: Networkx graph canvas with drag-and-drop

### Phase 3: CHRONICLE
- **Input**: Entities + relationships from Loom
- **Process**: Narrative generation with blueprint templates
- **Output**: `staging/narrative_report.md`
- **UI**: Blueprint selector, fact-check highlighting

### Phase 4: CARTOGRAPHY
- **Input**: Entities from previous phases
- **Process**: Spatial positioning on grid map
- **Output**: `staging/spatial_metadata.json`
- **UI**: Interactive map with entity placement

### Phase 5: ANVIL
- **Input**: All staging artifacts
- **Process**: Conflict detection, merge resolution, provenance tracking
- **Output**: Committed changes to `world.db`
- **UI**: Diff viewer, merge controls, conflict resolution

## Configuration

### LLM Providers

Supported providers (configured in project manifest):
- OpenRouter
- Cherry
- LM Studio
- LM Proxy

Set API keys in `.env`:
```bash
OPENROUTER_API_KEY=your_key_here
CHERRY_API_KEY=your_key_here
```

### Project Templates

Templates define entity schemas and extraction prompts:
- `default/` - Generic worldbuilding
- `espionage/` - Intelligence/spy scenarios
- `historical/` - Historical events

## Development

```bash
# Run tests
pytest

# Check linting
flake8 pyscrai_forge pyscrai_core

# Type checking
mypy pyscrai_forge pyscrai_core
```

## Dependencies

- **Core**: pydantic, pydantic-ai, httpx
- **UI**: tkinter (built-in), sv-ttk
- **Graph**: networkx
- **Embeddings**: sentence-transformers
- **Vector DB**: sqlite-vec (optional, falls back to FTS5/keyword)

## License

[Your License Here]

## Version

**2.0.0** - Sequential Intelligence Pipeline

