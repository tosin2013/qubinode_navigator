______________________________________________________________________

## description: Trigger an Airflow DAG execution allowed-tools: Bash(podman-compose:*), Bash(docker-compose:*), Bash(airflow:\*) argument-hint: \[dag-id\]

# Trigger DAG: $1

You are helping trigger a Qubinode Navigator Airflow DAG.

Before triggering, verify:

1. The DAG exists and is not paused
1. Any required configuration is in place
1. Prerequisites are met

To trigger the DAG:
!`cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow && podman-compose exec -T airflow-scheduler airflow dags trigger $1`

After triggering:

1. Explain what the DAG will do
1. How to monitor its progress in the Airflow UI (http://localhost:8888)
1. Expected duration and outcomes
1. How to check logs if it fails

IMPORTANT: Confirm with the user before executing any destructive DAGs (delete, cleanup, etc.).
