# Troubleshooting Guide

Use this rule when debugging issues with Qubinode Navigator.

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

## Quick Health Check

```bash
# All-in-one status check
echo "=== Containers ===" && podman-compose ps
echo "=== Airflow ===" && curl -s http://localhost:8888/health
echo "=== MCP ===" && curl -s http://localhost:8889/health
echo "=== Libvirt ===" && virsh list --all | head -5
```
