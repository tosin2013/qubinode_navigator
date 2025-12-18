# Troubleshooting Guide (SRE Mode)

Use this rule when debugging issues with Qubinode Navigator.

## CRITICAL SRE RULES

**When troubleshooting deployment or runtime issues:**

1. **PRIORITIZE environmental diagnostics over source code inspection**
1. **DO NOT refactor or rewrite deployment scripts during troubleshooting**
1. **FIX the environment** (DNS, disk, permissions, packages), not the code
1. **If you find a code bug, PROPOSE A GITHUB ISSUE** instead of fixing it

## Step 1: Environmental Diagnosis First

Before looking at ANY code, check these environmental factors:

| Check       | Command                            | Common Fix                    |
| ----------- | ---------------------------------- | ----------------------------- |
| Services    | `systemctl status libvirtd podman` | `systemctl restart <service>` |
| Disk Space  | `df -h / /var/lib/libvirt`         | Clean up old images/VMs       |
| Memory      | `free -h`                          | Stop unused containers        |
| DNS         | `nslookup $(hostname)`             | Check /etc/resolv.conf        |
| Firewall    | `firewall-cmd --list-all`          | Open required ports           |
| SELinux     | `getenforce; ausearch -m avc`      | Set correct contexts          |
| Permissions | `ls -la <path>`                    | chown/chmod as needed         |

## DAG Issues

### DAG not appearing in UI

```bash
# Check for import errors
podman-compose exec -T airflow-scheduler airflow dags list-import-errors

# Clear DAG cache
cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow && make clear-dag-cache

# Check file permissions
ls -la airflow/dags/
```

### DAG validation failing

```bash
# Run validation
./airflow/scripts/validate-dag.sh

# Check Python syntax
python3 -m py_compile airflow/dags/your_dag.py
```

## Service Issues

### Airflow not responding

```bash
# Check container status
cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow
podman-compose ps

# View logs
podman-compose logs airflow-webserver
podman-compose logs airflow-scheduler

# Restart services
podman-compose restart
```

### PostgreSQL connection failed

```bash
# Check if running
pg_isready -h localhost -p 5432

# Check container
podman-compose logs postgres
```

### MCP Server issues

```bash
# Check health
curl http://localhost:8889/health

# View logs
podman-compose logs airflow-mcp-server
```

## VM Issues

### VM won't start

```bash
# Check libvirt
systemctl status libvirtd
virsh list --all

# Check resources
free -h
df -h /var/lib/libvirt
```

### VM no network

```bash
# Check networks
virsh net-list --all

# Check DHCP leases
virsh net-dhcp-leases default
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

## Quick Health Check

```bash
# All-in-one status check
echo "=== Containers ===" && podman-compose ps
echo "=== Airflow ===" && curl -s http://localhost:8888/health
echo "=== MCP ===" && curl -s http://localhost:8889/health
echo "=== Libvirt ===" && virsh list --all | head -5
echo "=== Recent Errors ===" && journalctl -p err --since "30 minutes ago" | tail -10
```

**REMEMBER:** 90% of deployment issues are environmental. Fix the environment first!
