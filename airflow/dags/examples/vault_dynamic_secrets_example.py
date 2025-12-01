"""
Example DAG: Vault Dynamic Secrets
ADR-0051: HashiCorp Vault Secrets Management
ADR-0053: Dynamic Secrets for Airflow Tasks

This DAG demonstrates how to use Vault dynamic secrets in Airflow workflows:
1. Fetch dynamic database credentials
2. Use credentials to query database
3. Clean up credentials (revoke lease)

Prerequisites:
- Vault running: podman-compose --profile vault up -d
- Vault configured: ./scripts/setup-vault.sh
- Airflow connection 'vault_default' configured

Usage:
    Trigger this DAG manually from the Airflow UI to test Vault integration.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

# Import Qubinode Vault operators
try:
    from qubinode.vault import (
        VaultDatabaseCredsOperator,
        VaultLeaseRevokeOperator,
    )
    VAULT_AVAILABLE = True
except ImportError:
    VAULT_AVAILABLE = False

default_args = {
    'owner': 'qubinode',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}


def check_vault_available(**context):
    """Check if Vault operators are available."""
    if not VAULT_AVAILABLE:
        raise ImportError(
            "Vault operators not available. Install apache-airflow-providers-hashicorp "
            "and ensure qubinode.vault plugin is loaded."
        )
    return True


def use_database_credentials(**context):
    """
    Use the dynamic database credentials to query the database.

    The credentials were obtained by VaultDatabaseCredsOperator and stored in XCom.
    They will automatically expire after the TTL (1 hour by default).
    """
    import psycopg2

    # Pull credentials from XCom
    ti = context['ti']
    creds = ti.xcom_pull(task_ids='get_db_credentials', key='db_creds')

    if not creds:
        raise ValueError("No database credentials found in XCom")

    username = creds.get('username')
    password = creds.get('password')

    print(f"Using dynamic credentials: username={username}")
    print(f"Credential TTL: credentials will auto-expire")

    # Connect to database with dynamic credentials
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='airflow',
            user=username,
            password=password
        )

        cursor = conn.cursor()

        # Example query - count DAG runs
        cursor.execute("SELECT COUNT(*) FROM dag_run")
        dag_run_count = cursor.fetchone()[0]
        print(f"Total DAG runs in database: {dag_run_count}")

        # Example query - list recent DAG runs
        cursor.execute("""
            SELECT dag_id, run_id, state, start_date
            FROM dag_run
            ORDER BY start_date DESC
            LIMIT 5
        """)
        recent_runs = cursor.fetchall()
        print(f"Recent DAG runs:")
        for run in recent_runs:
            print(f"  - {run[0]}: {run[2]} ({run[3]})")

        cursor.close()
        conn.close()

        return {
            'dag_run_count': dag_run_count,
            'recent_runs': len(recent_runs)
        }

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        raise


def log_credential_usage(**context):
    """Log information about credential usage for audit purposes."""
    ti = context['ti']

    # Get lease information
    lease_id = ti.xcom_pull(task_ids='get_db_credentials', key='db_creds_lease_id')
    query_result = ti.xcom_pull(task_ids='use_db_credentials')

    print("=" * 60)
    print("CREDENTIAL USAGE AUDIT LOG")
    print("=" * 60)
    print(f"DAG Run ID: {context['run_id']}")
    print(f"Task Instance: {ti.task_id}")
    print(f"Execution Date: {context['execution_date']}")
    print(f"Vault Lease ID: {lease_id[:20] if lease_id else 'N/A'}...")
    print(f"Query Results: {query_result}")
    print("=" * 60)

    return {
        'lease_id': lease_id,
        'query_result': query_result
    }


# Only create DAG if Vault operators are available
if VAULT_AVAILABLE:
    with DAG(
        dag_id='vault_dynamic_secrets_example',
        default_args=default_args,
        description='Demonstrates Vault dynamic secrets for secure database access',
        schedule_interval=None,  # Manual trigger only
        start_date=datetime(2025, 1, 1),
        catchup=False,
        tags=['vault', 'security', 'example', 'adr-0051', 'adr-0053'],
        doc_md=__doc__,
    ) as dag:

        # Task 1: Check prerequisites
        check_prereqs = PythonOperator(
            task_id='check_prerequisites',
            python_callable=check_vault_available,
        )

        # Task 2: Get dynamic database credentials from Vault
        get_db_creds = VaultDatabaseCredsOperator(
            task_id='get_db_credentials',
            vault_conn_id='vault_default',
            db_role='airflow-readonly',
            mount_point='database',
            output_key='db_creds',
        )

        # Task 3: Use the credentials to query database
        use_creds = PythonOperator(
            task_id='use_db_credentials',
            python_callable=use_database_credentials,
        )

        # Task 4: Log usage for audit
        audit_log = PythonOperator(
            task_id='audit_log',
            python_callable=log_credential_usage,
        )

        # Task 5: Cleanup - revoke credentials early (optional, they expire anyway)
        cleanup = VaultLeaseRevokeOperator(
            task_id='cleanup_credentials',
            vault_conn_id='vault_default',
            lease_id_xcom_keys=['db_creds_lease_id'],
            trigger_rule=TriggerRule.ALL_DONE,  # Run even if upstream fails
        )

        # Define task dependencies
        check_prereqs >> get_db_creds >> use_creds >> audit_log >> cleanup

else:
    # Create a placeholder DAG that explains the issue
    with DAG(
        dag_id='vault_dynamic_secrets_example',
        default_args=default_args,
        description='Vault integration not available - install apache-airflow-providers-hashicorp',
        schedule_interval=None,
        start_date=datetime(2025, 1, 1),
        catchup=False,
        tags=['vault', 'disabled'],
    ) as dag:

        def show_installation_instructions():
            raise ImportError(
                "Vault operators not available.\n\n"
                "To enable Vault integration:\n"
                "1. Rebuild Airflow image: podman-compose build\n"
                "2. Start Vault: podman-compose --profile vault up -d\n"
                "3. Configure Vault: ./scripts/setup-vault.sh\n"
                "4. Create 'vault_default' connection in Airflow UI"
            )

        PythonOperator(
            task_id='show_instructions',
            python_callable=show_installation_instructions,
        )
