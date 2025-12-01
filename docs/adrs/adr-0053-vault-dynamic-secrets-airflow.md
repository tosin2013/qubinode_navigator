# ADR-0053: Dynamic Secrets for Apache Airflow Tasks

## Status
Accepted

## Date
2025-12-01

## Context

Airflow DAGs in Qubinode Navigator perform operations that require credentials:

1. **Database Operations**: PostgreSQL, Redis connections for data pipelines
2. **Cloud Deployments**: AWS, GCP, Azure credentials for VM provisioning
3. **SSH Access**: Keys for connecting to deployed VMs
4. **API Access**: External service API keys

Currently, these credentials are:
- Stored as static Airflow connections/variables
- Long-lived (months or years)
- Manually rotated (if at all)
- Shared across all DAGs regardless of need

This creates security risks:
- **Blast Radius**: Compromised credential exposes all resources it can access
- **Stale Credentials**: Unused credentials remain active indefinitely
- **Over-Provisioning**: DAGs have access to more than they need
- **No Expiration**: Credentials don't expire after task completion

## Decision

Leverage Vault's dynamic secrets engines to issue short-lived, task-scoped credentials for Airflow DAGs. Credentials are generated on-demand, used for the specific task, and automatically expire.

### Dynamic Secrets Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Airflow DAG Execution                        │
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│  │  Task 1  │───▶│  Task 2  │───▶│  Task 3  │───▶│  Task 4  │ │
│  │  (init)  │    │ (deploy) │    │(validate)│    │(cleanup) │ │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘ │
│                        │                                        │
│                        │ Request dynamic creds                  │
│                        ▼                                        │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    HashiCorp Vault                               │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Dynamic Secrets Engines                     │   │
│  │                                                          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │   │
│  │  │ Database │  │   AWS    │  │   SSH    │              │   │
│  │  │  Engine  │  │  Engine  │  │  Engine  │              │   │
│  │  │          │  │          │  │          │              │   │
│  │  │ postgres │  │  sts/    │  │ sign/    │              │   │
│  │  │ /creds/  │  │  creds/  │  │ issue/   │              │   │
│  │  │ airflow  │  │  deploy  │  │ vm-admin │              │   │
│  │  └──────────┘  └──────────┘  └──────────┘              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Credentials generated with:                                     │
│  - TTL: 1 hour (configurable per role)                          │
│  - Max TTL: 24 hours                                             │
│  - Auto-revocation on lease expiry                              │
└─────────────────────────────────────────────────────────────────┘
```

### Secrets Engine Configuration

#### 1. Database Secrets Engine (PostgreSQL)

```hcl
# Enable database secrets engine
vault secrets enable database

# Configure PostgreSQL connection
vault write database/config/qubinode-postgres \
    plugin_name=postgresql-database-plugin \
    allowed_roles="airflow-readonly,airflow-readwrite" \
    connection_url="postgresql://{{username}}:{{password}}@localhost:5432/airflow?sslmode=disable" \
    username="vault_admin" \
    password="vault_admin_password"

# Create read-only role for DAGs
vault write database/roles/airflow-readonly \
    db_name=qubinode-postgres \
    creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
    revocation_statements="DROP ROLE IF EXISTS \"{{name}}\";" \
    default_ttl="1h" \
    max_ttl="24h"

# Create read-write role for migration DAGs
vault write database/roles/airflow-readwrite \
    db_name=qubinode-postgres \
    creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
    revocation_statements="DROP ROLE IF EXISTS \"{{name}}\";" \
    default_ttl="30m" \
    max_ttl="4h"
```

#### 2. AWS Secrets Engine

```hcl
# Enable AWS secrets engine
vault secrets enable aws

# Configure AWS root credentials
vault write aws/config/root \
    access_key=AKIAXXXXXXXXXXXXXXXX \
    secret_key=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX \
    region=us-east-1

# Create role for VM deployment
vault write aws/roles/vm-deploy \
    credential_type=iam_user \
    policy_document=-<<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:RunInstances",
        "ec2:TerminateInstances",
        "ec2:DescribeInstances",
        "ec2:CreateTags"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create STS role for temporary credentials
vault write aws/roles/vm-deploy-sts \
    credential_type=assumed_role \
    role_arns=arn:aws:iam::123456789012:role/VaultDeployRole \
    default_sts_ttl="1h" \
    max_sts_ttl="4h"
```

#### 3. SSH Secrets Engine

```hcl
# Enable SSH secrets engine
vault secrets enable ssh

# Configure CA for signing
vault write ssh/config/ca generate_signing_key=true

# Create role for VM admin access
vault write ssh/roles/vm-admin \
    key_type=ca \
    default_user=admin \
    allowed_users="admin,root,qubinode" \
    allowed_extensions="permit-pty,permit-port-forwarding" \
    ttl="30m" \
    max_ttl="4h"
```

### Airflow Integration

#### VaultDynamicSecretsOperator

```python
# airflow/plugins/qubinode/vault/operators.py
"""
Vault Dynamic Secrets Operators for Airflow
ADR-0053: Dynamic Secrets for Apache Airflow Tasks
"""

from typing import Optional, Dict, Any
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
import hvac


class VaultDynamicSecretsOperator(BaseOperator):
    """
    Operator to fetch dynamic secrets from Vault.

    Credentials are automatically revoked when the DAG run completes
    or after the TTL expires, whichever comes first.
    """

    template_fields = ('vault_path', 'output_key')

    @apply_defaults
    def __init__(
        self,
        vault_path: str,
        output_key: str = 'credentials',
        vault_conn_id: str = 'vault_default',
        ttl: Optional[str] = None,
        revoke_on_completion: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.vault_path = vault_path
        self.output_key = output_key
        self.vault_conn_id = vault_conn_id
        self.ttl = ttl
        self.revoke_on_completion = revoke_on_completion

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch dynamic credentials from Vault."""
        client = self._get_vault_client()

        # Read dynamic secret
        response = client.read(self.vault_path)

        if not response:
            raise ValueError(f"No secret found at {self.vault_path}")

        credentials = response['data']
        lease_id = response.get('lease_id')
        lease_duration = response.get('lease_duration')

        self.log.info(
            f"Obtained dynamic credentials from {self.vault_path}, "
            f"lease_id={lease_id}, ttl={lease_duration}s"
        )

        # Store lease_id for cleanup
        if lease_id and self.revoke_on_completion:
            context['ti'].xcom_push(
                key=f'{self.output_key}_lease_id',
                value=lease_id
            )

        # Push credentials to XCom (encrypted)
        context['ti'].xcom_push(key=self.output_key, value=credentials)

        return credentials

    def _get_vault_client(self) -> hvac.Client:
        """Get authenticated Vault client."""
        from airflow.hooks.base import BaseHook

        conn = BaseHook.get_connection(self.vault_conn_id)

        client = hvac.Client(url=conn.host)

        # AppRole authentication
        if conn.login and conn.password:
            client.auth.approle.login(
                role_id=conn.login,
                secret_id=conn.password
            )

        return client


class VaultDatabaseCredsOperator(VaultDynamicSecretsOperator):
    """Specialized operator for database credentials."""

    def __init__(self, db_role: str, db_name: str = 'database', **kwargs):
        vault_path = f'{db_name}/creds/{db_role}'
        super().__init__(vault_path=vault_path, **kwargs)


class VaultAWSCredsOperator(VaultDynamicSecretsOperator):
    """Specialized operator for AWS credentials."""

    def __init__(self, aws_role: str, **kwargs):
        vault_path = f'aws/creds/{aws_role}'
        super().__init__(vault_path=vault_path, **kwargs)


class VaultSSHSignOperator(BaseOperator):
    """Operator to sign SSH public keys with Vault CA."""

    template_fields = ('public_key', 'vault_role')

    @apply_defaults
    def __init__(
        self,
        public_key: str,
        vault_role: str = 'vm-admin',
        valid_principals: str = 'admin',
        ttl: str = '30m',
        output_key: str = 'signed_key',
        **kwargs
    ):
        super().__init__(**kwargs)
        self.public_key = public_key
        self.vault_role = vault_role
        self.valid_principals = valid_principals
        self.ttl = ttl
        self.output_key = output_key

    def execute(self, context: Dict[str, Any]) -> str:
        """Sign SSH public key with Vault CA."""
        client = self._get_vault_client()

        response = client.secrets.ssh.sign_ssh_key(
            name=self.vault_role,
            public_key=self.public_key,
            valid_principals=self.valid_principals,
            ttl=self.ttl
        )

        signed_key = response['data']['signed_key']

        self.log.info(f"SSH key signed with role {self.vault_role}, ttl={self.ttl}")

        context['ti'].xcom_push(key=self.output_key, value=signed_key)

        return signed_key
```

#### Example DAG Using Dynamic Secrets

```python
# airflow/dags/examples/vault_dynamic_secrets_example.py
"""
Example DAG demonstrating Vault dynamic secrets usage.
ADR-0053: Dynamic Secrets for Apache Airflow Tasks
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from qubinode.vault.operators import (
    VaultDatabaseCredsOperator,
    VaultAWSCredsOperator,
    VaultSSHSignOperator
)

default_args = {
    'owner': 'qubinode',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='vault_dynamic_secrets_example',
    default_args=default_args,
    description='Demonstrates Vault dynamic secrets for secure credential management',
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['vault', 'security', 'example'],
) as dag:

    # Task 1: Get dynamic PostgreSQL credentials
    get_db_creds = VaultDatabaseCredsOperator(
        task_id='get_db_credentials',
        db_role='airflow-readonly',
        output_key='db_creds',
    )

    # Task 2: Use database credentials
    def query_database(**context):
        """Use dynamic credentials to query database."""
        import psycopg2

        creds = context['ti'].xcom_pull(
            task_ids='get_db_credentials',
            key='db_creds'
        )

        conn = psycopg2.connect(
            host='localhost',
            database='airflow',
            user=creds['username'],
            password=creds['password']
        )

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM dag_run")
        result = cursor.fetchone()

        print(f"Total DAG runs: {result[0]}")

        conn.close()

        return result[0]

    use_db_creds = PythonOperator(
        task_id='use_db_credentials',
        python_callable=query_database,
    )

    # Task 3: Get AWS credentials for cloud deployment
    get_aws_creds = VaultAWSCredsOperator(
        task_id='get_aws_credentials',
        aws_role='vm-deploy-sts',
        output_key='aws_creds',
    )

    # Task 4: Sign SSH key for VM access
    sign_ssh_key = VaultSSHSignOperator(
        task_id='sign_ssh_key',
        public_key='{{ var.value.ssh_public_key }}',
        vault_role='vm-admin',
        ttl='1h',
        output_key='signed_ssh_key',
    )

    # Define task dependencies
    get_db_creds >> use_db_creds
    get_aws_creds >> sign_ssh_key
```

## Consequences

### Positive

- **Reduced Blast Radius**: Compromised credential only valid for minutes/hours, not months
- **Automatic Expiration**: No manual cleanup of stale credentials
- **Task-Scoped Access**: Each task gets only the permissions it needs
- **Audit Trail**: Every credential request logged in Vault
- **No Credential Storage**: DAGs never store long-lived secrets

### Negative

- **Increased Latency**: Each task must request credentials from Vault
- **Vault Dependency**: Task failure if Vault is unavailable
- **Complexity**: More moving parts in credential flow
- **Lease Management**: Must handle lease renewal for long-running tasks

### Mitigations

| Concern | Mitigation |
|---------|------------|
| Latency | Connection pooling; credential caching within task |
| Vault availability | HA Vault cluster; retry with exponential backoff |
| Complexity | Wrapper operators; sensible defaults |
| Lease expiry | Auto-renewal; graceful handling of revocation |

## Implementation Plan

### Phase 1: Database Dynamic Secrets
1. Configure PostgreSQL secrets engine
2. Create Airflow-specific roles
3. Implement VaultDatabaseCredsOperator
4. Test with example DAG

### Phase 2: Cloud Provider Secrets
1. Configure AWS secrets engine
2. Create deployment roles with least privilege
3. Implement VaultAWSCredsOperator
4. Update existing deployment DAGs

### Phase 3: SSH Certificate Authority
1. Configure SSH secrets engine as CA
2. Deploy CA public key to VMs
3. Implement VaultSSHSignOperator
4. Update VM access workflows

## References

- [Vault Database Secrets Engine](https://developer.hashicorp.com/vault/docs/secrets/databases)
- [Vault AWS Secrets Engine](https://developer.hashicorp.com/vault/docs/secrets/aws)
- [Vault SSH Secrets Engine](https://developer.hashicorp.com/vault/docs/secrets/ssh)
- [ADR-0051: HashiCorp Vault Secrets Management](./adr-0051-hashicorp-vault-secrets-management.md)
- [ADR-0052: Vault Audit Logging](./adr-0052-vault-audit-logging.md)
