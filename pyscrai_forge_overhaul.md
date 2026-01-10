# PyScrAI | Forge 3.0: FletX "Tactical" Blueprint

**Version:** 3.0.0 (Flet Native Edition)
**Design Philosophy:** "The Cockpit." High-density, low-latency, dark-mode tactical interface.
**Core Stack:** Flet (UI), FletX (State), Plotly (Graph Viz), DuckDB (Analytics), SVG Stacks (Map).

---

## 1. System Architecture

The application shifts from a web-server model (NiceGUI) to a native app model (Flet). The state is managed via `FletX`, acting as the bridge between the heavy Python backend and the Flutter-based frontend.

### 1.1 The "Two-Brain" Data Layer

We separate **Transactional State** (World) from **Analytical State** (Stats).

1. **Hot Store (OLTP) - SQLite (`world.db`):**
* **Role:** Authoritative truth. Handles all Entities, Relationships, and Vector Embeddings (`sqlite-vec`).
* **Access:** Direct via `forge.systems.storage.DatabaseManager`.
* **UI Interaction:** Real-time CRUD operations.


2. **Cold Store (OLAP) - DuckDB (In-Memory):**
* **Role:** Deep analysis, aggregations, and "Why" questions.
* **Integration:** On Dashboard load (or trigger), DuckDB attaches to `world.db` or ingests snapshots.
* **Queries:** "Show actor growth over the last 100 events", "Find isolated sub-communities," "Calculate centrality distribution."



### 1.2 The AG-UI Interaction Contract

Advisors are **Tools**, not Actors. They never mutate state directly.

* **The Flow:**
1. **User Context:** User selects an entity in HUMINT.
2. **Advisor Trigger:** Background worker sends context to LLM (Advisor).
3. **AG-UI Event:** LLM returns a structured **Suggestion** (JSON).
4. **UI Render:** Suggestion appears in the "Comms Panel" (Right Sidebar) as a card.
5. **User Action:** User clicks "Accept" -> Flet calls `Backend.mutate()` -> UI Updates.



---

## 2. Directory Structure

Refactored `forge/frontend` to accommodate Flet patterns.

```text
forge/
├── app/
│   ├── state.py              # FletX State Store (Singleton)
│   └── ...
├── frontend/
│   ├── main.py               # Flet Entry Point
│   ├── style.py              # Theme definitions (Dark/Tactical colors)
│   ├── assets/               # Fonts (JetBrains Mono), Icons
│   ├── components/
│   │   ├── app_shell.py      # The "Cockpit" frame (Sidebar, Header, Right Drawer)
│   │   ├── ag_ui.py          # The Advisor Suggestion Cards
│   │   ├── telemetry.py      # DuckDB powered charts
│   │   └── tactical_map.py   # SVG Stack component
│   └── views/
│       ├── dashboard.py      # DuckDB Analytics view
│       ├── osint.py          # Drag-and-drop ingestion
│       ├── humint.py         # DataTable Entity management
│       ├── sigint.py         # Plotly Network Graph
│       └── geoint.py         # SVG Stack Map
└── systems/
    └── analytics/
        └── duck_ops.py       # DuckDB query interface

```

---

## 3. UI Implementation Details

### 3.1 Core UI: The Cockpit (Flet Shell)

The app uses a 3-pane layout:

1. **Nav Rail (Left):** Icons only (Radar, Files, People, Network, Map).
2. **Mission Area (Center):** The active View.
3. **Comms Panel (Right):** The AG-UI stream (Collapsible).

**Styling Strategy:**

* **Font:** `JetBrains Mono` for data, `Inter` for headers.
* **Colors:** `Surface: #0a0a0a`, `Panel: #111111`, `Accent: #00b8d4` (Cyan).
* **Feedback:** All actions emit "Toasts" (Snackbars) styled as terminal logs.

### 3.2 Phase 0: OSINT (Extraction)

* **Interaction:** Native **Drag-and-Drop**.
* User drags a file into the "Drop Zone".
* Flet triggers `TextChunker` -> `EntityExtractor`.


* **Sentinel View:**
* A split-column layout (`ft.Row`).
* **Left:** Extracted Entity Card.
* **Right:** Database Candidate Card.
* **Center:** "Diff" visualization (Text highlighting differences).
* **Action:** Drag Left Card onto Right Card to trigger **Merge**.



### 3.3 Phase 2: SIGINT (Network Visualization)

* **Technology:** `flet.PlotlyChart` + `networkx`.
* **Mechanism:**
1. Backend creates `networkx.Graph`.
2. `layout_algorithm` (Spring/Kamada-Kawai) calculates (x, y) for nodes.
3. Python generates a **Plotly Scatter Trace**:
* *Trace 1 (Lines):* Edges (Grey, opacity based on strength).
* *Trace 2 (Dots):* Nodes (Colored by Entity Type).


4. **Events:** Clicking a node in Plotly triggers a callback to open the Entity Detail drawer.



### 3.4 Phase 4: GEOINT (Tactical Map)

* **Technology:** `flet.Stack` (The SVG Stack approach).
* **Mechanism:**
* **Base Layer:** `ft.Image` (The Fantasy Map or Region Snapshot).
* **Overlay:** A `ft.Stack` containing `ft.Container` widgets positioned absolutely.
* **Coordinate Math:**
* World Coordinates (Lat/Long or X/Y) mapped to `%` of Image Width/Height.
* `left = (entity.x / map_width) * 100`
* `top = (entity.y / map_height) * 100`


* **Interaction:**
* Markers are `ft.Draggable`.
* Dropping a marker triggers `db.update_coordinates()`.





### 3.5 Analytics: The DuckDB Dashboard

* **Backend (`duck_ops.py`):**
```python
def get_entity_growth_metrics():
    con = duckdb.connect()
    con.execute("ATTACH 'world.db' AS world (TYPE SQLITE)")
    # Time-series analysis on the events_log table
    df = con.execute("""
        SELECT 
            time_bucket('1 hour', timestamp) as hour, 
            count(*) as mutations 
        FROM world.events_log 
        GROUP BY hour
    """).df()
    return df

```


* **Frontend:** Render `df` using a lightweight Plotly Bar Chart in the Dashboard view.

---

## 4. AG-UI Integration Schema

This defines how Advisors communicate with the Flet UI.

**Event Object (Python dataclass):**

```python
@dataclass
class AdvisorSuggestion:
    id: str
    advisor_name: str  # e.g., "SIGINT Advisor"
    severity: str      # "INFO", "WARNING", "OPPORTUNITY"
    message: str       # "Actor X has no connections."
    
    # The Payload defines what happens if User accepts
    suggested_action: str  # e.g., "LINK_ENTITIES"
    action_payload: dict   # {"source": "X", "target": "Y", "type": "associate"}

```

**UI Component (`ag_ui.py`):**

* Renders a Card in the Right Drawer.
* **Visuals:**
* Border color based on `severity`.
* "Typewriter" effect for the `message`.


* **Buttons:**
* `[APPLY]`: Calls `forge.core.actions.execute(suggested_action, action_payload)`.
* `[DISMISS]`: Removes card.



---

## 5. Implementation Roadmap

### Step 1: Foundation (The Skeleton)

1. Initialize `forge/frontend` with Flet structure.
2. Implement `FletX` state store connecting to `ForgeState`.
3. Build the `AppShell` (Sidebar + Main Area + Right Drawer).

### Step 2: The Core Loop (Entities)

1. Port `OSINT` Sentinel logic to Flet Drag-and-Drop.
2. Implement `HUMINT` DataTable with filtering/sorting.

### Step 3: Visualization (The Eye Candy)

1. Implement `SIGINT` using `networkx` -> Plotly translation.
2. Implement `GEOINT` using `ft.Stack` and relative positioning.

### Step 4: Intelligence (Brains)

1. Hook up DuckDB for the Dashboard metrics.
2. Implement the `AG-UI` right-drawer stream and connect one Advisor (e.g., Validator) to emit events.

## 6. Sample Code: Flet Entry Point

```python
import flet as ft
from forge.app.state import ForgeState
from forge.frontend.components.app_shell import AppShell

def main(page: ft.Page):
    # 1. Config
    page.title = "PyScrAI | Forge"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.window_width = 1400
    page.window_height = 900
    
    # 2. State Init
    state = ForgeState.init()
    
    # 3. Build Shell
    shell = AppShell(page, state)
    
    # 4. Routing
    def route_change(route):
        shell.navigate(route.route)
        
    page.on_route_change = route_change
    page.add(shell)
    page.go("/dashboard")

if __name__ == "__main__":
    ft.app(target=main)

```