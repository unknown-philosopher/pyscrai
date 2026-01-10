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


Here is an analysis of your NiceGUI implementation for PyScrAI, focusing on optimizing the "Intelligence Platform" aesthetic while improving data density and usability.

### **1. General Design Critique**

Your current implementation successfully establishes a distinct "Hacker/Cyberpunk" aesthetic using dark modes, monospace fonts (`JetBrains Mono`), and cyan accents (`#00b8d4`). However, the dashboard layouts shown in the screenshots (e.g., `image_52efcc.png`) suffer from **Low Information Density**.

* **The Issue:** Large swaths of black space with isolated metrics make the application feel "empty" rather than "clean." In intelligence interfaces (like Palantir or Maltego), the goal is usually high data density that remains scannable.
* **The Fix:** Transition from "Linear Stacking" (columns of cards) to a **"Bento Grid"** or **Modular Dashboard** layout. Use the empty space for *activity visualization* (timelines, activity feeds) rather than static static navigation lists.

---

### **2. Dashboard (Overview) Optimization**

**Current State:**
The current dashboard uses a 2-column grid. The left has metric cards and "Project Info," while the right has a redundant list of "Pipeline Phases" (which is already present in the sidebar) and "Quick Actions."

**Recommendation:**
Transform the Dashboard into a **Mission Control Center**.

1. **Remove Redundancy:** Eliminate the "Pipeline Phases" list from the main dashboard area. The Sidebar already handles navigation.
2. **Metrics Row:** Instead of vertical cards, use a top horizontal row for high-level stats (Entities, Relationships, Alerts) with mini sparkline charts (using ECharts) to show recent activity (e.g., "5 entities added in the last hour").
3. **Activity Feed:** Replace the static "Project Info" with a scrolling "System Log" or "Intelligence Feed" that shows the last 10-20 `BaseEvent` logs (Entity Created, Merge Approved). This makes the system feel *alive*.
4. **Visual Distribution:** Add a "Entity Distribution" pie/bar chart (Actors vs. Locations vs. Polities) to give an immediate sense of the dataset's composition.

**Proposed Layout (Code Sketch):**

```python
from nicegui import ui

def render_metric_card(label, value, subtext, icon):
    with ui.card().classes("bg-gray-900 border border-gray-800 p-4 gap-2 min-w-[200px]"):
        with ui.row().classes("items-center justify-between w-full"):
            ui.label(label).classes("text-gray-500 text-xs font-mono tracking-wider")
            ui.icon(icon, size="xs").classes("text-cyan-500")
        ui.label(str(value)).classes("text-3xl font-mono text-white font-bold my-1")
        ui.label(subtext).classes("text-xs text-cyan-700")

def optimized_dashboard():
    # 1. Metrics (Horizontal Row)
    with ui.row().classes("w-full gap-4 mb-6"):
        render_metric_card("ENTITIES", "142", "+12 this session", "group")
        render_metric_card("RELATIONS", "305", "High connectivity", "hub")
        render_metric_card("DOCUMENTS", "8", "1 pending extraction", "description")
        render_metric_card("ALERTS", "3", "2 Validation Errors", "warning")

    # 2. Main Content Grid (2/3 Activity, 1/3 Quick Actions)
    with ui.grid(columns=3).classes("w-full gap-6 h-full"):
        
        # Left: Activity & Visualization (Span 2 columns)
        with ui.column().classes("col-span-2 gap-6"):
            # Entity Type Breakdown (EChart)
            with ui.card().classes("w-full h-64 bg-gray-900 border border-gray-800 p-4"):
                ui.label("DATASET_COMPOSITION").classes("text-gray-500 text-xs font-mono mb-2")
                # ... Insert ui.echart here ...
            
            # Recent Activity Log
            with ui.card().classes("w-full flex-grow bg-gray-900 border border-gray-800 p-0"):
                ui.label("SYSTEM_LOG").classes("text-gray-500 text-xs font-mono p-4 border-b border-gray-800")
                with ui.scroll_area().classes("h-64 p-2"):
                    # Use a timeline or compact list
                    for i in range(10):
                        with ui.row().classes("text-xs font-mono py-1 px-2 hover:bg-gray-800 rounded"):
                            ui.label("22:45:12").classes("text-gray-600 mr-2")
                            ui.label("SENTINEL").classes("text-cyan-600 mr-2")
                            ui.label("Merged entity 'Viper' with 'Captain Rossi'")

        # Right: Quick Actions & Status (Span 1 column)
        with ui.column().classes("col-span-1 gap-4"):
            with ui.card().classes("w-full bg-gray-900 border border-gray-800 p-4"):
                ui.label("QUICK_OPS").classes("text-gray-500 text-xs font-mono mb-4")
                ui.button("UPLOAD SOURCE", icon="upload").classes("w-full mb-2 bg-cyan-900 text-cyan-100")
                ui.button("NEW ENTITY", icon="add").classes("w-full mb-2 bg-gray-800")
                ui.button("RUN EXPORT", icon="download").classes("w-full bg-gray-800")

```

---

### **3. Phase-Specific Optimizations**

#### **Phase 0: OSINT (Extraction)**

* **Split-Pane Layout:** The current layout stacks Source selection and Sentinel triage side-by-side.
* *Improvement:* Use `ui.splitter`. This allows the user to resize the pane between the raw text (left) and the extraction results (right). Extraction work often requires reading long documents, so flexibility is key.


* **Diff Highlighting:** For the Sentinel, instead of just showing "New Entity" vs "Database Entity," implement a visual "Diff" view (red/green text highlighting) to show exactly *what* attributes are changing in a merge.

#### **Phase 2: SIGINT (Network Graph)**

* **Maximize Graph Area:** `image_52f006.png` shows significant vertical space lost to headers and toolbars.
* *Optimization:* Make the graph area `h-screen` (minus header height). Move the controls (Refresh, Layout, Communities) into a **floating semi-transparent panel** *inside* the graph area (top-left or top-right absolute positioning). This mimics tools like Google Earth or Photoshop, giving maximum focus to the visualization.
* *Interactive Legend:* Instead of a static legend, make the entity type legend clickable to toggle the visibility of nodes (Actors, Polities, etc.) directly on the graph.



#### **Phase 4: GEOINT (Map)**

* **Collapsible Sidebar:** Similar to SIGINT, the map needs maximum space. The entity list ("ENTITIES WITH COORDINATES") at the bottom is good, but it pushes the map up.
* *Optimization:* Move the entity list to a collapsible side drawer (separate from the nav sidebar) or a floating panel.


* **Custom Map Integration:** Since you support fantasy maps (`image_path`), add a small "Mini-map" or navigator in the corner if the image is high-resolution, to help users orient themselves when zoomed in.

### **4. Technical Optimizations for NiceGUI**

1. **Styling Abstraction:**
Currently, you inject a large block of CSS in `theme.py`.
* *Recommendation:* Move this to a dedicated `static/style.css` file and load it. It keeps your Python code cleaner and allows for easier editing of the "Cyberpunk" theme (e.g., tweaking the glow effects).


2. **State Management:**
You are using a global `_session` in `forge/frontend/state.py`.
* *Recommendation:* While this works for a local single-user app, ensure you use `app.storage.user` or `app.storage.browser` if you ever plan to persist UI preferences (like "Dark Mode toggle" or "Last Opened View") across restarts without relying solely on the backend database.


3. **Performance (AG Grid):**
In `humint.py`, you are loading *all* entities into the grid at once.
* *Optimization:* For larger projects (1000+ entities), enable AG Grid's **Server-Side Row Model** or virtual pagination. You can implement a simple callback in Python that queries `sqlite` with `LIMIT` and `OFFSET` based on the grid's scroll position.



### **5. Summary of Next Steps**

1. **Refactor `dashboard.py`:** Implement the "Metrics" and "Activity Feed" layout to reduce emptiness.
2. **Create `ui_components.py`:** Extract the "Card" and "Button" styling logic from `theme.py` into reusable classes (`ForgeCard`, `ForgeButton`) to ensure consistency and reduce code duplication.
3. **Floating Controls:** Update `sigint.py` and `geoint.py` to use absolute positioning for controls, reclaiming screen space for the visualizations.