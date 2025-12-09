# Qubinode Navigator - AI Assistant Context

You are helping manage Qubinode Navigator, an enterprise infrastructure automation platform with **PydanticAI-based orchestration** (ADR-0063, ADR-0066).

## Architecture Overview

- **AI Assistant** (port 8080): PydanticAI orchestrator + RAG knowledge base
  - `/orchestrator/intent` - Natural language deployment (main interface)
  - `/orchestrator/observe` - DAG monitoring with Observer Agent
  - `/orchestrator/dags` - DAG discovery
  - `/orchestrator/status` - Check API keys and availability
- **Airflow** (port 8888): Workflow orchestration for VM provisioning and deployments
- **MCP Server** (port 8889): Tool API for AI integrations
- **PostgreSQL** (port 5432): Metadata, pgvector for RAG embeddings
- **Marquez** (port 5001/3000): OpenLineage lineage tracking

## PydanticAI Orchestrator (ADR-0063, ADR-0066)

The AI Assistant includes a multi-agent system for intent-based deployment:

- **Manager Agent**: Analyzes user intent, finds matching DAGs, creates execution plans
- **Developer Agent**: Validates DAGs, checks prerequisites (templates, resources)
- **Observer Agent**: Monitors DAG runs, detects shadow errors, provides recommendations

### Intent-Based Deployment Example

```bash
# Deploy infrastructure using natural language
curl -X POST http://localhost:8080/orchestrator/intent \
  -H "Content-Type: application/json" \
  -d '{"intent": "Deploy FreeIPA", "auto_execute": true}'

# Monitor deployment
curl -X POST "http://localhost:8080/orchestrator/observe?dag_id=freeipa_deployment"
```

## Key Directories

- `airflow/dags/` - Airflow DAG definitions
- `airflow/plugins/qubinode/` - Custom operators (KcliVMCreate/Delete/List, PydanticAIOperator)
- `docs/adrs/` - Architecture Decision Records (60+ ADRs)
- `ai-assistant/` - AI service with PydanticAI orchestrator
- `scripts/development/deploy-qubinode.sh` - One-shot deployment script

## Critical Standards (ADR-0045)

When working with DAGs:

- Use `"""` (triple double quotes) for bash_command, never `'''`
- DAG IDs must be snake_case matching filename
- Use ASCII markers: `[OK]`, `[ERROR]`, `[WARN]`, `[INFO]`, `[SKIP]`
- No string concatenation in bash_command

## Common Commands

```bash
# Deployment (CI-tested method)
sudo -E ./scripts/development/deploy-qubinode.sh

# DAG Management (use sudo for root containers)
sudo podman exec airflow-scheduler airflow dags list
sudo podman exec airflow-scheduler airflow dags unpause <dag_id>
sudo podman exec airflow-scheduler airflow dags trigger <dag_id>

# VM Management (use sudo!)
sudo kcli list vm
sudo kcli info vm <name>

# Service Status
sudo podman ps
curl http://localhost:8080/orchestrator/status
curl http://localhost:8888/health
```

## Environment Variables

```bash
OPENROUTER_API_KEY=sk-or-...     # Required for PydanticAI orchestrator
USE_LOCAL_MODEL=false            # Skip local llama.cpp model
QUBINODE_ENABLE_AIRFLOW=true     # Enable Airflow stack
```

## Related ADRs

- ADR-0063: PydanticAI Core Agent Orchestrator
- ADR-0066: Developer Agent DAG Validation and Smart Pipelines
- ADR-0067: Self-Hosted Runner E2E Testing
