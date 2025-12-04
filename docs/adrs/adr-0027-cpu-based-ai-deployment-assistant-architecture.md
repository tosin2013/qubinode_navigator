______________________________________________________________________

## layout: default title: ADR-0027 CPU-Based AI Deployment Assistant parent: Architecture & Design grand_parent: Architectural Decision Records nav_order: 0027

# ADR-0027: CPU-Based AI Deployment Assistant Architecture

## Status

Accepted - Implemented (2025-11-11)

AI Assistant has been fully implemented with containerized deployment, RAG system integration, and seamless terminal-based interaction through deploy-qubinode.sh.

## Context

The PRD analysis identified a significant opportunity to integrate a CPU-based AI deployment assistant to enhance user experience and reduce deployment complexity. Current challenges include:

- **Complex deployment troubleshooting**: Users struggle with error diagnosis and resolution
- **High barrier to entry**: Non-experts find infrastructure automation intimidating
- **Manual support overhead**: Common issues require human intervention
- **Limited real-time guidance**: Static documentation insufficient for dynamic scenarios

The solution must run locally without GPU dependencies, ensure data privacy, and integrate seamlessly with existing container-first execution model. Modern small language models like IBM Granite-4.0-Micro enable CPU-based inference with sufficient capability for technical assistance.

## Decision

Implement a CPU-based AI deployment assistant using the following architecture:

### Core Components

1. **Inference Engine**: llama.cpp for high-performance CPU inference
1. **Language Model**: IBM Granite-4.0-Micro (3B parameters, GGUF format)
1. **Agent Framework**: LangChain or LlamaIndex for orchestration
1. **Knowledge Base**: RAG over project documentation and best practices
1. **Tool Integration**: System diagnostics and configuration validation

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Qubinode Navigator                       │
│                   (Main System)                          │
└────────────────────┬────────────────────────────────────┘
                     │ REST API / CLI Interface
                     │
┌────────────────────▼────────────────────────────────────┐
│            AI Deployment Assistant                       │
│                (Podman Container)                        │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  llama.cpp + Granite-4.0-Micro (3B) GGUF        │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Agent Framework (LangChain/LlamaIndex)         │   │
│  │  - RAG over Qubinode documentation              │   │
│  │  - Tool-calling for system diagnostics          │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Integration Points

- **CLI Interface**: `qubinode-ai` command for interactive assistance
- **Ansible Integration**: Callback plugins for real-time monitoring
- **Setup Script Hooks**: Pre/post deployment validation and guidance
- **Log Analysis**: Automated error pattern recognition and resolution

## Consequences

### Positive

- **Enhanced User Experience**: Interactive guidance and troubleshooting
- **Reduced Barrier to Entry**: Assists non-experts through complex configurations
- **Operational Efficiency**: Automated diagnostics and error resolution
- **Scalable Support**: Handles common issues without human intervention
- **Competitive Differentiation**: Unique AI-powered infrastructure automation
- **Data Privacy**: All processing remains local with no external dependencies

### Negative

- **Resource Requirements**: Additional CPU and memory overhead for inference
- **Container Orchestration Complexity**: Managing AI service alongside existing components
- **Model Maintenance**: Need for periodic model updates and retraining
- **Integration Complexity**: Coordinating AI service with existing workflows
- **Performance Impact**: Inference latency during real-time assistance

### Risks

- **Model Accuracy Limitations**: AI may provide incorrect guidance for edge cases
- **Integration Stability**: Potential issues with Ansible callback integration
- **Resource Contention**: AI inference competing with deployment processes
- **Maintenance Overhead**: Additional component to monitor and update

## Alternatives Considered

1. **Cloud-based AI services**: Rejected due to data privacy and dependency concerns
1. **GPU-accelerated inference**: Rejected due to hardware requirements constraint
1. **Rule-based expert system**: Insufficient flexibility for complex scenarios
1. **External chatbot integration**: Lacks deep system integration capabilities
1. **Human-only support**: Does not scale with user growth

## Implementation Plan

### Phase 1: Core AI Service (Weeks 1-4)

- Build llama.cpp-based container with Granite-4.0-Micro model
- Implement basic REST API for inference
- Create CLI interface (`qubinode-ai`) for testing
- Validate CPU performance and resource requirements

### Phase 2: Knowledge Integration (Weeks 5-8)

- Structure existing documentation for RAG embedding
- Implement vector database (ChromaDB) for knowledge retrieval
- Create tool-calling framework for system diagnostics
- Test knowledge accuracy and retrieval performance

### Phase 3: Deployment Integration (Weeks 9-12)

- Integrate with setup scripts for pre/post deployment guidance
- Implement Ansible callback plugins for real-time monitoring
- Create automated log analysis and error resolution
- Comprehensive testing across deployment scenarios

### Phase 4: Production Readiness (Weeks 13-16)

- Performance optimization and resource tuning
- Security hardening and access controls
- Monitoring and observability integration
- Documentation and user training materials

## Technical Requirements

### Hardware Requirements

- **CPU**: x86_64 with AVX2 support (minimum for llama.cpp optimization)
- **Memory**: Additional 4-8GB RAM for model loading and inference
- **Storage**: 2-4GB for model files and knowledge base

### Software Dependencies

- **Container Runtime**: Podman (existing requirement)
- **Python Libraries**: langchain, chromadb, fastapi
- **Model Format**: GGUF-quantized Granite-4.0-Micro
- **Vector Database**: ChromaDB for document embeddings

## Related ADRs

- ADR-0001: Container-First Execution Model (containerized AI service)
- ADR-0004: Security Architecture (local processing, no external APIs)
- ADR-0007: Bash-First Orchestration (CLI integration points)
- ADR-0011: Comprehensive Platform Validation (enhanced with AI analysis)

## Date

2025-11-07

## Stakeholders

- AI/ML Engineering Team
- DevOps Team
- UX/Product Team
- Infrastructure Team
- Security Team
