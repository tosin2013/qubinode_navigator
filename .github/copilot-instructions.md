# Qubinode Navigator Copilot Instructions

## Architecture Snapshot

- Container-first, plugin-based automation platform: `core/` holds orchestration services (plugin manager, event bus, config, rollout/rollback, monitoring) that load plugins from `plugins/**`.
- Plugins follow ADR-0028: each class subclasses `core/base_plugin.py::QubiNodePlugin`, implements `_initialize_plugin`, `check_state`, `get_desired_state`, and `apply_changes` returning `PluginResult` with idempotent `SystemState` comparisons.
- `qubinode_cli.py` is the canonical entry point; it wires `ConfigManager`, `PluginManager`, and `ExecutionContext`, exposing `list`, `execute`, `status`, and `ask` commands.
- Configuration lives in `config/plugins.yml`: `global.plugin_directories` controls discovery, `plugins.enabled` defines runtime order, and each plugin section mirrors the Python class name.
- Major plugin families: `plugins/os` (RHEL/Rocky/CentOS), `plugins/cloud` (Hetzner, Equinix), `plugins/services` (AI assistant, log analysis, vault integration), and `plugins/environments` (deployment contexts).

## PydanticAI Orchestrator (ADR-0063, ADR-0066)

The AI Assistant now includes a **PydanticAI-based orchestrator** for intent-based infrastructure deployment:

- **Manager Agent**: Analyzes user intent, finds matching DAGs, creates execution plans
- **Developer Agent**: Validates DAGs, checks prerequisites, handles execution
- **Observer Agent**: Monitors DAG runs, detects shadow errors, provides status updates

### Orchestrator Endpoints (port 8080)

| Endpoint                      | Method | Purpose                                        |
| ----------------------------- | ------ | ---------------------------------------------- |
| `/orchestrator/status`        | GET    | Check orchestrator availability and API keys   |
| `/orchestrator/dags`          | GET    | List discovered DAGs from airflow/dags/        |
| `/orchestrator/intent`        | POST   | Natural language deployment (main entry point) |
| `/orchestrator/observe`       | POST   | Monitor DAG run status with Observer Agent     |
| `/orchestrator/shadow-errors` | GET    | Check for shadow failures in executions        |

### Example: Intent-Based Deployment

```bash
# Deploy FreeIPA using natural language
curl -X POST http://localhost:8080/orchestrator/intent \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "Deploy FreeIPA server for identity management",
    "params": {"vm_name": "freeipa", "action": "create"},
    "auto_approve": true,
    "auto_execute": true
  }'

# Monitor with Observer Agent
curl -X POST "http://localhost:8080/orchestrator/observe?dag_id=freeipa_deployment"
```

### Environment Variables for PydanticAI

```bash
OPENROUTER_API_KEY=sk-or-...     # Required: LLM provider for agents
PYDANTICAI_MODEL=openai/gpt-4o   # Optional: Override default model
USE_LOCAL_MODEL=false            # Skip local llama.cpp model download
```

## Day-to-Day Workflows

- **Environment bootstrap**: `./deploy-qubinode.sh` (or `./scripts/development/deploy-qubinode.sh`) is the modern one-shot deployment entry point; handles plugin orchestration, AI assistant setup, and post-deployment checks. Legacy `qubinode_navigator_legacy.sh` still available for vault-integrated advanced deployments.
- **Execution images**: `make install-ansible-navigator` and `make build-image` (see `Makefile`) install the required ansible-navigator ≥25.5.0 and build the `qubinode-installer` execution environment via ansible-builder.
- **Navigator config**: `make copy-navigator` syncs `ansible-navigator/release-ansible-navigator.yml` into `~/.ansible-navigator.yml`; keep SOURCE/INSTALL paths aligned when relocating repos.
- **Plugin runs**: `python3 qubinode_cli.py execute --plugins RHEL10Plugin HetznerDeploymentPlugin --inventory localhost` executes in dependency order with the config defaults.
- **MCP validation**: `make mcp-install` pulls `tosin2013.mcp_audit`; `make test-mcp`, `test-mcp-ai`, or `test-mcp-airflow` (see `tests/mcp/*.yml`) run Ansible-based MCP audits and emit Markdown summaries.
- **Python tests**: lightweight validation still uses `python3 -m pytest tests/unit` or targeted plugin suites (mirrors root README guidance).
- **Development scripts** (`scripts/development/`): `setup_modernized.sh` prepares ansible-navigator environments, `deploy-qubinode.sh` is the primary one-shot deployment entry point, and `serve-docs-with-podman.sh` runs the docs site inside Podman—favor these helpers instead of re-implementing their logic.

## Plugin & Config Conventions

- Keep plugin names/class names synchronized with `config/plugins.yml`; enabling a plugin without matching class breaks dependency resolution in `core/plugin_manager.py`.
- Always return `SystemState` snapshots with Python primitives; avoid non-serializable objects since comparisons power idempotency short-circuiting.
- Use `get_dependencies()` to express ordering (e.g., deployment plugins can depend on OS prep plugins); the topological sort in `PluginManager._resolve_dependencies` stops execution if requirements go missing.
- Build `ExecutionContext`-aware behavior (inventory, environment, `context.config` overrides) rather than reading globals; CLI and future MCP servers rely on that contract.
- Emit actionable `PluginResult.data` (e.g., installed packages, versions) so `qubinode_cli` status output stays informative and downstream analytics in `core/analytics_engine.py` can consume the metadata.

## AI Assistant & MCP Services

- `ai-assistant/` is a standalone FastAPI service with **dual architecture**:
  - **Local LLM** (optional): llama.cpp + IBM Granite 4B for offline RAG queries
  - **PydanticAI Orchestrator** (ADR-0063): Cloud LLM agents for intent-based deployment
- Build via `ai-assistant/scripts/build.sh`, run with Podman (`sudo podman run ... localhost/qubinode-ai-assistant:latest`).
- **Key endpoints**:
  - `/health` - Service health check
  - `/chat` - RAG-powered chat (local or cloud LLM)
  - `/orchestrator/intent` - **PydanticAI intent-based deployment** (primary interface)
  - `/orchestrator/observe` - DAG monitoring with Observer Agent
  - `/orchestrator/dags` - DAG discovery from airflow/dags/
- `ai-assistant/mcp_server*.py` expose MCP tools: `query_documents`, `chat_with_context`, `get_project_status`, and `ask_qubinode`.
- The `AIAssistantPlugin` (`plugins/services/ai_assistant_plugin.py`) checks health at `ai_service_url`, can auto-start the container (`auto_start: true`), and surfaces log-analysis helpers to other plugins.
- `qubinode_cli.py ask "question"` tunnels directly into the AI Assistant's `/chat`; scripts should reuse this HTTP API rather than shelling out to CLI helpers.

### PydanticAI Agent Architecture

```
User Intent ("Deploy FreeIPA")
        │
        ▼
┌───────────────────┐
│  Manager Agent    │ → Analyzes intent, finds DAG, creates plan
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ Developer Agent   │ → Validates DAG, checks prerequisites
└─────────┬─────────┘
          ▼
┌───────────────────┐
│  Airflow DAG      │ → Executes via airflow trigger
└─────────┬─────────┘
          ▼
┌───────────────────┐
│  Observer Agent   │ → Monitors status, detects shadow errors
└───────────────────┘
```

## Airflow Orchestration Layer

- `airflow/` implements ADR-0036/0037 by bundling docker/podman-compose stacks, DAGs, and custom operators under `airflow/plugins/qubinode/` (e.g., `operators.py`, `sensors.py`, `hooks.py`).
- Feature flag `ENABLE_AIRFLOW` plus credentials live in `airflow/config/airflow.env`; pods start with `podman-compose up -d` (preferred on RHEL) or `docker-compose up -d`.
- DAGs assume kcli + AI assistant availability; keep DAG-side env vars synced with the main repo `.env` to avoid MCP auth failures.
- Airflow MCP server runs on 8889 (see `airflow/start-mcp-services.sh`) and is covered by `tests/mcp/test_airflow_mcp.yml`; coordination scripts live in `airflow/scripts/`.

## Documentation & Decision Records

- Project docs are Just-the-Docs Jekyll site inside `docs/`; run `cd docs && bundle install && bundle exec jekyll serve` to preview.
- ADRs (`docs/adrs/*.md`) capture design rationale referenced throughout code comments (e.g., ADR-0026 for RHEL10 breaking changes, ADR-0028 for plugins, ADR-0036/0037 for Airflow).
- The AI assistant README (`ai-assistant/README.md`) and Airflow README (`airflow/README.md`) contain authoritative configuration matrices—link to them when adding new automation so instructions stay centralized.

## Gotchas

- Most shell scripts assume Podman (not Docker) and RHEL-style paths; when targeting other hosts update both script shebangs and the instructions in `README.md` to avoid confusing contributors.
- Secrets (Vault tokens, MCP API keys) are loaded from `.env`/`setup-vault-integration.sh`; never hardcode them—reference `VaultIntegrationPlugin` defaults and environment variable names documented there.
- Tests expect AI/Airflow services reachable on localhost; if you change ports, adjust `config/plugins.yml`, `tests/mcp/*.yml`, and the respective README callouts together.
