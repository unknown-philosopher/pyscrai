Forge 3.0: Comprehensive Architectural Blueprint

**Version:** 3.0.0-Draft  
**Date:** 2026-01-08  
**Status:** FINALIZED

---

## 1. Executive Summary

Forge 3.0 is a complete overhaul focused on Unified Extraction, Architectural Flattening, and Local‑First Semantic Memory. It retires the legacy split for a unified `/forge` directory, adopts a dual‑label nomenclature (UI/Code) for clarity, and enshrines a single authoritative extraction pass with sentinel‑driven reconciliation.

---

## 2. Directory Structure (high level)

(See existing blueprint for the full tree.) Key notes:
- `data/projects/{Name}/world.db` now stores both relational data and embedded vectors (sqlite‑vec).
- `systems/memory/` implements the local semantic memory layer and vector helpers.

---

## 3. The Semantic Memory Module (sqlite‑vec)

Forge integrates sqlite‑vec directly into `world.db` to enable native, local vector similarity without external services.

- Technical Implementation
    - Storage: `world.db` hosts a vec0 virtual table, e.g.:
        CREATE VIRTUAL TABLE entity_embeddings USING vec0(embedding float[1536]);
    - Runtime: `systems/memory/` loads the sqlite extension (sqlite_vec.load) and provides serialization helpers (serialize_float32 -> BLOB).
- Uses
    - Phase 0 (OSINT): Sentinel performs near‑match vector searches during staging to prevent duplicates.
    - Phase 3 (SYNTH): Semantic retrieval grounds narrative generation with relevant world facts.

---

## 4. Phase 0 & The Sentinel Logic

### Unified Extraction (ExtractionAgent)
- Processes source text in managed chunks to avoid context overflow.
- Produces modular staging JSONs (e.g., `entities_staging.json`, `relationships_staging.json`) for deterministic, reviewable merges.

### The Sentinel (Gatekeeper)
- Reconciliation: Semantically compares staged JSONs against `world.db` (including vector similarity).
- Merge Plan: Generates a clear diff for the user (e.g., "Add 5 new entities, update 2 existing, ignore 1 duplicate") and requests approval before commit.
- Conflict Resolution: Flags contradictory relationships and provenance mismatches for user review.
- Provenance & History: Tracks source documents and full event history for rollbacks.

---

## 5. Source Code Adaptation Highlights

- Systems/memory: Implement sqlite‑vec integration and vector helper APIs.
- Entities & Models: Update dataclasses to use dynamic attributes and support sqlite‑vec row IDs for embeddings.
- ExtractionAgent & Sentinel: Extraction produces modular staging JSONs; Sentinel performs semantic merges and produces merge plans.
- Prompts & Templates: Centralize prompt manager in `agents/prompts/manager.py`.

---

(Other sections in the original blueprint remain applicable; this content merges the semantic‑memory and extraction/sentinel updates into the existing structure.) Forge 3.0: Comprehensive Architectural Blueprint

**Version:** 3.0.0-Draft  
**Date:** 2026-01-08  
**Status:** Approved for Implementation

---

## 1. Executive Summary

Forge 3.0 represents a foundational "Reset & Refactor" of the PyScrAI system. The primary objectives are:

- **Unified Extraction (Phase Zero):** Solving the stability issues of previous versions by extracting Entities and Relationships in a single, authoritative pass ("OSINT").
- **Architectural Flattening:** Retiring the split between `pyscrai_forge` and `pyscrai_core` in favor of a single, self-contained `/forge` directory.
- **Strict Nomenclature Standards:** Decoupling UI "Lore" terms (OSINT, HUMINT, SIGINT) from the codebase. The code will strictly use functional naming (extraction, entities, relationships).
- **Data/Logic Separation:** Distinct separation between Runtime Data (`/data`), User Templates (`/prefabs`), and Application Logic (`/app`, `/agents`).

---

## 2. Directory Structure

This structure replaces all legacy directories. All development occurs strictly within `/forge`.

```
/forge
├── app/                        # Main Application Logic
│   ├── main.py                 # Entry point & Loop
│   ├── state.py                # Global state (Active project, view stack)
│   └── settings.py             # App-wide user preference handling
│
├── data/                       # Runtime/User Data (The "Save Files")
│   ├── global_config.json      # Global user preferences
│   └── projects/               # Project Repositories
│       └── {ProjectName}/
│           ├── project.json    # Single source of truth for project config
│           ├── world.db        # SQLite (The authoritative graph)
│           ├── vector_store/   # Embeddings folder (Chroma/FAISS)
│           └── staging/        # Raw source texts & extracted JSONs
│
├── prefabs/                    # Static User Assets (The "Loadouts")
│   ├── schemas/                # YAML templates for Entity/Relationship schemas
│   ├── settings/               # Reusable configurations (e.g., "SciFi Settings")
│   └── advisors/               # Advisor personalities/configs
│
├── core/                       # Data Models (Absorbs legacy pyscrai_core)
│   ├── models/
│   │   ├── entity.py           # Flexible Entity dataclass
│   │   ├── relationship.py     # Graph Relationship dataclass
│   │   └── project.py          # Project config handler
│   └── events/                 # Event bus for history/logging/undo
│
├── systems/                    # Infrastructure & Backend Services
│   ├── llm/                    # LLM Interface Layer (Adapters, Providers)
│   ├── memory/                 # Vector DB integration logic
│   └── storage/                # SQLite & File I/O manager
│
├── phases/                     # Pipeline UI & Frontend Logic
│   │                           # (Strict Functional Naming in Code)
│   ├── p0_extraction/          # UI Label: OSINT
│   │   ├── processor.py        # Logic for the unified extraction pass
│   │   └── ui.py               # The Extraction/Staging dashboard
│   ├── p1_entities/            # UI Label: HUMINT
│   │   ├── editor.py           # Entity Grid/Form logic
│   │   └── ui.py
│   ├── p2_relationships/       # UI Label: SIGINT
│   │   ├── inference.py        # Graph analysis & connection logic
│   │   └── ui.py
│   ├── p3_narrative/           # UI Label: SYNTH
│   ├── p4_map/                 # UI Label: GEOINT
│   └── p5_finalize/            # UI Label: ANVIL
│
├── agents/                     # AI Logic & Workers
│   ├── advisors/               # Module-Specific Advisor Logic
│   │   ├── entity_advisor.py
│   │   ├── relationship_advisor.py
│   │   └── ...
│   ├── prompts/                # CENTRALIZED PROMPT STORAGE
│   │   ├── advisors/           # Advisor-specific YAML/Jinja templates
│   │   ├── extraction/         # Phase 0 extraction prompts
│   │   └── analysis/           # General analysis/reasoning prompts
│   ├── extraction_agent.py     # Unified Extraction specialist
│   ├── sentinel.py             # Data Integrity, Reconciler, & History Manager
│   └── analyst.py              # High-level reasoning agent
│
├── ui/                         # Shared UI Components (sv-ttk)
│   ├── components/             # Reusable widgets (Cards, Tables, Modals)
│   ├── styles/                 # Theme and visual depth definitions
│   └── dialogs/                # Common popups (Settings, Import, Processing)
│
└── utils/                      # Helpers (Logging, String manipulation)
```

---

## 3. The Pipeline (Phase Zero & Beyond)

**Phase 0: Extraction (UI: OSINT)**

- **Goal:** Create an authoritative, consistent dataset from raw text.
- **The Unified Pass:** Unlike legacy versions, Phase 0 extracts both Entities and Relationships in one pass to ensure structural coherence.
- **The Sentinel:** This agent acts as the gatekeeper. It compares incoming "Staged" data against the existing `world.db` to identify duplicates, conflicts, or updates without destroying manual user edits.
- **Persistence:** Once the user approves the "Merge Plan" provided by the Sentinel, the data is committed permanently to SQLite.

---

## 4. Agentic Architecture

### The "Advisor" Pattern

- Advisors are specialized agents tied to specific modules (HUMINT, SIGINT, etc.).
    - **Logic:** Defined in `agents/advisors/`.
    - **Personality/Prompt:** Loaded dynamically from `agents/prompts/advisors/`.
    - **Config:** Users can swap advisor "Loadouts" from `prefabs/advisors/` to change the AI's specialty (e.g., changing from a "Historical Analyst" to a "Sci-Fi Analyst").

### The Sentinel

The Sentinel is the most critical logic block in Forge 3.0. It manages the "Staging to Production" pipeline.

- **Reconciliation:** Merges new data with old, deduplicating IDs.
- **Provenance:** Tracks exactly which source document an entity or relationship came from.
- **History:** Maintains the events/ log for project-wide rollbacks, as well as a providing a series of progressive events to the SYNTH or other modules as needed to potentially provide a series of events with changes.

---

## 5. UI Nomenclature Standards

To provide a premium expert experience, we use high-level acronyms in the UI while keeping the codebase functional.

| Code Directory     | UI Sidebar | UI Overview                  |
|--------------------|------------|------------------------------|
| `p0_extraction`    | OSINT      | Phase 0: Extraction          |
| `p1_entities`      | HUMINT     | Phase 1: Entities            |
| `p2_relationships` | SIGINT     | Phase 2: Relationships       |
| `p3_narrative`     | SYNTH      | Phase 3: Narrative           |
| `p4_map`           | GEOINT     | Phase 4: Cartography         |
| `p5_finalize`      | ANVIL      | Phase 5: Finalize            |

---

## 6. Source Code Extraction & Adaptation Strategy

For developers migrating to 3.0, the following components represent the "High Value" parts of the legacy repo that should be refactored into the new `/forge` structure.

### A. Infrastructure & Systems
- **LLM Interface (`pyscrai_core/llm_interface/`):** Port directly to `systems/llm/`. The provider factory and OpenRouter/Anthropic adapters are stable.
- **Memory Service (`pyscrai_core/memory_service.py`):** Port to `systems/memory/`. Refactor to interface with the new Entity model.
- **File Extractors (`pyscrai_forge/src/extractor.py`):** Port text-cleaning and format-handling (PDF/HTML/MD) logic to `phases/p0_extraction/extractor.py`.

### B. UI Components
- **Treeview Sorter:** Generic sorting logic in `ui/widgets/treeview_sorter.py` is an immediate candidate for `ui/components/`.
- **Stats Panel:** Logic for counting entity types/frequencies should be moved to a shared component in `ui/components/dashboard_widgets.py`.

### C. AI Logic & Prompts
- **Template Manager:** The Jinja2 loading logic in `prompts/template_manager.py` should be moved to `agents/prompts/manager.py`.
- **Relationship Inference:** The core logic inside the legacy LoomAgent (`phases/loom/agent.py`) should be extracted and utilized by the new `RelationshipAdvisor`.
- **Scout to Extraction Agent:** Refactor the legacy Scout (`agents/scout.py`) into the new `ExtractionAgent`. Its prompt must be updated to output a unified JSON of entities AND relationships.

### D. Data Models
- **Entity/Relationship Models:** The dataclasses in `pyscrai_core/models.py` must be updated for 3.0.
- **Change:** Ensure Entity uses a dynamic attributes dictionary rather than fixed fields to support the flexible schemas stored in `/prefabs/schemas`