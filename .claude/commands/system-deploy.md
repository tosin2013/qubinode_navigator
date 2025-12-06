______________________________________________________________________

## description: Deploy or redeploy Qubinode Navigator stack allowed-tools: Bash(podman-compose:*), Bash(docker-compose:*), Bash(./scripts/preflight-check.sh:*), Bash(make:*) argument-hint: \[options\]

# Deploy Qubinode Navigator

You are helping deploy the Qubinode Navigator stack.

Deployment request: $ARGUMENTS

Review current deployment status:
!`cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow && (podman-compose ps 2>/dev/null || docker-compose ps 2>/dev/null)`

Check prerequisites:
!`${QUBINODE_HOME:-$HOME/qubinode_navigator}/scripts/preflight-check.sh 2>/dev/null | tail -20 || echo "Preflight check script not found"`

Deployment options:

1. **Full Stack**: ./deploy-qubinode-with-airflow.sh
1. **Airflow Only**: cd airflow && make up
1. **With Vault**: cd airflow && make up-vault
1. **With Lineage**: Services start by default with Marquez

For full deployment:

```bash
./deploy-qubinode-with-airflow.sh
```

For Airflow-only:

```bash
cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow && make install
```

Before deploying, verify:

- Prerequisites cloned (/opt/qubinode-pipelines)
- Sufficient system resources
- No conflicting services on ports (8888, 5432, 8889, 5001, 3000)

IMPORTANT: Deployment may take several minutes. Monitor progress in logs.
