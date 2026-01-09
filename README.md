# PyScrAI | Forge 3.0

Forge is a narrative intelligence system for entity extraction, relationship mapping, and knowledge graph construction from unstructured documents.

## Quick Start

### Install

```bash
pip install -e .
```

**Optional arguments:**
- `pip install -e ".[dev]"` — Install test dependencies
- `pip install -e ".[ui]"` — Install Textual TUI support (future UI)
- `pip install -e ".[all]"` — Install all optional dependencies
- `pip install -e ".[dev,ui]"` — Combine multiple extras

### Run

```bash
python -m forge.__main__
```

Or use the installed `forge` command (when console script is enabled):
```bash
forge
```

## Project Structure

### `/forge` — Core System

The main Forge engine organized by phase:

- **`agents/`** — LLM-powered agents for analysis, review, and validation
- **`app/`** — Application layer: config, state management, and UI entry points
- **`core/`** — Domain models: entities, relationships, events, and projects
- **`phases/`** — Pipeline stages:
  - `p0_extraction/` — Document chunking and entity/relationship extraction via LLM
  - `p1_entities/` — (Reserved for entity enrichment)
  - `p2_relationships/` — Graph analysis and visualization
  - `p3_narrative/` — (Reserved for narrative generation)
  - `p4_map/` — (Reserved for cartography/mapping)
  - `p5_finalize/` — Entity management, merging, and editing (Anvil)
- **`prefabs/`** — Reusable schema and template system
- **`systems/`** — Core subsystems:
  - `llm/` — LLM provider interfaces (OpenRouter, Cherry, LM Studio, LM Proxy)
  - `memory/` — Vector embeddings and semantic search
  - `storage/` — Database and file I/O management
- **`utils/`** — ID generation, logging, and utilities
- **`ui/`** — User interface components (TBD)

### `/data` — Projects & Resources

- **`projects/`** — User projects (each a subdirectory with `project.json` manifest + `world.db`)
- **`user/`** — User configuration and templates
- **`intel_report.txt`** — Sample narrative input for testing

## Configuration: `.env.sample`

Copy `.env.sample` to `.env` and configure:

```dotenv
# LLM Provider (default: openrouter)
# Options: openrouter, lm_proxy, lm_studio, cherry
OPENROUTER_API_KEY=<your_api_key>
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Cherry (local LLM server)
CHERRY_API_URL=http://127.0.0.1:23333/v1/chat/completions
CHERRY_API_KEY=<your_api_key>

# LM Proxy (VS Code LM proxy)
LM_PROXY_BASE_URL=http://localhost:4000/openai/v1
LM_PROXY_API_KEY=not-needed

# LM Studio (local LLM)
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_API_KEY=not-needed

# HuggingFace cache (for embeddings & models)
HF_HOME=~/.cache/huggingface/hub
```

## Key Concepts

- **Project** — A self-contained workspace with entities, relationships, and an SQLite database
- **Entity** — A person, organization, location, resource, or abstract concept
- **Relationship** — A typed connection between two entities (e.g., "member_of", "located_in")
- **Extraction** — Phase 0: LLM-powered extraction of entities and relationships from documents
- **Sentinel** — Entity reconciliation system: detects duplicates and manages merge candidates
- **Finalize** — Phase 5: Manual entity editing and conflict resolution

## Testing

Run the test suite:

```bash
python -m pytest forge/tests/test_forge.py -v
```

Run individual tests:

```bash
python -m pytest forge/tests/test_forge.py::test_entity_creation -v
```

## Development Notes

- Async-first: Use `async/await` for LLM and I/O operations
- Events: All significant state changes logged to the event log for auditability
- Embeddings: Entity vectors stored in SQLite (with sqlite-vec); semantic search enabled
- Prompts: Template system in `forge/agents/prompts/` for customizable LLM instructions

## PyScrAI|Forge 3.0 Blueprint
[Blueprint](blueprint.md)