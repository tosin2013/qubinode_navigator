# Migration Guide: Root User to Non-Root User

This guide helps you migrate an existing Qubinode deployment running as `root` to run as a non-root user (e.g., `vpcuser`, `cloud-user`).

## Prerequisites

- Existing Qubinode deployment running as root
- A non-root user account with sudo access
- SSH access configured

## Migration Steps

### 1. Create Non-Root User (if needed)

```bash
# As root, create the user
useradd -m -G wheel vpcuser
passwd vpcuser

# Add to wheel group for sudo
usermod -aG wheel vpcuser

# Configure sudo without password (optional)
echo "vpcuser ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/vpcuser
chmod 440 /etc/sudoers.d/vpcuser
```

### 2. Copy SSH Keys

```bash
# As root, copy SSH keys to new user
cp -r /root/.ssh /home/vpcuser/
chown -R vpcuser:vpcuser /home/vpcuser/.ssh
chmod 700 /home/vpcuser/.ssh
chmod 600 /home/vpcuser/.ssh/*
```

### 3. Copy Generated Files

```bash
# Copy inventory and generated files
cp -r /root/.generated /home/vpcuser/
chown -R vpcuser:vpcuser /home/vpcuser/.generated

# Copy vault password file
cp /root/.vault_password /home/vpcuser/
chown vpcuser:vpcuser /home/vpcuser/.vault_password
chmod 600 /home/vpcuser/.vault_password

# Copy pull secret
if [ -f /root/pull-secret.json ]; then
    cp /root/pull-secret.json /home/vpcuser/
    chown vpcuser:vpcuser /home/vpcuser/pull-secret.json
    chmod 600 /home/vpcuser/pull-secret.json
fi
```

### 4. Configure SSH Access

```bash
# As the new user, test SSH to localhost
su - vpcuser
ssh-copy-id -i ~/.ssh/id_rsa.pub localhost
ssh localhost "echo 'SSH works!'"
```

### 5. Set Environment Variables

Create `/home/vpcuser/.bashrc` additions:

```bash
# Qubinode configuration
export QUBINODE_SSH_USER=vpcuser
export QUBINODE_SSH_KEY_PATH=/home/vpcuser/.ssh/id_rsa
export QUBINODE_INVENTORY_DIR=/home/vpcuser/.generated
export QUBINODE_VAULT_PASSWORD_FILE=/home/vpcuser/.vault_password
export QUBINODE_PULL_SECRET_PATH=/home/vpcuser/pull-secret.json
```

Source the file:

```bash
source ~/.bashrc
```

### 6. Update Airflow Configuration

Edit `airflow/config/airflow.env`:

```ini
QUBINODE_SSH_USER=vpcuser
QUBINODE_SSH_KEY_PATH=/home/vpcuser/.ssh/id_rsa
QUBINODE_INVENTORY_DIR=/home/vpcuser/.generated
QUBINODE_VAULT_PASSWORD_FILE=/home/vpcuser/.vault_password
QUBINODE_PULL_SECRET_PATH=/home/vpcuser/pull-secret.json
```

### 7. Update Docker/Podman Compose

Edit `airflow/docker-compose.yml` or `airflow/podman-compose.yml`:

```yaml
services:
  airflow-webserver:
    environment:
      - QUBINODE_SSH_USER=vpcuser
      - QUBINODE_SSH_KEY_PATH=/home/vpcuser/.ssh/id_rsa
      - QUBINODE_INVENTORY_DIR=/home/vpcuser/.generated

  airflow-scheduler:
    environment:
      - QUBINODE_SSH_USER=vpcuser
      - QUBINODE_SSH_KEY_PATH=/home/vpcuser/.ssh/id_rsa
      - QUBINODE_INVENTORY_DIR=/home/vpcuser/.generated

  airflow-worker:
    environment:
      - QUBINODE_SSH_USER=vpcuser
      - QUBINODE_SSH_KEY_PATH=/home/vpcuser/.ssh/id_rsa
      - QUBINODE_INVENTORY_DIR=/home/vpcuser/.generated
```

### 8. Restart Airflow

```bash
# As vpcuser
cd /opt/qubinode_navigator/airflow

# Stop existing services
sudo podman-compose down

# Start as new user
podman-compose up -d
```

### 9. Verify Migration

Test that DAGs work with the new user:

```bash
# Check Airflow is running
podman ps

# Access the web UI
# http://localhost:8080

# Trigger a test DAG
airflow dags trigger smoke_test_dag

# Check logs
airflow dags list
```

### 10. Test SSH Commands

Verify SSH works from Airflow containers:

```bash
# From Airflow container
podman exec -it airflow_airflow-webserver_1 bash

# Inside container, test SSH
ssh -o StrictHostKeyChecking=no vpcuser@localhost "echo 'Container SSH works!'"

# Test kcli command
ssh vpcuser@localhost "kcli list vm"
```

## Troubleshooting

### Issue: Permission Denied on SSH

```bash
# Check SSH key permissions
ls -la ~/.ssh/
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_rsa
chmod 644 ~/.ssh/id_rsa.pub

# Test SSH connection
ssh -vvv localhost
```

### Issue: Cannot Write to Inventory Directory

```bash
# Check directory permissions
ls -ld ~/.generated
mkdir -p ~/.generated
chmod 755 ~/.generated
```

### Issue: DAGs Still Using Root

```bash
# Verify environment variables are set
echo $QUBINODE_SSH_USER
env | grep QUBINODE

# Clear Airflow cache
cd /opt/qubinode_navigator/airflow
podman-compose down
podman system prune -f
podman-compose up -d
```

### Issue: Vault Password File Not Found

```bash
# Check file exists and is readable
ls -la ~/.vault_password

# If missing, recreate from root's file
sudo cp /root/.vault_password ~/
sudo chown $USER:$USER ~/.vault_password
chmod 600 ~/.vault_password
```

## Rollback Plan

If migration fails, you can roll back:

```bash
# Stop services as new user
podman-compose down

# Switch back to root
su -

# Start services as root
cd /opt/qubinode_navigator/airflow
podman-compose up -d
```

## Verification Checklist

After migration, verify:

- [ ] SSH from Airflow containers to localhost works
- [ ] Environment variables are set correctly
- [ ] Airflow web UI is accessible
- [ ] Test DAGs execute successfully
- [ ] kcli commands work via SSH
- [ ] Inventory files are created in correct location
- [ ] VM deployments complete successfully
- [ ] Ansible playbooks execute properly

## Post-Migration Cleanup

Once verified, clean up root's files (optional):

```bash
# As root, archive old files
cd /root
tar -czf /backup/root-qubinode-$(date +%Y%m%d).tar.gz .generated .ssh .vault_password pull-secret.json

# Remove old files (be careful!)
# rm -rf /root/.generated
# rm -rf /root/.vault_password
```

## Security Considerations

- Non-root users reduce attack surface
- Proper file permissions are critical
- Use SSH keys, not passwords
- Regularly rotate credentials
- Monitor user activity logs

## Support

For issues during migration:

1. Check logs: `podman logs airflow_airflow-webserver_1`
1. Review environment: `env | grep QUBINODE`
1. Test SSH manually: `ssh localhost`
1. Consult DAG-USER-CONFIGURATION.md
1. Open GitHub issue with migration details

## Next Steps

After successful migration:

1. Update documentation with your user
1. Test all DAGs you regularly use
1. Document any environment-specific changes
1. Update backup scripts for new user paths
1. Train team on new user context

## Related Documentation

- [DAG User Configuration Guide](DAG-USER-CONFIGURATION.md)
- [Airflow Deployment Guide](README.md)
- [ADR-0046: DAG Validation Pipeline](../docs/adrs/)
