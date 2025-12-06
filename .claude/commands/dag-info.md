______________________________________________________________________

## description: Get detailed information about a specific DAG allowed-tools: Bash(podman-compose:*), Bash(docker-compose:*), Bash(airflow:\*), Read argument-hint: \[dag-id\]

# DAG Information: $1

You are helping analyze a Qubinode Navigator Airflow DAG.

Get details for the DAG:
!`cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow && podman-compose exec -T airflow-scheduler airflow dags show $1 2>/dev/null || docker-compose exec -T airflow-scheduler airflow dags show $1`

Then read the DAG source code from airflow/dags/ directory.

Provide:

1. DAG purpose and what it automates
1. Task dependencies and execution order
1. Required configuration or variables
1. How to trigger it and expected outcomes
1. Any prerequisites (VMs, services, credentials)
