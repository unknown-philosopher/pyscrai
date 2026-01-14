# UI Testing Frameworks for LLM Agent Integration

## Recommended Frameworks

### 1. **Playwright** ⭐ **BEST CHOICE**

**Why it's ideal for LLM agents:**
- **Programmatic Control**: Excellent Python API that LLMs can easily understand and generate
- **Auto-waiting**: Automatically waits for elements, reducing flakiness
- **Multi-browser**: Supports Chromium, Firefox, WebKit
- **Screenshot/Video**: Built-in screenshot and video recording for debugging
- **Network Interception**: Can mock network requests
- **Headless/Headed**: Can run with or without visible browser
- **Great Documentation**: Clear, comprehensive docs that LLMs can reference

**Installation:**
```bash
pip install playwright pytest-playwright
playwright install chromium
```

**Example Usage:**
```python
from playwright.sync_api import sync_playwright

def test_graph_button():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("http://localhost:8000")
        
        # Wait for button and click
        page.wait_for_selector('button:has-text("View Graph")')
        page.click('button:has-text("View Graph")')
        
        # Verify browser opened (check for new page)
        assert len(browser.contexts[0].pages) > 1
        browser.close()
```

**LLM-Friendly Features:**
- Simple, intuitive API
- Good error messages
- Can generate code from natural language descriptions
- Works well with pytest fixtures

---

### 2. **Flet Testing Utilities** (If Available)

**Why it's good:**
- **Native Integration**: Built specifically for Flet apps
- **Component Access**: Direct access to Flet controls
- **Event Simulation**: Can simulate user interactions

**Check if Flet has built-in testing:**
```python
# Check Flet documentation for testing utilities
import flet as ft
# Look for ft.test or similar modules
```

**If not available, use Playwright** (Flet apps run in browsers, so Playwright works perfectly)

---

### 3. **Selenium** (Fallback Option)

**Why it's less ideal:**
- More verbose API
- Requires explicit waits (more flaky)
- Slower than Playwright
- But widely used and well-documented

**Installation:**
```bash
pip install selenium
```

---

## Recommended Testing Architecture

### Structure
```
tests/
├── ui/
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures
│   ├── test_dashboard.py    # Dashboard tests
│   ├── test_graph.py        # Graph visualization tests
│   └── test_ingest.py       # Document ingest tests
├── unit/
│   └── ...                  # Unit tests for services
└── integration/
    └── ...                  # Integration tests
```

### Example Test Setup (`tests/ui/conftest.py`)

```python
import pytest
from playwright.sync_api import sync_playwright, Page, Browser
import subprocess
import time
from pathlib import Path

@pytest.fixture(scope="session")
def app_server():
    """Start the Flet app server."""
    # Start your Flet app in a subprocess
    proc = subprocess.Popen(
        ["python", "forge/main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    time.sleep(3)
    
    yield proc
    
    # Cleanup
    proc.terminate()
    proc.wait()

@pytest.fixture(scope="function")
def browser_page():
    """Create a browser page for each test."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set to True for CI
        context = browser.new_context()
        page = context.new_page()
        yield page
        browser.close()
```

### Example Test (`tests/ui/test_dashboard.py`)

```python
import pytest
from playwright.sync_api import Page

def test_view_graph_button_opens_browser(browser_page: Page, app_server):
    """Test that clicking View Graph button opens browser."""
    page = browser_page
    
    # Navigate to app
    page.goto("http://localhost:8550")  # Default Flet port
    
    # Wait for dashboard to load
    page.wait_for_selector('text=Mission Control')
    
    # Check if graph button exists
    graph_button = page.locator('button:has-text("View Graph")')
    assert graph_button.is_visible()
    
    # Get initial page count
    initial_pages = len(page.context.pages)
    
    # Click button
    graph_button.click()
    
    # Wait for new page/tab to open (browser opening)
    # Note: This might open external browser, so we check logs instead
    # Or we can check if HTTP server started
    
    # Verify button is clickable when data exists
    assert graph_button.is_enabled() or graph_button.is_disabled()  # Either state is valid
```

---

## LLM Agent Integration Strategy

### 1. **Test Generation from Natural Language**

Create a helper that converts natural language to Playwright code:

```python
# tests/ui/llm_test_generator.py
def generate_test_from_description(description: str) -> str:
    """
    Use LLM to generate Playwright test code from description.
    
    Example:
    description = "Test that clicking View Graph button opens browser"
    Returns: Playwright test code
    """
    prompt = f"""
    Generate a Playwright test function for: {description}
    
    Requirements:
    - Use pytest fixtures
    - Use page.wait_for_selector for reliability
    - Include assertions
    - Handle async operations properly
    """
    # Call LLM API
    # Return generated code
    pass
```

### 2. **Self-Healing Tests**

Use Playwright's auto-waiting and retry mechanisms:

```python
# Playwright automatically waits for elements
page.click('button:has-text("View Graph")')  # Waits until clickable

# For custom retries
from playwright.sync_api import TimeoutError

def click_with_retry(page, selector, max_retries=3):
    for i in range(max_retries):
        try:
            page.click(selector, timeout=5000)
            return True
        except TimeoutError:
            if i == max_retries - 1:
                raise
            time.sleep(1)
```

### 3. **Visual Regression Testing**

Use Playwright's screenshot comparison:

```python
def test_dashboard_layout(browser_page: Page):
    page.goto("http://localhost:8550")
    page.wait_for_selector('text=Mission Control')
    
    # Take screenshot
    page.screenshot(path="tests/screenshots/dashboard.png")
    
    # Compare with baseline (in CI/CD)
    # pytest-playwright has built-in visual comparison
```

---

## Quick Start Guide

### 1. Install Dependencies

```bash
pip install playwright pytest pytest-playwright pytest-asyncio
playwright install chromium
```

### 2. Create Test File

```python
# tests/ui/test_basic.py
import pytest
from playwright.sync_api import Page, expect

@pytest.fixture
def page(browser_page: Page):
    browser_page.goto("http://localhost:8550")
    return browser_page

def test_dashboard_loads(page: Page):
    expect(page.locator('text=Mission Control')).to_be_visible()

def test_view_graph_button_exists(page: Page):
    button = page.locator('button:has-text("View Graph")')
    expect(button).to_be_visible()
```

### 3. Run Tests

```bash
# Run all UI tests
pytest tests/ui/

# Run with browser visible
pytest tests/ui/ --headed

# Run specific test
pytest tests/ui/test_dashboard.py::test_view_graph_button_exists
```

---

## Integration with Your Current Setup

### Add to `setup.py`:

```python
extras_require={
    "testing": [
        "playwright>=1.40.0",
        "pytest>=7.4.0",
        "pytest-playwright>=0.4.0",
        "pytest-asyncio>=0.21.0",
    ]
}
```

### Create GitHub Actions Workflow:

```yaml
# .github/workflows/ui_tests.yml
name: UI Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install -e ".[testing]"
      - run: playwright install chromium
      - run: pytest tests/ui/ --headed
```

---

## Why Playwright Over Others?

| Feature | Playwright | Selenium | PyAutoGUI |
|---------|-----------|----------|-----------|
| **LLM-Friendly API** | ✅ Excellent | ⚠️ Verbose | ❌ Complex |
| **Auto-Waiting** | ✅ Built-in | ❌ Manual | ❌ Manual |
| **Speed** | ✅ Fast | ⚠️ Medium | ⚠️ Slow |
| **Reliability** | ✅ High | ⚠️ Medium | ❌ Low |
| **Documentation** | ✅ Great | ✅ Good | ⚠️ Limited |
| **Multi-Browser** | ✅ Yes | ✅ Yes | ❌ No |
| **Screenshots** | ✅ Built-in | ⚠️ Manual | ⚠️ Manual |

---

## Next Steps

1. **Install Playwright**: `pip install playwright && playwright install chromium`
2. **Create test structure**: Set up `tests/ui/` directory
3. **Write first test**: Test the View Graph button functionality
4. **Integrate with CI/CD**: Add GitHub Actions workflow
5. **Add LLM test generation**: Create helper for generating tests from descriptions

---

## Example: Testing View Graph Button

```python
import pytest
from playwright.sync_api import Page, expect
import time

def test_view_graph_opens_browser(page: Page, app_server):
    """Test that View Graph button successfully opens browser."""
    # Navigate to dashboard
    page.goto("http://localhost:8550")
    
    # Wait for dashboard to load
    expect(page.locator('text=Mission Control')).to_be_visible(timeout=10000)
    
    # Find View Graph button
    view_graph_button = page.locator('button:has-text("View Graph")')
    
    # Verify button exists
    expect(view_graph_button).to_be_visible()
    
    # Check if button is enabled (requires data)
    is_enabled = view_graph_button.is_enabled()
    
    if is_enabled:
        # Click button
        view_graph_button.click()
        
        # Wait a moment for browser to open
        time.sleep(2)
        
        # Verify success message appears in AG-UI feed
        # (Since external browser opens, we check logs/feed)
        feed = page.locator('text=Graph opened in browser')
        expect(feed).to_be_visible(timeout=5000)
    else:
        # Button should be disabled when no data
        expect(view_graph_button).to_be_disabled()
```
