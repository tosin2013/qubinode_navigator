______________________________________________________________________

## description: Check status of all infrastructure services allowed-tools: Bash(systemctl:*), Bash(podman-compose:*), Bash(docker-compose:*), Bash(virsh:*), Bash(curl:*), Bash(pg_isready:*)

# Infrastructure Status

You are helping check infrastructure service status in Qubinode Navigator.

Check core services:
!`echo "=== Airflow ===" && (cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow && podman-compose ps 2>/dev/null || docker-compose ps 2>/dev/null)`

!`echo "=== Libvirt ===" && systemctl is-active libvirtd && virsh list --all 2>/dev/null | head -10`

!`echo "=== AI Assistant ===" && curl -s http://localhost:8080/health 2>/dev/null | head -5 || echo "AI Assistant not responding"`

!`echo "=== MCP Server ===" && curl -s http://localhost:8889/health 2>/dev/null | head -5 || echo "MCP server not responding"`

!`echo "=== PostgreSQL ===" && pg_isready -h localhost 2>/dev/null || echo "PostgreSQL not ready"`

!`echo "=== Marquez (Lineage) ===" && curl -s http://localhost:5001/api/v1/namespaces 2>/dev/null | head -5 || echo "Marquez not running"`

Provide a summary:

1. Overall system health
1. Any services that need attention
1. Resource utilization concerns
1. Recommended actions

$ARGUMENTS
