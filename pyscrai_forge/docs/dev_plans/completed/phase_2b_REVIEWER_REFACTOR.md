## Plan: Implement 3-State UI Architecture for PyScrAI|Forge

This refactoring transforms the reviewer interface from a simple component editor into a project-first workflow application with three distinct states: landing page → project dashboard → component editor.

### Steps

1. **Add State Management Infrastructure** - Add AppState enum (`LANDING`, `DASHBOARD`, `COMPONENT_EDITOR`), `UserConfig` integration, `current_state` tracking, and `manifest` loading to `ReviewerApp.__init__()`.

2. **Restructure Menu System** - Replace current menu structure in `_build_ui()` with new consolidated menus: File (project lifecycle), Project (configuration), Data (import/export/editing), Tools (utilities), with dynamic enable/disable based on project loaded state.

3. **Implement State Transition Logic** - Create `_transition_to_state()` method that clears main container, updates menu states, and delegates to state-specific builders (`_build_landing_page()`, `_build_dashboard()`, `_build_component_editor()`).

4. **Build Landing Page State** - Create `_build_landing_page()` that instantiates `LandingPageWidget` with New Project, Open Project buttons and recent projects list.

5. **Build Dashboard State** - Create `_build_dashboard()` that instantiates `ProjectDashboardWidget` showing project info, stats from database, and action buttons (Import/Edit/Browse).

6. **Move Component Editor to State Method** - Extract all existing validation banner, entity/relationship treeview code from current `_build_ui()` into new `_build_component_editor()` method, add "Back to Dashboard" button.

### Further Considerations

1. **Backward Compatibility** - Current CLI usage `python -m pyscrai_forge.src.reviewer packet.json` should still work - if packet_path provided, bypass landing/dashboard and go straight to component editor?

2. **Testing Strategy** - Test state transitions: LANDING→DASHBOARD (open project), DASHBOARD→COMPONENT_EDITOR (import file), COMPONENT_EDITOR→DASHBOARD (back button), menu enable/disable synchronization?

3. **User Config Persistence** - Recent projects list updates on every project load, max 10 entries, stored in %APPDATA%/pyscrai/user_config.json - verify cross-platform paths work correctly?

