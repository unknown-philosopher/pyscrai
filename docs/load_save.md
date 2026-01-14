Here’s how UI state (workspace schemas/intelligence cards) is saved and loaded:

## How UI State is Saved

1. **Intelligence services generate cards**: When services like `SemanticProfilerService`, `NarrativeSynthesisService`, etc. generate intelligence cards, they publish `TOPIC_WORKSPACE_SCHEMA` events:
   ```python
   await self.event_bus.publish(
       events.TOPIC_WORKSPACE_SCHEMA,
       events.create_workspace_schema_event({
           "type": "semantic_profile",
           "title": "Profile: Entity Name",
           "props": {...}
       })
   )
   ```

2. **Auto-save via subscription**: `DuckDBPersistenceService` subscribes to `TOPIC_WORKSPACE_SCHEMA` in its `start()` method:
   ```48:51:forge/infrastructure/persistence/duckdb_service.py
   await self.event_bus.subscribe(
       events.TOPIC_WORKSPACE_SCHEMA,
       self.handle_workspace_schema
   )
   ```

3. **Persist to database**: When a schema event is published, `handle_workspace_schema()` automatically:
   - Converts the schema to JSON
   - Creates a hash-based unique ID (to prevent duplicates)
   - Stores it in the `ui_artifacts` table
   ```182:206:forge/infrastructure/persistence/duckdb_service.py
   async def handle_workspace_schema(self, payload: EventPayload):
       """Persist workspace schema (UI artifact) to DuckDB."""
       schema = payload.get("schema")
       if not schema or not self.conn:
           return
       
       # Generate a unique ID for this schema artifact
       # Use a hash of the schema content or timestamp-based ID
       import hashlib
       schema_json = json.dumps(schema, sort_keys=True)
       artifact_id = hashlib.md5(schema_json.encode()).hexdigest()
       
       # Check if this artifact already exists
       result = self.conn.execute(
           "SELECT id FROM ui_artifacts WHERE id = ?",
           (artifact_id,)
       ).fetchone()
       
       if not result:
           # Insert new artifact
           self.conn.execute("""
               INSERT INTO ui_artifacts (id, schema)
               VALUES (?, ?)
           """, (artifact_id, schema_json))
           self.conn.commit()
   ```

## How UI State is Loaded

1. **Restore session triggers load**: When you click "Open Project" or "Reload Session", `restore_session()` is called:
   ```45:51:forge/domain/session/session_manager.py
   # 2. Restore UI Visualizations
   artifacts = self.persistence.get_stored_ui_artifacts()
   if artifacts:
       logger.info(f"Loading {len(artifacts)} UI artifacts...")
       for schema in artifacts:
           # Emit to AppController to render in Workspace
           await self.controller.emit_schema(schema)
   ```

2. **Retrieve from database**: `get_stored_ui_artifacts()` reads all schemas from the `ui_artifacts` table:
   ```230:250:forge/infrastructure/persistence/duckdb_service.py
   def get_stored_ui_artifacts(self) -> List[Dict[str, Any]]:
       """Retrieve all stored UI artifacts."""
       if not self.conn:
           return []
       
       result = self.conn.execute("""
           SELECT id, schema, created_at
           FROM ui_artifacts
           ORDER BY created_at ASC
       """).fetchall()
       
       artifacts = []
       for row in result:
           try:
               schema_dict = json.loads(row[1])
               artifacts.append(schema_dict)
           except json.JSONDecodeError:
               # Skip malformed JSON
               continue
       
       return artifacts
   ```

3. **Emit schemas to UI**: Each schema is emitted via `controller.emit_schema()`, which publishes a `TOPIC_WORKSPACE_SCHEMA` event that:
   - Adds the schema to `AppController.workspace_schemas` reactive list
   - Triggers the shell's `_sync_workspace()` listener
   - Renders the schemas as UI cards in the Intel dashboard

## Summary

- Save: Automatic — whenever an intelligence service generates a card, it’s saved to the database via event subscription
- Load: Manual — triggered by "Open Project" or "Reload Session", which reads from the database and emits schemas to rebuild the UI

The UI state is the collection of workspace schemas (intelligence cards) stored as JSON in the `ui_artifacts` table.