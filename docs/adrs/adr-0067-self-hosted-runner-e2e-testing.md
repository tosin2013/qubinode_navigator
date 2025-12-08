# ADR-0067: Self-Hosted Runner E2E Testing with One-Shot Deployment

## Status

**ACCEPTED** - Implementation Started (2025-12-08)

## Context

The Qubinode Navigator project needs automated end-to-end testing that:

1. Deploys the complete stack including KVM/libvirt for VM creation
1. Runs on a schedule (weekly) and on Dependabot PRs
1. Validates the Smart Pipeline (ADR-0066) shadow error detection
1. Provides confidence that releases work correctly

### Current State

We have `deploy-qubinode.sh` which is a comprehensive one-shot script (~2000 lines) that:

- Detects OS (RHEL 9/10, CentOS Stream 9/10, Rocky 9, AlmaLinux 9)
- Configures KVM/libvirt hypervisor
- Deploys AI Assistant container
- Optionally deploys Airflow orchestration
- Configures SSH, firewall, DNS
- Sets up Ansible Navigator and vault

### Gap Analysis

| Component      | Current State          | E2E Requirement              |
| -------------- | ---------------------- | ---------------------------- |
| KVM/libvirt    | Deployed by script     | Needs VM creation validation |
| Airflow        | Optional flag          | Required for Smart Pipeline  |
| FreeIPA VM     | Not deployed           | Required as test workload    |
| Smart Pipeline | Implemented (ADR-0066) | Needs E2E validation         |
| OpenLineage    | Implemented            | Needs Marquez validation     |

## Decision

### 1. Use Existing `deploy-qubinode.sh` with E2E Profile

The existing `deploy-qubinode.sh` script has been enhanced with a new `BUILD_AI_ASSISTANT_FROM_SOURCE` option that builds the AI Assistant container locally with all PydanticAI + Smart Pipeline dependencies.

```bash
# E2E Testing Configuration
export QUBINODE_DOMAIN="e2e.qubinode.local"
export QUBINODE_ADMIN_USER="admin"
export QUBINODE_CLUSTER_NAME="e2e-test"
export QUBINODE_DEPLOYMENT_MODE="production"
export QUBINODE_ENABLE_AI_ASSISTANT=true
export QUBINODE_ENABLE_AIRFLOW=true
export QUBINODE_ENABLE_NGINX_PROXY=true
export BUILD_AI_ASSISTANT_FROM_SOURCE=true  # NEW: Build with PydanticAI + Smart Pipeline
export SSH_PASSWORD="${E2E_SSH_PASSWORD}"
export CICD_PIPELINE=true
export INVENTORY=localhost

# PydanticAI Model Configuration (via OpenRouter)
# Format: openrouter:<provider>/<model> (note the COLON, not slash)
export OPENROUTER_API_KEY="${OPENROUTER_API_KEY}"
export MANAGER_MODEL="openrouter:anthropic/claude-3.5-sonnet"
export DEVELOPER_MODEL="openrouter:google/gemini-2.0-flash-exp"
export PYDANTICAI_MODEL="openrouter:anthropic/claude-3-haiku"

# Run deployment
./deploy-qubinode.sh
```

#### PydanticAI Model Format

**IMPORTANT**: PydanticAI uses `provider:model` format with a **colon** separator, not the LiteLLM slash format.

| Provider   | Format                          | Example                                  |
| ---------- | ------------------------------- | ---------------------------------------- |
| OpenRouter | `openrouter:<provider>/<model>` | `openrouter:anthropic/claude-3.5-sonnet` |
| Google     | `google-gla:<model>`            | `google-gla:gemini-2.0-flash`            |
| OpenAI     | `openai:<model>`                | `openai:gpt-4o`                          |
| Anthropic  | `anthropic:<model>`             | `anthropic:claude-3-5-sonnet-latest`     |
| Ollama     | `ollama:<model>`                | `ollama:granite3.3:8b`                   |
| Groq       | `groq:<model>`                  | `groq:llama-3.3-70b-versatile`           |

See `.env.example` for full model configuration documentation.

#### Key Changes to deploy-qubinode.sh

1. **New environment variable**: `BUILD_AI_ASSISTANT_FROM_SOURCE`

   - When `true`: Builds AI Assistant from `ai-assistant/` directory with all dependencies
   - When `false` (default): Pulls pre-built image from `quay.io/takinosh/qubinode-ai-assistant`

1. **Enhanced container startup**: Adds environment variables for OpenLineage/Marquez integration

   - `MARQUEZ_API_URL=http://host.containers.internal:5001`
   - `AIRFLOW_API_URL=http://host.containers.internal:8888`

1. **Data persistence**: Mounts `ai-assistant/data/` for RAG document storage

### 2. Self-Hosted Runner Requirements

**Hardware:**

- CPU: 8+ cores (for parallel VM operations)
- RAM: 32GB minimum (Airflow + containers + 1 FreeIPA VM)
- Disk: 200GB SSD (VM images, container layers)
- Network: Internet access for package downloads

**Software:**

- OS: CentOS Stream 10 or RHEL 10 (matching production)
- Nested virtualization enabled (if VM-based runner)
- GitHub Actions runner installed

**Estimated Costs (Hetzner):**

- AX41-NVMe: ~$50/month (AMD Ryzen 5 3600, 64GB RAM, 512GB NVMe)
- Suitable for weekly E2E testing

### 3. E2E Test Workflow

```yaml
name: E2E Integration Test

on:
  schedule:
    - cron: '0 3 * * 0'  # Weekly Sunday 3am UTC
  pull_request:
    types: [opened, synchronize]
    paths:
      - 'airflow/**'
      - 'ai-assistant/**'
      - 'deploy-*.sh'
  workflow_dispatch:
    inputs:
      deploy_freeipa:
        description: 'Deploy FreeIPA VM for full test'
        type: boolean
        default: true

jobs:
  e2e-test:
    runs-on: self-hosted
    timeout-minutes: 90

    steps:
      # Phase 1: Deploy Infrastructure
      - name: Deploy Qubinode Stack
        run: |
          source .github/workflows/e2e-env.sh
          ./deploy-qubinode.sh

      # Phase 2: Deploy Test VM via Smart Pipeline
      - name: Trigger FreeIPA Deployment via AI Assistant
        run: |
          curl -X POST http://localhost:8080/orchestrator/execute \
            -H "Content-Type: application/json" \
            -d '{
              "user_intent": "Deploy FreeIPA for E2E testing",
              "auto_approve": true,
              "auto_execute": true
            }'

      # Phase 3: Validate Smart Pipeline
      - name: Check Shadow Errors
        run: |
          ERRORS=$(curl -s http://localhost:8080/orchestrator/shadow-errors)
          if echo "$ERRORS" | jq -e '.total_shadow_failures > 0'; then
            echo "Shadow errors detected!"
            echo "$ERRORS" | jq .
            exit 1
          fi

      # Phase 4: Validate OpenLineage
      - name: Check Marquez Lineage
        run: |
          curl -s http://localhost:5001/api/v1/namespaces/qubinode/jobs | jq .

      # Phase 5: Cleanup
      - name: Delete Test VMs
        if: always()
        run: |
          kcli delete vm freeipa -y || true
```

### 4. Dependabot Integration

When Dependabot creates PRs, the E2E workflow:

1. Runs full deployment with updated dependencies
1. Validates no regressions in Smart Pipeline
1. Checks shadow error detection still works
1. Auto-merges if all checks pass (optional)

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/ai-assistant"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5

  - package-ecosystem: "pip"
    directory: "/airflow"
    schedule:
      interval: "weekly"
```

### 5. Smart Pipeline Validation

The E2E test specifically validates ADR-0066 functionality:

```python
# Expected flow:
# 1. User intent -> AI Assistant
# 2. DAG discovery/creation
# 3. DAG validation (syntax + prerequisites)
# 4. Execution via Airflow
# 5. Shadow error detection
# 6. OpenLineage emission to Marquez
# 7. Manager Agent notification (if errors)
```

## Consequences

### Positive

1. **Confidence in Releases**: Every Dependabot update is validated E2E
1. **Early Bug Detection**: Shadow errors caught before production
1. **Documentation by Example**: E2E workflow documents deployment process
1. **Regression Prevention**: Changes to Smart Pipeline are validated

### Negative

1. **Infrastructure Cost**: ~$50/month for self-hosted runner
1. **Maintenance Overhead**: Runner needs periodic updates
1. **Test Duration**: ~60-90 minutes per full E2E run
1. **Complexity**: Another system to monitor

### Risks

| Risk                           | Mitigation                                      |
| ------------------------------ | ----------------------------------------------- |
| Runner becomes unavailable     | Alert on workflow failures, have backup runner  |
| Tests flaky due to timing      | Implement proper wait/retry logic               |
| Resource exhaustion            | Cleanup step always runs, scheduled maintenance |
| Security of self-hosted runner | Dedicated machine, not shared with production   |

## Implementation Plan

### Phase 1: Runner Setup (Week 1)

- [ ] Provision self-hosted runner (Hetzner AX41 or similar)
- [ ] Install CentOS Stream 10
- [ ] Configure GitHub Actions runner
- [ ] Enable nested virtualization

### Phase 2: E2E Workflow (Week 2)

- [ ] Create `.github/workflows/e2e-test.yml`
- [ ] Create `.github/workflows/e2e-env.sh`
- [ ] Test manual workflow dispatch
- [ ] Add schedule trigger

### Phase 3: Dependabot Integration (Week 3)

- [ ] Create `.github/dependabot.yml`
- [ ] Configure auto-merge rules
- [ ] Test with sample dependency update

### Phase 4: Monitoring (Week 4)

- [ ] Add Slack/Discord notifications for failures
- [ ] Create runner health dashboard
- [ ] Document troubleshooting procedures

## Related ADRs

- [ADR-0066](adr-0066-developer-agent-dag-validation-smart-pipelines.md): Smart Pipeline implementation
- [ADR-0049](adr-0049-multi-agent-llm-memory-architecture.md): OpenLineage/Marquez integration
- [ADR-0055](adr-0055-zero-friction-infrastructure-services.md): Infrastructure deployment

## References

- [GitHub Self-Hosted Runners](https://docs.github.com/en/actions/hosting-your-own-runners)
- [Hetzner Dedicated Servers](https://www.hetzner.com/dedicated-rootserver)
- [Dependabot Configuration](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates)
