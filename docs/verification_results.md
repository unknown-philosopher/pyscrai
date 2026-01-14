# Verification Results: Deduplication & Semantic Profiling

## 1. Deduplication Logic Verification ✅

**Your Logic:**
- Deduplication shouldn't run during restore because it already ran during initial extraction
- Entities/relationships would have already been merged
- Restore state means no new information coming in

**Verification:**
✅ **CORRECT** - This logic is sound and has been implemented:
- Added `skip_deduplication: True` flag when triggering graph analysis during restore
- `DeduplicationService.handle_graph_updated()` checks this flag and skips processing
- During normal extraction, deduplication runs when `TOPIC_GRAPH_UPDATED` is published
- During restore, deduplication is skipped to avoid unnecessary LLM calls

**Code Reference:**
- `forge/domain/resolution/deduplication_service.py:65-70` - Skip logic implemented
- `forge/domain/session/session_manager.py:160-167` - Flag set during restore

---

## 2. Are Both Entities AND Relationships Deduplicated? ❌

**Answer: NO - Only entities are deduplicated**

**Entities:**
- ✅ Entities are deduplicated (similarity search + LLM confirmation)
- Duplicate entities are merged (one kept, one deleted)

**Relationships:**
- ❌ Relationships are **NOT deduplicated**
- Relationships are **UPDATED/REPOINTED** when entities merge:
  - When entity2 merges into entity1, all relationships pointing to entity2 are updated to point to entity1
  - Relationships pointing FROM entity2 → updated to FROM entity1
  - Relationships pointing TO entity2 → updated to TO entity1
  - The duplicate entity is deleted AFTER relationships are updated

**Code Reference:**
```185:243:forge/domain/resolution/deduplication_service.py
async def _merge_entities(self, entity1_id: str, entity2_id: str):
    """Merge two entities in the database.
    
    Keeps entity1, updates all relationships pointing to entity2 to point to entity1,
    then deletes entity2.
    """
    # Update relationships where entity2 is the source
    self.db_conn.execute("""
        UPDATE relationships
        SET source = ?
        WHERE source = ?
    """, (entity1_id, entity2_id))
    
    # Update relationships where entity2 is the target
    self.db_conn.execute("""
        UPDATE relationships
        SET target = ?
        WHERE target = ?
    """, (entity1_id, entity2_id))
    
    # Delete entity2
    self.db_conn.execute("""
        DELETE FROM entities
        WHERE id = ?
    """, (entity2_id,))
```

**Summary:**
- Only **entities** are deduplicated
- **Relationships** are updated/repointed (not deduplicated)

---

## 3. Are Duplicates Deleted After Merge and Persisted? ✅

**Answer: YES - Duplicates are deleted and persisted immediately**

**Process:**
1. Relationships pointing to duplicate entity are updated to point to kept entity
2. Duplicate entity is **DELETED** from database
3. Changes are **COMMITTED** to database immediately
4. Entity merged event is published

**Persistence:**
- ✅ Changes are **persisted immediately** via `self.db_conn.commit()`
- ✅ Not just in memory - written to database
- ✅ When project is saved, these changes are already in the database

**Code Reference:**
```214:227:forge/domain/resolution/deduplication_service.py
# Delete entity2
self.db_conn.execute("""
    DELETE FROM entities
    WHERE id = ?
""", (entity2_id,))

# Update entity1's timestamp
self.db_conn.execute("""
    UPDATE entities
    SET updated_at = NOW()
    WHERE id = ?
""", (entity1_id,))

self.db_conn.commit()  # ← Persisted immediately
```

**Summary:**
- ✅ Duplicates are **deleted** after merge
- ✅ Changes are **persisted immediately** (not just in memory)
- ✅ When project is saved, merged state is already in database

---

## 4. Semantic Profiles - Are They Saved to Database? ❌

**Answer: NO - Semantic profiles are NOT persisted to database**

**Current Implementation:**
- Semantic profiles are **cached in memory** only (`self._profile_cache`)
- Profiles are published to workspace schema (saved to `ui_artifacts` table)
- But profiles themselves are **NOT saved to a dedicated database table**
- Profiles are **regenerated** each time entities are loaded

**Database Schema:**
- ✅ `entities` table - exists
- ✅ `relationships` table - exists
- ✅ `ui_artifacts` table - exists (stores workspace schemas)
- ❌ `semantic_profiles` table - **DOES NOT EXIST**

**Code Reference:**
```44:45:forge/domain/intelligence/semantic_profiler.py
# Cache profiles to avoid re-computation
self._profile_cache: Dict[str, Dict[str, Any]] = {}
```

```147:168:forge/domain/intelligence/semantic_profiler.py
if profile:
    # Cache the profile
    self._profile_cache[entity_id] = profile  # ← Only in memory
    
    # Emit semantic profile event
    await self.event_bus.publish(
        events.TOPIC_SEMANTIC_PROFILE,
        {
            "entity_id": entity_id,
            "profile": profile,
        }
    )
    
    # Also publish to workspace schema for UI visualization
    await self.event_bus.publish(
        events.TOPIC_WORKSPACE_SCHEMA,  # ← Saved to ui_artifacts table
        events.create_workspace_schema_event({
            "type": "semantic_profile",
            "title": f"Profile: {entity_info['label']}",
            "props": profile
        })
    )
```

**Impact:**
- Profiles are regenerated on project load (expensive - many LLM calls)
- During restore, profiles need to be regenerated for all entities
- Profiles are not persisted across sessions

**Summary:**
- ❌ Semantic profiles are **NOT saved to database**
- ❌ Only stored in memory cache (`_profile_cache`)
- ❌ Published to workspace schema (saved to `ui_artifacts` table, but not as structured data)
- ❌ Profiles are **regenerated** each time (costly)

---

## Recommendations

### For Deduplication: ✅ Already Correct
- Current implementation is correct
- Skip deduplication during restore (already implemented)

### For Semantic Profiles: ⚠️ Consider Adding Persistence
If you want semantic profiles to persist across sessions:
1. Create a `semantic_profiles` table in the database
2. Save profiles after generation
3. Load profiles from database on restore (skip regeneration)
4. This would save LLM costs and improve restore speed

**Suggested Schema:**
```sql
CREATE TABLE IF NOT EXISTS semantic_profiles (
    entity_id VARCHAR PRIMARY KEY,
    profile_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (entity_id) REFERENCES entities(id)
)
```
