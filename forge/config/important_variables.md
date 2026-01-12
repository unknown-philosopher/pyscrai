# Important Variables Reference

Master reference for configuration variables, thresholds, and settings throughout PyScrAI Forge. This document will be replaced by a YAML config file in the future.

## Rate Limiting (LLM API)

### Location: `forge/infrastructure/llm/rate_limiter.py`

| Variable | Default | Env Var | Description |
|----------|---------|---------|-------------|
| `max_concurrent` | `1` | `LLM_RATE_LIMIT_MAX_CONCURRENT` | Maximum concurrent LLM API requests (conservative for free tier) |
| `min_delay` | `2.0` | `LLM_RATE_LIMIT_MIN_DELAY` | Minimum delay between requests (seconds) |
| `max_retries` | `3` | `LLM_RATE_LIMIT_MAX_RETRIES` | Maximum retries for rate limit errors |
| `initial_retry_delay` | `3.0` | `LLM_RATE_LIMIT_RETRY_DELAY` | Initial retry delay with exponential backoff (seconds) |

## Deduplication & Similarity

### Location: `forge/domain/resolution/deduplication_service.py`
- `similarity_threshold`: `0.85` - Minimum similarity score to consider entities as duplicates
  - Passed to `QdrantService.deduplicate_entities()`

### Location: `forge/infrastructure/vector/qdrant_service.py`
- `find_similar_entities()`:
  - `limit`: `5` - Maximum similar entities to return per query (reduced from 10)
  - `score_threshold`: `0.7` - Minimum similarity score for general similarity search
- `deduplicate_entities()`:
  - `similarity_threshold`: `0.85` - Minimum similarity for duplicate detection
  - `limit`: `1000` - Maximum entities to scroll through
  - Entity type filtering: Only compares entities of the same type (PERSON vs PERSON, ORG vs ORG)

## Database & Storage

### Location: `forge/infrastructure/persistence/duckdb_service.py`
- `db_path`: `data/db/forge_data.duckdb` (relative to project root)
  - Default path: `{project_root}/data/db/forge_data.duckdb`
  - Directory is auto-created if it doesn't exist

## Vector Database (Qdrant)

### Location: `forge/infrastructure/vector/qdrant_service.py`
- `url`: `":memory:"` - Qdrant connection URL (in-memory mode by default)
- `api_key`: `None` - Optional API key for authentication
- `embedding_dimension`: `768` - Vector dimension (for bge-base/nomic-embed models)
- Collection names:
  - `"entities"` - Entity embeddings collection
  - `"relationships"` - Relationship embeddings collection

## Embedding Models

### Location: `forge/infrastructure/embeddings/embedding_service.py`
- `device`: `"cuda"` - Device for inference ('cuda' or 'cpu')
- `general_model`: `"BAAI/bge-base-en-v1.5"` - General purpose embedding model
- `long_context_model`: `"nomic-ai/nomic-embed-text-v1.5"` - Long context model (8192 tokens)
- `batch_size`: `32` - Batch size for embedding processing
- `long_context_threshold`: `512` - Token threshold for switching to long context model

## LLM Model Settings

### Location: Various service files

#### Entity Extraction (`forge/domain/extraction/service.py`)
- `max_tokens`: `2000`
- `temperature`: `0.3`

#### Relationship Extraction (`forge/domain/resolution/service.py`)
- `max_tokens`: `2000`
- `temperature`: `0.3`

#### Semantic Profiling (`forge/domain/intelligence/semantic_profiler.py`)
- `max_tokens`: `500`
- `temperature`: `0.3`

#### Narrative Synthesis (`forge/domain/intelligence/narrative_service.py`)
- `max_tokens`: `1500`
- `temperature`: `0.5`

#### Relationship Inference (`forge/domain/graph/advanced_analyzer.py`)
- `max_tokens`: `200`
- `temperature`: `0.3`

#### Deduplication Confirmation (`forge/domain/resolution/deduplication_service.py`)
- `max_tokens`: `10`
- `temperature`: `0.0` (deterministic)

### Default Model
- **Location**: `forge/infrastructure/llm/openrouter_provider.py`
- **Env Vars**: `OPENROUTER_MODEL` or `OPENROUTER_DEFAULT_MODEL`
- **Default**: `None` (uses first available model from API)

## Processing Delays

### Location: `forge/domain/intelligence/semantic_profiler.py`
- `asyncio.sleep(0.3)` - Delay between entity profile generations to avoid rate limits

### Location: `forge/domain/graph/service.py`
- `asyncio.sleep(0.2)` - Delay in graph analysis processing

## Event Topics

### Location: `forge/core/events.py`
- `TOPIC_DATA_INGESTED` - Document ingestion complete
- `TOPIC_ENTITY_EXTRACTED` - Entity extraction complete
- `TOPIC_RELATIONSHIP_FOUND` - Relationship identified
- `TOPIC_GRAPH_UPDATED` - Knowledge graph updated
- `TOPIC_ENTITY_EMBEDDED` - Entity embedding generated
- `TOPIC_RELATIONSHIP_EMBEDDED` - Relationship embedding generated
- `TOPIC_ENTITY_MERGED` - Entities merged (deduplication)
- `TOPIC_SEMANTIC_PROFILE` - Semantic profile generated
- `TOPIC_NARRATIVE_GENERATED` - Narrative synthesized
- `TOPIC_GRAPH_ANALYSIS` - Graph analysis complete
- `TOPIC_INFERRED_RELATIONSHIP` - Relationship inferred

## Environment Variables Summary

| Variable | Purpose | Default |
|----------|---------|---------|
| `LLM_RATE_LIMIT_MAX_CONCURRENT` | Max concurrent LLM requests | `1` |
| `LLM_RATE_LIMIT_MIN_DELAY` | Min delay between requests (s) | `2.0` |
| `LLM_RATE_LIMIT_MAX_RETRIES` | Max retries for rate limits | `3` |
| `LLM_RATE_LIMIT_RETRY_DELAY` | Initial retry delay (s) | `3.0` |
| `OPENROUTER_MODEL` | LLM model to use | `None` |
| `OPENROUTER_DEFAULT_MODEL` | LLM model (backwards compat) | `None` |
| `OPENROUTER_API_KEY` | OpenRouter API key | Required |

## Notes

- All rate limiting variables can be overridden via environment variables
- Similarity thresholds are tuned for entity deduplication (0.85) vs general similarity search (0.7)
- Qdrant runs in-memory by default (`:memory:`) - data is lost on restart
- DuckDB database persists to disk at `data/db/forge_data.duckdb`
- Embedding models are lazy-loaded on first use
- LLM temperature settings vary by task (lower for extraction/inference, higher for narrative)
