# PyScrAI | Forge 3.0

Forge is a narrative intelligence system for entity extraction, relationship mapping, and knowledge graph construction from unstructured documents.

## Quick Start


### Install

```bash
pip install -e .
```

**Optional arguments:**
- `pip install -e ".[dev]"` — Install test dependencies
- `pip install -e ".[cuda]"` — Install PyTorch with CUDA support
- `pip install -e ".[all]"` — Install all optional dependencies
- `pip install -e ".[dev,cuda]"` — Combine multiple extras

### Virtual Environment

Activate your environment before running or testing:
```pwsh
.venv\Scripts\activate
# On Linux/macOS: source .venv/bin/activate
```

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
  - `advisors/` — Phase-specific AI assistants (OSINT, HUMINT, SIGINT, SYNTH, GEOINT, ANVIL)
  - `prompts/` — Centralized YAML/Jinja2 prompt templates for all agents
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
DEFAULT_PROVIDER=openrouter

OPENROUTER_API_KEY=<your_api_key>
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
# OPENROUTER_MODEL=xiaomi/mimo-v2-flash:free

CHERRY_API_URL=http://127.0.0.1:23333/v1/chat/completions
CHERRY_API_KEY=<your_api_key>
# CHERRY_MODEL=xiaomi/mimo-v2-flash:free

LM_PROXY_BASE_URL=http://localhost:4000/openai/v1
LM_PROXY_API_KEY=not-needed
# LM_PROXY_MODEL=vscode-lm-proxy

LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_API_KEY=not-needed
# LM_STUDIO_MODEL=phi-3.5-mini-instruct-hermes-fc-json

# HuggingFace cache (for embeddings & models)
HF_HOME=D:/dev/.cache/huggingface/hub
```

## Key Concepts

- **Project** — A self-contained workspace with entities, relationships, and an SQLite database
- **Entity** — A person, organization, location, resource, or abstract concept
- **Relationship** — A typed connection between two entities (e.g., "member_of", "located_in")
- **Extraction** — Phase 0: LLM-powered extraction of entities and relationships from documents
- **Sentinel** — Entity reconciliation system: detects duplicates and manages merge candidates
- **Finalize** — Phase 5: Manual entity editing and conflict resolution

## Testing

Run all tests:

```bash
pytest forge/tests/ -v
```

Run a specific test module:

```bash
pytest forge/tests/test_core.py -v
```

Run a specific test function:

```bash
pytest forge/tests/test_core.py::test_entity_creation -v
```

| Test | Description |
|------|-------------|
| `test_imports` | Verifies all core modules can be imported |
| `test_entity_creation` | Tests Entity model creation with factory functions |
| `test_relationship_creation` | Tests Relationship model creation |
| `test_database_operations` | Tests CRUD operations on SQLite database |
| `test_id_generation` | Tests ID utilities (generate, parse, validate) |
| `test_text_chunker` | Tests document chunking for extraction |
| `test_prefab_system` | Tests schema prefab system and registry |
| `test_prompt_manager` | Tests YAML prompt loading and Jinja2 rendering |
| `test_event_system` | Tests event creation and state change events |
| `test_advisor_system` | Tests 6 advisor prompts (OSINT-ANVIL) |
| `test_llm_models` | Tests LLMMessage, Conversation serialization |
| `test_file_manager` | Tests staging JSON read/write operations |
| `test_forge_config` | Tests LLMConfig, ExtractionConfig, UIConfig |
| `test_project_manifest` | Tests ProjectManifest Pydantic model |
| `test_vector_memory_serialization` | Tests float32 vector serialization |
| `test_sentinel_merge_candidate` | Tests Sentinel merge candidate system |
| `test_graph_manager` | Tests NodeData/EdgeData graph structures |
| `test_forge_state_creation` | Tests ForgeState lazy initialization |

## Development Notes

- Async-first: Use `async/await` for LLM and I/O operations
- Events: All significant state changes logged to the event log for auditability
- Embeddings: Entity vectors stored in SQLite (with sqlite-vec); semantic search enabled
- Prompts: Centralized YAML/Jinja2 templates in `forge/agents/prompts/` for customizable LLM instructions
  - `extraction.yaml` — Entity extraction prompts
  - `analysis.yaml` — Deep analysis prompts  
  - `review.yaml` — QA and review prompts
  - `advisors/` — Phase-specific advisor prompts (osint.yaml, humint.yaml, sigint.yaml, synth.yaml, geoint.yaml, anvil.yaml)

## PyScrAI|Forge 3.0 Documents
[NiceGUI Blueprint](nicegui_blueprint.md)

