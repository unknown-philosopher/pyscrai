# Intelligence Dashboard - Usage Guide

## Overview

The Intelligence Dashboard is now **fully integrated** into your Flet UI! Intelligence services automatically generate and display visualizations as documents are processed.

## Architecture

```
Document Input
      ↓
[Extraction Service] → Entities Extracted
      ↓
[Resolution Service] → Entities Resolved
      ↓
[Graph Service] → Graph Updated
      ↓
╔═══════════════════════════════════╗
║   Intelligence Services Layer     ║
║  ─────────────────────────────── ║
║  • Semantic Profiler              ║
║  • Narrative Synthesizer          ║
║  • Graph Analyzer                 ║
║  • Deduplication Service          ║
╚═══════════════════════════════════╝
      ↓
[Event Bus] → TOPIC_WORKSPACE_SCHEMA
      ↓
[App Controller] → workspace_schemas (RxList)
      ↓
[Shell UI] → _sync_workspace()
      ↓
[Component Registry] → render_schema()
      ↓
[Flet UI Controls] → Displayed!
```

## What's Integrated

### ✅ Services Running
All intelligence services are initialized in `forge/main.py`:

1. **EmbeddingService** - CUDA-accelerated embeddings
2. **QdrantService** - Vector search (in-memory mode)
3. **DeduplicationService** - Semantic duplicate detection
4. **SemanticProfilerService** - Entity profiling
5. **NarrativeSynthesisService** - Document narratives
6. **AdvancedGraphAnalysisService** - Graph analytics

### ✅ UI Components Registered
All components are registered in `forge/presentation/renderer/registry.py`:

- `semantic_profile` → Entity analysis cards
- `narrative` → Document narratives with insights
- `graph_analytics` → Network metrics & centrality
- `entity_card` → Compact entity displays

### ✅ Event Flow
The complete event pipeline:

1. **Document Ingestion** → `TOPIC_DATA_INGESTED`
2. **Entity Extraction** → `TOPIC_ENTITY_EXTRACTED`
3. **Relationship Discovery** → `TOPIC_RELATIONSHIP_FOUND`
4. **Graph Update** → `TOPIC_GRAPH_UPDATED`
5. **Intelligence Generation** → `TOPIC_WORKSPACE_SCHEMA`
6. **UI Rendering** → Automatic visualization

## How to Use

### Starting the Application

```bash
cd /home/tyler/_development/pyscrai
source .venv/bin/activate
python forge/main.py
```

The Flet window will open with:
- **Left Panel**: Navigation (Ingest, Graph, Intel)
- **Center Panel**: Workspace (intelligence visualizations)
- **Right Panel**: AG-UI Feed (event log)

### Triggering Intelligence Analysis

#### Option 1: Using the UI
*(To be implemented in Phase 6)*

1. Navigate to "Ingest" tab
2. Upload or paste document text
3. Click "Process"
4. Watch visualizations appear automatically

#### Option 2: Programmatically

Run the test script while the app is running:

```bash
# In a separate terminal
cd /home/tyler/_development/pyscrai
source .venv/bin/activate
python examples/test_ui_integration.py
```

This will:
- Publish sample document events
- Trigger entity extraction
- Create relationships
- Generate intelligence visualizations

#### Option 3: Direct Event Publishing

```python
from forge.core.event_bus import EventBus
from forge.core import events

bus = EventBus()

# Publish a document
await bus.publish(
    events.TOPIC_DATA_INGESTED,
    events.create_data_ingested_event(
        doc_id="doc123",
        content="Your document text here..."
    )
)
```

### What You'll See

#### 1. Semantic Profiles
**Appearance**: Cyan-accented card with entity details

**Content**:
- Entity name and type badge
- Summary paragraph
- Key characteristics (expandable)
- Behavioral patterns (expandable)
- Related entities
- Confidence score

**Triggered by**: Graph update events (after entities are added)

#### 2. Narratives
**Appearance**: Purple-accented card with markdown content

**Content**:
- Document title
- Executive summary
- Full narrative (expandable)
- Key insights list
- Entity mentions with counts
- Word count & model info

**Triggered by**: Document ingestion and graph building

#### 3. Graph Analytics
**Appearance**: Green-accented card with metrics

**Content**:
- Statistics (entity count, density, avg degree)
- Centrality rankings (degree, betweenness, closeness)
- Community detection results
- Inferred relationships with confidence

**Triggered by**: Significant graph changes (threshold-based)

#### 4. Entity Cards
**Appearance**: Compact white-bordered cards

**Content**:
- Entity name with type badge
- Attribute list
- Relationship count
- Source document links

**Triggered by**: Mentioned in other intelligence outputs

## Configuration

### Adjusting Intelligence Sensitivity

Edit service parameters in `forge/main.py`:

```python
# Semantic profiling (every N entities)
profiler_service = SemanticProfilerService(
    controller.bus,
    llm_provider,
    db_connection,
    profile_threshold=5  # Profile every 5th entity
)

# Graph analysis (minimum entities to trigger)
advanced_graph_service = AdvancedGraphAnalysisService(
    controller.bus,
    llm_provider,
    db_connection,
    min_entities=10  # Analyze when 10+ entities exist
)
```

### LLM Provider Configuration

Set environment variables in `.env`:

```bash
# OpenRouter (default)
OPENROUTER_API_KEY=your_key_here
OPENROUTER_DEFAULT_MODEL=anthropic/claude-3.5-sonnet

# Or use a different provider
FORGE_LLM_PROVIDER=cherry
CHERRY_API_KEY=your_key_here
```

### Vector Store Configuration

Modify in `forge/main.py`:

```python
# Use in-memory (default)
qdrant_service = QdrantService(controller.bus, url=":memory:")

# Or connect to external Qdrant
qdrant_service = QdrantService(
    controller.bus,
    url="http://localhost:6333",
    api_key="your_qdrant_key"
)
```

## Troubleshooting

### No Visualizations Appearing

**Check 1**: Are services running?
- Look for startup logs: "SemanticProfilerService started", etc.
- Check terminal for errors

**Check 2**: Are events being published?
- Run `examples/test_ui_integration.py` to test event flow
- Check AG-UI Feed (right panel) for event activity

**Check 3**: Is the database populated?
- Check `forge_data.duckdb` exists
- Run: `duckdb forge_data.duckdb "SELECT COUNT(*) FROM entities;"`

### Services Crashing

**Common Issues**:

1. **Missing API Key**:
   ```
   Error: OpenRouter API key not found
   Solution: Set OPENROUTER_API_KEY in .env
   ```

2. **CUDA Not Available**:
   ```
   Warning: CUDA not available, using CPU
   Solution: Install torch with CUDA support, or ignore (will work on CPU)
   ```

3. **Qdrant Connection Failed**:
   ```
   Error: Failed to connect to Qdrant
   Solution: Using in-memory mode (no action needed)
   ```

### Slow Performance

**Optimization Tips**:

1. **Enable GPU Acceleration**:
   ```bash
   # Check if CUDA is available
   python -c "import torch; print(torch.cuda.is_available())"
   
   # If False, install CUDA-enabled PyTorch
   pip install torch --index-url https://download.pytorch.org/whl/cu121
   ```

2. **Reduce LLM Calls**:
   - Increase profiling thresholds
   - Disable auto-narrative generation for small docs
   - Use faster models (e.g., `openai/gpt-3.5-turbo`)

3. **Batch Processing**:
   - Process multiple documents together
   - Let services accumulate before triggering analysis

## Development & Extension

### Adding New Intelligence Components

1. **Create Render Function** in `forge/presentation/components/intelligence.py`:

```python
def render_my_component(schema: Dict[str, Any]) -> ft.Control:
    """Render my custom intelligence component."""
    data = schema.get("data", {})
    
    return ft.Container(
        bgcolor="rgba(30, 30, 30, 1.0)",
        padding=16,
        border_radius=12,
        content=ft.Column([
            ft.Text(data.get("title"), size=16, weight=ft.FontWeight.W_600),
            # ... your UI controls
        ])
    )
```

2. **Register Component** in `forge/presentation/renderer/registry.py`:

```python
from forge.presentation.components.intelligence import render_my_component

_COMPONENT_REGISTRY = {
    # ...existing...
    "my_component": render_my_component,
}
```

3. **Publish from Service**:

```python
await self.event_bus.publish(
    events.TOPIC_WORKSPACE_SCHEMA,
    {
        "schema_type": "my_component",
        "data": {
            "type": "my_component",
            "title": "My Analysis",
            # ... your data
        }
    }
)
```

### Adding New Intelligence Services

See `forge/domain/intelligence/` for examples:
- Extend base service pattern
- Subscribe to relevant events
- Publish to `TOPIC_WORKSPACE_SCHEMA`
- Initialize in `forge/main.py`

## Next Steps

With the intelligence dashboard running, consider:

1. **User Interactions** (Phase 6):
   - Approve/reject entity merges
   - Provide feedback on profiles
   - Request re-analysis

2. **Enhanced Visualizations**:
   - Interactive network graphs (D3.js/vis.js)
   - Timeline views for document sequences
   - Heatmaps for relationship strength

3. **Export Capabilities**:
   - PDF reports of narratives
   - JSON export of graph data
   - CSV entity/relationship lists

4. **Real-time Streaming**:
   - Progressive rendering during analysis
   - Status indicators for long operations
   - Cancellation support

## Conclusion

Your intelligence dashboard is **fully operational**! 🎉

All services are integrated, components are registered, and visualizations will automatically appear as you process documents. The event-driven architecture ensures loose coupling and makes it easy to add new intelligence capabilities.

**Happy analyzing!**
