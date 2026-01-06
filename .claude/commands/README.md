# Qubinode Navigator - Claude Code Custom Commands

Custom slash commands for managing Qubinode Navigator infrastructure using [Claude Code](https://claude.ai/code).

## Installation

These commands are automatically available when you run Claude Code from the qubinode_navigator directory:

```bash
cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}
claude
```

## Path Configuration

Commands use `${QUBINODE_HOME:-$HOME/qubinode_navigator}` for flexible path resolution:

```bash
# If installed in non-standard location, set QUBINODE_HOME
export QUBINODE_HOME=/custom/path/qubinode_navigator

# Default: Uses $HOME/qubinode_navigator (works for both root and regular users)
```

## Available Commands

### DAG Management

| Command                        | Description                              |
| ------------------------------ | ---------------------------------------- |
| `/dag-list`                    | List all Airflow DAGs with status        |
| `/dag-info <dag-id>`           | Get detailed information about a DAG     |
| `/dag-trigger <dag-id>`        | Trigger a DAG execution                  |
| `/dag-validate`                | Validate DAG syntax and check for errors |
| `/dag-scaffold <requirements>` | Generate a new DAG from template         |

**Examples:**

```
/dag-list
/dag-info ocp_initial_deployment
/dag-trigger rag_document_ingestion
/dag-validate
/dag-scaffold deploy FreeIPA server with DNS
```

### VM Management

| Command                  | Description                             |
| ------------------------ | --------------------------------------- |
| `/vm-list`               | List all virtual machines               |
| `/vm-info <vm-name>`     | Get VM details (CPU, memory, IP)        |
| `/vm-create <specs>`     | Create a new virtual machine            |
| `/vm-delete <vm-name>`   | Delete a virtual machine                |
| `/vm-preflight <config>` | Run preflight checks before VM creation |

**Examples:**

```
/vm-list
/vm-info freeipa-server
/vm-create centos-stream-10 with 4GB RAM and 2 CPUs
/vm-preflight ocp-bootstrap
```

### Infrastructure

| Command                          | Description                             |
| -------------------------------- | --------------------------------------- |
| `/infra-cert-request <hostname>` | Request a TLS certificate               |
| `/infra-cert-list`               | List all managed certificates           |
| `/infra-dns-add <hostname> <ip>` | Add a DNS record                        |
| `/infra-dns-check <hostname>`    | Check DNS resolution                    |
| `/infra-status`                  | Check all infrastructure service status |

**Examples:**

```
/infra-cert-request api.example.com
/infra-cert-list
/infra-dns-add myvm.lab.local 192.168.122.50
/infra-dns-check freeipa.lab.local
/infra-status
```

### RAG Knowledge Base

| Command                   | Description                    |
| ------------------------- | ------------------------------ |
| `/rag-query <question>`   | Query the knowledge base       |
| `/rag-ingest <file-path>` | Ingest a document              |
| `/rag-stats`              | Show knowledge base statistics |

**Examples:**

```
/rag-query how do I deploy OpenShift disconnected
/rag-ingest docs/new-procedure.md
/rag-stats
```

### Diagnostics

| Command                 | Description                           |
| ----------------------- | ------------------------------------- |
| `/diagnose <problem>`   | AI-powered issue diagnosis            |
| `/troubleshoot <issue>` | Interactive troubleshooting assistant |

**Examples:**

```
/diagnose DAG not appearing in Airflow UI
/troubleshoot VM won't start after reboot
```

### GitHub Repository Maintenance

| Command                       | Description                                    |
| ----------------------------- | ---------------------------------------------- |
| `/github-resolve failures`    | Analyze and fix failed GitHub Actions runs     |
| `/github-resolve prs`         | Review and fix PRs with failed checks          |
| `/github-resolve dependabot`  | Process and merge Dependabot PRs strategically |
| `/github-resolve triage`      | Full triage across all issue types             |
| `/github-resolve <pr-number>` | Investigate specific PR or run                 |

**Examples:**

```
/github-resolve failures
/github-resolve dependabot
/github-resolve triage
/github-resolve 42
```

### System Operations

| Command                  | Description                          |
| ------------------------ | ------------------------------------ |
| `/system-deploy`         | Deploy or redeploy the stack         |
| `/system-logs <service>` | View service logs                    |
| `/system-health`         | Run comprehensive health checks      |
| `/system-backup`         | Backup configuration and data        |
| `/system-adr <topic>`    | Search Architecture Decision Records |

**Examples:**

```
/system-deploy
/system-logs airflow-scheduler
/system-health
/system-backup
/system-adr DAG development standards
```

## Command Format

Claude Code commands use markdown files with YAML frontmatter:

```markdown
---
description: Brief description shown in /help
allowed-tools: Bash(command:*), Read, Write
argument-hint: [arg1] [arg2]
---

# Command Title

Command instructions and shell commands.
!`shell command here`

Reference files:
@path/to/file.md

Use arguments:
$ARGUMENTS (all args) or $1, $2 (positional)
```

## Architecture Reference

These commands integrate with:

| Component    | Port | Purpose                       |
| ------------ | ---- | ----------------------------- |
| AI Assistant | 8080 | PydanticAI orchestrator + RAG |
| Airflow UI   | 8888 | DAG management                |
| MCP Server   | 8889 | Tool API                      |
| PostgreSQL   | 5432 | Metadata and vectors          |
| Marquez      | 5001 | Lineage tracking              |
| Marquez Web  | 3000 | Lineage visualization         |

## PydanticAI Orchestrator (ADR-0063, ADR-0066)

The AI Assistant includes a multi-agent system for **intent-based deployment**:

### Orchestrator Endpoints

| Endpoint                | Method | Purpose                                      |
| ----------------------- | ------ | -------------------------------------------- |
| `/orchestrator/status`  | GET    | Check orchestrator availability and API keys |
| `/orchestrator/dags`    | GET    | List discovered DAGs                         |
| `/orchestrator/intent`  | POST   | Natural language deployment (main entry)     |
| `/orchestrator/observe` | POST   | Monitor DAG run with Observer Agent          |

### Agent Architecture

- **Manager Agent**: Analyzes intent, finds DAGs, creates execution plans
- **Developer Agent**: Validates DAGs, checks prerequisites
- **Observer Agent**: Monitors runs, detects shadow errors

### Example Usage

```bash
# Deploy via natural language
curl -X POST http://localhost:8080/orchestrator/intent \
  -H "Content-Type: application/json" \
  -d '{"intent": "Deploy FreeIPA", "auto_execute": true}'

# Monitor deployment
curl -X POST "http://localhost:8080/orchestrator/observe?dag_id=freeipa_deployment"
```

## Comparison: Claude Code vs Gemini CLI

| Feature         | Claude Code        | Gemini CLI        |
| --------------- | ------------------ | ----------------- |
| File format     | Markdown (.md)     | TOML (.toml)      |
| Shell execution | `` !`cmd` ``       | `!{cmd}`          |
| File reference  | `@path/file`       | `@{path/file}`    |
| Arguments       | `$ARGUMENTS`, `$1` | `{{args}}`        |
| Namespacing     | Hyphens (dag-list) | Colons (dag:list) |

## Related Documentation

- [ADR-0045](../../docs/adrs/adr-0045-dag-development-standards.md): DAG Development Standards
- [ADR-0047](../../docs/adrs/adr-0047-qubinode-pipelines-integration.md): Pipeline Integration
- [Airflow README](../../airflow/README.md): Airflow setup guide
- [Gemini CLI Commands](../../.gemini/commands/README.md): Equivalent Gemini commands

## Code Quality Hooks

Claude Code hooks automatically enforce code quality standards. These hooks run on file operations.

### Active Hooks

| Hook                 | Trigger                  | Purpose                                   |
| -------------------- | ------------------------ | ----------------------------------------- |
| `code-quality.py`    | PostToolUse (Write/Edit) | Routes to appropriate linter by file type |
| `pre-write-check.sh` | PreToolUse (Write/Edit)  | Blocks writes to sensitive files          |

### Linting by File Type

| File Type                  | Linter     | Actions                    |
| -------------------------- | ---------- | -------------------------- |
| Python (`.py`)             | ruff       | Auto-fix + format          |
| Shell (`.sh`, `.bash`)     | shellcheck | Lint warnings              |
| Markdown (`.md`)           | custom     | Language tags + formatting |
| YAML (`.yml`, `.yaml`)     | yamllint   | Lint warnings              |
| JSON (`.json`)             | built-in   | Syntax validation          |
| DAGs (`airflow/dags/*.py`) | ADR-0045   | Compliance validation      |

### Hook Configuration

Hooks are configured in `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/code-quality.py",
            "timeout": 45
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/pre-write-check.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

### Protected Files

The `pre-write-check.sh` hook blocks writes to:

- `.env`, `.env.local` - Environment files
- `credentials.json`, `secrets.yaml` - Secret files
- `*.pem`, `*.key` - Certificates and keys
- `pull-secret.json` - OpenShift secrets
- `vault.yml` - Vault configuration
- Lock files (warns but doesn't block)

### Individual Hook Scripts

| Script               | Purpose                                    |
| -------------------- | ------------------------------------------ |
| `python-lint.sh`     | Standalone Python linting with ruff        |
| `bash-lint.sh`       | Standalone Bash linting with shellcheck    |
| `dag-validate.sh`    | Standalone DAG validation per ADR-0045     |
| `markdown-format.py` | Markdown formatting and language detection |

### Adding Custom Hooks

1. Create script in `.claude/hooks/`
1. Make executable: `chmod +x .claude/hooks/my-hook.sh`
1. Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/my-hook.sh"
          }
        ]
      }
    ]
  }
}
```

### Hook Exit Codes

| Code  | Meaning | Behavior                              |
| ----- | ------- | ------------------------------------- |
| 0     | Success | Continue, show stdout in verbose mode |
| 2     | Block   | Stop operation, show stderr to Claude |
| Other | Warning | Continue, show stderr in verbose mode |

## Extending Commands

To add new commands:

1. Create a `.md` file in `.claude/commands/`
1. Add YAML frontmatter with `description` and `allowed-tools`
1. Use `argument-hint` for expected arguments
1. Include shell commands with `` !`...` ``
1. Reference files with `@path/to/file`

Example:

```markdown
---
description: My custom command
allowed-tools: Bash(echo:*)
argument-hint: [name]
---

# My Command

Hello $1!
!`echo "Processing $1..."`

See configuration:
@config/settings.yml
```
