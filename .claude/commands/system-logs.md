______________________________________________________________________

## description: View service logs allowed-tools: Bash(podman-compose:*), Bash(docker-compose:*), Bash(journalctl:\*) argument-hint: \[service-name\]

# View Service Logs

You are helping view Qubinode Navigator service logs.

Service or filter: $ARGUMENTS

View Airflow logs:
!`cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow && (podman-compose logs --tail=50 $ARGUMENTS 2>/dev/null || docker-compose logs --tail=50 $ARGUMENTS 2>/dev/null) || echo "Showing all services..." && (podman-compose logs --tail=30 2>/dev/null || docker-compose logs --tail=30 2>/dev/null)`

Common log locations:

- Airflow scheduler: airflow/logs/scheduler/
- Airflow tasks: airflow/logs/dag_id/task_id/
- AI Assistant: journalctl -u qubinode-ai-assistant
- System: journalctl -xe

To follow logs in real-time:

```bash
cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow
podman-compose logs -f <service>
```

Available services:

- airflow-webserver
- airflow-scheduler
- airflow-mcp-server
- postgres
- marquez
- marquez-web

Analyze the logs for:

1. Error patterns
1. Warning signs
1. Performance issues
1. Connection problems
