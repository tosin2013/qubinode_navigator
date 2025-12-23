# ADR-0062: External Project Integration Guide

**Status:** Proposed
**Date:** 2025-12-05
**Authors:** Qubinode Team
**Related:** ADR-0045, ADR-0046, ADR-0047, ADR-0061

## Context and Problem Statement

External projects (such as ocp4-disconnected-helper, freeipa-workshop-deployer, and user-created automation projects) need clear guidance on how to integrate with the Qubinode ecosystem. Current documentation is fragmented across multiple ADRs, leading to confusion about:

1. Where to contribute DAGs
1. How to structure automation for Airflow orchestration
1. What standards must be followed
1. How to test before submitting contributions

This ADR provides a comprehensive integration guide for external projects.

## Decision

Establish a standardized integration pattern for external projects based on **PR-based contribution** to **qubinode-pipelines**.

## Integration Guide

### 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        YOUR PROJECT                                      │
│              (e.g., ocp4-disconnected-helper)                           │
│                                                                          │
│  You maintain:                                                           │
│  - Domain-specific playbooks and scripts                                 │
│  - Configuration files and templates                                     │
│  - Documentation for your automation                                     │
│                                                                          │
│  You contribute:                                                         │
│  - DAGs to qubinode-pipelines (via PR)                                  │
│  - Deployment scripts if needed                                          │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              │ PR to qubinode-pipelines
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      QUBINODE-PIPELINES                                  │
│                (github.com/Qubinode/qubinode-pipelines)                 │
│                                                                          │
│  Accepts:                                                                │
│  - Deployment DAGs (dags/<category>/*.py)                               │
│  - Deployment scripts (scripts/<component>/deploy.sh)                    │
│  - Registry updates (dags/registry.yaml)                                │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              │ Volume mount
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     QUBINODE_NAVIGATOR                                   │
│                     (runtime platform)                                   │
│                                                                          │
│  Provides:                                                               │
│  - Airflow execution environment                                         │
│  - DAG validation tools                                                  │
│  - UI for triggering and monitoring                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2. What You Own vs What You Contribute

| Type              | Your Project Owns    | You Contribute To                         |
| ----------------- | -------------------- | ----------------------------------------- |
| Ansible playbooks | Yes                  | No (stay in your repo)                    |
| Shell scripts     | Yes                  | qubinode-pipelines/scripts/ (if reusable) |
| DAG files         | No (develop locally) | qubinode-pipelines/dags/                  |
| Configuration     | Yes                  | No (reference via volume mounts)          |
| Documentation     | Yes                  | qubinode-pipelines README (brief)         |

### 3. DAG Contribution Workflow

#### Step 1: Develop Locally

Create your DAG in your project for development and testing:

```
your-project/
├── playbooks/
│   └── deploy-component.yml
├── airflow/
│   └── dags/                    # Local development
│       └── your_component.py
└── tests/
```

#### Step 2: Follow DAG Standards (ADR-0045)

Your DAG MUST comply with these standards:

```python
"""
DAG: your_component_deployment
Description: Deploy Your Component via Qubinode
Category: infrastructure  # or: ocp, networking, storage
Contributed by: your-project-name

This DAG calls playbooks from your-project via SSH to the host.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

# Standard default args
default_args = {
    'owner': 'qubinode',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=3),
}

# DAG ID MUST match filename (snake_case)
dag = DAG(
    'your_component_deployment',  # Matches filename: your_component_deployment.py
    default_args=default_args,
    description='Deploy Your Component',
    schedule=None,
    catchup=False,
    tags=['qubinode', 'your-category'],
    params={
        'action': 'create',
        # Add your parameters here
    },
)

# Use SSH to execute on host (ADR-0046)
deploy = BashOperator(
    task_id='deploy_component',
    bash_command="""
    set -euo pipefail

    ACTION="{{ params.action }}"

    # Execute on host via SSH
    ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \
        "cd /path/to/your-project && \
         export ACTION=$ACTION && \
         ansible-playbook playbooks/deploy-component.yml"

    echo "[OK] Component deployment completed"
    """,
    dag=dag,
)
```

#### Step 3: Validate Before Submitting

Clone qubinode_navigator and use validation tools:

```bash
# Clone if you haven't
git clone https://github.com/Qubinode/qubinode_navigator.git

# Validate your DAG
./qubinode_navigator/airflow/scripts/validate-dag.sh your-project/airflow/dags/your_component.py

# Run linting
./qubinode_navigator/airflow/scripts/lint-dags.sh your-project/airflow/dags/your_component.py
```

**Validation Checklist:**

- [ ] DAG file uses snake_case naming
- [ ] DAG ID matches filename exactly
- [ ] Uses `"""` (triple double quotes) for bash_command, NEVER `'''`
- [ ] No Unicode/emoji in bash commands (use `[OK]`, `[ERROR]`, `[WARN]`, `[INFO]`)
- [ ] No string concatenation in bash_command
- [ ] SSH pattern used for host execution (ADR-0046)
- [ ] Python syntax check passes
- [ ] Airflow import check passes

#### Step 4: Submit PR to qubinode-pipelines

```bash
# Fork and clone qubinode-pipelines
git clone https://github.com/YOUR-USERNAME/qubinode-pipelines.git
cd qubinode-pipelines

# Create branch
git checkout -b add-your-component-dag

# Copy your validated DAG
cp /path/to/your-project/airflow/dags/your_component.py dags/infrastructure/

# Update registry (optional but recommended)
# Edit dags/registry.yaml to add your DAG

# Commit and push
git add .
git commit -m "feat(dags): Add your_component_deployment DAG

Contributed by: your-project-name
Category: infrastructure
Calls: your-project playbooks via SSH

Tested with validate-dag.sh and lint-dags.sh"

git push origin add-your-component-dag

# Create PR via GitHub
```

#### Step 5: PR Review Process

Your PR will be reviewed for:

1. **ADR-0045 compliance** - DAG standards
1. **ADR-0046 compliance** - SSH execution pattern
1. **Security** - No hardcoded credentials, safe script execution
1. **Documentation** - Clear docstring explaining the DAG
1. **Testing** - Evidence of validation

**Automated CI Validation:**

When you submit a PR, the `airflow-validate.yml` workflow automatically:

- Clones your PR branch
- Validates Python syntax
- Runs ADR-0045/ADR-0046 compliance checks (lint-dags.sh)
- Tests Airflow DagBag imports
- Reports results in the PR checks

You can also test against a specific qubinode-pipelines branch before submitting:

```bash
# Test your qubinode_navigator changes against a specific pipelines branch
gh workflow run airflow-validate.yml -f pipelines_ref=your-feature-branch
```

### 4. DAG Categories

Place your DAG in the appropriate category directory:

| Category       | Directory              | Examples                                        |
| -------------- | ---------------------- | ----------------------------------------------- |
| OCP/OpenShift  | `dags/ocp/`            | ocp_initial_deployment.py, ocp_registry_sync.py |
| Infrastructure | `dags/infrastructure/` | freeipa_deployment.py, vyos_router.py           |
| Networking     | `dags/networking/`     | dns_setup.py, firewall_config.py                |
| Storage        | `dags/storage/`        | nfs_server.py, ceph_deployment.py               |
| Security       | `dags/security/`       | step_ca_operations.py, vault_setup.py           |

### 5. Calling Your Playbooks

Your DAG should call your project's playbooks via SSH:

```python
# Pattern 1: Project cloned on host
bash_command="""
ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \
    "cd /root/your-project && \
     ansible-playbook playbooks/deploy.yml -e action={{ params.action }}"
"""

# Pattern 2: Using ansible-navigator (recommended)
bash_command="""
ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \
    "cd /root/your-project && \
     ansible-navigator run playbooks/deploy.yml \
         --mode stdout \
         --pull-policy missing \
         -e action={{ params.action }}"
"""

# Pattern 3: Calling a deploy.sh script
bash_command="""
ssh -o StrictHostKeyChecking=no -o LogLevel=ERROR root@localhost \
    "export ACTION={{ params.action }} && \
     cd /opt/qubinode-pipelines/scripts/your-component && \
     ./deploy.sh"
"""
```

### 6. Environment Variables and Secrets

**DO:**

- Use Airflow params for user-configurable values
- Use Airflow Variables for shared configuration
- Use Airflow Connections for credentials
- Reference environment files on the host

**DON'T:**

- Hardcode credentials in DAGs
- Include secrets in bash_command strings
- Commit .env files with real values

```python
# Good: Using params
bash_command="""
ACTION="{{ params.action }}"
COMPONENT_VERSION="{{ params.version }}"

ssh root@localhost \
    "export ACTION=$ACTION VERSION=$COMPONENT_VERSION && \
     ./deploy.sh"
"""

# Good: Referencing host environment
bash_command="""
ssh root@localhost \
    "source /opt/qubinode-pipelines/scripts/helper_scripts/default.env && \
     ./deploy.sh"
"""

# Bad: Hardcoded credentials (NEVER do this)
bash_command="""
ssh root@localhost \
    "export PASSWORD='secret123' && ./deploy.sh"  # NEVER!
"""
```

### 7. Testing Your Integration

Before submitting, test your DAG works with qubinode_navigator:

```bash
# 1. Start qubinode_navigator Airflow
cd /opt/qubinode_navigator
./deploy-qubinode-with-airflow.sh

# 2. Copy your DAG to test location
cp your-dag.py /opt/qubinode_navigator/airflow/dags/

# 3. Wait for Airflow to detect (or restart scheduler)
docker compose -f airflow/docker-compose.yml restart airflow-scheduler

# 4. Access Airflow UI
open http://localhost:8888

# 5. Trigger your DAG manually and verify execution

# 6. Check logs for errors
docker compose -f airflow/docker-compose.yml logs -f airflow-worker
```

### 8. Updating Your DAGs

When your project evolves and DAGs need updates:

1. **Minor updates** (parameter changes, bug fixes): Submit PR to qubinode-pipelines
1. **Breaking changes**: Increment version in DAG ID or create new DAG
1. **Deprecation**: Mark old DAG with `# DEPRECATED: Use new_dag_name instead`

### 9. Version Compatibility

Your DAG should document compatibility:

```python
"""
DAG: your_component_deployment
Version: 1.2.0
Requires:
  - qubinode_navigator >= 1.0.0
  - your-project >= 2.0.0
  - Ansible >= 2.14

Breaking changes from 1.1.0:
  - Renamed param 'server' to 'target_server'
"""
```

### 10. Common Mistakes to Avoid

| Mistake                      | Problem                               | Solution                     |
| ---------------------------- | ------------------------------------- | ---------------------------- |
| Using `'''` for bash_command | Breaks Jinja templating               | Always use `"""`             |
| Running Ansible in container | Version mismatch, missing collections | Use SSH to host              |
| String concatenation         | Unpredictable behavior                | Use single heredoc string    |
| Unicode in output            | Breaks logging                        | Use ASCII: `[OK]`, `[ERROR]` |
| Not validating               | DAG breaks in production              | Run validate-dag.sh          |

## Consequences

### Positive

- External projects have clear integration path
- Consistent DAG quality through validation
- Centralized DAG discovery in qubinode-pipelines
- Contributors maintain ownership of domain logic

### Negative

- Two-step process (develop locally, contribute upstream)
- PR review adds latency to DAG availability
- External projects must track qubinode standards

## FAQ

### Q: Can I keep DAGs in my own repository?

A: You can develop and test DAGs locally, but for integration with qubinode_navigator, they must be contributed to qubinode-pipelines. This ensures:

- Consistent validation
- Centralized discovery
- Community visibility

### Q: What if my DAG needs custom Python dependencies?

A: Document dependencies in your PR. If widely needed, they may be added to the Airflow container. Otherwise, use SSH to run Python on the host.

### Q: How do I handle DAG-specific secrets?

A: Use Airflow Connections and Variables, accessed via Jinja templating:

```python
"{{ conn.my_connection.password }}"
"{{ var.value.my_variable }}"
```

### Q: Can I use the Airflow API instead of SSH?

A: The SSH pattern (ADR-0046) is required for Ansible execution to ensure consistent behavior with CLI usage. API calls are acceptable for Airflow-native operations.

## References

- ADR-0045: Airflow DAG Development Standards
- ADR-0046: DAG Validation Pipeline and Host-Based Execution
- ADR-0047: kcli-pipelines as DAG Source Repository (superseded by ADR-0061)
- ADR-0061: Multi-Repository Architecture
- [Airflow BashOperator Documentation](https://airflow.apache.org/docs/apache-airflow/stable/howto/operator/bash.html)

______________________________________________________________________

**This guide enables seamless integration for external projects into the Qubinode ecosystem.**
