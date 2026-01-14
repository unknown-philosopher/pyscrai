Here’s what happens when a prior project is reloaded and then new intel is added:

## Flow After Project Reload + New Intel

### 1. **Project Reload (Current State)**
- **Database**: Entities and relationships remain (unchanged)
- **Qdrant**: Collections cleared, then entities/relationships re-indexed as vectors
- **UI**: Restored cards from saved UI artifacts appear

Important: During restore, we bypass `TOPIC_ENTITY_EXTRACTED` and `TOPIC_RELATIONSHIP_FOUND`, so:
- No new database entries are created
- No duplicate extraction happens
- Only vectors are re-indexed

### 2. **New Intel Added**

When a new document is ingested:

```
New Document → Extraction → TOPIC_ENTITY_EXTRACTED
                              ↓
                    ┌─────────┴─────────┐
                    │                   │
         EmbeddingService      EntityResolutionService
                    │                   │
         TOPIC_ENTITY_EMBEDDED    TOPIC_RELATIONSHIP_FOUND
                    │                   │
            QdrantService          EmbeddingService
                    │                   │
         (stores vectors)      TOPIC_RELATIONSHIP_EMBEDDED
                                        │
                                  QdrantService
                                        │
                                  (stores vectors)
```

Then:
- **GraphAnalysisService** listens to `TOPIC_RELATIONSHIP_FOUND` → publishes `TOPIC_GRAPH_UPDATED`
- **DuckDBPersistenceService** listens to `TOPIC_GRAPH_UPDATED` → persists to database:
  - **Entities**: Uses UPSERT logic (UPDATE if exists, INSERT if new) — no duplicates by entity ID
  - **Relationships**: Uses INSERT (append only) — allows duplicates (same relationship from different documents)

### 3. **What This Means**

- **Entities**:
  - New entities → inserted into database
  - Existing entities → updated in database (timestamp refreshed)
  - Qdrant: Vectors added (duplicates are acceptable for similarity search)

- **Relationships**:
  - All relationships → inserted into database (duplicates allowed)
  - Qdrant: Vectors added

- **UI**:
  - New intelligence cards generated and added to existing restored cards
  - All cards (old + new) appear together

### 4. **Potential Considerations**

1. **Relationship duplicates**: The database allows duplicate relationships (same source/target/type from different documents). This is intentional for tracking provenance.
2. **Qdrant duplicates**: Vectors may have duplicates, which is fine for similarity search.
3. **Entity updates**: Existing entities get their `updated_at` timestamp refreshed, which helps track when they last appeared.

Overall, the system handles this gracefully: restored data coexists with new data, deduplication works, and the UI accumulates both old and new intelligence cards.