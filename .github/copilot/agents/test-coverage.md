# Test Coverage Agent

This agent helps increase and maintain test coverage for the Qubinode Navigator AI Assistant.

## Goal

Achieve and maintain 80% test coverage across all AI Assistant source files.

## Context

The AI Assistant (`ai-assistant/`) is a Python-based service that provides:

- PydanticAI-based agents for infrastructure automation
- RAG (Retrieval-Augmented Generation) using Qdrant + FastEmbed
- Web search integration using DuckDuckGo
- Diagnostic tools for system monitoring
- FastAPI endpoints for AI chat and diagnostics

## Current State

- **Current coverage**: ~40% (failing the 70% threshold)
- **Target coverage**: 80%
- **Test framework**: pytest with pytest-asyncio for async tests
- **Coverage tool**: pytest-cov with .coveragerc configuration

## Files Needing Coverage

Priority files with low or no coverage:

1. **src/enhanced_ai_service.py** - Core AI service with LiteLLM integration
1. **src/qdrant_rag_service.py** - RAG service with Qdrant vector DB
1. **src/lineage_service.py** - OpenLineage tracking for data lineage
1. **src/tools/web_search.py** - PydanticAI web search integration
1. **src/rag_ingestion_api.py** - RAG document ingestion API

## Test Patterns

### Async Tests

```python
@pytest.mark.asyncio
async def test_async_method(self, tmp_path):
    """Test async method."""
    service = SomeService(data_dir=str(tmp_path))
    result = await service.async_method()
    assert result is True
```

### Mocking External Services

```python
from unittest.mock import patch, AsyncMock, MagicMock

def test_with_mocked_external(self):
    """Test with mocked external dependency."""
    with patch("src.module.external_service") as mock_service:
        mock_service.return_value = AsyncMock()
        # Test code here
```

### Skip When Dependencies Missing

```python
import pytest

DEPENDENCY_AVAILABLE = False
try:
    import optional_dependency
    DEPENDENCY_AVAILABLE = True
except ImportError:
    pass

@pytest.mark.skipif(not DEPENDENCY_AVAILABLE, reason="Dependency not available")
class TestWithDependency:
    pass
```

## Instructions

When improving test coverage:

1. **Run coverage report** to identify gaps:

   ```bash
   cd ai-assistant
   python -m pytest tests/ -v --cov=src --cov-report=term-missing
   ```

1. **Focus on critical paths** first:

   - Happy path tests for main functionality
   - Error handling and edge cases
   - Integration between components

1. **Follow existing patterns**:

   - Use fixtures from `tests/conftest.py`
   - Mock external services (Qdrant, LiteLLM, HTTP clients)
   - Use `tmp_path` fixture for file-based tests

1. **Avoid flaky tests**:

   - Don't rely on network calls in unit tests
   - Use deterministic test data
   - Mock time-dependent operations

1. **Document test purpose**:

   - Each test should have a docstring explaining what it tests
   - Group related tests in classes

## Coverage Configuration

See `ai-assistant/.coveragerc`:

```ini
[run]
source = src
omit =
    src/__pycache__/*
    src/tests/*

[report]
fail_under = 70
show_missing = true
```

## Related Files

- `ai-assistant/tests/` - Test directory
- `ai-assistant/.coveragerc` - Coverage configuration
- `ai-assistant/pytest.ini` - Pytest configuration
- `.github/workflows/ai-assistant-ci.yml` - CI workflow
