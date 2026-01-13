# PyScrAI | Forge

**PyScrAI | Forge** is a **server-driven, event-based intelligence synthesis and worldbuilding engine** designed for real-time entity extraction, relationship analysis, and semantic synthesis using **local CUDA-accelerated models** and a **generative UI layer**.

---

## 1. High-Level Architecture

### Event-Driven · Server-Driven · Modular

Forge follows a **Hub-and-Spoke (Blackboard)** topology:

* A **central Event Bus** owns application state
* Autonomous **Domain Services** subscribe, react, and publish results
* The **UI is server-driven**, rendered dynamically from schemas emitted by services

The frontend is a *projection* of server state—not a controller of it.

---

## A. Presentation Layer (Frontend)

**Purpose:** Render intelligence, not manage logic.

* **Framework:** Flet (Flutter via Python)
* **State Management:** FletXr (Reactive + Dependency Injection)
* **Pattern:** Server-Driven UI (SDUI)

### Key Concepts

* No hard-coded views
* A **Component Registry** maps schema → widgets
* Backend services emit **UI Schemas (JSON)** via **AG-UI**
* UI elements (Graphs, Cards, Dashboards) are instantiated at runtime

---

### **1. The Application Shell (Persistent Layout)**

In the new **Server-Driven UI (SDUI)** architecture, the initial Dashboard view—prior to any agent-driven generation—functions as a **reactive host shell**. It provides the high-level layout, telemetry, and event-stream monitoring required to manage the underlying event-driven systems.

The dashboard is contained within a persistent application shell that manages global navigation and layout consistency:

* **Navigation Rail**: A slim vertical navigation bar on the far left for switching between primary system domains (e.g., Data Ingestion, Graph Analysis, Intelligence Synthesis).
* **Global Status Indicators**: Real-time counts for the entity and relationship graph, pulled from the DuckDB analytical store via the `AppController`.

### **2. The Command Feed (AG-UI Panel)**

A dedicated vertical pane, typically positioned on the right, serves as the primary interface for the **AG-UI protocol**:

* **Live Event Stream**: A scrolling list of transient "Thinking" logs and system events published to the central Blackboard.
* **Action Queue**: A section for "User Interrupts," where domain services post suggestions that require explicit user approval (e.g., "Merge detected duplicate entities?").
* **Activity Feed**: A high-level chronological log of state mutations, such as `ENTITY_CREATED` or `RELATIONSHIP_LINKED`.

### **3. The Reactive Workspace (The Canvas)**

The center of the screen is a blank **Generative Canvas** awaiting instructions from the A2UI specification:

* **Component Placeholder**: This area is bound to a `FletXr` `RxList`. Initially, it renders a "System Ready" or "Idle" state.
* **Dynamic Renderer**: An underlying **Widget Factory** (Registry) is initialized and listening to the event bus. It is prepared to hydrate incoming JSON blueprints into native Flet controls (e.g., Network Graphs, KPI Cards, Geo Maps).
* **Responsive Grid**: The canvas uses a flexible grid layout to ensure that when an agent "orders" multiple components (e.g., a chart and a table), they are arranged optimally for the user's current window size.

### **Baseline State Summary**

| Section | Component | Source of Truth | Visual State |
| --- | --- | --- | --- |
| **Header** | Telemetry Bar | `nvidia-ml-py` | Real-time GPU/VRAM % |
| **Sidebar** | Navigation Rail | App Routing Table | Domain Icons |
| **Right Pane** | AG-UI Feed | `core/event_bus.py` | "System Initialized..." |
| **Center** | Workspace | `FletXr` `RxList` | Empty Canvas / "Awaiting Intel" |

This configuration ensures that the system is ready to receive and render complex visualizations immediately upon the first event being published to the **Blackboard**.


---

## B. Application Layer (Orchestration)

**Purpose:** Coordinate intent, state, and events.

* **Pattern:** Blackboard / Event Bus
* **Global State:** Entities, relationships, system status
* **Controller:** `AppController`

  * Routes user intent → Event Bus
  * Subscribes to state updates
  * Updates FletXr `Rx` variables reactively

This layer contains **no domain logic**.

---

## C. Domain Layer (Business Logic)

**Purpose:** Perform intelligence work.

* **Services:** Stateless, asynchronous workers
* **Runtime:** Python `asyncio`
* **Flow:**

  1. Subscribe to event topics (e.g. `DATA_INGESTED`)
  2. Perform computation (extraction, resolution, graph analysis)
  3. Publish results back to the Event Bus

Services never talk to each other directly—**only through events**.

---

## D. Infrastructure Layer (Data & Compute)

**Purpose:** Provide high-performance local intelligence.

* **LLM Inference:**

  * PyTorch + `bitsandbytes`
  * 4-bit quantized Llama-3 / Mistral
  * RTX 4060 (local)
* **Vector Store:**

  * Qdrant (Local Mode)
  * GPU-accelerated semantic retrieval
* **Structured Analytics:**

  * DuckDB for fast graph and synthesis queries

---

## 2. Project Structure (Clean Architecture)

```text
forge/
├── __init__.py
├── main.py                    # Application entry point
│
├── core/                      # Framework primitives
│   ├── event_bus.py           # Blackboard / PubSub hub
│   ├── controller.py          # Base FletXr controller
│   ├── events.py              # Canonical event definitions
│   └── exceptions.py
│
├── domain/                    # Business logic (Services)
│   ├── extraction/            # Parsing, OCR
│   ├── resolution/            # Entity extraction & dedup
│   ├── graph/                 # Relationship analysis
│   ├── intelligence/          # Semantic profiling
│   └── synthesis/             # Narrative & report generation
│
├── infrastructure/            # External systems
│   ├── llm/                   # Model loaders
│   ├── persistence/           # DuckDB / filesystem
│   └── vector/                # Qdrant implementations
│
└── presentation/              # UI layer
    ├── controllers/
    ├── layouts/
    ├── components/
    └── renderer/              # AG-UI → Widget registry
```

---

## 3. Generative UI (SDUI via AG-UI)

AG-UI defines the **contract** between domain logic and presentation.

### Flow

1. **Schema Definition**

   ```json
   { "type": "kpi_card", "props": { "value": 50 } }
   ```

2. **Service Output**
   Services emit structured UI schemas—not raw text.

3. **Dynamic Rendering**
   `presentation/renderer/registry.py` maps schema → Flet widgets.

Result:
**Backend-controlled visualization with zero frontend redeploys.**

---

## Next Step

### Implement the Core Infrastructure

We start with the **Blackboard Event Bus**, since everything depends on it.

---

# `forge/core/event_bus.py`

Below is a functional example of a **minimal, extensible, asyncio-native Event Bus** 
designed for:

* Topic-based pub/sub
* Async handlers
* Strong typing compatibility
* Future A2A / MCP / persistence hooks

```python
# forge/core/event_bus.py

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict, List, TypeAlias

EventPayload: TypeAlias = Dict[str, Any]
EventHandler: TypeAlias = Callable[[EventPayload], Awaitable[None]]


class EventBus:
    """
    Central Blackboard / PubSub hub.

    - Async, non-blocking
    - Topic-based subscriptions
    - Fire-and-forget publishing
    """

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def subscribe(self, topic: str, handler: EventHandler) -> None:
        """
        Register an async handler for a given topic.
        """
        async with self._lock:
            if handler not in self._subscribers[topic]:
                self._subscribers[topic].append(handler)

    async def unsubscribe(self, topic: str, handler: EventHandler) -> None:
        """
        Remove a handler from a topic.
        """
        async with self._lock:
            if handler in self._subscribers.get(topic, []):
                self._subscribers[topic].remove(handler)

    async def publish(self, topic: str, payload: EventPayload) -> None:
        """
        Publish an event to all subscribers.

        Handlers are scheduled concurrently and do not block the publisher.
        """
        async with self._lock:
            handlers = list(self._subscribers.get(topic, []))

        if not handlers:
            return

        for handler in handlers:
            asyncio.create_task(self._safe_dispatch(handler, payload))

    async def _safe_dispatch(
        self,
        handler: EventHandler,
        payload: EventPayload,
    ) -> None:
        """
        Dispatch wrapper to prevent a single handler failure
        from crashing the bus.
        """
        try:
            await handler(payload)
        except Exception as exc:
            # TODO: hook into structured logging / diagnostics
            print(
                f"[EventBus] Handler error in {handler.__name__}: {exc}"
            )

    def clear(self) -> None:
        """
        Remove all subscriptions.
        Useful for teardown or hot-reload.
        """
        self._subscribers.clear()
```

---

## Why This Implementation Is Correct

* ✅ Async-native (no blocking)
* ✅ Stateless services supported
* ✅ UI, domain, and infra can all subscribe safely
* ✅ Failure-isolated handlers
* ✅ Ready for:

  * Event persistence
  * Replay
  * Distributed buses
  * A2A routing
  * MCP tool dispatch

---

Possible Future Tasks:

* Define **canonical event schemas (`events.py`)**
* Add **event versioning & replay**
* Introduce **priority lanes / throttling**
* Wire this into **AppController**
* Or design the **A2A / MCP bridge layer**
