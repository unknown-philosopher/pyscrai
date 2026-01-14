# Persistence & Relationships Analysis

## 1. Narrative Persistence ❌

**Answer: NO - Narratives are NOT persisted to database**

**Current Implementation:**
- Narratives are **only cached in memory** (`self._narrative_cache: Dict[str, str]`)
- Narratives are published to workspace schema (saved to `ui_artifacts` table)
- But narratives themselves are **NOT saved to a dedicated database table**
- Narratives are **regenerated** each time (requires LLM calls)

**Code Reference:**
```44:105:forge/domain/intelligence/narrative_service.py
# Cache narratives per document
self._narrative_cache: Dict[str, str] = {}

# Later in generate_narrative():
if narrative:
    # Cache the narrative
    self._narrative_cache[doc_id] = narrative  # ← Only in memory
```

**Database Schema:**
- ❌ No `narratives` table exists
- Narratives are only in `ui_artifacts` table as part of workspace schemas (not structured)

**Summary:**
- ❌ Narratives are **NOT persisted** to database
- ❌ Only cached in memory
- ❌ Regenerated on each extraction (expensive)

---

## 2. Relationship-Entity Links ✅

**Answer: YES - Relationships are linked to entities via FOREIGN KEY constraints**

**Database Schema:**
```83:95:forge/infrastructure/persistence/duckdb_service.py
CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY DEFAULT nextval('rel_seq'),
    source VARCHAR NOT NULL,
    target VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    confidence DOUBLE NOT NULL,
    doc_id VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source) REFERENCES entities(id),  # ← Link to entities
    FOREIGN KEY (target) REFERENCES entities(id)   # ← Link to entities
)
```

**Indexes for Performance:**
```101:106:forge/infrastructure/persistence/duckdb_service.py
CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source)
CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target)
```

**Link Structure:**
- Each relationship has `source` and `target` columns
- Both are FOREIGN KEY references to `entities.id`
- Indexes on both `source` and `target` for fast lookups
- This ensures referential integrity - relationships can't point to non-existent entities

**Benefits:**
- ✅ Referential integrity enforced by database
- ✅ Can query relationships by entity (JOIN operations)
- ✅ Can query entities and their relationships efficiently
- ✅ Prevents orphaned relationships

**Summary:**
- ✅ **Strong linkage** between relationships and entities
- ✅ FOREIGN KEY constraints ensure integrity
- ✅ Indexes optimize queries

---

## 3. Semantic Profile Persistence - Critical Analysis

### Should Semantic Profiles Be Persisted? ✅ **YES - Highly Recommended**

### Current State:
- ❌ Profiles only cached in memory (`self._profile_cache`)
- ❌ Not persisted to database
- ❌ Regenerated on every restore (expensive - many LLM calls)

### Recommended Implementation:

**1. Create `semantic_profiles` Table:**
```sql
CREATE TABLE IF NOT EXISTS semantic_profiles (
    entity_id VARCHAR PRIMARY KEY,
    summary TEXT NOT NULL,
    key_attributes TEXT,  -- JSON array of attributes
    related_entities TEXT,  -- JSON array of related entity IDs
    significance_score DOUBLE,
    profile_json TEXT,  -- Full profile as JSON for flexibility
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
)

CREATE INDEX IF NOT EXISTS idx_profiles_significance ON semantic_profiles(significance_score)
```

**2. Benefits of Persistence:**
- ✅ **Cost Savings**: No need to regenerate profiles on restore (saves 37+ LLM calls per restore)
- ✅ **Performance**: Instant profile loading vs. waiting for LLM generation
- ✅ **Consistency**: Profiles persist across sessions
- ✅ **Queryability**: Can query profiles by significance, entity type, etc.
- ✅ **Version Control**: Track when profiles were created/updated

**3. Link to Entities:**
- ✅ **FOREIGN KEY constraint** links `entity_id` to `entities.id`
- ✅ **ON DELETE CASCADE** ensures profile is deleted if entity is deleted
- ✅ Can JOIN entities with profiles for rich queries
- ✅ Provides referential integrity

**4. Update Workflow:**
- When entity is merged/deleted, profile should be updated/deleted
- When new relationships are discovered, profile can be regenerated
- Profile version tracking (created_at, updated_at)

**Critical Feedback:**
- **STRONGLY RECOMMEND** adding semantic profile persistence
- The cost of regeneration (37+ LLM calls × ~$0.001/call = $0.037+ per restore) adds up
- Profiles are valuable intelligence that should be preserved
- The link to entities via FOREIGN KEY is essential for data integrity

---

## 4. Project Save Mechanism - Database File Copy ✅

**Answer: The entire `forge_data.duckdb` file is COPIED when saving a project**

**Current Implementation:**
```214:253:forge/domain/session/session_manager.py
async def save_project(self, file_path: str) -> None:
    """Save the current project database to the specified file path."""
    # ... checkpoint and commit ...
    
    # Copy the database file to the target location
    db_path = Path(self.persistence.db_path)  # forge_data.duckdb
    target_path = Path(file_path)  # project.duckdb
    
    # Copy the database file
    if db_path.exists():
        shutil.copy2(db_path, target_path)  # ← Copies entire file
        # Also copy WAL file if it exists
        wal_path = db_path.with_suffix('.duckdb.wal')
        if wal_path.exists():
            target_wal_path = target_path.with_suffix('.duckdb.wal')
            shutil.copy2(wal_path, target_wal_path)
```

**Data Flow:**
1. **During Extraction:**
   - Entities/relationships are **auto-saved** to `forge_data.duckdb` via `handle_graph_updated()`
   - Deduplication changes are **committed immediately** to `forge_data.duckdb`
   - UI artifacts are saved to `forge_data.duckdb`
   - Everything goes into the **scratch database** (`forge_data.duckdb`)

2. **When Saving Project:**
   - `CHECKPOINT` ensures WAL is flushed to main database file
   - Entire `forge_data.duckdb` file is **copied** to project location
   - WAL file is also copied (if exists)
   - This is a **file-level copy**, not individual record collection

**What Gets Saved:**
- ✅ All entities (including deduplicated state)
- ✅ All relationships (with updated entity references after deduplication)
- ✅ UI artifacts (workspace schemas)
- ✅ Everything in `forge_data.duckdb` at the time of save

**What Does NOT Get Saved:**
- ❌ Semantic profiles (not in database - only in memory)
- ❌ Narratives (not in database - only in memory)
- ❌ Vector embeddings in Qdrant (in-memory, re-indexed on restore)

**Your Understanding:**
✅ **CORRECT** - The scratch database (`forge_data.duckdb`) receives all data during extraction, and when saving a project, the entire file is copied. This means:
- Deduplication changes are already in `forge_data.duckdb` before save
- Project save is a simple file copy operation
- All persisted data (entities, relationships, UI artifacts) is included in the copy

---

## 5. Critical Feedback on Linking

### Semantic Profiles → Entities Link ✅ **HIGHLY RECOMMENDED**

**Why Link is Valuable:**
1. **Referential Integrity**: Ensures profiles can't exist for non-existent entities
2. **Cascade Delete**: When entity is deleted/merged, profile is automatically cleaned up
3. **Query Efficiency**: Can JOIN entities with profiles for rich queries
4. **Data Consistency**: Single source of truth for entity-profile relationships

**Implementation:**
```sql
FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
```

**Benefits:**
- ✅ Automatic cleanup on entity deletion
- ✅ Database enforces relationship integrity
- ✅ Can query entities with their profiles efficiently
- ✅ Can find entities by profile attributes

### Relationships → Entities Link ✅ **ALREADY IMPLEMENTED**

**Current State:**
- ✅ FOREIGN KEY constraints on `source` and `target`
- ✅ Indexes for performance
- ✅ Referential integrity enforced

**Why This is Valuable:**
1. **Data Integrity**: Prevents orphaned relationships
2. **Query Efficiency**: Can find all relationships for an entity quickly
3. **Cascade Updates**: When entity is merged, relationships are updated (manual in deduplication service)
4. **Graph Traversal**: Can efficiently traverse the graph via JOIN operations

**Already Working Well:**
- ✅ Strong linkage via FOREIGN KEY
- ✅ Indexes optimize lookups
- ✅ Deduplication service properly updates relationships when entities merge

---

## Summary & Recommendations

### Current Persistence Status:

| Data Type | Persisted? | Storage Location |
|-----------|------------|------------------|
| Entities | ✅ Yes | `forge_data.duckdb` → copied to project |
| Relationships | ✅ Yes | `forge_data.duckdb` → copied to project |
| Deduplication State | ✅ Yes | Already reflected in entities/relationships |
| UI Artifacts | ✅ Yes | `ui_artifacts` table in `forge_data.duckdb` |
| Semantic Profiles | ❌ No | Only in memory cache |
| Narratives | ❌ No | Only in memory cache |
| Vector Embeddings | ❌ No | Qdrant (in-memory, re-indexed on restore) |

### Recommended Actions:

1. **✅ Add Semantic Profile Persistence:**
   - Create `semantic_profiles` table with FOREIGN KEY to entities
   - Save profiles after generation
   - Load profiles on restore (skip regeneration)
   - **Impact**: Saves significant LLM costs and improves restore speed

2. **✅ Add Narrative Persistence (Optional):**
   - Create `narratives` table linked to `doc_id`
   - Save narratives after generation
   - Load narratives on restore
   - **Impact**: Saves LLM costs, but narratives are less frequently accessed than profiles

3. **✅ Keep Relationship-Entity Links:**
   - Current FOREIGN KEY implementation is excellent
   - Maintains data integrity and query efficiency

### Project Save Mechanism:

✅ **Your understanding is correct:**
- `forge_data.duckdb` serves as the scratch database
- All data (entities, relationships, deduplication changes) is auto-saved to `forge_data.duckdb` during extraction
- When saving a project, the entire database file is copied
- This means deduplication changes are already persisted before save

### Critical Feedback on Semantic Profile Persistence:

**STRONGLY RECOMMEND** adding semantic profile persistence because:
1. **Cost Efficiency**: Avoids 37+ LLM calls per restore (saves ~$0.037+ per restore)
2. **Performance**: Instant profile loading vs. waiting for generation
3. **Data Value**: Profiles are valuable intelligence that should be preserved
4. **Link Value**: FOREIGN KEY link ensures data integrity and enables rich queries
5. **Consistency**: Profiles persist across sessions, maintaining analysis continuity

The link to entities via FOREIGN KEY is essential and provides the same benefits as the relationship-entity link (referential integrity, cascade delete, query efficiency).
