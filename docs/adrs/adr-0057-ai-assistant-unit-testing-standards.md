# ADR-0057: AI Assistant Unit Testing Standards

## Status

PROPOSED

## Date

2025-12-05

## Context

Following ADR-0056's test strategy, we need to establish specific unit testing standards for the AI Assistant component. Unit tests form the base of our test pyramid (85% of tests) and must be:

- Fast (\< 100ms per test)
- Isolated (no external dependencies)
- Deterministic (same result every run)
- Maintainable (clear, readable, documented)

### Current Unit Test Analysis

**Existing Strengths:**

- Good fixture infrastructure in `conftest.py`
- Proper async test support with `pytest-asyncio`
- Comprehensive mocking of external dependencies (LangChain, LiteLLM)
- Logical test class organization

**Areas for Improvement:**

- 14 tests skipped due to LangChain mocking complexity
- `model_manager.py` at 57.69% coverage (target: 85%)
- Missing edge case tests for error handling
- No property-based testing for input validation

### What Constitutes a "Unit"

In the AI Assistant context, a "unit" is defined as:

| Component Type    | Unit Definition          | Test Isolation         |
| ----------------- | ------------------------ | ---------------------- |
| Service Classes   | Single public method     | Mock all collaborators |
| Tool Classes      | `execute()` method       | Mock subprocess/system |
| Data Classes      | Initialization + methods | Pure unit test         |
| Utility Functions | Single function          | Mock file I/O only     |
| Async Handlers    | Single async function    | Mock httpx/aiohttp     |

## Decision

### 1. Unit Test Naming Convention

Tests follow the pattern: `test_<method>_<scenario>_<expected_outcome>`

```python
# Good examples
def test_get_config_value_from_env_returns_env_value()
def test_chat_not_initialized_raises_runtime_error()
def test_process_message_with_rag_failure_falls_back_to_direct()

# Avoid
def test_config()  # Too vague
def test_it_works()  # Not descriptive
def test_process_message_1()  # No semantic meaning
```

### 2. Test Structure: Arrange-Act-Assert (AAA)

All unit tests MUST follow the AAA pattern with clear separation:

```python
@pytest.mark.asyncio
async def test_chat_success_with_rag_context(mock_config, mock_rag_service):
    """Test successful chat with RAG context retrieval."""
    # Arrange
    service = EnhancedAIService(mock_config)
    service.rag_service = mock_rag_service
    service.llm = MagicMock()

    mock_retrieval = MagicMock()
    mock_retrieval.contexts = ["VM deployment guide"]
    mock_retrieval.sources = ["docs/deployment.md"]
    mock_rag_service.retrieve_relevant_context = AsyncMock(return_value=mock_retrieval)

    # Act
    with patch.object(service, "_generate_local_response", return_value="AI Response"):
        result = await service.chat("How to deploy a VM?")

    # Assert
    assert "response" in result
    assert result["metadata"]["rag_enabled"] is True
    mock_rag_service.retrieve_relevant_context.assert_called_once()
```

### 3. Mocking Strategy

#### Solitary vs Sociable Testing

We use **Solitary Unit Tests** (full mocking) for:

- Service classes with external dependencies
- Tool classes making system calls
- HTTP client interactions

We use **Sociable Unit Tests** (minimal mocking) for:

- Data classes and pure functions
- Configuration parsing logic
- Result formatting utilities

#### Mock Patterns

```python
# Pattern 1: Fixture-based mocks (preferred for reuse)
@pytest.fixture
def mock_rag_service():
    """Provide a mock RAG service."""
    mock_service = AsyncMock()
    mock_service.initialize = AsyncMock(return_value=True)
    mock_service.get_context_for_query = AsyncMock(
        return_value=("# Mock Context", ["source.md"])
    )
    return mock_service

# Pattern 2: Context manager for scope control
def test_hardware_detection_with_gpu(mock_config):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="8192")
        manager = ModelManager(mock_config)
        capabilities = manager.detect_hardware_capabilities()
    assert capabilities["gpu_available"] is True

# Pattern 3: Patch decorator for clean setup
@patch("enhanced_ai_service.ModelManager")
def test_enhanced_service_creation(mock_mm, mock_config):
    mock_mm.return_value.get_model_info.return_value = {
        "model_type": "granite-4.0-micro",
        "preset_info": {},
    }
    service = EnhancedAIService(mock_config)
    assert service is not None
```

### 4. Test Categories and Markers

```python
# pytest.ini
[pytest]
markers =
    unit: Pure unit tests with full mocking
    slow: Tests that take > 1 second
    requires_gpu: Tests requiring NVIDIA GPU
    requires_kvm: Tests requiring KVM/libvirt
    flaky: Known intermittent failures (should be fixed)
```

Usage:

```python
@pytest.mark.unit
def test_config_manager_creation():
    """Pure unit test - no external dependencies."""
    manager = ConfigManager()
    assert manager is not None

@pytest.mark.slow
@pytest.mark.asyncio
async def test_full_diagnostic_workflow():
    """Test takes > 1s due to system calls."""
    result = await diagnostic_registry.run_comprehensive_diagnostics()
    assert "summary" in result
```

### 5. Fixture Design

#### Shared Fixtures (conftest.py)

```python
# Level 1: Data fixtures (stateless)
@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Provide a mock configuration dictionary."""
    return {
        "ai": {"model_name": "granite-4.0-micro", "max_tokens": 512},
        "server": {"host": "0.0.0.0", "port": 8080},
        # ... complete configuration
    }

# Level 2: Service fixtures (stateful mocks)
@pytest.fixture
def mock_config_manager(mock_config):
    """Provide a mock ConfigManager."""
    manager = ConfigManager(config_path="/tmp/test-config.yaml")
    manager.config = mock_config
    return manager

# Level 3: Application fixtures (complex setup)
@pytest.fixture
async def initialized_ai_service(mock_config_manager, mock_rag_service):
    """Provide a fully initialized AI service for testing."""
    service = AIService(mock_config_manager)
    service.is_initialized = True
    service.rag_service = mock_rag_service
    service.llm = MagicMock()
    service.llm._call.return_value = "Test response"
    return service
```

### 6. Async Testing Patterns

```python
# Pattern 1: Simple async test
@pytest.mark.asyncio
async def test_process_message_success(initialized_ai_service):
    result = await initialized_ai_service.process_message("Test message")
    assert "text" in result

# Pattern 2: Testing async exceptions
@pytest.mark.asyncio
async def test_chat_not_initialized_raises_error(mock_config):
    with patch("enhanced_ai_service.ModelManager"):
        service = EnhancedAIService(mock_config)
        service.llm = None  # Force not initialized state

    with pytest.raises(RuntimeError, match="not initialized"):
        await service.chat("Test message")

# Pattern 3: Testing async timeouts
@pytest.mark.asyncio
async def test_llm_call_timeout():
    async def slow_response(*args, **kwargs):
        await asyncio.sleep(10)
        return "response"

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(slow_response(), timeout=0.1)
```

### 7. Coverage Requirements

| Module                   | Current | Target | Priority |
| ------------------------ | ------- | ------ | -------- |
| `config_manager.py`      | 91.72%  | 95%    | Low      |
| `model_manager.py`       | 57.69%  | 85%    | **HIGH** |
| `diagnostic_tools.py`    | 79.43%  | 90%    | Medium   |
| `health_monitor.py`      | 83.95%  | 95%    | Low      |
| `main.py`                | 75.85%  | 90%    | Medium   |
| `enhanced_ai_service.py` | ~75%    | 90%    | **HIGH** |

### 8. Edge Cases and Error Handling

Every unit test class SHOULD include:

```python
class TestConfigManagerEdgeCases:
    """Test edge cases and error handling."""

    def test_load_config_invalid_yaml(self, tmp_path):
        """Test handling of malformed YAML file."""
        config_path = tmp_path / "invalid.yaml"
        config_path.write_text("invalid: yaml: content: [")

        manager = ConfigManager(config_path=str(config_path))
        # Should fall back to defaults, not crash
        await manager.load_config()
        assert manager.config is not None

    def test_env_var_with_empty_value(self):
        """Test environment variable with empty string."""
        with patch.dict(os.environ, {"AI_MODEL_PATH": ""}):
            manager = ConfigManager()
            result = manager._get_config_value("model_path", "default")
        assert result == ""  # Empty string is valid

    def test_config_key_none_value(self):
        """Test handling of None values in config."""
        manager = ConfigManager()
        manager.config = {"ai": {"model_path": None}}
        result = manager.get("ai", "model_path", "fallback")
        assert result is None  # Explicit None should be preserved
```

### 9. Test Documentation

```python
def test_extract_key_findings_from_diagnostics():
    """
    Verify that _extract_key_findings correctly summarizes diagnostic results.

    This test validates:
    1. System info is properly extracted (platform, uptime)
    2. Resource usage is formatted (CPU%, memory%)
    3. KVM status is included when available
    4. Missing data is handled gracefully

    Related: ADR-0027 Section 4.3 - Diagnostic Pipeline
    """
    # Test implementation...
```

## Consequences

### Positive

1. **Consistent Test Quality**: All developers follow same patterns
1. **Fast Feedback**: Unit tests complete in \< 30 seconds
1. **Clear Ownership**: Easy to identify what each test validates
1. **Maintainable Mocks**: Fixture reuse reduces duplication
1. **Coverage Tracking**: Clear targets per module

### Negative

1. **Initial Learning Curve**: Team must learn patterns
1. **Mock Maintenance**: Mocks must track API changes
1. **Fixture Complexity**: Shared fixtures can become large

### Implementation Checklist

- [ ] Add missing `model_manager.py` tests (target: 85%)
- [ ] Enable skipped LangChain LLM tests with proper mocking
- [ ] Add edge case tests for all services
- [ ] Document test patterns in `tests/README.md`
- [ ] Add pre-commit hook for test coverage check

## Related ADRs

- [ADR-0056: AI Assistant Test Strategy Overview](adr-0056-ai-assistant-test-strategy-overview.md)
- [ADR-0058: Integration Testing Approach](adr-0058-ai-assistant-integration-testing-approach.md)
- [ADR-0027: CPU-Based AI Deployment Assistant](adr-0027-cpu-based-ai-deployment-assistant-architecture.md)

## References

- [The Practical Test Pyramid - Unit Tests](https://martinfowler.com/articles/practical-test-pyramid.html#UnitTests)
- [pytest Best Practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
