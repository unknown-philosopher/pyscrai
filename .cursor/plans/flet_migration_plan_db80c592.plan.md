---
name: Flet Migration Plan
overview: Migrate PyScrAI Forge from NiceGUI (web-based) to Flet (native desktop), implementing the "Cockpit" tactical interface with FletX state management, DuckDB analytics, Plotly visualizations, and AG-UI advisor suggestion integration.
todos:
  - id: foundation_structure
    content: Create forge/frontend/ directory structure with components/, views/, assets/ subdirectories
    status: completed
  - id: fletx_state
    content: Implement forge/frontend/state.py (FletX wrapper bridging ForgeState to Flet reactive state)
    status: completed
    dependencies:
      - foundation_structure
  - id: app_shell
    content: Build forge/frontend/components/app_shell.py with 3-pane layout (Nav Rail, Mission Area, Comms Panel)
    status: completed
    dependencies:
      - fletx_state
  - id: theme_system
    content: Create forge/frontend/style.py with tactical dark theme (colors, fonts, reusable styles)
    status: completed
    dependencies:
      - foundation_structure
  - id: flet_entry_point
    content: Create forge/frontend/main.py as Flet entry point with routing setup
    status: completed
    dependencies:
      - app_shell
      - theme_system
  - id: landing_view
    content: Migrate landing page to forge/frontend/views/landing.py with project selection/creation
    status: completed
    dependencies:
      - flet_entry_point
  - id: dashboard_view
    content: Migrate dashboard to forge/frontend/views/dashboard.py with metrics cards and activity feed
    status: completed
    dependencies:
      - flet_entry_point
  - id: osint_view
    content: Migrate OSINT view with native drag-and-drop file upload and Sentinel triage panel
    status: pending
    dependencies:
      - flet_entry_point
  - id: humint_view
    content: Migrate HUMINT view with Flet DataTable for entity management
    status: pending
    dependencies:
      - flet_entry_point
  - id: network_graph_component
    content: Create forge/frontend/components/network_graph.py using networkx + Plotly (replacing ECharts)
    status: pending
    dependencies:
      - flet_entry_point
  - id: sigint_view
    content: Migrate SIGINT view with Plotly network graph integration
    status: pending
    dependencies:
      - network_graph_component
  - id: tactical_map_component
    content: Create forge/frontend/components/tactical_map.py using SVG Stack approach (replacing Leaflet)
    status: pending
    dependencies:
      - flet_entry_point
  - id: geoint_view
    content: Migrate GEOINT view with draggable markers on SVG stack map
    status: pending
    dependencies:
      - tactical_map_component
  - id: synth_anvil_views
    content: Migrate SYNTH and ANVIL views to Flet
    status: completed
    dependencies:
      - flet_entry_point
  - id: duckdb_analytics
    content: Create forge/systems/analytics/duck_ops.py with DuckDB query functions for time-series and metrics
    status: completed
  - id: dashboard_analytics_integration
    content: Integrate DuckDB analytics into dashboard view with Plotly charts
    status: pending
    dependencies:
      - dashboard_view
      - duckdb_analytics
  - id: ag_ui_component
    content: Create forge/frontend/components/ag_ui.py with AdvisorSuggestion cards and action handlers
    status: completed
    dependencies:
      - app_shell
  - id: action_execution_system
    content: Create forge/core/actions.py for executing advisor-suggested actions (LINK_ENTITIES, etc.)
    status: completed
  - id: advisor_event_integration
    content: Connect advisors to emit suggestions via event system, displayed in AG-UI component
    status: pending
    dependencies:
      - ag_ui_component
      - action_execution_system
  - id: update_entry_point
    content: Update forge/app/main.py to launch Flet frontend instead of NiceGUI
    status: completed
    dependencies:
      - flet_entry_point
  - id: update_dependencies
    content: Update setup.py with flet, plotly, duckdb dependencies
    status: completed
---

# Flet Migration Plan: NiceGUI to Flet Native

## Overview

Migrate the PyScrAI Forge frontend from NiceGUI (web-server model) to Flet (native desktop app) with a tactical "Cockpit" interface. The migration maintains all existing functionality while improving performance and adding new capabilities.

## Architecture Changes

### Current State

- **Frontend**: NiceGUI (web-based, runs as local server)
- **Location**: `forge/legacy_nicegui/` (imported as `forge.frontend`)
- **Visualization**: ECharts (JavaScript charts), Leaflet (maps)
- **State**: Singleton `ForgeState` with session tracking
- **Advisors**: Exist but not connected to UI

### Target State

- **Frontend**: Flet (native desktop, Flutter-based)
- **Location**: New `forge/frontend/` directory
- **Visualization**: Plotly (Python charts), SVG Stack (maps)
- **State**: Custom FletX wrapper bridging `ForgeState` to Flet state
- **Analytics**: DuckDB for deep analytics queries
- **AG-UI**: Structured advisor suggestion cards in right drawer

## Implementation Phases

### Phase 1: Foundation Setup

**1.1 Create New Frontend Structure**

- Create `forge/frontend/` directory with subdirectories:
  - `components/` - Reusable UI components
  - `views/` - Page views (renamed from `pages/`)
  - `assets/` - Fonts (JetBrains Mono), icons
- Create `forge/frontend/main.py` - Flet entry point
- Create `forge/frontend/style.py` - Theme definitions (dark/tactical colors)
- Create `forge/frontend/__init__.py` with proper exports

**1.2 Implement FletX State Management**

- Create `forge/frontend/state.py` (FletX wrapper):
  - Wraps `ForgeState` singleton
  - Bridges Flet reactive state to backend `ForgeState`
  - Manages UI context (active_page, selected_entities)
  - Provides update callbacks for UI refresh
- Implement reactive state updates when backend state changes

**1.3 Build App Shell Component**

- Create `forge/frontend/components/app_shell.py`:
  - **Nav Rail (Left)**: Icon-only navigation (Dashboard, OSINT, HUMINT, SIGINT, SYNTH, GEOINT, ANVIL)
  - **Mission Area (Center)**: Main content area with routing
  - **Comms Panel (Right)**: Collapsible drawer for AG-UI suggestions
- Implement navigation routing system
- Apply tactical dark theme styling

**1.4 Theme System**

- Port color palette from `legacy_nicegui/theme.py`:
  - Surface: `#0a0a0a`, Panel: `#111111`, Accent: `#00b8d4`
  - Fonts: JetBrains Mono for data, Inter for headers
- Create reusable style functions in `forge/frontend/style.py`
- Implement toast notifications styled as terminal logs

### Phase 2: Core Views Migration

**2.1 Landing/Project Selection View**

- Create `forge/frontend/views/landing.py`:
  - Port project list from `legacy_nicegui/pages/landing.py`
  - Port project creation form
  - Use Flet `ft.ListView` or `ft.DataTable` for project list
  - Flet file picker for project selection

**2.2 Dashboard View**

- Create `forge/frontend/views/dashboard.py`:
  - Port metrics cards from `legacy_nicegui/pages/dashboard.py`
  - **NEW**: Integrate DuckDB analytics (see Phase 4)
  - Port activity feed component
  - Replace ECharts pie chart with Plotly (via `ft.PlotlyChart`)

**2.3 OSINT View (Sentinel)**

- Create `forge/frontend/views/osint.py`:
  - Port file upload from `legacy_nicegui/pages/osint.py`
  - **NEW**: Implement native drag-and-drop using Flet `ft.FilePicker`
  - Port Sentinel triage panel (left vs right entity comparison)
  - Port merge/reject actions
  - **ENHANCEMENT**: Drag-and-drop merge (drag left card onto right card)

**2.4 HUMINT View (Entities)**

- Create `forge/frontend/views/humint.py`:
  - Port entity management from `legacy_nicegui/pages/humint.py`
  - Replace AG Grid with Flet `ft.DataTable`:
    - Columns: ID, Name, Type, Description, Tags
    - Support filtering, sorting, inline editing
  - Port entity editor dialog as Flet `ft.AlertDialog`
  - Port entity creation form

### Phase 3: Visualization Components

**3.1 SIGINT Network Graph**

- Create `forge/frontend/components/network_graph.py`:
  - **Replacement**: Use `networkx` + `plotly` instead of ECharts
  - Implement graph generation:

    1. Backend creates `networkx.Graph` from entities/relationships
    2. Apply layout algorithm (Spring/Kamada-Kawai) for (x, y) coordinates
    3. Generate Plotly Scatter traces:

       - Trace 1: Edges (lines, grey, opacity by strength)
       - Trace 2: Nodes (dots, colored by entity type)
  - Display via `ft.PlotlyChart`
  - Wire node click events to open entity detail drawer
- Create `forge/frontend/views/sigint.py`:
  - Port controls from `legacy_nicegui/pages/sigint.py`
  - Integrate network graph component
  - Port community detection and key actor analysis

**3.2 GEOINT Tactical Map**

- Create `forge/frontend/components/tactical_map.py`:
  - **Replacement**: SVG Stack approach instead of Leaflet
  - Base layer: `ft.Image` widget (fantasy map or region snapshot)
  - Overlay: `ft.Stack` containing absolutely positioned `ft.Container` widgets
  - Coordinate mapping: World coordinates (lat/long or X/Y) → % of image dimensions
    - `left = (entity.x / map_width) * 100`
    - `top = (entity.y / map_height) * 100`
  - Markers as `ft.Draggable` widgets
  - Handle drag events to update coordinates via `db.update_coordinates()`
- Create `forge/frontend/views/geoint.py`:
  - Port map controls from `legacy_nicegui/pages/geoint.py`
  - Integrate tactical map component
  - Port entity list drawer (right side, collapsible)

**3.3 SYNTH View (Narrative)**

- Create `forge/frontend/views/synth.py`:
  - Port narrative editor from `legacy_nicegui/pages/synth.py`
  - Use Flet `ft.TextField` for multi-line text editing
  - Port Fact Deck sidebar (semantic search suggestions)
  - Maintain debounced suggestion updates

**3.4 ANVIL View (Finalize)**

- Create `forge/frontend/views/anvil.py`:
  - Port finalization controls from `legacy_nicegui/pages/anvil.py`
  - Port merge suggestions display
  - Port export functionality

### Phase 4: Analytics & Intelligence

**4.1 DuckDB Integration**

- Create `forge/systems/analytics/` directory:
  - `__init__.py`
  - `duck_ops.py` - DuckDB query interface:
    ```python
    def get_entity_growth_metrics():
        con = duckdb.connect()
        con.execute("ATTACH 'world.db' AS world (TYPE SQLITE)")
        df = con.execute("""
            SELECT 
                time_bucket('1 hour', timestamp) as hour, 
                count(*) as mutations 
            FROM world.events_log 
            GROUP BY hour
        """).df()
        return df
    ```

  - Implement functions for:
    - Entity growth over time
    - Relationship network metrics
    - Centrality distributions
    - Sub-community detection
- Add DuckDB to `setup.py` dependencies

**4.2 Dashboard Analytics**

- Update `forge/frontend/views/dashboard.py`:
  - Call DuckDB analytics functions on load
  - Display time-series charts using Plotly
  - Show entity growth metrics, relationship density trends

**4.3 AG-UI Integration**

- Create `forge/frontend/components/ag_ui.py`:
  - Implement `AdvisorSuggestion` dataclass:
    ```python
    @dataclass
    class AdvisorSuggestion:
        id: str
        advisor_name: str  # "SIGINT Advisor"
        severity: str  # "INFO", "WARNING", "OPPORTUNITY"
        message: str  # "Actor X has no connections."
        suggested_action: str  # "LINK_ENTITIES"
        action_payload: dict  # {"source": "X", "target": "Y"}
    ```

  - Create suggestion card component:
    - Border color based on severity
    - Typewriter effect for message display
    - `[APPLY]` button: calls `forge.core.actions.execute()`
    - `[DISMISS]` button: removes card
- Integrate with App Shell right drawer (Comms Panel)
- Create suggestion event stream/listener system

**4.4 Connect Advisors to AG-UI**

- Modify advisor base class or create event emitter:
  - Advisors emit `AdvisorSuggestion` events
  - Event bus/listener pattern connects advisors to UI
  - Update `forge/agents/advisors/*.py` to emit suggestions
  - Example: ValidatorAgent validates and emits suggestions for missing relationships
- Create `forge/core/actions.py`:
  - Implements action execution: `execute(action: str, payload: dict)`
  - Routes to appropriate backend mutation methods
  - Returns success/failure for UI feedback

### Phase 5: Component Library & Utilities

**5.1 Reusable Components**

- Port `forge/frontend/components/entity_grid.py` → Use Flet `ft.DataTable`
- Port `forge/frontend/components/file_picker.py` → Use Flet `ft.FilePicker`
- Create `forge/frontend/components/telemetry.py`:
  - DuckDB-powered chart components
  - Reusable Plotly chart wrappers
- Create `forge/frontend/components/activity_feed.py`:
  - Port from `legacy_nicegui/components/activity_feed.py`
  - Display recent BaseEvent logs in terminal style

**5.2 Utility Functions**

- Port toast/notification system from NiceGUI to Flet
- Create terminal-style snackbar component
- Port UI context helpers from `legacy_nicegui/state.py`

### Phase 6: Entry Point & Integration

**6.1 Update Application Entry**

- Modify `forge/app/main.py`:
  - Update `run_ui()` to launch Flet instead of NiceGUI
  - Import from `forge.frontend.main` instead of `forge.legacy_nicegui.main`
  - Maintain backward compatibility flag if needed

**6.2 Update Imports**

- Update all backend code that imports from `forge.frontend`:
  - Change imports to use new `forge/frontend/` structure
  - Update `forge/__main__.py` if it has UI references

**6.3 Dependency Management**

- Update `setup.py`:
  - Add `flet` dependency
  - Add `plotly` dependency
  - Add `duckdb` dependency
  - Remove or make optional `nicegui` dependency
  - Add `networkx` if not already present

### Phase 7: Testing & Refinement

**7.1 Functional Testing**

- Test all views load correctly
- Test navigation between views
- Test entity CRUD operations
- Test file upload and extraction
- Test network graph interaction
- Test map marker dragging
- Test advisor suggestion flow

**7.2 Performance Testing**

- Verify native app performance (vs web server)
- Test large dataset handling (1000+ entities)
- Test network graph rendering with 100+ nodes
- Test DuckDB query performance

**7.3 UI/UX Refinement**

- Verify tactical dark theme consistency
- Test font rendering (JetBrains Mono)
- Verify toast notifications
- Test responsive layouts
- Verify accessibility (keyboard navigation)

## File Structure

```
forge/
├── frontend/                    # NEW: Flet frontend
│   ├── __init__.py
│   ├── main.py                 # Flet entry point
│   ├── state.py                # FletX state wrapper
│   ├── style.py                # Theme definitions
│   ├── assets/                 # Fonts, icons
│   ├── components/
│   │   ├── __init__.py
│   │   ├── app_shell.py        # Cockpit layout
│   │   ├── ag_ui.py            # Advisor suggestions
│   │   ├── network_graph.py    # Plotly network viz
│   │   ├── tactical_map.py     # SVG stack map
│   │   ├── telemetry.py        # DuckDB charts
│   │   └── activity_feed.py
│   └── views/                  # Page views
│       ├── __init__.py
│       ├── dashboard.py
│       ├── landing.py
│       ├── osint.py
│       ├── humint.py
│       ├── sigint.py
│       ├── synth.py
│       ├── geoint.py
│       └── anvil.py
├── systems/
│   └── analytics/              # NEW: DuckDB analytics
│       ├── __init__.py
│       └── duck_ops.py
├── core/
│   └── actions.py              # NEW: Action execution
└── legacy_nicegui/             # KEEP: Original implementation
    └── ...                     # (for reference)
```

## Key Design Decisions

1. **FletX Implementation**: Custom wrapper class that bridges `ForgeState` singleton to Flet's reactive state system, allowing both imperative backend updates and reactive UI updates.

2. **State Synchronization**: Use Flet's `on_event` callbacks to update UI when backend state changes. Backend mutations trigger UI refreshes via the FletX wrapper.

3. **Visualization Migration**: 

   - ECharts → Plotly: Direct Python integration, better performance
   - Leaflet → SVG Stack: Full control, supports fantasy maps, simpler coordinate system

4. **AG-UI Event System**: Implement an event bus pattern where advisors emit structured suggestions. UI subscribes to suggestion events and displays cards in the right drawer.

5. **Backward Compatibility**: Keep `legacy_nicegui/` directory for reference. New code uses `forge/frontend/` exclusively. Consider deprecation timeline separately.

## Migration Notes

- **No breaking changes to backend**: All `forge.systems.*`, `forge.phases.*`, `forge.core.*` remain unchanged
- **State management**: `ForgeState` singleton continues to work; FletX is a UI wrapper layer
- **Advisor integration**: Advisors don't need major changes; just add suggestion emission hooks
- **Testing strategy**: Migrate one view at a time, test thoroughly before moving to next

## Dependencies to Add

```python
# setup.py additions
flet >= 0.24.0
plotly >= 5.18.0
duckdb >= 0.10.0
networkx >= 3.2  # If not already present
```

## Success Criteria

1. All views functional in Flet native app
2. Network graph renders correctly with Plotly
3. Map markers draggable and save coordinates
4. DuckDB analytics queries working in Dashboard
5. AG-UI suggestions display and are actionable
6. Performance improved over web-based NiceGUI
7. Dark tactical theme consistently applied
8. All existing functionality preserved