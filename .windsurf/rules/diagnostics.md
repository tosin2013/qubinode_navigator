# Diagnostics and Troubleshooting (SRE Mode)

Use this rule when debugging issues with Qubinode Navigator.

## CRITICAL SRE RULES

**When troubleshooting deployment or runtime issues:**

1. **PRIORITIZE environmental diagnostics over source code inspection**
1. **DO NOT refactor or rewrite deployment scripts during troubleshooting**
1. **FIX the environment** (DNS, disk, permissions, packages), not the code
1. **If you find a code bug, PROPOSE A GITHUB ISSUE** instead of fixing it

## Step 1: Environmental Diagnosis First

Before looking at ANY code, run these diagnostic commands:

| Check       | Command                            | Common Fix                    |
| ----------- | ---------------------------------- | ----------------------------- |
| Services    | `systemctl status libvirtd podman` | `systemctl restart <service>` |
| Disk Space  | `df -h / /var/lib/libvirt`         | Clean up old images/VMs       |
| Memory      | `free -h`                          | Stop unused containers        |
| DNS         | `nslookup $(hostname)`             | Check /etc/resolv.conf        |
| Firewall    | `firewall-cmd --list-all`          | Open required ports           |
| SELinux     | `getenforce; ausearch -m avc`      | Set correct contexts          |
| Permissions | `ls -la <path>`                    | chown/chmod as needed         |

## Quick Diagnostic Commands

### System Overview

```bash
echo "=== System ===" && uname -a && free -h && df -h /
echo "=== Containers ===" && cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow && podman-compose ps
echo "=== Services ===" && systemctl is-active libvirtd postgresql
echo "=== Recent Errors ===" && journalctl -p err --since "30 minutes ago" --no-pager | tail -20
```

### Network/DNS Check

```bash
ping -c1 8.8.8.8
nslookup $(hostname)
firewall-cmd --list-all
```

### SELinux Check

```bash
getenforce
ausearch -m avc -ts recent | tail -10
```

### Service Health

```bash
curl -s http://localhost:8888/health  # Airflow
curl -s http://localhost:8889/health  # MCP
curl -s http://localhost:8080/health  # AI Assistant
curl -s http://localhost:5001/api/v1/namespaces  # Marquez
```

## Common Issues

### DAG Not Appearing

1. Check import errors:
   ```bash
   podman-compose exec -T airflow-scheduler airflow dags list-import-errors
   ```
1. Clear cache:
   ```bash
   cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow && make clear-dag-cache
   ```
1. Check file permissions and syntax

### DAG Validation Failing

1. Run validation:
   ```bash
   ./airflow/scripts/validate-dag.sh
   ```
1. Check ADR-0045 compliance:
   - Using `"""` not `'''`?
   - snake_case DAG ID?
   - ASCII markers only?

### Airflow Not Responding

1. Check containers:
   ```bash
   podman-compose ps
   podman-compose logs airflow-webserver
   ```
1. Check PostgreSQL:
   ```bash
   pg_isready -h localhost
   ```
1. Restart:
   ```bash
   podman-compose restart
   ```

### VM Issues

1. Check libvirt:
   ```bash
   systemctl status libvirtd
   virsh list --all
   ```
1. Check resources:
   ```bash
   free -h
   df -h /var/lib/libvirt
   ```

### MCP Server Issues

```bash
# Check if running
curl http://localhost:8889/health

# View logs
podman-compose logs airflow-mcp-server

# Check API key
grep MCP_API_KEY ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow/.env
```

## SRE Mode Rules

| Action                         | Allowed | Forbidden |
| ------------------------------ | ------- | --------- |
| Check journalctl/systemctl     | ✓       |           |
| Diagnose DNS/firewall/SELinux  | ✓       |           |
| Suggest dnf/yum install        | ✓       |           |
| Fix permissions/disk space     | ✓       |           |
| Propose GitHub Issues for bugs | ✓       |           |
| Refactor deploy-qubinode.sh    |         | ✗         |
| Rewrite core Python files      |         | ✗         |
| Add new features during debug  |         | ✗         |

## Query Knowledge Base for Help

```bash
curl -s -X POST http://localhost:8080/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "troubleshoot <your issue>"}'
```

## Recent Errors

```bash
# System journal
journalctl -p err --since "1 hour ago" --no-pager | tail -30

# Airflow scheduler logs
tail -100 ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow/logs/scheduler/latest/*.log | grep -i error
```

**REMEMBER:** 90% of deployment issues are environmental. Fix the environment first!
