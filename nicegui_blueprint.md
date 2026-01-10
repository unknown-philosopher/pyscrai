Master Blueprint for **PyScrAI|Forge 3.0**. This document unifies the 3.0 architecture analysis with the streamlined, singleton NiceGUI implementation plan.

# PyScrAI|Forge 3.0: Master System Blueprint

**Version:** 3.0.0
**Type:** Narrative Intelligence System (Local-First Desktop Application)
**Architecture:** State-Centralized Core + Thin Reactive Frontend (NiceGUI)

---

## 1. Executive Summary

PyScrAI|Forge 3.0 is a modular intelligence system designed to extract, analyze, and manage world-building data from unstructured text. It acts as a bridge between raw documents and a structured Knowledge Graph, utilizing Large Language Models (LLMs) for extraction and specialized "Advisors" for analysis.

The system adopts an **Intelligence Agency Metaphor** for its user interface and pipeline, guiding data from raw extraction to a refined knowledge base:

* **OSINT** (Open Source Intelligence) → Extraction
* **HUMINT** (Human Intelligence) → Entity Refinement
* **SIGINT** (Signals Intelligence) → Relationship/Network Analysis
* **SYNTH** (Synthesis) → Narrative Generation
* **GEOINT** (Geospatial Intelligence) → Map Anchoring
* **ANVIL** → Finalization

---

## 2. Core Architecture (The Backend)

The backend relies on a **State-Centralized** model where `ForgeState` serves as the mutable container for the active Project, Database, and LLM Provider.

### 2.1 Data Models (The "Blank Canvas")

* **Dynamic Entities:** Entities utilize a Pydantic `BaseModel` with a flexible `attributes: dict` field, moving away from rigid SQL columns. This allows the system to adapt to any genre (Espionage, Cyberpunk, Fantasy) seamlessly.
* **Prefabs & Schemas:** Field structures are defined by "Prefabs" (YAML/JSON templates). An `actor_espionage` schema injects fields like "clearance_level" and "handler" dynamically.
* **Event Sourcing:** Every state change (create, update, merge) is logged as an immutable `BaseEvent`. This ensures data integrity and enables "Retcon" (undo/history) capabilities.

### 2.2 Key Systems

* **Vector Memory (`sqlite-vec`):**
* **Local-First:** Embeddings are stored directly within `world.db` using the `sqlite-vec` extension, eliminating external vector DB dependencies.
* **Engine:** Uses `sentence-transformers` (e.g., `all-MiniLM-L6-v2`) to generate embeddings locally on the CPU/GPU.


* **The Sentinel:**
* A gatekeeper subsystem for **Phase 0 (OSINT)**.
* Ingests extracted entities and queries Vector Memory to detect duplicates.
* **High Similarity (>95%):** Auto-merge.
* **Moderate Similarity (>85%):** Flag as "Merge Candidate" for human review.


* **Prompt Engine:**
* Managed via `PromptManager` using **Jinja2** templates and YAML config.
* Supports dynamic context injection (loops, conditionals) to tailor Agent personas (Reviewer, Analyst, Validator).



---

## 3. Frontend Architecture (NiceGUI)

The frontend is a **Thin, Reactive Client** built with **NiceGUI**. It is designed as a **Single-User Desktop Application**, removing the complexity of web sessions, authentication, and API layers.

### 3.1 Design Philosophy

1. **Native Experience:** The app runs in "Native Mode" (using `pywebview`), appearing as a standard OS window without a browser address bar.
2. **Singleton State:** Since there is only one user, we use a single global instance of `ForgeState`.
3. **Direct Integration:** The UI calls backend functions directly (e.g., `orchestrator.process()`), bypassing REST APIs or JSON serialization overhead.
4. **Async/Sync Hybrid:** Blocking core operations (SQLite reads, File I/O) are wrapped in `app.storage` or `run.io_bound` to keep the UI reactive.

### 3.2 Directory Structure (`forge/frontend`)

```text
forge/frontend/
├── __init__.py
├── main.py                 # Entry point: ui.run(native=True)
├── theme.py                # Layout Shell: Sidebar, Header, Assistant Drawer
├── state.py                # Singleton State Manager
├── components/             # Reusable Widgets
│   ├── assistant.py        # Global LLM Chat Sidebar
│   ├── entity_grid.py      # AgGrid wrapper for HUMINT
│   ├── map_widget.py       # Leaflet wrapper for GEOINT
│   └── navigation.py       # Phase switching logic
└── pages/                  # Route Definitions
    ├── landing.py          # Project Select
    ├── dashboard.py        # Overview & Stats
    ├── osint.py            # P0: Extraction & Sentinel
    ├── humint.py           # P1: Entities
    ├── sigint.py           # P2: Relationships
    ├── synth.py            # P3: Narrative
    ├── geoint.py           # P4: Cartography
    └── anvil.py            # P5: Finalize

```

---

## 4. The Intelligence Pipeline (UI Implementation)

The UI maps the internal orchestrators (`p0`...`p5`) to the specific Intelligence Agency "Lore" names.

### 4.1 Global Layout (`theme.py`)

* **Sidebar (Left):** Navigation rail with icons for OSINT, HUMINT, SIGINT, etc.
* **Assistant Drawer (Right):** A persistent, collapsible chat interface available on *every* page.
* **Header:** Displays active project name and "Retcon" (Undo) controls.

### 4.2 Dashboard

* **Goal:** Mission Overview.
* **Components:**
* **Stats Cards:** Total Actors, Locations, Relationships, and Token Usage.
* **Activity Log:** A live scrolling log window (piping Python `logging` directly to a UI element).
* **Phase Stepper:** Visual progress bar showing the status of the current pipeline.



### 4.3 Phase 0: OSINT (Extraction)

* **Backend:** `forge.phases.p0_extraction`
* **UI Workflow:**
* **Source Input:** Native file picker to load text/PDFs.
* **Chunking View:** Visualize how the text is split for the LLM.
* **Sentinel Dashboard:** A "Triage" view.
* **Left Column:** New Extractions.
* **Right Column:** Database Matches (sorted by vector distance).
* **Action:** "Merge", "Create New", or "Discard" buttons.





### 4.4 Phase 1: HUMINT (Entities)

* **Backend:** `forge.phases.p1_entities`
* **UI Workflow:**
* **Entity Grid:** A high-performance `ui.aggrid` spreadsheet view.
* **Detail Editor:** Clicking a row opens a drawer to edit the JSON `attributes` directly or via a form generated from the active Prefab Schema.
* **Advisor Hook:** The "Assistant" panel gains context on selected rows to answer queries like *"Generate a psychological profile for this Agent."*



### 4.5 Phase 2: SIGINT (Relationships)

* **Backend:** `forge.phases.p2_relationships`
* **UI Workflow:**
* **Network Graph:** A `ui.echarts` or Cytoscape wrapper visualizing the social network.
* **Analysis Tools:** Buttons to trigger backend NetworkX algorithms (e.g., "Identify Community Clusters", "Find Shortest Path").
* **Matrix View:** An adjacency matrix table for rapid auditing of connections.



### 4.6 Phase 3: SYNTH (Narrative)

* **Backend:** `forge.phases.p3_narrative`
* **UI Workflow:**
* **Split Editor:**
* **Left:** Narrative text editor (`ui.codemirror` or `ui.textarea`).
* **Right:** "Fact Deck" (draggable entity cards/snippets).


* **LLM Tools:** Toolbar actions for "Expand", "Rewrite Tone", "Fact Check against DB".



### 4.7 Phase 4: GEOINT (Cartography)

* **Backend:** `forge.phases.p4_map`
* **UI Workflow:**
* **Map Engine:** **Leaflet** integration via `ui.leaflet`.
* **Functionality:**
* Render entities with `coordinates` as interactive markers.
* Draggable markers that update the underlying Entity's location data in real-time.
* Layer controls to toggle visibility of different Entity types (e.g., "Show Safehouses", "Hide Civilians").





### 4.8 Phase 5: ANVIL (Finalize)

* **Backend:** `forge.phases.p5_finalize`
* **UI Workflow:**
* **Validation Report:** A list of data integrity warnings (e.g., "Orphaned Entity", "Missing Description").
* **Export Center:** One-click generation of the final JSON packet, SQLite backup, or Markdown World Bible.



---

## 5. The "Assistant" Integration strategy

The Assistant is not just a chatbot; it is a command-line interface wrapped in natural language.

* **Implementation:**
* Built in `components/assistant.py`.
* Uses `forge.agents.UserProxyAgent`.


* **Context Awareness:**
* The `Assistant` component checks the `app.storage` or `state` to see the **Active Page**.
* **If on OSINT:** Context = "Current Source Document".
* **If on HUMINT:** Context = "Currently Selected Entities".


* **Direct Mutation:** The Assistant can trigger backend `OperationHandlers`.
* *User:* "Change Agent 47's status to MIA."
* *System:* Parses intent -> Calls `Entity.update(id="agent_47", status="MIA")` -> UI Auto-refreshes.



---

## 6. Implementation Checklist

1. **Scaffold:** Create `forge/frontend` directory and `main.py` configured with `ui.run(native=True)`.
2. **State Singleton:** Implement `state.py` to initialize `ForgeState` once on startup.
3. **Shell Layout:** Build `theme.py` with the "Intelligence Agency" dark mode aesthetic and sidebar navigation.
4. **Pages - Wave 1:** Implement `landing.py` (Load Project) and `dashboard.py` (Stats).
5. **Pages - Wave 2 (The Core):**
* `humint.py` (Entity Grid).
* `osint.py` (File loading + Sentinel view).


6. **Pages - Wave 3 (Visuals):**
* `geoint.py` (Leaflet map integration).
* `sigint.py` (Graph viz).


7. **Assistant:** Wire up the `UserProxyAgent` to the Right Drawer and ensure it can read the current page's context.