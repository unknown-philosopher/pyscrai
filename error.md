**Issue Summary:**  
The phase2 integration tests in `tests/test_phase2_integration.py` were failing because entities were not being extracted from documents, which prevented the entire pipeline from functioning. Without entity extraction, relationship extraction could not occur, and no graph updates were generated.

**Root Cause:**  
The test setup was not initializing LLM providers for the services. The `DocumentExtractionService` and `EntityResolutionService` were created without LLM providers in the test's `asyncSetUp()` method, causing them to silently fail when attempting to extract entities.

**Resolution:**  
✅ **FIXED** - Updated `test_phase2_integration.py` to:
1. Import and initialize LLM providers using `ProviderFactory.create_from_env()` in `asyncSetUp()`
2. Pass LLM providers to `DocumentExtractionService` and `EntityResolutionService` constructors
3. Add skip logic for tests when LLM provider is not available (with helpful error message)
4. Increase wait times to account for rate limiting and async processing delays

**Changes Made:**
- Added imports: `ProviderFactory`, `LLMProvider`, `load_dotenv`, and logging
- Modified `asyncSetUp()` to initialize LLM provider before creating services
- Updated all test methods to skip gracefully if LLM provider is unavailable
- Increased sleep durations to accommodate rate-limited LLM API calls

**Current State:**  
✅ **RESOLVED** - Tests are now passing. The pipeline correctly:
- Extracts entities from documents using LLM
- Extracts relationships between entities
- Updates the knowledge graph
- Persists data to DuckDB

**Note:** Some tests may occasionally fail due to rate limiting from the LLM API provider. The tests include appropriate wait times, but very high API usage may require additional delays.

---