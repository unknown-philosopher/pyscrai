# Phase 4 Relationship Extraction Optimization Strategies

## Current Bottleneck Analysis

**Problem**: `EntityResolutionService` processes ALL entities (50+) in a single LLM call, blocking the pipeline.

**Current Flow**:
- Receives `TOPIC_ENTITY_EXTRACTED` with all entities
- Single LLM call with all entities + full document content
- Blocks until complete
- Publishes `TOPIC_RELATIONSHIP_FOUND` once at the end

**Constraints**:
- ✅ Must not lose any data
- ✅ Minimize slowdown to overall pipeline
- ✅ Maintain event-driven architecture
- ✅ Keep retry logic for reliability

---

## Strategy 1: Batched Parallel Processing ⭐ RECOMMENDED

### Approach
Split entities into smaller batches (20 entities per batch) and process them concurrently.

### Implementation
```python
# Split entities into batches
BATCH_SIZE = 20  # Optimal for LLM context window
batches = [entities[i:i+BATCH_SIZE] for i in range(0, len(entities), BATCH_SIZE)]

# Process batches in parallel
tasks = [self._extract_relationships_batch(doc_id, batch, document_content) 
         for batch in batches]
results = await asyncio.gather(*tasks, return_exceptions=True)

# Merge results
all_relationships = []
for result in results:
    if isinstance(result, Exception):
        logger.error(f"Batch failed: {result}")
    else:
        all_relationships.extend(result)
```

### Pros
- ✅ **Fast**: Parallel processing reduces total time significantly
- ✅ **No data loss**: All entities processed
- ✅ **Scalable**: Handles any number of entities
- ✅ **Fault tolerant**: One batch failure doesn't stop others
- ✅ **Lower token costs**: Smaller prompts per batch

### Cons
- ⚠️ May miss cross-batch relationships (entities in different batches)
- ⚠️ More LLM calls (but parallel, so faster overall)

### Mitigation for Cross-Batch Relationships
- **Option A**: Add a final "cross-batch" pass for high-value entity pairs
- **Option B**: Use entity embeddings to find similar entities across batches
- **Option C**: Accept minor loss (most relationships are within document sections)

### Performance Estimate
- **Current**: 1 call × 50 entities = ~15-30 seconds
- **Optimized**: 5 batches × 3 seconds (parallel) = ~3-5 seconds
- **Speedup**: 5-10x faster

---

## Strategy 2: Progressive/Streaming Publishing

### Approach
Publish relationships as they're found, rather than waiting for all batches.

### Implementation
```python
# Process batches and publish incrementally
for batch_idx, batch in enumerate(batches):
    relationships = await self._extract_relationships_batch(...)
    if relationships:
        await self.event_bus.publish(
            events.TOPIC_RELATIONSHIP_FOUND,
            {
                "doc_id": doc_id,
                "relationships": relationships,
                "batch_index": batch_idx,
                "is_complete": batch_idx == len(batches) - 1
            }
        )
```

### Pros
- ✅ **Faster perceived time**: Downstream services start processing immediately
- ✅ **Better UX**: Users see progress
- ✅ **Resilient**: Partial results if service crashes

### Cons
- ⚠️ Downstream services need to handle partial/incremental updates
- ⚠️ More events published (but async, so minimal overhead)

### Compatibility
- `GraphAnalysisService`: Already handles incremental updates ✅
- `EmbeddingService`: Can process incrementally ✅
- `DuckDBPersistenceService`: Can batch inserts ✅

---

## Strategy 3: Smart Batching by Entity Type/Proximity

### Approach
Group entities intelligently before batching:
1. **By type**: Group PERSON entities together, ORGANIZATION together, etc.
2. **By document position**: Entities mentioned close together
3. **By semantic similarity**: Use embeddings to cluster similar entities

### Implementation
```python
# Group by entity type
type_groups = defaultdict(list)
for entity in entities:
    type_groups[entity["type"]].append(entity)

# Create batches prioritizing same-type relationships
batches = []
for entity_type, type_entities in type_groups.items():
    batches.extend([type_entities[i:i+BATCH_SIZE] 
                   for i in range(0, len(type_entities), BATCH_SIZE)])
```

### Pros
- ✅ **Better accuracy**: Related entities processed together
- ✅ **Fewer cross-batch misses**: Similar entities in same batch
- ✅ **Context optimization**: LLM sees related entities together

### Cons
- ⚠️ More complex implementation
- ⚠️ May create uneven batch sizes

---

## Strategy 4: Two-Phase Extraction

### Approach
1. **Phase 4a**: Extract high-confidence relationships (explicit mentions) - fast, small batches
2. **Phase 4b**: Extract low-confidence relationships (implied) - slower, can be deferred

### Implementation
```python
# Phase 4a: High-confidence pass
high_conf_relationships = await self._extract_relationships(
    entities, document_content, min_confidence=0.8
)

# Publish immediately
await self.event_bus.publish(TOPIC_RELATIONSHIP_FOUND, {
    "relationships": high_conf_relationships,
    "phase": "high_confidence"
})

# Phase 4b: Low-confidence pass (can be async/background)
low_conf_relationships = await self._extract_relationships(
    entities, document_content, min_confidence=0.5
)
```

### Pros
- ✅ **Fast initial results**: High-confidence relationships published quickly
- ✅ **Pipeline unblocks**: Downstream services start processing
- ✅ **Progressive enhancement**: Low-confidence added later

### Cons
- ⚠️ Requires two passes (but second can be background)
- ⚠️ More complex prompt logic

---

## Strategy 5: Entity Pair Batching (Most Granular)

### Approach
Instead of entity batches, create relationship candidate pairs and batch those.

### Implementation
```python
# Generate all possible entity pairs
pairs = [(e1, e2) for i, e1 in enumerate(entities) 
                for e2 in entities[i+1:]]

# Batch pairs (e.g., 20 pairs per batch)
pair_batches = [pairs[i:i+20] for i in range(0, len(pairs), 20)]

# Process pairs in parallel
tasks = [self._extract_relationships_from_pairs(batch, document_content)
         for batch in pair_batches]
```

### Pros
- ✅ **Most granular**: Can process exactly N pairs at a time
- ✅ **Predictable**: Fixed token usage per batch

### Cons
- ⚠️ **Too many batches**: 50 entities = 1,225 pairs = 62 batches (even with 20 per batch)
- ⚠️ **Inefficient**: Many pairs have no relationship
- ⚠️ **High LLM call count**: Not recommended

---

## Strategy 6: Hybrid Approach (Recommended Combination)

### Best of Multiple Worlds

**Primary**: Strategy 1 (Batched Parallel Processing)
- Split into 20 entity batches
- Process batches concurrently with `asyncio.gather`

**Enhancement**: Strategy 2 (Progressive Publishing)
- Publish relationships as batches complete
- Downstream services start processing immediately

**Optimization**: Strategy 3 (Smart Batching)
- Group entities by type before batching
- Improves relationship detection accuracy

### Implementation Flow
```
1. Receive TOPIC_ENTITY_EXTRACTED (50 entities)
2. Group entities by type (PERSON, ORG, LOCATION, etc.)
3. Create batches of 12 entities (prioritizing same-type)
4. Process batches in parallel (asyncio.gather)
5. Publish relationships incrementally as batches complete
6. Final event marks completion
```

### Code Structure
```python
async def handle_entity_extracted(self, payload: EventPayload):
    doc_id = payload.get("doc_id")
    entities = payload.get("entities", [])
    document_content = self._document_cache.get(doc_id, "")
    
    if len(entities) <= 15:
        # Small set: process normally
        relationships = await self._extract_relationships(...)
        await self._publish_relationships(doc_id, relationships, is_complete=True)
    else:
        # Large set: use batched parallel processing
        await self._extract_relationships_batched(doc_id, entities, document_content)

async def _extract_relationships_batched(self, doc_id, entities, document_content):
    # Smart batching by type
    batches = self._create_smart_batches(entities, batch_size=12)
    
    # Process batches in parallel
    tasks = [
        self._extract_relationships_batch(doc_id, batch, document_content, batch_idx)
        for batch_idx, batch in enumerate(batches)
    ]
    
    # Gather results (with error handling)
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Publish incrementally
    all_relationships = []
    for batch_idx, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Batch {batch_idx} failed: {result}")
        else:
            all_relationships.extend(result)
            # Publish this batch's relationships immediately
            await self._publish_relationships(
                doc_id, result, 
                batch_index=batch_idx,
                is_complete=(batch_idx == len(batches) - 1)
            )
    
    return all_relationships
```

---

## Performance Comparison

| Strategy | Time (50 entities) | LLM Calls | Data Loss Risk | Complexity |
|----------|-------------------|-----------|----------------|------------|
| **Current** | 15-30s | 1 | None | Low |
| **Strategy 1** | 3-5s | 5 (parallel) | Low* | Medium |
| **Strategy 2** | 3-5s | 5 (parallel) | Low* | Medium |
| **Strategy 3** | 3-5s | 5 (parallel) | Very Low | Medium-High |
| **Strategy 4** | 2s + 3s (bg) | 2 phases | None | Medium |
| **Strategy 5** | 30-60s | 62+ | None | High |
| **Strategy 6** | 3-5s | 5 (parallel) | Very Low | Medium-High |

*Cross-batch relationships may be missed, but can be mitigated

---

## Recommended Implementation Plan

### Phase 1: Basic Batching (Quick Win)
1. Implement Strategy 1 (Batched Parallel Processing)
2. Use simple sequential batching (no smart grouping yet)
3. Publish all relationships at once (keep current behavior)
4. **Expected improvement**: 5-10x speedup

### Phase 2: Progressive Publishing
1. Add Strategy 2 (Progressive Publishing)
2. Publish relationships as batches complete
3. Update downstream services if needed
4. **Expected improvement**: Better perceived performance

### Phase 3: Smart Batching (Optional Enhancement)
1. Add Strategy 3 (Smart Batching by Type)
2. Improve relationship detection accuracy
3. **Expected improvement**: Better accuracy, fewer missed relationships

---

## Migration Considerations

### Backward Compatibility
- Keep `is_complete` flag in event payload
- Downstream services can check flag for incremental vs. final processing
- Default to current behavior if flag missing

### Error Handling
- One batch failure shouldn't stop others
- Log failed batches but continue processing
- Retry logic per batch (not global)

### Testing
- Test with small entity sets (< 15) - should use current path
- Test with large entity sets (50+) - should use batched path
- Test with mixed entity types
- Test error scenarios (batch failures)

---

## Code Changes Required

### Files to Modify
1. `forge/domain/resolution/service.py`
   - Add `_extract_relationships_batched()` method
   - Add `_create_smart_batches()` helper
   - Modify `handle_entity_extracted()` to route to batched version
   - Add `_publish_relationships()` helper for incremental publishing

2. `forge/core/events.py` (optional)
   - Add `batch_index` and `is_complete` fields to relationship event

3. Downstream Services (if using progressive publishing)
   - `GraphAnalysisService`: Handle incremental updates
   - `EmbeddingService`: Handle incremental updates
   - `DuckDBPersistenceService`: Batch inserts efficiently

### New Dependencies
- None (uses existing `asyncio`)

---

## Conclusion

**Recommended Approach**: **Strategy 6 (Hybrid)** - Batched Parallel Processing with Progressive Publishing and Smart Batching

**Expected Results**:
- ⚡ **5-10x speedup** (15-30s → 3-5s)
- ✅ **No data loss** (with smart batching)
- ✅ **Better UX** (progressive publishing)
- ✅ **Scalable** (handles any number of entities)

**Implementation Priority**:
1. **High**: Strategy 1 (Basic Batching) - Quick win, low risk
2. **Medium**: Strategy 2 (Progressive Publishing) - Better UX
3. **Low**: Strategy 3 (Smart Batching) - Nice to have, improves accuracy
