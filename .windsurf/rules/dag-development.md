# DAG Development Standards (ADR-0045)

Apply this rule when working with files in `airflow/dags/` or any `**/dags/**/*.py` files.

## Naming Conventions

- DAG ID: `snake_case` matching the filename (e.g., `ocp_initial_deployment.py` → `ocp_initial_deployment`)
- Task IDs: `snake_case`, descriptive of the action

## Bash Command Quoting

ALWAYS use triple double quotes for bash_command:

```python
# CORRECT
bash_command="""
ssh -o StrictHostKeyChecking=no root@localhost \
    "cd /opt/kcli-pipelines && ./deploy.sh"
"""

# WRONG - Never use triple single quotes
bash_command='''
some command
'''

# WRONG - Never use string concatenation
bash_command="command " + variable + " more"
```

## Status Markers

Use ASCII-only status markers in output:

- `[OK]` - Success
- `[ERROR]` - Failure
- `[WARN]` - Warning
- `[INFO]` - Information
- `[SKIP]` - Skipped

Never use emojis or Unicode symbols.

## DAG Template

```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'qubinode',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='my_dag_name',  # Must match filename
    default_args=default_args,
    description='Brief description',
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['qubinode', 'category'],
) as dag:

    task = BashOperator(
        task_id='task_name',
        bash_command="""
        echo "[INFO] Starting task..."
        # Commands here
        echo "[OK] Task completed"
        """,
    )
```

## Validation

After creating/modifying DAGs, validate:

```bash
cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow
./scripts/validate-dag.sh
podman-compose exec -T airflow-scheduler airflow dags list-import-errors
```
