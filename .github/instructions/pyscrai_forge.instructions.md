# Copilot Instructions for PyScrAI Forge 3.0

## Architecture Overview

**Forge** is a narrative intelligence system for entity extraction, relationship mapping, and knowledge graph construction. It follows a **pipeline architecture** with 6 phases (P0-P5), backed by modular subsystems.

### Core Philosophy
- **Unified Extraction (Phase 0)**: Single authoritative pass via `ExtractionAgent` → staging JSONs → `Sentinel` reconciliation
- **ECS Pattern**: Entities are flexible dataclasses with dynamic `attributes: dict` for schema flexibility
- **Functional Code Naming**: Code uses `extraction`, `entities`, `relationships` (not UI labels like OSINT, HUMINT)
- **Local-First Semantics**: sqlite-vec for vector embeddings directly in `world.db`
- **Lazy-Loaded State**: `ForgeState` initializes systems on-demand

# ---
# STATUS: IMPLEMENTATION IN PROGRESS
#
# As of January 2026, the NiceGUI frontend and several pipeline phases (P1, P3, P4, P5) are not yet implemented. This instruction file reflects the current backend and design intent.
#

### Key Files by Responsibility

| Component | Location | Purpose |
|-----------|----------|---------|
| **Entity Models** | `core/models/entity.py`, `relationship.py` | Pydantic dataclasses with dynamic attributes |
| **Extraction Pipeline** | `phases/p0_extraction/` | Chunker → Extractor → Sentinel workflow |
| **Agents** | `agents/` | LLM-powered workers (extraction, review, validation) |
| **LLM System** | `systems/llm/` | Provider abstraction (OpenRouter, LM Studio, Cherry, LM Proxy) |
| **Storage** | `systems/storage/database.py` | SQLite (`world.db`) CRUD operations |
| **Vector Memory** | `systems/memory/vector_memory.py` | sqlite-vec integration & semantic search |
| **App State** | `app/state.py` | Singleton-like container for runtime resources |

---

## Critical Development Patterns

### * Make sure to activate the virtual environment before running or testing:
```pwsh
.venv\Scripts\activate
# On Linux/macOS: source .venv/bin/activate
```

### 1. **ForgeState: The Central Hub**

All subsystems flow through `ForgeState`:

## Conventions

- **Type hints**: Always use `from __future__ import annotations` and full type hints
- **Logging**: Use `get_logger(__name__)` from `forge.utils.logging`
- **Errors**: Raise specific exceptions from `forge.systems.llm.base` (e.g., `AuthenticationError`)
- **Async**: Use `async/await`; all I/O is non-blocking
- **Imports**: Group as (stdlib, third-party, local); use absolute imports
- **IDs**: Always use `generate_id(prefix)` for entity/relationship IDs

## PyScrAI|Forge 3.0 Documentation
[README](../../README.md)
[Forge Flet overhaul](../../pyscrai_forge_overhaul.md)
