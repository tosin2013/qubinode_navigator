# ADR-0046: DAG Validation Pipeline and Host-Based Execution Strategy

## Status
Proposed

## Date
2025-11-27

## Context and Problem Statement

During FreeIPA DAG development, we encountered two significant issues:

### Issue 1: Ansible Version Mismatch
The Airflow container may have a different Ansible version than the host system. This causes:
- Playbook compatibility issues
- Missing collections/modules
- Different behavior between container and host execution
- Maintenance burden of keeping container Ansible in sync with host

### Issue 2: No DAG Validation Before Deployment
Users can deploy DAGs with:
- Syntax errors (Python)
- Bash command issues (Unicode, quoting, PATH)
- Missing dependencies
- Incorrect Jinja templating

These errors are only discovered at runtime, causing failed DAG runs.

## Decision Drivers

* Ansible playbooks should run with the host's Ansible installation
* DAGs should be validated before deployment
* Validation should be automated and easy to use
* Errors should be caught early in the development cycle
* Solution should work in CI/CD pipelines

## Decision Outcome

Implement two complementary solutions:

### Solution 1: SSH-Based Host Execution for Ansible

Instead of running Ansible inside the container, use SSH to execute Ansible on the host.

```python
# Instead of running ansible-playbook directly in container:
bash_command="""
ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -i inventory playbook.yaml
"""

# Use SSH to run on host:
bash_command="""
ssh -o StrictHostKeyChecking=no root@localhost \
    "cd /opt/freeipa-workshop-deployer && \
     ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook \
     -i $INVENTORY_DIR/inventory \
     --extra-vars 'idm_hostname=${IDM_HOSTNAME}' \
     2_ansible_config/deploy_idm.yaml -v"
"""
```

**Benefits:**
- Uses host's Ansible version and collections
- No need to maintain Ansible in container
- Consistent with manual execution
- Access to host's SSH keys and credentials

**Requirements:**
- SSH key from container to host (passwordless)
- Host SSH server running on localhost
- Container must have SSH client installed

### Solution 2: DAG Validation Pipeline

Create a validation script and pre-commit hook for DAG validation.

#### Validation Script: `airflow/scripts/validate-dag.sh`

```bash
#!/bin/bash
# DAG Validation Script
# Usage: ./validate-dag.sh <dag_file.py>

set -e

DAG_FILE="$1"

if [ -z "$DAG_FILE" ]; then
    echo "Usage: $0 <dag_file.py>"
    exit 1
fi

echo "========================================"
echo "DAG Validation: $DAG_FILE"
echo "========================================"

ERRORS=0

# 1. Python Syntax Check
echo -n "[1/6] Python syntax... "
if python3 -c "import ast; ast.parse(open('$DAG_FILE').read())" 2>/dev/null; then
    echo "OK"
else
    echo "FAILED"
    python3 -c "import ast; ast.parse(open('$DAG_FILE').read())"
    ERRORS=$((ERRORS + 1))
fi

# 2. Airflow Import Check
echo -n "[2/6] Airflow imports... "
if python3 -c "
from airflow.models import DagBag
import os
os.chdir('$(dirname $DAG_FILE)')
db = DagBag('.', include_examples=False)
if db.import_errors:
    for dag, error in db.import_errors.items():
        print(f'Error in {dag}: {error}')
    exit(1)
" 2>/dev/null; then
    echo "OK"
else
    echo "FAILED"
    ERRORS=$((ERRORS + 1))
fi

# 3. Unicode Character Check
echo -n "[3/6] Unicode characters... "
if grep -P '[^\x00-\x7F]' "$DAG_FILE" > /dev/null 2>&1; then
    echo "WARNING - Non-ASCII characters found:"
    grep -n -P '[^\x00-\x7F]' "$DAG_FILE" | head -5
    # Warning only, not an error
else
    echo "OK"
fi

# 4. String Concatenation in bash_command Check
echo -n "[4/6] Bash command concatenation... "
if grep -E "bash_command=.*'''\s*\+" "$DAG_FILE" > /dev/null 2>&1; then
    echo "FAILED - String concatenation in bash_command:"
    grep -n -E "bash_command=.*'''\s*\+" "$DAG_FILE"
    ERRORS=$((ERRORS + 1))
else
    echo "OK"
fi

# 5. Deprecated Parameters Check
echo -n "[5/6] Deprecated parameters... "
if grep -E "schedule_interval\s*=" "$DAG_FILE" > /dev/null 2>&1; then
    echo "WARNING - Deprecated 'schedule_interval' found (use 'schedule'):"
    grep -n "schedule_interval" "$DAG_FILE"
else
    echo "OK"
fi

# 6. PATH Export Check (for container execution)
echo -n "[6/6] PATH configuration... "
if grep -q "kcli\|ansible-playbook" "$DAG_FILE"; then
    if grep -q 'export PATH=' "$DAG_FILE"; then
        echo "OK"
    else
        echo "WARNING - Uses kcli/ansible but no PATH export found"
    fi
else
    echo "OK (no kcli/ansible usage)"
fi

echo ""
echo "========================================"
if [ $ERRORS -eq 0 ]; then
    echo "Validation PASSED"
    exit 0
else
    echo "Validation FAILED ($ERRORS errors)"
    exit 1
fi
```

#### Pre-commit Hook: `.pre-commit-config.yaml`

```yaml
repos:
  - repo: local
    hooks:
      - id: validate-airflow-dags
        name: Validate Airflow DAGs
        entry: bash -c 'for f in "$@"; do ./airflow/scripts/validate-dag.sh "$f" || exit 1; done' --
        language: system
        files: ^airflow/dags/.*\.py$
        pass_filenames: true
```

#### GitHub Actions Workflow: `.github/workflows/dag-validation.yml`

```yaml
name: DAG Validation

on:
  pull_request:
    paths:
      - 'airflow/dags/**/*.py'
      - 'kcli-pipelines/dags/**/*.py'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install apache-airflow==2.10.4
          pip install kcli
      
      - name: Validate DAGs
        run: |
          for dag in airflow/dags/*.py; do
            echo "Validating $dag..."
            ./airflow/scripts/validate-dag.sh "$dag"
          done
```

---

## Implementation Plan

### Phase 1: SSH-Based Execution (Immediate)
1. Add SSH client to Airflow container Dockerfile
2. Configure SSH key sharing between container and host
3. Update DAGs to use SSH for Ansible execution
4. Document the SSH execution pattern

### Phase 2: Validation Script (Short-term)
1. Create `airflow/scripts/validate-dag.sh`
2. Add to repository with executable permissions
3. Document usage in ADR-0045

### Phase 3: CI/CD Integration (Medium-term)
1. Add pre-commit hook configuration
2. Create GitHub Actions workflow
3. Add validation to PR template checklist

---

## SSH Execution Pattern

### Container Dockerfile Addition

```dockerfile
# Add SSH client for host execution
RUN apt-get update && apt-get install -y \
    openssh-client \
    && apt-get clean
```

### Docker Compose Volume Mount

```yaml
volumes:
  # Mount SSH keys for host access
  - /root/.ssh:/root/.ssh:ro
  # Mount SSH socket for agent forwarding (optional)
  - ${SSH_AUTH_SOCK:-/dev/null}:/ssh-agent:ro
```

### DAG Pattern for Host Execution

```python
# Task that runs Ansible on host via SSH
run_ansible = BashOperator(
    task_id='run_ansible_on_host',
    bash_command="""
    export PATH="/home/airflow/.local/bin:/usr/local/bin:$PATH"
    
    # Variables
    INVENTORY_DIR="/root/.generated/.idm.example.com"
    PLAYBOOK_DIR="/opt/freeipa-workshop-deployer"
    
    # Execute Ansible on host via SSH
    ssh -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        root@localhost \
        "cd $PLAYBOOK_DIR && \\
         ANSIBLE_HOST_KEY_CHECKING=False \\
         ansible-playbook \\
         -i $INVENTORY_DIR/inventory \\
         --extra-vars 'domain=example.com' \\
         2_ansible_config/deploy_idm.yaml -v"
    """,
    dag=dag,
)
```

---

## Validation Checklist

### Before Submitting a DAG PR

- [ ] Run `./airflow/scripts/validate-dag.sh <dag_file.py>`
- [ ] All validation checks pass
- [ ] No Unicode characters in bash commands
- [ ] No string concatenation in bash_command
- [ ] PATH export included for kcli/ansible usage
- [ ] SSH execution pattern used for Ansible playbooks
- [ ] Tested locally with `airflow dags test`

---

## Consequences

### Positive
- Ansible version consistency with host
- Early error detection before deployment
- Automated validation in CI/CD
- Reduced debugging time
- Better developer experience

### Negative
- SSH setup required between container and host
- Additional validation step in development workflow
- Slightly more complex DAG patterns for Ansible

### Risks
- SSH key security must be managed carefully
- Host must have SSH server running
- Network policies may block localhost SSH

## Automated SSH Configuration

The `deploy-qubinode-with-airflow.sh` script automatically configures SSH access:

```bash
# From deploy-qubinode-with-airflow.sh

# Ensure SSH key exists
if [[ ! -f "$HOME/.ssh/id_rsa" ]]; then
    ssh-keygen -t rsa -b 4096 -f "$HOME/.ssh/id_rsa" -N '' -q
fi

# Add the key to authorized_keys for localhost access
if ! grep -q "$(cat $HOME/.ssh/id_rsa.pub)" "$HOME/.ssh/authorized_keys" 2>/dev/null; then
    cat "$HOME/.ssh/id_rsa.pub" >> "$HOME/.ssh/authorized_keys"
    chmod 600 "$HOME/.ssh/authorized_keys"
fi
```

This ensures the Airflow container can SSH to the host for Ansible execution without manual intervention.

---

## Related ADRs

- ADR-0043: Airflow Container Host Network Access
- ADR-0044: User-Configurable Airflow Volume Mounts
- ADR-0045: Airflow DAG Development Standards

## References

- Apache Airflow Best Practices
- Pre-commit framework documentation
- GitHub Actions workflow syntax
