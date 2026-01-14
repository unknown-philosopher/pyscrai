# PyScrAI Data Extraction Pipeline

## Overview

The PyScrAI Forge data extraction pipeline is an event-driven architecture that processes documents through multiple phases, extracting entities, relationships, and generating intelligence. The system uses an **EventBus** for asynchronous communication between services.

## Architecture

**Event-Driven Architecture (EDA)**: All services communicate via an `EventBus` using topics. Services subscribe to events they care about and publish events when they complete their work.

## Pipeline Phases

### Phase 1: Document Ingestion
**Service**: `IngestController` (Presentation Layer)  
**Location**: `forge/presentation/controllers/ingest_controller.py`

1. User uploads/pastes document text via UI
2. Controller publishes `TOPIC_DATA_INGESTED` event
3. Event payload: `{doc_id: "doc_0001", content: "..."}`

**Event Published**: `TOPIC_DATA_INGESTED`

---

### Phase 2: Entity Extraction
**Service**: `DocumentExtractionService`  
**Location**: `forge/domain/extraction/service.py`  
**LLM Provider**: Required (e.g., OpenRouter)

**Subscribes to**: `TOPIC_DATA_INGESTED`

**Process**:
1. Receives document content from event
2. Uses LLM (via `call_llm_and_parse_json`) with `extraction_service.j2` template
3. Extracts entities (PERSON, ORGANIZATION, LOCATION, EVENT, etc.)
4. Normalizes entity format: `{type: "...", text: "..."}`
5. Retry logic with JSON format reminders (max 3 retries)

**Event Published**: `TOPIC_ENTITY_EXTRACTED`  
**Payload**: `{doc_id: "...", entities: [{type: "...", text: "..."}]}`

**Example Output**: 34-60 entities extracted per document

---

### Phase 3: Entity Embedding
**Service**: `EmbeddingService`  
**Location**: `forge/infrastructure/embeddings/embedding_service.py`  
**Model**: `BAAI/bge-base-en-v1.5` (CUDA-accelerated)

**Subscribes to**: `TOPIC_ENTITY_EXTRACTED`

**Process**:
1. Receives extracted entities
2. Generates semantic embeddings using SentenceTransformers
3. Batches entities (batch_size=32) for efficiency
4. Uses CUDA if available for GPU acceleration
5. Stores embeddings in memory (later persisted to Qdrant)

**Event Published**: `TOPIC_ENTITY_EMBEDDED`  
**Payload**: `{doc_id: "...", entities: [...], embeddings: [...]}`

**Note**: Runs in parallel with Phase 4 (Relationship Extraction)

---

### Phase 4: Relationship Extraction
**Service**: `EntityResolutionService`  
**Location**: `forge/domain/resolution/service.py`  
**LLM Provider**: Required

**Subscribes to**: 
- `TOPIC_DATA_INGESTED` (caches document content)
- `TOPIC_ENTITY_EXTRACTED` (extracts relationships)

**Process**:
1. Caches document content when `TOPIC_DATA_INGESTED` is received
2. Receives extracted entities from `TOPIC_ENTITY_EXTRACTED`
3. Uses LLM (via `call_llm_and_parse_json`) with `resolution_service.j2` template
4. Extracts relationships between entities:
   - Source entity
   - Target entity
   - Relationship type (e.g., "works_for", "located_in", "related_to")
   - Confidence score
5. Retry logic with JSON format reminders (max 3 retries)
6. **Important**: Processes ALL entities at once (can be 50+ entities)

**Event Published**: `TOPIC_RELATIONSHIP_FOUND`  
**Payload**: `{doc_id: "...", relationships: [{source: "...", target: "...", relation_type: "...", confidence: 0.9}]}`

**Example Output**: 22 relationships extracted from 34 entities

**Note**: `max_tokens` recently increased to handle large entity sets (previously caused JSON truncation errors)

**⚠️ Performance Bottleneck**: Processing all entities at once (50+) blocks the pipeline. See [Phase 4 Optimization Strategies](./phase4_optimization_strategies.md) for optimization approaches.

---

### Phase 5: Relationship Embedding
**Service**: `EmbeddingService` (same as Phase 3)

**Subscribes to**: `TOPIC_RELATIONSHIP_FOUND`

**Process**:
1. Receives extracted relationships
2. Generates embeddings for relationship triples (source, relation, target)
3. Batches relationships for efficiency
4. Stores embeddings in memory

**Event Published**: `TOPIC_RELATIONSHIP_EMBEDDED`  
**Payload**: `{doc_id: "...", relationships: [...], embeddings: [...]}`

---

### Phase 6: Graph Construction
**Service**: `GraphAnalysisService`  
**Location**: `forge/domain/graph/service.py`

**Subscribes to**: `TOPIC_RELATIONSHIP_FOUND`

**Process**:
1. Receives relationships from event
2. Builds in-memory graph structure:
   - Nodes: entities (entities are added as nodes)
   - Edges: relationships between entities
3. Maintains graph statistics:
   - Node count
   - Edge count
   - Node/edge lists

**Event Published**: `TOPIC_GRAPH_UPDATED`  
**Payload**: `{doc_id: "...", graph_stats: {node_count: 34, edge_count: 22, nodes: [...], edges: [...]}}`

**Note**: This is a critical event that triggers multiple downstream services

---

### Phase 7: Persistence (Database Save)
**Service**: `DuckDBPersistenceService`  
**Location**: `forge/infrastructure/persistence/duckdb_service.py`  
**Database**: DuckDB (`data/db/forge_data.duckdb`)

**Subscribes to**: `TOPIC_GRAPH_UPDATED`

**Process**:
1. Receives graph statistics (nodes and edges)
2. Upserts entities to `entities` table:
   - `id` (VARCHAR PRIMARY KEY)
   - `type` (VARCHAR)
   - `label` (VARCHAR)
   - `created_at`, `updated_at` (TIMESTAMP)
3. Inserts relationships to `relationships` table:
   - `id` (INTEGER PRIMARY KEY, auto-increment)
   - `source_id`, `target_id` (VARCHAR, foreign keys)
   - `relation_type` (VARCHAR)
   - `confidence` (DOUBLE)
   - `doc_id` (VARCHAR)
   - `created_at` (TIMESTAMP)

**No Event Published** (terminal operation)

**Note**: This ensures entities are persisted before intelligence services query them

---

### Phase 8: Deduplication
**Service**: `DeduplicationService`  
**Location**: `forge/domain/resolution/deduplication_service.py`  
**LLM Provider**: Required  
**Vector DB**: QdrantService (for similarity search)

**Subscribes to**: `TOPIC_GRAPH_UPDATED`

**Process**:
1. Retrieves entity embeddings from QdrantService
2. Performs similarity search (threshold=0.85)
3. Finds potential duplicate pairs (e.g., "Russia Today" vs "RT")
4. Uses LLM to confirm if pairs are duplicates
5. If confirmed, merges entities:
   - Updates relationships to point to kept entity
   - Deletes duplicate entity
   - Updates database

**Event Published**: `TOPIC_ENTITY_MERGED` (when duplicates found)  
**Payload**: `{kept_entity: "...", merged_entity: "...", doc_id: "..."}`

**Example Output**: "Found 11 potential duplicate pairs (from 34 entities, threshold=0.85)"

**Note**: Runs multiple LLM calls (one per duplicate pair)

---

### Phase 9: Semantic Profiling (Parallel)
**Service**: `SemanticProfilerService`  
**Location**: `forge/domain/intelligence/semantic_profiler.py`  
**LLM Provider**: Required  
**Database**: DuckDB connection

**Subscribes to**:
- `TOPIC_GRAPH_UPDATED` (generates profiles for new entities)
- `TOPIC_ENTITY_MERGED` (regenerates profile for merged entity)

**Process**:
1. Receives graph update event
2. For each entity in graph:
   - Queries database for entity details
   - Queries database for entity's relationships
   - Uses LLM with `semantic_profiler.j2` template to generate profile:
     - Summary
     - Key attributes
     - Related entities
     - Significance score
   - Retry logic with exponential backoff (0.5s, 1s, 2s) if entity not found (timing issue)
3. Stores profile (currently in-memory, could be persisted)

**Event Published**: `TOPIC_SEMANTIC_PROFILE`  
**Payload**: `{entity_id: "...", profile: {...}}`

**Note**: 
- Runs for ALL entities (can be 34+ LLM calls)
- Uses retry logic to handle timing issues (entity not yet persisted)
- Logs at DEBUG level during retries

---

### Phase 10: Narrative Generation (Parallel)
**Service**: `NarrativeSynthesisService`  
**Location**: `forge/domain/intelligence/narrative_service.py`  
**LLM Provider**: Required  
**Database**: DuckDB connection

**Subscribes to**: `TOPIC_GRAPH_UPDATED`

**Process**:
1. Receives graph update event
2. Retrieves entities and relationships from graph_stats or database
3. Uses LLM with `narrative_service.j2` template to generate narrative:
   - Summary of document
   - Key relationships
   - Significant entities
4. Caches narrative per document

**Event Published**: `TOPIC_NARRATIVE_GENERATED`  
**Payload**: `{doc_id: "...", narrative: "..."}`

**Note**: Generates one narrative per document

---

### Phase 11: Advanced Graph Analysis (Parallel)
**Service**: `AdvancedGraphAnalysisService`  
**Location**: `forge/domain/graph/advanced_analyzer.py`  
**LLM Provider**: Required  
**Database**: DuckDB connection

**Subscribes to**: `TOPIC_GRAPH_UPDATED`

**Process**:
1. Receives graph update event
2. Performs advanced graph analytics:
   - Community detection
   - Centrality analysis
   - Path finding
   - Clustering
3. Uses LLM for interpretation of results

**Event Published**: `TOPIC_GRAPH_ANALYSIS`  
**Payload**: `{doc_id: "...", analysis: {...}}`

---

## Event Flow Diagram

```
User Upload
    ↓
[IngestController]
    ↓ TOPIC_DATA_INGESTED
[DocumentExtractionService] ──→ TOPIC_ENTITY_EXTRACTED
    ↓                              ↓
[EntityResolutionService]    [EmbeddingService]
    ↓                              ↓
TOPIC_RELATIONSHIP_FOUND      TOPIC_ENTITY_EMBEDDED
    ↓                              ↓
[EmbeddingService]           [QdrantService] (vector storage)
    ↓                              ↓
TOPIC_RELATIONSHIP_EMBEDDED
    ↓
[GraphAnalysisService]
    ↓ TOPIC_GRAPH_UPDATED
    ├─→ [DuckDBPersistenceService] (saves to DB)
    ├─→ [DeduplicationService] ──→ TOPIC_ENTITY_MERGED
    ├─→ [SemanticProfilerService] ──→ TOPIC_SEMANTIC_PROFILE
    ├─→ [NarrativeSynthesisService] ──→ TOPIC_NARRATIVE_GENERATED
    └─→ [AdvancedGraphAnalysisService] ──→ TOPIC_GRAPH_ANALYSIS
```

## Service Dependencies

### LLM-Dependent Services
- `DocumentExtractionService` (entity extraction)
- `EntityResolutionService` (relationship extraction)
- `DeduplicationService` (duplicate confirmation)
- `SemanticProfilerService` (profile generation)
- `NarrativeSynthesisService` (narrative generation)
- `AdvancedGraphAnalysisService` (analysis interpretation)

### Infrastructure Services
- `EmbeddingService` (embedding generation)
- `QdrantService` (vector storage)
- `DuckDBPersistenceService` (relational storage)

### Coordination Services
- `GraphAnalysisService` (graph construction)
- `IntelligenceStreamingService` (streaming intelligence)
- `UserInteractionWorkflowService` (user workflows)

## Key Design Patterns

1. **Event-Driven Architecture**: Loose coupling via EventBus
2. **Retry Logic**: JSON parsing retries with prompt reminders
3. **Exponential Backoff**: Used in SemanticProfilerService for timing issues
4. **Batch Processing**: EmbeddingService batches entities/relationships
5. **Caching**: EntityResolutionService caches document content, NarrativeService caches narratives
6. **Parallel Processing**: Multiple services process `TOPIC_GRAPH_UPDATED` in parallel

## Performance Considerations

1. **Large Entity Sets**: EntityResolutionService processes all entities at once (50+ entities)
   - Solution: Increased `max_tokens` to handle large JSON responses
2. **Timing Issues**: SemanticProfilerService may query entities before persistence
   - Solution: Retry logic with exponential backoff
3. **Multiple LLM Calls**: Each service makes separate LLM calls (can be 50+ calls per document)
   - Consideration: Rate limiting via RateLimiter
4. **GPU Acceleration**: EmbeddingService uses CUDA for faster embeddings

## Error Handling

- **JSON Parsing Errors**: Retry logic with JSON format reminders and temperature reduction
- **Entity Not Found**: Retry logic with exponential backoff
- **LLM Failures**: Logged and services continue with partial data
- **Database Errors**: Logged (services may retry on next event)
