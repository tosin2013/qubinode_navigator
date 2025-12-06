______________________________________________________________________

## description: List all Airflow DAGs with their status allowed-tools: Bash(podman-compose:*), Bash(docker-compose:*), Bash(airflow:\*)

# List Airflow DAGs

You are helping manage Qubinode Navigator's Airflow DAGs.

List all available DAGs by running:
!`cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow && podman-compose exec -T airflow-scheduler airflow dags list 2>/dev/null || docker-compose exec -T airflow-scheduler airflow dags list`

For each DAG, explain:

- What it does based on its name and tags
- Whether it's paused or active
- When it was last run (if available)

Reference the DAG source files in airflow/dags/ for additional context about what each workflow accomplishes.

$ARGUMENTS
