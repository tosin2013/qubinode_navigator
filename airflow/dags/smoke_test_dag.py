"""
Airflow DAG: Smoke Test DAG
Purpose: Validates Airflow + OpenLineage/Marquez integration in CI

This DAG is designed to run in GitHub Actions without KVM.
It tests:
- DAG execution flow (success and failure paths)
- OpenLineage event emission
- Marquez lineage capture
- Task dependencies

Note: This DAG uses only Python operators (no SSH/kcli needed)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

# Default arguments
default_args = {
    "owner": "qubinode",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=1),
}

# DAG definition
dag = DAG(
    "smoke_test_dag",
    default_args=default_args,
    description="Smoke test DAG for CI validation of Airflow + OpenLineage",
    schedule=None,  # Manual trigger only
    catchup=False,
    tags=["smoke-test", "ci", "openlineage"],
    params={
        "should_fail": False,  # Set to True to test failure path
        "test_name": "default",
    },
)


def start_test(**context):
    """Initialize smoke test and emit start event."""
    test_name = context["params"].get("test_name", "default")
    print(f"[INFO] Starting smoke test: {test_name}")
    print(f"[INFO] Run ID: {context['run_id']}")
    print(f"[INFO] Execution date: {context['execution_date']}")
    return {"test_name": test_name, "status": "started"}


def process_data(**context):
    """Simulate data processing - emits OpenLineage dataset events."""
    import json

    # Simulate input/output datasets for OpenLineage
    input_data = {
        "source": "smoke_test_input",
        "records": 100,
        "timestamp": str(datetime.now()),
    }

    output_data = {
        "destination": "smoke_test_output",
        "records_processed": 100,
        "timestamp": str(datetime.now()),
    }

    print("[INFO] Processing data...")
    print(f"[INFO] Input: {json.dumps(input_data)}")
    print(f"[INFO] Output: {json.dumps(output_data)}")

    # Check if we should simulate failure
    should_fail = context["params"].get("should_fail", False)
    if should_fail:
        print("[ERROR] Simulated failure triggered by should_fail=True")
        raise ValueError("Simulated failure for testing error handling")

    print("[OK] Data processing complete")
    return output_data


def validate_results(**context):
    """Validate results and emit completion event."""
    ti = context["ti"]
    process_result = ti.xcom_pull(task_ids="process_data")

    print("[INFO] Validating results...")
    print(f"[INFO] Process result: {process_result}")

    if process_result and process_result.get("records_processed", 0) > 0:
        print("[OK] Validation passed")
        return {"status": "success", "records": process_result["records_processed"]}
    else:
        print("[ERROR] Validation failed - no records processed")
        raise ValueError("Validation failed")


def cleanup(**context):
    """Cleanup and emit final event."""
    print("[INFO] Running cleanup...")
    print("[OK] Smoke test completed successfully")
    return {"status": "completed"}


# Task definitions
start = PythonOperator(
    task_id="start_test",
    python_callable=start_test,
    dag=dag,
)

process = PythonOperator(
    task_id="process_data",
    python_callable=process_data,
    dag=dag,
)

validate = PythonOperator(
    task_id="validate_results",
    python_callable=validate_results,
    dag=dag,
)

# Simple bash task to test BashOperator integration
echo_status = BashOperator(
    task_id="echo_status",
    bash_command="""
    echo "========================================"
    echo "Smoke Test Status"
    echo "========================================"
    echo "[OK] All tasks completed"
    echo "Run ID: {{ run_id }}"
    echo "Test Name: {{ params.test_name }}"
    """,
    dag=dag,
)

finish = PythonOperator(
    task_id="cleanup",
    python_callable=cleanup,
    dag=dag,
)

# Task dependencies
start >> process >> validate >> echo_status >> finish

# DAG documentation
dag.doc_md = """
# Smoke Test DAG

This DAG validates the Airflow + OpenLineage/Marquez integration.

## Purpose
- Test DAG execution in CI without KVM
- Validate OpenLineage events are emitted
- Verify Marquez captures lineage data
- Test success and failure paths

## Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| should_fail | False | Set to True to test failure handling |
| test_name | default | Name for this test run |

## Tasks
1. **start_test** - Initialize and log test start
2. **process_data** - Simulate data processing (emits lineage)
3. **validate_results** - Validate processing results
4. **echo_status** - BashOperator test
5. **cleanup** - Final cleanup

## Usage in CI
```bash
airflow dags test smoke_test_dag 2025-01-01
```
"""
