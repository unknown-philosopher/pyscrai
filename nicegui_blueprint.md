# PyScrAI|Forge 3.0: Master Implementation Blueprint

**Version:** 3.0.0 (NiceGUI Native Desktop Edition)
**Architecture:** Singleton State + Thin Reactive Frontend + Intelligence Agency Pipeline
**UI Framework:** NiceGUI (running in Native Mode via `pywebview`)

---

## 1. System Architecture

The application runs as a local Python process. It avoids the complexity of client-server sessions by instantiating a single **Global State** object accessible by the UI.

### 1.1 Core State (Singleton)

The `ForgeState` acts as the central nervous system.

* **Location:** `forge/app/state.py`.
* **Responsibility:** Holds the active `ProjectManager`, `Database` connection, and `LLMProvider`.
* **Access:** Imported directly by UI pages (`from forge.frontend.state import session`).

### 1.2 The "User Proxy" Layer

To keep the NiceGUI frontend "dumb," we introduce the `UserProxyAgent`.

* **Location:** `forge/agents/user_proxy.py` (New).
* **Role:** The "Brain" of the Assistant Sidebar.
* **Workflow:**
1. Receives text from UI (`assistant.py`).
2. **Intent Classification:** Uses LLM to classify as `COMMAND` or `QUERY`.
3. **Routing:**
* `COMMAND` → Triggers `forge.core.events.mutations` (e.g., `update_entity`).
* `QUERY` → Routes to phase-specific Advisor (e.g., `OSINTAdvisor` if in Phase 0).





---

## 2. Directory Structure

This structure merges the legacy functional requirements with the 3.0 modular architecture.

```text
forge/
├── app/
│   ├── state.py                # Singleton State Definition
│   └── ...
├── agents/
│   ├── user_proxy.py           # NEW: Intent Router for Assistant
│   └── advisors/               # Existing specialized agents (humint, osint, etc.)
├── phases/
│   ├── p0_extraction/          # OSINT (Sentinel + Extractor)
│   ├── p1_entities/            # HUMINT (Entity Editor)
│   ├── p2_relationships/       # SIGINT (Graph/NetworkX)
│   ├── p3_narrative/           # SYNTH (Markdown + Vector Search) [Stub -> Impl]
│   ├── p4_map/                 # GEOINT (Leaflet Wrapper) [Stub -> Impl]
│   └── p5_finalize/            # ANVIL
│       ├── exporter.py         # NEW: JSON/MD/SQL Export Utilities
│       └── ...
└── frontend/                   # NEW: NiceGUI Implementation
    ├── __init__.py
    ├── main.py                 # Entry Point (ui.run(native=True))
    ├── state.py                # Session Wrapper
    ├── theme.py                # Layout (Sidebar, Header, Drawer)
    ├── components/
    │   ├── assistant.py        # Chat Widget (talks to UserProxyAgent)
    │   ├── entity_grid.py      # AG Grid Wrapper
    │   └── file_picker.py      # Native File Dialog Wrapper
    └── pages/
        ├── dashboard.py
        ├── osint.py
        ├── humint.py
        ├── sigint.py
        ├── synth.py
        ├── geoint.py
        └── anvil.py

```

---

## 3. The Intelligence Pipeline (UI Specification)

Each UI page maps to a backend `Orchestrator` and a specific `Advisor`.

### 3.1 Dashboard (Overview)

* **Backend:** `ProjectManager`.
* **UI Elements:**
* **Stats:** Cards showing Entity/Relationship counts.
* **Console:** A `ui.log` element streaming `forge.log` content in real-time.
* **Action:** "Load/Create Project" using native file dialogs.



### 3.2 Phase 0: OSINT (Extraction)

* **Backend:** `ExtractionOrchestrator` & `Sentinel`.
* **UI Elements:**
* **Source Manager:** List of uploaded files (`.txt`, `.pdf`).
* **Sentinel Triage:** A split view comparing "New Extractions" vs. "Database Candidates" (Vector Match).
* **Controls:** "Merge", "Reject", "Commit to DB".



### 3.3 Phase 1: HUMINT (Entities)

* **Backend:** `forge.core.models.Entity`.
* **UI Elements:**
* **Grid:** `ui.aggrid` displaying all entities. Editable columns.
* **Detail Drawer:** Clicking a row opens the full JSON editor for that entity.
* **Assistant Context:** Selection in grid = Context for `UserProxyAgent`.



### 3.4 Phase 2: SIGINT (Relationships)

* **Backend:** `RelationshipsOrchestrator`.
* **UI Elements:**
* **Graph:** `ui.echarts` visualization (Nodes/Links).
* **Matrix:** Adjacency matrix table for dense relationship auditing.



### 3.5 Phase 3: SYNTH (Narrative)

* **Backend:** `NarrativeOrchestrator` (New).
* *Function:* Manages Markdown files in `project/narrative/`.
* *Search:* Exposes `VectorMemory.search()` to find entities relevant to the text.


* **UI Elements:**
* **Editor:** `ui.codemirror` (Markdown).
* **Fact Deck:** A sidebar suggesting entities based on the cursor's current paragraph (Semantic Search).



### 3.6 Phase 4: GEOINT (Cartography)

* **Backend:** `MapOrchestrator` (New).
* *Function:* Queries `world.db` for entities where `coordinates IS NOT NULL`.


* **UI Elements:**
* **Map:** `ui.leaflet` centered on the project's region.
* **Markers:** Draggable pins that update the underlying Entity's `coordinates` field.



### 3.7 Phase 5: ANVIL (Finalize)

* **Backend:** `FinalizeOrchestrator` & `Exporter`.
* **UI Elements:**
* **Validation:** Report view showing "Orphaned Entities" or "Missing Fields".
* **Export Deck:** Buttons invoking `exporter.py`:
* "Export to JSON" (Standard Format).
* "Export to World Bible" (Markdown Document).
* "Backup Database" (SQLite dump).





---

## 4. Implementation Priorities

### Step 1: The Skeleton (Critical Path)

1. **Init:** Set up `forge/frontend/main.py` with `native=True` and `forge/frontend/theme.py` (Layout).
2. **State:** Implement the Singleton `ForgeState` in `forge/frontend/state.py`.
3. **Dashboard:** Build `pages/dashboard.py` to verify project loading works.

### Step 2: The Core Loop (OSINT -> HUMINT)

1. **Agent:** Implement `forge/agents/user_proxy.py` to handle basic intent.
2. **OSINT:** Build `pages/osint.py` hooking into the existing `Sentinel` logic.
3. **HUMINT:** Build `pages/humint.py` using `ui.aggrid` for entity management.

### Step 3: The Expansions (P3, P4, P5)

1. **Stubs Implementation:** Write the `orchestrator.py` logic for P3 and P4 (Backend first).
2. **Visuals:** Add Leaflet (P4) and Editor (P3) to the UI.
3. **Export:** Create `exporter.py` and link it to `pages/anvil.py`.

### Step 4: Refinement

1. **Assistant Polish:** Refine the `UserProxyAgent` prompts to better handle "Edit Entity" commands.
2. **Testing:** Run manual smoke tests on the UI; write `pytest` cases for the new `exporter.py` and `user_proxy.py`.