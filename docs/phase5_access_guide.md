# Phase 5 Features Access Guide

This guide explains how to access and use the Phase 5 advanced features in PyScrAI Forge.

## Overview

Phase 5 features are automatically active when you run the application. They include:
- ✅ Intelligence dashboard UI components (semantic profiles, narratives, graph visualizations, entity cards)
- ✅ Automatic publishing from intelligence services to AG-UI feed
- ✅ Full AG-UI component registry (basic + intelligence components)
- ✅ User interaction workflows (approvals, corrections)
- ✅ Real-time intelligence streaming
- ✅ Export and integration capabilities

## Accessing Phase 5 Features

### 1. **Intelligence Dashboard** (Main Interface)

**Location**: Click the **"Intel"** tab in the left navigation rail (🧠 psychology icon)

**What you'll see**:
- The Intelligence Dashboard workspace displays all intelligence visualizations
- Components appear automatically as intelligence services process your data
- Each component is rendered using the AG-UI schema system

**Features available**:
- **Semantic Profiles**: Entity analysis cards showing detailed semantic information
- **Narratives**: Document narratives synthesized from extracted entities and relationships
- **Graph Analytics**: Visualizations of graph metrics, centrality, and community detection
- **Entity Cards**: Interactive cards for individual entities

### 2. **AG-UI Feed** (Real-time Activity Stream)

**Location**: Right sidebar in the main application window

**What it shows**:
- Real-time updates from all intelligence services
- Status messages, notifications, and system events
- Automatically scrolls to show latest activity
- Color-coded by level (info, warning, error)

**Example messages you'll see**:
- `📊 Generated semantic profile for [Entity Name]`
- `📝 Generated narrative for document [doc_id]`
- `📈 Completed graph analysis: X entities, Y relationships`
- `🔄 Merged N duplicate entities`

### 3. **How Intelligence Components Appear**

Intelligence services automatically publish to the workspace when they process data:

1. **Semantic Profiler Service**: 
   - Triggers on `graph.updated` events
   - Generates semantic profiles for entities
   - Publishes to workspace as `semantic_profile` components

2. **Narrative Synthesis Service**:
   - Triggers on `graph.updated` events
   - Generates document narratives
   - Publishes to workspace as `narrative` components

3. **Advanced Graph Analysis Service**:
   - Triggers on `graph.updated` events
   - Performs advanced graph analytics
   - Publishes to workspace as `graph_analytics` components

4. **User Interaction Workflow Service**:
   - Handles user approvals and corrections
   - Publishes interactive components (buttons, forms, dialogs)
   - Responds to user actions via event bus

### 4. **Triggering Intelligence Features**

Intelligence services are event-driven and activate automatically:

**To see intelligence features**:
1. **Upload/Process a Document**:
   - Go to the "Ingest" tab
   - Upload a document (PDF, text, etc.)
   - The pipeline will:
     - Extract entities and relationships
     - Store them in DuckDB
     - Generate embeddings
     - Trigger intelligence services

2. **Wait for Processing**:
   - Services process data asynchronously
   - Watch the AG-UI feed for progress updates
   - Navigate to "Intel" tab to see results

3. **View Results**:
   - Intelligence components appear in the workspace
   - Each component is interactive and rendered via AG-UI
   - Components stack vertically and scroll automatically

### 5. **User Interaction Workflows**

**Location**: Components appear in the Intelligence Dashboard workspace

**Available interactions**:
- **Approval workflows**: Buttons to approve/reject entity merges
- **Correction forms**: Input fields to correct entity information
- **Confirmation dialogs**: Pop-ups for critical actions
- **Action buttons**: Trigger specific intelligence operations

**How to interact**:
- Click buttons, fill forms, confirm dialogs
- Actions are sent via `user.action` events
- Workflow service processes actions and updates the system

### 6. **Real-time Intelligence Streaming**

**Location**: Automatic background service

**What it does**:
- Monitors intelligence events
- Streams updates to the AG-UI feed
- Publishes new intelligence components as they're generated
- Maintains real-time synchronization

**No manual action needed** - it runs automatically!

### 7. **Export Capabilities**

**Location**: ExportService (programmatic access)

**Available exports**:
- JSON exports of entities and relationships
- CSV exports for analytics
- Graph exports (NetworkX format)
- Intelligence reports

**How to use** (programmatic):
```python
from forge.infrastructure.export.export_service import ExportService
import duckdb

# Get database connection
db_conn = duckdb.connect("path/to/database.db")
export_service = ExportService(db_conn)

# Export entities to JSON
export_service.export_entities_json("output.json")

# Export relationships to CSV
export_service.export_relationships_csv("output.csv")
```

## Navigation Structure

```
PyScrAI Forge
├── Ingest Tab (📊 database icon)
│   └── Document upload and processing
│
├── Graph Tab (🌳 account_tree icon)
│   └── Graph visualization (coming soon)
│
└── Intel Tab (🧠 psychology icon) ← **Phase 5 Features Here**
    ├── Intelligence Dashboard Workspace
    │   ├── Semantic Profiles (auto-generated)
    │   ├── Narratives (auto-generated)
    │   ├── Graph Analytics (auto-generated)
    │   └── Entity Cards (auto-generated)
    │
    └── AG-UI Feed (right sidebar)
        └── Real-time activity stream
```

## Service Dependencies

**Required for Phase 5 features**:
- ✅ LLM Provider (OpenRouter) - Required for intelligence services
- ✅ DuckDB - Required for data persistence
- ✅ Qdrant - Required for vector search and deduplication
- ✅ Embedding Service - Required for semantic operations

**Check service status**:
- Look at application logs on startup
- Services log their initialization status
- Missing services will show warnings but won't crash the app

## Troubleshooting

**If intelligence components don't appear**:

1. **Check LLM Provider**:
   - Ensure `OPENROUTER_API_KEY` is set in `.env`
   - Check logs for LLM provider initialization
   - Intelligence services require LLM provider

2. **Check Data Processing**:
   - Upload a document first
   - Wait for extraction to complete
   - Check AG-UI feed for processing status

3. **Check Navigation**:
   - Make sure you're on the "Intel" tab
   - Workspace should show "Awaiting Intel" if no data yet

4. **Check Service Logs**:
   - Look for service initialization messages
   - Check for error messages in the console
   - Verify all services started successfully

## Example Workflow

1. **Start Application**:
   ```bash
   python -m forge.main
   ```

2. **Upload Document**:
   - Click "Ingest" tab
   - Upload a PDF or text file
   - Watch AG-UI feed for extraction progress

3. **View Intelligence**:
   - Click "Intel" tab
   - Wait for intelligence services to process
   - See semantic profiles, narratives, and analytics appear

4. **Interact**:
   - Click buttons in components
   - Fill out correction forms
   - Approve/reject suggestions

5. **Monitor Activity**:
   - Watch AG-UI feed for real-time updates
   - See status messages and notifications

## Summary

Phase 5 features are **fully integrated and automatic**. Simply:
1. Run the application
2. Process documents
3. Navigate to the "Intel" tab
4. View and interact with intelligence components

All features work together seamlessly through the event-driven architecture!
