# Architecture Decision Records (ADRs)

Apply when working with ADRs or documentation.

## Overview

Qubinode Navigator uses ADRs to document architectural decisions. There are 54+ ADRs in `docs/adrs/`.

## Finding ADRs

```bash
# List all ADRs
ls docs/adrs/*.md

# Search by topic
grep -l -i "topic" docs/adrs/*.md
```

## Key ADRs by Category

### Core Architecture

- **ADR-0001**: Core architecture decisions
- **ADR-0036**: Airflow integration architecture
- **ADR-0043**: Host network access for VM connectivity

### DAG Development (CRITICAL)

- **ADR-0045**: DAG development standards
  - Triple double quotes for bash_command
  - snake_case naming
  - ASCII-only markers
- **ADR-0046**: Validation pipeline & host execution
- **ADR-0047**: qubinode-pipelines integration

### Infrastructure

- **ADR-0050**: Hybrid host-container architecture
- **ADR-0051**: Vault secrets management
- **ADR-0055**: Zero-friction infrastructure services

### AI/RAG

- **ADR-0049**: Multi-agent LLM memory (pgvector + OpenLineage)

### Testing

- **ADR-0056**: AI assistant test strategy overview
- **ADR-0057**: Unit testing standards
- **ADR-0058**: Integration testing approach
- **ADR-0059**: E2E testing strategy

## ADR Format

Each ADR follows this structure:

1. **Title**: Short descriptive title
1. **Status**: Proposed, Accepted, Deprecated, Superseded
1. **Context**: Why this decision is needed
1. **Decision**: What was decided
1. **Consequences**: Impact of the decision

## When to Reference ADRs

- Creating new DAGs → ADR-0045
- Adding VM operations → ADR-0046, ADR-0047
- Modifying services → ADR-0050
- Adding secrets → ADR-0051
- Working with RAG → ADR-0049
- Writing tests → ADR-0056 through ADR-0059

## Creating New ADRs

```bash
# Next ADR number
ls docs/adrs/adr-*.md | tail -1

# Create new ADR
cp docs/adrs/template.md docs/adrs/adr-00XX-title.md
```
