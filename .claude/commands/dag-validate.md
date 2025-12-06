______________________________________________________________________

## description: Validate DAG syntax and check for errors allowed-tools: Bash(podman-compose:*), Bash(docker-compose:*), Bash(airflow:*), Bash(./airflow/scripts/validate-dag.sh:*), Read

# Validate Airflow DAGs

You are helping validate Qubinode Navigator Airflow DAGs.

Run DAG validation:
!`cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow && ./scripts/validate-dag.sh`

Also check for import errors:
!`cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow && podman-compose exec -T airflow-scheduler airflow dags list-import-errors 2>/dev/null || docker-compose exec -T airflow-scheduler airflow dags list-import-errors`

Review the DAG development standards from ADR-0045:
@docs/adrs/adr-0045-dag-development-standards.md

For any errors found:

1. Identify the root cause
1. Reference the specific ADR standard violated
1. Provide the exact fix needed
1. Explain how to prevent similar issues

$ARGUMENTS
