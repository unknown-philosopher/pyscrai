# **Phase 2 Final & Phase 3: Embedding Integration & Intelligence Services**

## **Executive Summary**

Complete the intelligence pipeline by adding:
1. **Semantic Embeddings** via local sentence-transformers (CUDA-accelerated)
2. **Qdrant Vector Store** with GPU support for semantic search and deduplication
3. **Intelligence Services** (semantic profiling, narrative synthesis, graph analysis)

---

## **Part 1: Embedding Integration Architecture**

### **1.1 EmbeddingService** (`forge/infrastructure/embeddings/embedding_service.py`)

```python
class EmbeddingService:
    def __init__(self, device="cuda"):
        # Two models for different use cases
        self.general_model = SentenceTransformer(
            "BAAI/bge-base-en-v1.5",
            device=device
        )  # 768-dim, ~440MB, general purpose
        
        self.long_context_model = SentenceTransformer(
            "nomic-ai/nomic-embed-text-v1.5",
            device=device
        )  # 768-dim, ~500MB, up to 8192 tokens
    
    async def embed_text(
        text: str, 
        use_long_context: bool = False
    ) -> List[float]
    
    async def embed_batch(
        texts: List[str],
        use_long_context: bool = False
    ) -> List[List[float]]
```

**Features:**
- **CUDA-accelerated** inference for fast batch processing
- **Two specialized models:**
  - `bge-base-en-v1.5`: General purpose, optimal for entities/short relationships
  - `nomic-embed-text-v1.5`: Long context (8192 tokens), for documents/narratives
- **Smart model selection:** Automatically switches based on text length
- **Batch processing:** Efficiently process multiple entities/relationships at once
- **Async wrapper:** Non-blocking for event-driven architecture

**Event Handling:**
- Subscribes to: `TOPIC_ENTITY_EXTRACTED`, `TOPIC_RELATIONSHIP_FOUND`
- Processing:
  - Entities/relationships < 512 tokens → `bge-base-en-v1.5`
  - Long documents/narratives → `nomic-embed-text-v1.5`
- Caches embeddings in memory to avoid re-computation
- Batch processes entities per document for GPU efficiency

### **1.2 QdrantService** (`forge/infrastructure/vector/qdrant_service.py`)

**GPU-Accelerated Qdrant Instance:**
- Runs with CUDA support for fast similarity search
- In-memory mode for development (`:memory:`)
- Persistent mode for production (`./qdrant_storage`)

**Two Collections:**
- **entities** - Entity embeddings (768-dim) with metadata (id, type, label)
- **relationships** - Relationship embeddings (768-dim) with endpoints

```python
async def add_entity_embedding(entity_id, embedding, metadata)
async def find_similar_entities(entity_id, limit=5) -> List[SimilarEntity]
async def deduplicate_entities(similarity_threshold=0.85) -> List[EntityPair]
```

### **1.3 DeduplicationService** (`forge/domain/resolution/deduplication_service.py`)

**Process:**
1. Query Qdrant for entities with similarity > 0.85
2. Use LLM to confirm duplicates
3. Merge in DuckDB (update all relationships)
4. Emit `TOPIC_ENTITY_MERGED` event

---

## **Part 2: Intelligence Services**

### **2.1 SemanticProfilerService** (`forge/domain/intelligence/semantic_profiler.py`)

**Generates semantic profiles per entity:**

```json
{
  "entity_id": "Alice",
  "summary": "Alice is an experienced researcher at PyScrAI",
  "attributes": ["researcher", "technical"],
  "importance": 8,
  "key_relationships": ["WORKS_AT:PyScrAI"],
  "confidence": 0.92
}
```

- Subscribes to: `TOPIC_ENTITY_MERGED`, `TOPIC_RELATIONSHIP_FOUND`
- Uses LLM to analyze entity + relationships
- Publishes: `TOPIC_SEMANTIC_PROFILE`

### **2.2 NarrativeSynthesisService** (`forge/domain/intelligence/narrative_service.py`)

**Generates intelligent narratives from documents:**

```markdown
## NARRATIVE

PyScrAI is an AI research organization. Alice works at PyScrAI 
as a researcher, indicating focus on cutting-edge research.

### KEY ENTITIES
- PyScrAI (Organization, Importance: 8)
- Alice (Person, Importance: 8)

### EVIDENCE CHAIN
Document → Alice → PyScrAI → Organization
```

- Subscribes to: `TOPIC_GRAPH_UPDATED`
- Uses LLM for natural language generation
- Publishes: `TOPIC_NARRATIVE_GENERATED`

### **2.3 AdvancedGraphAnalysisService** (`forge/domain/graph/advanced_analyzer.py`)

**Graph analytics and relationship inference:**

```json
{
  "centrality": {
    "most_connected": [{"entity": "PyScrAI", "degree": 5}],
    "bridges": [{"entity": "Alice", "betweenness": 0.8}]
  },
  "communities": [{"entities": ["PyScrAI", "Alice"], "cohesion": 0.92}],
  "inferred_relationships": [
    {
      "source": "Alice",
      "target": "AI",
      "type": "INFLUENCED_BY",
      "confidence": 0.72
    }
  ]
}
```

- Subscribes to: `TOPIC_GRAPH_UPDATED`
- Uses NetworkX for graph algorithms
- Uses LLM for relationship inference validation
- Publishes: `TOPIC_GRAPH_ANALYSIS`

---

## **Part 3: New Events**

Add to events.py:

```python
# Embedding events
TOPIC_ENTITY_EMBEDDED = "entity.embedded"
TOPIC_RELATIONSHIP_EMBEDDED = "relationship.embedded"

# Intelligence events
TOPIC_ENTITY_MERGED = "entity.merged"
TOPIC_SEMANTIC_PROFILE = "semantic.profile"
TOPIC_NARRATIVE_GENERATED = "narrative.generated"
TOPIC_GRAPH_ANALYSIS = "graph.analysis"
TOPIC_INFERRED_RELATIONSHIP = "relationship.inferred"
```

---

## **Part 4: Service Startup Order**

```
1. DocumentExtractionService
2. EntityResolutionService
3. GraphAnalysisService
4. DuckDBPersistenceService
5. EmbeddingService (new)
6. QdrantService (new)
7. DeduplicationService (new)
8. SemanticProfilerService (new)
9. NarrativeSynthesisService (new)
10. AdvancedGraphAnalysisService (new)
```

---

## **Part 5: Event Flow Example**

```
Document: "Alice works at PyScrAI"
    ↓ (TOPIC_DATA_INGESTED)
Extract: [Alice(PERSON), PyScrAI(ORG)]
    ↓ (TOPIC_ENTITY_EXTRACTED)
Resolve: [Alice WORKS_AT PyScrAI]
    ↓ (TOPIC_RELATIONSHIP_FOUND)
Graph: {nodes: 2, edges: 1}
    ↓ (TOPIC_GRAPH_UPDATED)
DuckDB: Store entities & relationships
    ↓
Embed: Convert to vectors
    ↓ (TOPIC_ENTITY_EMBEDDED, TOPIC_RELATIONSHIP_EMBEDDED)
Qdrant: Store embeddings
    ↓
Deduplicate: Check similarity (no duplicates found)
    ↓
Profile: Generate semantic profiles
    ↓ (TOPIC_SEMANTIC_PROFILE)
Narrative: Generate document narrative
    ↓ (TOPIC_NARRATIVE_GENERATED)
Graph Analysis: Compute centrality, infer relationships
    ↓ (TOPIC_GRAPH_ANALYSIS)
```

---

## **Part 6: Configuration**

```env
# Embeddings (Local Models with CUDA)
EMBEDDING_DEVICE=cuda  # or 'cpu' for non-GPU systems
EMBEDDING_GENERAL_MODEL=BAAI/bge-base-en-v1.5
EMBEDDING_LONG_CONTEXT_MODEL=nomic-ai/nomic-embed-text-v1.5
EMBEDDING_DIMENSION=768
EMBEDDING_BATCH_SIZE=32  # Adjust based on GPU VRAM

# Qdrant (GPU-accelerated)
QDRANT_URL=:memory:  # or http://localhost:6333 for persistent
QDRANT_API_KEY=optional
QDRANT_CUDA_ENABLED=true
```

**Dependencies to Add:**
```bash
pip install sentence-transformers
# Already installed: torch (with CUDA support)
# Already installed: qdrant-client
```

**Model Download:**
Models will auto-download on first run (~940MB total):
- `bge-base-en-v1.5`: ~440MB
- `nomic-embed-text-v1.5`: ~500MB

---

## **Part 7: Implementation Phases**

### **Phase 2 Final (Weeks 1-2)**
1. EmbeddingService + QdrantService
2. DeduplicationService
3. SemanticProfilerService
4. NarrativeSynthesisService
5. AdvancedGraphAnalysisService
6. Integration testing

### **Phase 3 (Week 3+)**
- Qdrant persistence to disk
- Community detection algorithms
- Real-time intelligence dashboards
- UI components for profiles/narratives

---

**This plan enables a fully-functional AI-powered knowledge extraction engine. Ready to implement?**