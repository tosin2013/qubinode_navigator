# Qubinode Navigator - AI Assistant Context

You are helping manage Qubinode Navigator, an enterprise infrastructure automation platform.

## Architecture Overview

- **Airflow** (port 8888): Workflow orchestration for VM provisioning and deployments
- **MCP Server** (port 8889): Tool API for AI integrations
- **AI Assistant** (port 8080): Local LLM with RAG knowledge base
- **PostgreSQL** (port 5432): Metadata, pgvector for RAG embeddings
- **Marquez** (port 5001/3000): OpenLineage lineage tracking

## Key Directories

- `airflow/dags/` - Airflow DAG definitions
- `airflow/plugins/qubinode/` - Custom operators (KcliVMCreate/Delete/List)
- `docs/adrs/` - Architecture Decision Records (54+ ADRs)
- `ai-assistant/` - AI service with llama.cpp + IBM Granite
- `scripts/` - CLI tools (qubinode-cert, qubinode-dns)

## Critical Standards (ADR-0045)

When working with DAGs:

- Use `"""` (triple double quotes) for bash_command, never `'''`
- DAG IDs must be snake_case matching filename
- Use ASCII markers: `[OK]`, `[ERROR]`, `[WARN]`, `[INFO]`, `[SKIP]`
- No string concatenation in bash_command

## Common Commands

```bash
# DAG Management
cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow
podman-compose exec -T airflow-scheduler airflow dags list
./scripts/validate-dag.sh

# VM Management
kcli list vm
kcli info vm <name>

# Service Status
podman-compose ps
curl http://localhost:8888/health
```

## Related Repositories

- `/opt/qubinode-pipelines` - Deployment DAGs and scripts (ADR-0047)
