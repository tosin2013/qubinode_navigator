______________________________________________________________________

## layout: default title: Architecture & Design parent: Architectural Decision Records nav_order: 4 has_children: true

# Architecture & Design ADRs

This section contains ADRs related to system architecture, design patterns, and extensibility frameworks.

## ADRs in this Category

### Core Architecture

- **[ADR-0006](adr-0006-modular-dependency-management.md)**: Modular Dependency Management Strategy
- **[ADR-0028](adr-0028-modular-plugin-framework-for-extensibility.md)**: Modular Plugin Framework for Extensibility
- **[ADR-0033](adr-0033-terminal-based-one-shot-deployment-architecture.md)**: Terminal-Based One-Shot Deployment Architecture ⭐ *Primary Entry Point*

### AI & RAG Architecture

- **[ADR-0027](adr-0027-cpu-based-ai-deployment-assistant-architecture.md)**: CPU-Based AI Deployment Assistant Architecture
- **[ADR-0038](adr-0038-fastmcp-framework-migration.md)**: FastMCP Framework Migration for MCP Server Implementation
- **[ADR-0049](adr-0049-multi-agent-llm-memory-architecture.md)**: Multi-Agent LLM Memory Architecture with PgVector ⭐ *Strategic*
- **[ADR-0050](adr-0050-hybrid-host-container-architecture.md)**: Hybrid Host-Container Architecture for Resource Optimization

### Workflow Orchestration

- **[ADR-0036](adr-0036-apache-airflow-workflow-orchestration-integration.md)**: Apache Airflow Workflow Orchestration Integration
- **[ADR-0045](adr-0045-airflow-dag-development-standards.md)**: Airflow DAG Development Standards 📋 *Guidelines*
- **[ADR-0046](adr-0046-dag-validation-pipeline-and-host-execution.md)**: DAG Validation Pipeline and Host-Based Execution
- **[ADR-0047](adr-0047-kcli-pipelines-dag-integration-pattern.md)**: kcli-pipelines as DAG Source Repository

## Key Themes

- **Modular Design**: Extensible architecture with clear separation of concerns
- **Plugin Framework**: Flexible system for adding new functionality
- **AI Integration**: Modern AI-assisted deployment and troubleshooting with RAG capabilities
- **Dependency Management**: Clean handling of external dependencies
- **Workflow Orchestration**: Apache Airflow for infrastructure automation tasks
