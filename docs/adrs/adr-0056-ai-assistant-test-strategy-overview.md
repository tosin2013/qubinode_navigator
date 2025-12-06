# ADR-0056: AI Assistant Test Strategy Overview

## Status

PROPOSED

## Date

2025-12-05

## Context

The Qubinode AI Assistant is a critical component that provides AI-powered infrastructure guidance using:

- **FastAPI** REST API framework
- **LangChain** for LLM orchestration
- **llama.cpp** for CPU-based inference with IBM Granite models
- **Qdrant** vector database for RAG (Retrieval-Augmented Generation)
- **LiteLLM** for multi-model API support
- **Marquez/OpenLineage** for infrastructure lineage context

### Current Test Coverage Analysis

| Module                | Coverage   | Test Count | Status         |
| --------------------- | ---------- | ---------- | -------------- |
| `config_manager.py`   | 91.72%     | 33         | Good           |
| `diagnostic_tools.py` | 79.43%     | 26         | Adequate       |
| `health_monitor.py`   | 83.95%     | 18         | Good           |
| `main.py` (FastAPI)   | 75.85%     | 27         | Adequate       |
| `model_manager.py`    | 57.69%     | 19         | **Needs Work** |
| **TOTAL**             | **76.20%** | 228        | Above Target   |

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                          │
│  ┌──────────────────────┬───────────────────┬────────────────────┐ │
│  │   REST Endpoints     │   Health Monitor   │   RAG Ingestion   │ │
│  │   /chat, /health     │   get_health_status│   API Router      │ │
│  │   /diagnostics       │                    │                   │ │
│  └──────────┬───────────┴─────────┬─────────┴────────┬──────────┘ │
│             │                     │                  │             │
│  ┌──────────▼───────────┐  ┌──────▼──────────┐ ┌─────▼──────────┐ │
│  │  EnhancedAIService   │  │  ConfigManager  │ │ QdrantRAGSvc   │ │
│  │  - chat()            │  │  - load_config  │ │ - search_docs  │ │
│  │  - process_message() │  │  - env_override │ │ - get_context  │ │
│  │  - run_diagnostics() │  │                 │ │                │ │
│  └──────────┬───────────┘  └─────────────────┘ └────────────────┘ │
│             │                                                      │
│  ┌──────────▼───────────┐  ┌─────────────────┐ ┌────────────────┐ │
│  │    ModelManager      │  │ DiagnosticTools │ │  MarquezSvc    │ │
│  │  - hardware detect   │  │ - SystemInfo    │ │ - lineage ctx  │ │
│  │  - model download    │  │ - ResourceUsage │ │ - DAG status   │ │
│  │  - llama server      │  │ - KVMDiagnostic │ │                │ │
│  └──────────────────────┘  └─────────────────┘ └────────────────┘ │
│                                                                    │
│                     External Dependencies                          │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  ┌────────────┐  │
│  │ llama.cpp   │  │   Qdrant    │  │  Marquez  │  │  LiteLLM   │  │
│  │ (port 8081) │  │ (embedded)  │  │ (port5001)│  │   APIs     │  │
│  └─────────────┘  └─────────────┘  └───────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Integration Points

1. **llama.cpp Server** - Local inference engine on port 8081
1. **Qdrant Vector DB** - Embedded mode for document embeddings
1. **Marquez API** - OpenLineage data for infrastructure context
1. **LiteLLM** - External API providers (OpenAI, Anthropic, Azure)
1. **System Services** - libvirtd, KVM, NetworkManager via subprocess

### Critical Business Logic

1. **AI Chat Pipeline**: Message → RAG Context → Lineage Context → LLM → Response
1. **Diagnostics Framework**: Tool Registry → Tool Execution → AI Analysis
1. **Health Monitoring**: System Metrics → Service Status → Overall Health
1. **Configuration Management**: YAML → Env Vars → Validation → Runtime

## Decision

We will implement a **customized Test Pyramid** for the AI Assistant with the following distribution:

```
                    /\
                   /  \         E2E Tests: ~5 tests
                  /----\        - API integration workflow
                 /      \       - Health check pipeline
                /--------\
               /          \     Integration Tests: ~30 tests
              /   ------   \    - LLM server interaction
             /   /      \   \   - RAG service operations
            /---/--------\---\  - Marquez connectivity
           /                  \ - Diagnostic tools with system
          /--------------------\
         /                      \   Unit Tests: ~200 tests
        /------------------------\  - Service logic
       /                          \ - Configuration parsing
      /----------------------------\- Tool result handling
                                    - Prompt building

    Target Distribution: 85% Unit | 12% Integration | 3% E2E
    Target Coverage: 80% overall, 90% for critical paths
```

### Testing Principles

1. **Test Observable Behavior**: Focus on inputs/outputs, not implementation
1. **Isolate External Dependencies**: Mock llama.cpp, Qdrant, Marquez
1. **Use Realistic Test Data**: Infrastructure-related queries and responses
1. **Fast Feedback Loop**: Unit tests complete in \< 30 seconds
1. **Deterministic Tests**: No flaky tests depending on network/timing

### Test Categories

| Category    | Scope                 | Mocking Strategy  | CI Execution    |
| ----------- | --------------------- | ----------------- | --------------- |
| Unit        | Single class/function | Full mocking      | Every PR        |
| Integration | Service boundaries    | Partial mocking   | Every PR        |
| E2E         | Full API workflow     | Minimal mocking   | Nightly/Release |
| Contract    | API schemas           | Schema validation | Every PR        |

## Consequences

### Positive

1. **Higher Confidence**: 80%+ coverage on critical AI/RAG pipelines
1. **Faster Development**: Quick unit test feedback
1. **Better Documentation**: Tests serve as usage examples
1. **Regression Prevention**: Catch breaking changes early
1. **Refactoring Safety**: Change implementation without breaking behavior

### Negative

1. **Maintenance Overhead**: Test code requires ongoing updates
1. **Mocking Complexity**: LangChain and LLM mocking is non-trivial
1. **CI Time**: Integration tests add ~2 minutes to pipeline
1. **Learning Curve**: Team must understand mocking patterns

### Risks and Mitigations

| Risk                              | Impact | Mitigation                     |
| --------------------------------- | ------ | ------------------------------ |
| LangChain API changes break mocks | High   | Pin versions, use adapters     |
| Flaky integration tests           | Medium | Proper async handling, retries |
| Model download tests              | Low    | Mock all network calls         |
| System-dependent diagnostic tests | Medium | Skip in CI, run locally        |

## Implementation Details

### Test File Organization

```
ai-assistant/
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── unit/
│   │   ├── test_config_manager.py
│   │   ├── test_model_manager.py
│   │   ├── test_ai_service.py
│   │   ├── test_enhanced_ai_service.py
│   │   ├── test_diagnostic_tools.py
│   │   ├── test_health_monitor.py
│   │   └── test_rag_services.py
│   ├── integration/
│   │   ├── test_api_endpoints.py
│   │   ├── test_llm_integration.py
│   │   ├── test_rag_workflow.py
│   │   └── test_diagnostics_workflow.py
│   └── e2e/
│       ├── test_chat_workflow.py
│       └── test_health_check_pipeline.py
├── pytest.ini
└── .coveragerc
```

### Coverage Requirements

| Module                   | Minimum | Target  |
| ------------------------ | ------- | ------- |
| `config_manager.py`      | 85%     | 95%     |
| `enhanced_ai_service.py` | 80%     | 90%     |
| `model_manager.py`       | 70%     | 85%     |
| `diagnostic_tools.py`    | 80%     | 90%     |
| `qdrant_rag_service.py`  | 75%     | 85%     |
| `health_monitor.py`      | 85%     | 95%     |
| `main.py`                | 80%     | 90%     |
| **Overall**              | **80%** | **85%** |

### CI/CD Integration

```yaml
# .github/workflows/ai-assistant-tests.yml
jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: pytest tests/ --cov=src --cov-fail-under=80
```

## Related ADRs

- [ADR-0027: CPU-Based AI Deployment Assistant Architecture](adr-0027-cpu-based-ai-deployment-assistant-architecture.md)
- [ADR-0049: Multi-Agent LLM Memory Architecture](adr-0049-implementation-plan.md)
- [ADR-0057: Unit Testing Standards](adr-0057-ai-assistant-unit-testing-standards.md)
- [ADR-0058: Integration Testing Approach](adr-0058-ai-assistant-integration-testing-approach.md)

## References

- [The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html) - Ham Vocke
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [respx - HTTPX Mocking](https://lundberg.github.io/respx/)
