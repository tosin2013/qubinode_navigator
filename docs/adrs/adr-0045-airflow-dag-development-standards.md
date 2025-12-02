# ADR-0045: Airflow DAG Development Standards

## Status
Accepted

## Date
2025-11-27

## Context and Problem Statement

During the development of FreeIPA and VyOS deployment DAGs, we encountered several issues that caused DAG failures:

1. **Unicode characters** in bash commands caused parsing errors (`unexpected EOF while looking for matching quote`)
2. **String concatenation** in triple-quoted bash commands broke the command syntax
3. **Complex error handling** with special characters failed in containerized environments
4. **Missing volume mounts** caused DAGs to fail when accessing host resources
5. **Inconsistent coding patterns** made debugging difficult

We need a standardized approach for developing Airflow DAGs in the Qubinode Navigator project.

## Decision Drivers

* DAGs must work reliably in containerized Airflow environments
* Code should be maintainable and debuggable
* Standards should be easy to follow for new contributors
* DAGs should be portable across different environments

## Decision Outcome

Establish the following development standards for all Airflow DAGs in the Qubinode Navigator project.

---

## DAG Development Standards

### 1. File Structure and Naming

```
dags/
├── <service>_deployment.py      # Main deployment DAG
├── <service>_maintenance.py     # Maintenance/cleanup DAG (optional)
└── README.md                    # DAG documentation
```

**Naming Conventions:**
- DAG files: `snake_case.py`
- DAG IDs: Match the filename without `.py` extension
- Task IDs: `snake_case`, descriptive action names

### 2. DAG Template

```python
"""
Airflow DAG: <Service Name> Deployment
ADR-XXXX: <Related ADR Title>

<Brief description of what this DAG does>
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import BranchPythonOperator

# Default arguments
default_args = {
    'owner': 'qubinode',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=3),
}

# DAG definition
dag = DAG(
    '<dag_id>',
    default_args=default_args,
    description='<Description>',
    schedule=None,  # Manual trigger only for deployment DAGs
    catchup=False,
    tags=['qubinode', '<service>', '<category>'],
    params={
        'action': 'create',
        # Add other parameters with defaults
    },
)
```

### 3. BashOperator Standards

#### DO: Use Double Quotes for Bash Commands

```python
# CORRECT - Use triple double quotes
task = BashOperator(
    task_id='my_task',
    bash_command="""
    set -e
    echo "Starting task..."
    VARIABLE="{{ params.my_param }}"
    echo "Value: $VARIABLE"
    """,
    dag=dag,
)
```

#### DON'T: Use Triple Single Quotes with String Concatenation

```python
# WRONG - This causes parsing errors
task = BashOperator(
    task_id='my_task',
    bash_command='''
    cd ''' + SOME_PATH + '''
    echo "This will fail"
    ''',
    dag=dag,
)
```

#### DO: Use Hardcoded Paths or Environment Variables

```python
# CORRECT - Hardcoded path
bash_command="""
cd /opt/freeipa-workshop-deployer
ansible-playbook playbook.yaml
"""

# CORRECT - Environment variable
bash_command="""
cd ${DEPLOYER_PATH:-/opt/freeipa-workshop-deployer}
ansible-playbook playbook.yaml
"""
```

### 4. Character Encoding Standards

#### DON'T: Use Unicode/Emoji Characters

```python
# WRONG - Unicode characters cause parsing issues
echo "✅ Task completed!"
echo "━━━━━━━━━━━━━━━━━━"
echo "❌ Task failed!"
echo "⚠️ Warning!"
```

#### DO: Use ASCII-Only Characters

```python
# CORRECT - ASCII only
echo "[OK] Task completed!"
echo "========================================"
echo "[ERROR] Task failed!"
echo "[WARN] Warning!"
```

### 5. Error Handling

#### DO: Use Simple Exit Codes

```python
bash_command="""
set -e  # Exit on first error

# Check prerequisites
if [ -z "$REQUIRED_VAR" ]; then
    echo "[ERROR] REQUIRED_VAR is not set"
    exit 1
fi

# Run command
some_command || {
    echo "[ERROR] Command failed"
    exit 1
}

echo "[OK] Task completed"
"""
```

#### DON'T: Use Complex Nested Error Handling

```python
# WRONG - Complex nesting with special characters
some_command || {
    echo "❌ Failed"
    echo "Check the logs above for details"
    exit 1
}
```

### 6. Jinja Templating

#### DO: Use Proper Jinja Syntax

```python
bash_command="""
DOMAIN="{{ params.domain }}"
ACTION="{{ params.action }}"

if [ "$ACTION" == "create" ]; then
    echo "Creating for domain: $DOMAIN"
fi
"""
```

#### DON'T: Mix Jinja with Complex Bash Substitutions

```python
# WRONG - Confusing mix of Jinja and bash
{% raw %}echo "Result: {{ params.value | default('${DEFAULT_VALUE}') }}"{% endraw %}
```

### 7. Volume Mount Requirements

DAGs that access host resources must document required mounts:

```python
"""
Required Volume Mounts:
- /root/qubinode_navigator:/opt/qubinode_navigator:ro
- /root/freeipa-workshop-deployer:/opt/freeipa-workshop-deployer
- /root/.ssh:/root/.ssh:ro
- /var/run/libvirt/libvirt-sock:/var/run/libvirt/libvirt-sock
"""
```

### 8. Task Documentation

Each task should have a clear purpose:

```python
# Task: Validate prerequisites before deployment
validate_environment = BashOperator(
    task_id='validate_environment',
    bash_command="""
    echo "========================================"
    echo "Validating Environment"
    echo "========================================"
    
    # Check kcli is available
    command -v kcli || { echo "[ERROR] kcli not found"; exit 1; }
    
    # Check required files exist
    [ -f "/opt/qubinode_navigator/inventories/localhost/group_vars/control/vault.yml" ] || {
        echo "[ERROR] vault.yml not found"
        exit 1
    }
    
    echo "[OK] Environment validation complete"
    """,
    dag=dag,
)
```

### 9. Logging Standards

Use consistent log prefixes:

| Prefix | Meaning |
|--------|---------|
| `[OK]` | Success |
| `[ERROR]` | Error/Failure |
| `[WARN]` | Warning |
| `[INFO]` | Informational |
| `[SKIP]` | Skipped step |

### 10. Testing DAGs

Before committing, test DAGs:

```bash
# Syntax check
python -c "import ast; ast.parse(open('dags/my_dag.py').read())"

# Airflow import check
python -c "from airflow.models import DagBag; d = DagBag('.'); print(d.import_errors)"

# Dry run (if applicable)
airflow dags test my_dag_id 2025-01-01
```

---

## Consequences

### Positive
- Consistent, maintainable DAG code across the project
- Fewer runtime errors from encoding/parsing issues
- Easier onboarding for new contributors
- Better debugging experience

### Negative
- Less visually appealing output (no emojis/Unicode)
- Requires updating existing DAGs to comply
- Some flexibility is reduced for standardization

## Related ADRs

- ADR-0036: Airflow Integration Architecture
- ADR-0039: FreeIPA and VyOS Airflow DAG Integration
- ADR-0043: Airflow Container Host Network Access
- ADR-0044: User-Configurable Airflow Volume Mounts

## Compliance Checklist

Before submitting a DAG PR, verify:

- [ ] DAG file uses snake_case naming
- [ ] DAG ID matches filename
- [ ] Uses `"""` (double quotes) for bash_command
- [ ] No Unicode/emoji characters in bash commands
- [ ] No string concatenation in bash_command
- [ ] All paths are hardcoded or use environment variables
- [ ] Error handling uses simple exit codes
- [ ] Required volume mounts are documented
- [ ] Python syntax check passes
- [ ] Airflow import check passes
