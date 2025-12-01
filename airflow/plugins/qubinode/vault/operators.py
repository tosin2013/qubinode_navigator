"""
Vault Dynamic Secrets Operators for Airflow
ADR-0053: Dynamic Secrets for Apache Airflow Tasks

These operators extend the official apache-airflow-providers-hashicorp
to support dynamic secrets (database, AWS, SSH) with automatic lease management.

The official provider's VaultHook is used for authentication and connection.

Usage:
    from qubinode.vault import VaultDatabaseCredsOperator

    get_creds = VaultDatabaseCredsOperator(
        task_id='get_db_creds',
        vault_conn_id='vault_default',
        db_role='airflow-readonly',
    )
"""

from typing import Optional, Dict, Any, List
import logging

from airflow.models import BaseOperator
from airflow.utils.context import Context

logger = logging.getLogger(__name__)


class VaultDynamicSecretsOperator(BaseOperator):
    """
    Base operator for fetching dynamic secrets from Vault.

    Uses the official VaultHook from apache-airflow-providers-hashicorp
    for authentication and connection management.

    Dynamic secrets are generated on-demand with a TTL and automatically
    revoked when the lease expires.

    :param vault_conn_id: Airflow connection ID for Vault
    :param vault_path: Full path to the dynamic secret (e.g., 'database/creds/my-role')
    :param output_key: XCom key to store the credentials
    :param store_lease_id: Whether to store lease_id in XCom for later revocation
    """

    template_fields = ('vault_path', 'output_key')
    ui_color = '#7B68EE'  # Medium slate blue

    def __init__(
        self,
        vault_conn_id: str = 'vault_default',
        vault_path: str = '',
        output_key: str = 'credentials',
        store_lease_id: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.vault_conn_id = vault_conn_id
        self.vault_path = vault_path
        self.output_key = output_key
        self.store_lease_id = store_lease_id

    def execute(self, context: Context) -> Dict[str, Any]:
        """Fetch dynamic credentials from Vault."""
        try:
            from airflow.providers.hashicorp.hooks.vault import VaultHook
        except ImportError:
            raise ImportError(
                "apache-airflow-providers-hashicorp is required. "
                "Install with: pip install apache-airflow-providers-hashicorp"
            )

        hook = VaultHook(vault_conn_id=self.vault_conn_id)

        self.log.info(f"Requesting dynamic credentials from {self.vault_path}")

        # Read dynamic secret - this generates new credentials
        response = hook.get_secret(secret_path=self.vault_path)

        if not response:
            raise ValueError(f"No secret found at {self.vault_path}")

        # Extract credentials and lease info
        credentials = response.get('data', response)
        lease_id = response.get('lease_id')
        lease_duration = response.get('lease_duration')

        self.log.info(
            f"Obtained dynamic credentials, "
            f"lease_id={lease_id[:20] + '...' if lease_id else 'N/A'}, "
            f"ttl={lease_duration}s"
        )

        # Store lease_id for cleanup
        if lease_id and self.store_lease_id:
            context['ti'].xcom_push(
                key=f'{self.output_key}_lease_id',
                value=lease_id
            )

        # Push credentials to XCom
        context['ti'].xcom_push(key=self.output_key, value=credentials)

        return credentials

    def get_vault_hook(self):
        """Get VaultHook instance."""
        from airflow.providers.hashicorp.hooks.vault import VaultHook
        return VaultHook(vault_conn_id=self.vault_conn_id)


class VaultDatabaseCredsOperator(VaultDynamicSecretsOperator):
    """
    Operator to fetch dynamic database credentials from Vault.

    Uses Vault's database secrets engine to generate short-lived credentials.

    :param db_role: Database role name configured in Vault
    :param mount_point: Mount point for database secrets engine (default: 'database')
    :param output_key: XCom key to store credentials (contains 'username' and 'password')

    Example:
        get_creds = VaultDatabaseCredsOperator(
            task_id='get_postgres_creds',
            db_role='airflow-readonly',
            output_key='db_creds',
        )

        # In downstream task:
        creds = context['ti'].xcom_pull(task_ids='get_postgres_creds', key='db_creds')
        conn = psycopg2.connect(user=creds['username'], password=creds['password'], ...)
    """

    template_fields = ('db_role', 'mount_point', 'output_key')

    def __init__(
        self,
        db_role: str,
        mount_point: str = 'database',
        **kwargs
    ):
        self.db_role = db_role
        self.mount_point = mount_point
        vault_path = f'{mount_point}/creds/{db_role}'
        super().__init__(vault_path=vault_path, **kwargs)


class VaultAWSCredsOperator(VaultDynamicSecretsOperator):
    """
    Operator to fetch dynamic AWS credentials from Vault.

    Uses Vault's AWS secrets engine to generate temporary IAM credentials
    or assume roles via STS.

    :param aws_role: AWS role name configured in Vault
    :param mount_point: Mount point for AWS secrets engine (default: 'aws')
    :param credential_type: Type of credentials ('creds' for IAM user, 'sts' for assumed role)
    :param ttl: TTL for the credentials (e.g., '1h', '30m')
    :param output_key: XCom key to store credentials

    Example:
        get_aws = VaultAWSCredsOperator(
            task_id='get_aws_creds',
            aws_role='deploy-role',
            credential_type='sts',
            ttl='1h',
        )

        # Credentials contain: access_key, secret_key, security_token (for STS)
    """

    template_fields = ('aws_role', 'mount_point', 'ttl', 'output_key')

    def __init__(
        self,
        aws_role: str,
        mount_point: str = 'aws',
        credential_type: str = 'creds',
        ttl: Optional[str] = None,
        **kwargs
    ):
        self.aws_role = aws_role
        self.mount_point = mount_point
        self.credential_type = credential_type
        self.ttl = ttl

        # Build path based on credential type
        if credential_type == 'sts':
            vault_path = f'{mount_point}/sts/{aws_role}'
        else:
            vault_path = f'{mount_point}/creds/{aws_role}'

        super().__init__(vault_path=vault_path, **kwargs)

    def execute(self, context: Context) -> Dict[str, Any]:
        """Fetch AWS credentials with optional TTL."""
        from airflow.providers.hashicorp.hooks.vault import VaultHook

        hook = VaultHook(vault_conn_id=self.vault_conn_id)

        self.log.info(f"Requesting AWS credentials for role {self.aws_role}")

        # For STS, we may need to pass TTL
        if self.ttl and self.credential_type == 'sts':
            # Use the underlying hvac client for more control
            client = hook.get_conn()
            response = client.secrets.aws.generate_credentials(
                name=self.aws_role,
                ttl=self.ttl,
                mount_point=self.mount_point
            )
        else:
            response = hook.get_secret(secret_path=self.vault_path)

        if not response:
            raise ValueError(f"Failed to get AWS credentials for role {self.aws_role}")

        credentials = response.get('data', response)
        lease_id = response.get('lease_id')
        lease_duration = response.get('lease_duration')

        self.log.info(
            f"Obtained AWS credentials, type={self.credential_type}, "
            f"ttl={lease_duration}s"
        )

        if lease_id and self.store_lease_id:
            context['ti'].xcom_push(
                key=f'{self.output_key}_lease_id',
                value=lease_id
            )

        context['ti'].xcom_push(key=self.output_key, value=credentials)

        return credentials


class VaultSSHSignOperator(BaseOperator):
    """
    Operator to sign SSH public keys using Vault's SSH CA.

    Uses Vault's SSH secrets engine in CA mode to sign public keys,
    enabling certificate-based SSH authentication.

    :param public_key: SSH public key to sign (or XCom reference)
    :param vault_role: SSH role configured in Vault
    :param valid_principals: Comma-separated list of valid principals
    :param ttl: TTL for the signed certificate
    :param extensions: SSH certificate extensions
    :param vault_conn_id: Airflow connection ID for Vault
    :param mount_point: Mount point for SSH secrets engine
    :param output_key: XCom key to store signed certificate

    Example:
        sign_key = VaultSSHSignOperator(
            task_id='sign_ssh_key',
            public_key='{{ ti.xcom_pull(task_ids="generate_key", key="public_key") }}',
            vault_role='vm-admin',
            valid_principals='admin,deploy',
            ttl='1h',
        )
    """

    template_fields = ('public_key', 'vault_role', 'valid_principals', 'ttl', 'output_key')
    ui_color = '#7B68EE'

    def __init__(
        self,
        public_key: str,
        vault_role: str = 'default',
        valid_principals: str = '',
        ttl: str = '30m',
        extensions: Optional[Dict[str, str]] = None,
        vault_conn_id: str = 'vault_default',
        mount_point: str = 'ssh',
        output_key: str = 'signed_key',
        **kwargs
    ):
        super().__init__(**kwargs)
        self.public_key = public_key
        self.vault_role = vault_role
        self.valid_principals = valid_principals
        self.ttl = ttl
        self.extensions = extensions or {'permit-pty': ''}
        self.vault_conn_id = vault_conn_id
        self.mount_point = mount_point
        self.output_key = output_key

    def execute(self, context: Context) -> str:
        """Sign SSH public key with Vault CA."""
        try:
            from airflow.providers.hashicorp.hooks.vault import VaultHook
        except ImportError:
            raise ImportError(
                "apache-airflow-providers-hashicorp is required. "
                "Install with: pip install apache-airflow-providers-hashicorp"
            )

        hook = VaultHook(vault_conn_id=self.vault_conn_id)
        client = hook.get_conn()

        self.log.info(f"Signing SSH key with role {self.vault_role}, ttl={self.ttl}")

        response = client.secrets.ssh.sign_ssh_key(
            name=self.vault_role,
            public_key=self.public_key,
            valid_principals=self.valid_principals,
            ttl=self.ttl,
            extensions=self.extensions,
            mount_point=self.mount_point
        )

        signed_key = response['data']['signed_key']

        self.log.info(f"SSH key signed successfully")

        context['ti'].xcom_push(key=self.output_key, value=signed_key)

        return signed_key


class VaultLeaseRevokeOperator(BaseOperator):
    """
    Operator to revoke Vault leases.

    Used to clean up dynamic credentials before their natural expiration.
    Typically used in DAG cleanup tasks or on_failure callbacks.

    :param lease_ids: List of lease IDs to revoke, or XCom references
    :param lease_id_xcom_keys: List of XCom keys containing lease IDs
    :param vault_conn_id: Airflow connection ID for Vault

    Example:
        cleanup = VaultLeaseRevokeOperator(
            task_id='cleanup_credentials',
            lease_id_xcom_keys=['db_creds_lease_id', 'aws_creds_lease_id'],
            trigger_rule='all_done',  # Run even if upstream fails
        )
    """

    template_fields = ('lease_ids',)
    ui_color = '#DC143C'  # Crimson

    def __init__(
        self,
        lease_ids: Optional[List[str]] = None,
        lease_id_xcom_keys: Optional[List[str]] = None,
        vault_conn_id: str = 'vault_default',
        **kwargs
    ):
        super().__init__(**kwargs)
        self.lease_ids = lease_ids or []
        self.lease_id_xcom_keys = lease_id_xcom_keys or []
        self.vault_conn_id = vault_conn_id

    def execute(self, context: Context) -> Dict[str, Any]:
        """Revoke Vault leases."""
        try:
            from airflow.providers.hashicorp.hooks.vault import VaultHook
        except ImportError:
            raise ImportError(
                "apache-airflow-providers-hashicorp is required. "
                "Install with: pip install apache-airflow-providers-hashicorp"
            )

        hook = VaultHook(vault_conn_id=self.vault_conn_id)
        client = hook.get_conn()

        # Collect lease IDs from XCom
        all_lease_ids = list(self.lease_ids)

        for xcom_key in self.lease_id_xcom_keys:
            lease_id = context['ti'].xcom_pull(key=xcom_key)
            if lease_id:
                all_lease_ids.append(lease_id)

        results = {
            'revoked': [],
            'failed': [],
            'not_found': []
        }

        for lease_id in all_lease_ids:
            if not lease_id:
                continue

            try:
                self.log.info(f"Revoking lease: {lease_id[:20]}...")
                client.sys.revoke_lease(lease_id=lease_id)
                results['revoked'].append(lease_id)
            except Exception as e:
                if 'invalid lease' in str(e).lower():
                    self.log.warning(f"Lease not found (may have expired): {lease_id[:20]}...")
                    results['not_found'].append(lease_id)
                else:
                    self.log.error(f"Failed to revoke lease {lease_id[:20]}...: {e}")
                    results['failed'].append(lease_id)

        self.log.info(
            f"Lease cleanup complete: "
            f"{len(results['revoked'])} revoked, "
            f"{len(results['not_found'])} expired, "
            f"{len(results['failed'])} failed"
        )

        return results
