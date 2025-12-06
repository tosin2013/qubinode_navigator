______________________________________________________________________

## description: Backup Qubinode Navigator configuration and data allowed-tools: Bash(pg_dump:*), Bash(tar:*), Bash(ls:*), Bash(date:*) argument-hint: \[backup-type\]

# Backup Qubinode Navigator

You are helping backup Qubinode Navigator.

Backup request: $ARGUMENTS

Critical data to backup:

1. **Airflow metadata** (PostgreSQL)
1. **DAG definitions** (airflow/dags/)
1. **Configuration** (vault.yml, inventory)
1. **Certificates** (/etc/pki/tls/)
1. **RAG knowledge base** (pgvector data)

Backup PostgreSQL:
!`echo "PostgreSQL backup command:" && echo "pg_dump -h localhost -U airflow airflow > airflow_backup_$(date +%Y%m%d).sql"`

Backup configuration:
!`echo "Configuration backup:" && echo "tar -czf qubinode_config_$(date +%Y%m%d).tar.gz ${QUBINODE_HOME:-$HOME/qubinode_navigator}/vault.yml ${QUBINODE_HOME:-$HOME/qubinode_navigator}/inventory/ ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow/config/"`

Backup DAGs:
!`echo "DAG backup:" && echo "tar -czf qubinode_dags_$(date +%Y%m%d).tar.gz ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow/dags/"`

List current backup-worthy files:
!`ls -la ${QUBINODE_HOME:-$HOME/qubinode_navigator}/vault.yml 2>/dev/null`
!`ls -la ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow/dags/*.py 2>/dev/null | wc -l`

IMPORTANT:

- Store backups off-system
- Test restore procedures periodically
- Encrypt sensitive data (vault.yml, certificates)
