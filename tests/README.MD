## Test Coverage Status

### ✅ Implemented Tests

1. **Event Bus Robustness** (`test_event_bus_robustness.py`)
   - ✅ Handler exceptions (ensure bus remains stable)
   - ✅ Unsubscribe/resubscribe logic
   - ✅ Multiple handlers unsubscribe one
   - ✅ Subscribe/unsubscribe/resubscribe cycle
   - ✅ Unsubscribe after clear
   - ✅ Handler exception isolation

2. **Negative/Edge Cases** (`test_domain_edge_cases.py`)
   - ✅ No entities found in document
   - ✅ Only one entity type present (PERSON only, ORG only)
   - ✅ Malformed or missing fields in event payloads
     - Missing doc_id
     - Missing content
     - Missing entities list
     - Empty entities list
     - Missing entity type
     - Missing entity text

3. **Multiple Documents** (`test_domain_edge_cases.py`)
   - ✅ Sequential ingestion of multiple documents
   - ✅ Event routing and isolation verification
   - ✅ Document ID preservation across events

4. **Concurrency** (`test_domain_concurrency.py`)
   - ✅ Simultaneous ingestion of multiple documents
   - ✅ Async stress test (50+ concurrent documents)
   - ✅ Mixed document types concurrent processing
   - ✅ Event bus stability under concurrent load

### 📋 Remaining Tests (Not Yet Implemented)

5. **Persistence Layer**
   - Once implemented, verify entities/relationships are stored and retrieved correctly

6. **Integration with UI**
   - Confirm that AG-UI events and workspace schema events are emitted and renderable

---

## Automated GUI Testing with Flet

### Plan

1. **Unit Test UI Logic**
   - Test FletXr state changes and event handlers in isolation (no UI needed)

2. **Flet App Integration Tests**
   - Use Flet’s built-in `TestClient` (if available) or run the app in headless mode
   - Simulate user actions (navigation, button clicks) and assert UI state

3. **Snapshot Testing**
   - Capture rendered widget trees for given event payloads and compare to expected output

4. **End-to-End (E2E) Testing**
   - Use tools like Selenium, Playwright, or Pyppeteer to launch the Flet app, interact with the UI, and verify visual/functional outcomes

5. **CI Integration**
   - Run all tests (unit, integration, E2E) in CI pipeline with headless display (e.g., xvfb on Linux)

### Test Files

- `test_event_bus.py` - Basic event bus functionality tests
- `test_event_bus_robustness.py` - Event bus unsubscribe/resubscribe and robustness tests
- `test_domain_edge_cases.py` - Edge cases and multiple documents tests
- `test_domain_concurrency.py` - Concurrency and stress tests
- `test_pipeline.py` - Manual pipeline integration test

### Running Tests

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific test file
python3 -m pytest tests/test_event_bus_robustness.py -v

# Run with coverage
python3 -m pytest tests/ --cov=forge --cov-report=html
```

### Next Steps

- Research Flet's official or community-supported test utilities for widget/UI automation
- Prototype a simple E2E test: launch app, trigger event, assert UI update
- Add persistence layer tests once implemented
- Add UI integration tests for AG-UI events and workspace schemas