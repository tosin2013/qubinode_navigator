"""
DAG Diagnostics and Troubleshooting Tools
Helps diagnose failed DAG runs and task instances
"""

import subprocess
import json
from typing import Dict, Any, Optional


def get_dag_failures() -> Dict[str, Any]:
    """
    Get all recent DAG and task failures with detailed error information
    """
    try:
        # Get failed task instances
        result = subprocess.run(
            ["airflow", "tasks", "failed-deps", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        failures = {
            "failed_tasks": [],
            "import_errors": [],
            "scheduler_health": {},
            "recent_errors": [],
        }

        # Check for import errors
        import_result = subprocess.run(
            ["airflow", "dags", "list-import-errors", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if import_result.returncode == 0 and import_result.stdout.strip():
            try:
                failures["import_errors"] = json.loads(import_result.stdout)
            except json.JSONDecodeError:
                failures["import_errors"] = import_result.stdout

        return failures

    except Exception as e:
        return {"error": str(e)}


def diagnose_dag(dag_id: str) -> Dict[str, Any]:
    """
    Comprehensive diagnostics for a specific DAG
    """
    diagnostics = {
        "dag_id": dag_id,
        "status": "unknown",
        "last_run": None,
        "failed_tasks": [],
        "task_logs": {},
        "recommendations": [],
    }

    try:
        # Get DAG state
        result = subprocess.run(
            ["airflow", "dags", "state", dag_id],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            diagnostics["status"] = result.stdout.strip()

        # List recent DAG runs
        runs_result = subprocess.run(
            ["airflow", "dags", "list-runs", "--dag-id", dag_id, "--output", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if runs_result.returncode == 0 and runs_result.stdout.strip():
            try:
                runs = json.loads(runs_result.stdout)
                if runs:
                    diagnostics["last_run"] = (
                        runs[0] if isinstance(runs, list) else runs
                    )
            except json.JSONDecodeError:
                pass

        return diagnostics

    except Exception as e:
        diagnostics["error"] = str(e)
        return diagnostics


def get_task_logs(dag_id: str, task_id: str, run_id: str, try_number: int = 1) -> str:
    """
    Retrieve task logs for a specific task instance
    """
    try:
        result = subprocess.run(
            [
                "airflow",
                "tasks",
                "log",
                dag_id,
                task_id,
                run_id,
                "--try",
                str(try_number),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error retrieving logs: {result.stderr}"

    except Exception as e:
        return f"Exception: {str(e)}"


def format_diagnostic_report(dag_id: Optional[str] = None) -> str:
    """
    Generate a formatted diagnostic report in markdown
    """
    report = "# Airflow Diagnostics Report\n\n"

    if dag_id:
        report += f"## DAG: {dag_id}\n\n"
        diag = diagnose_dag(dag_id)

        report += f"**Status**: {diag.get('status', 'unknown')}\n\n"

        if diag.get("last_run"):
            report += "### Last Run\n"
            report += f"```json\n{json.dumps(diag['last_run'], indent=2)}\n```\n\n"

        if diag.get("failed_tasks"):
            report += "### Failed Tasks\n"
            for task in diag["failed_tasks"]:
                report += f"- **{task.get('task_id')}**: {task.get('error', 'Unknown error')}\n"
            report += "\n"

        if diag.get("recommendations"):
            report += "### Recommendations\n"
            for rec in diag["recommendations"]:
                report += f"- {rec}\n"
            report += "\n"
    else:
        report += "## System-Wide Issues\n\n"
        failures = get_dag_failures()

        if failures.get("import_errors"):
            report += "### Import Errors\n"
            report += f"```\n{failures['import_errors']}\n```\n\n"

        if failures.get("recent_errors"):
            report += "### Recent Errors\n"
            for error in failures["recent_errors"][:5]:
                report += f"- {error}\n"
            report += "\n"

    return report


# Safe commands for AI to suggest
DIAGNOSTIC_COMMANDS = {
    "list_dags": "airflow dags list",
    "list_failed": "airflow tasks failed-deps --output json",
    "check_imports": "airflow dags list-import-errors",
    "dag_state": "airflow dags state <dag_id>",
    "list_runs": "airflow dags list-runs --dag-id <dag_id>",
    "task_log": "airflow tasks log <dag_id> <task_id> <run_id>",
    "test_task": "airflow tasks test <dag_id> <task_id> <date>",
}
