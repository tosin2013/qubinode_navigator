______________________________________________________________________

## description: Run comprehensive health checks allowed-tools: Bash(podman-compose:*), Bash(docker-compose:*), Bash(curl:*), Bash(pg_isready:*), Bash(virsh:*), Bash(free:*), Bash(df:\*)

# System Health Check

You are helping run health checks on Qubinode Navigator.

Run comprehensive health check:

!`echo "=== Container Status ===" && cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow && (podman-compose ps 2>/dev/null || docker-compose ps 2>/dev/null)`

!`echo "=== Airflow Health ===" && curl -s http://localhost:8888/health 2>/dev/null || echo "Airflow webserver not responding"`

!`echo "=== MCP Server ===" && curl -s http://localhost:8889/health 2>/dev/null || echo "MCP server not responding"`

!`echo "=== AI Assistant ===" && curl -s http://localhost:8080/health 2>/dev/null || echo "AI Assistant not responding"`

!`echo "=== PostgreSQL ===" && pg_isready -h localhost -p 5432 2>/dev/null || echo "PostgreSQL not ready"`

!`echo "=== Marquez Lineage ===" && curl -s http://localhost:5001/api/v1/namespaces 2>/dev/null | head -5 || echo "Marquez not responding"`

!`echo "=== Libvirt ===" && virsh list --all 2>/dev/null | head -5 || echo "Libvirt not accessible"`

!`echo "=== System Resources ===" && free -h && echo "---" && df -h / /var/lib/libvirt 2>/dev/null | grep -v Filesystem`

Health Summary:

1. Service availability
1. Resource utilization
1. Connectivity between services
1. Recommended actions for any issues

$ARGUMENTS
