"""
Qubinode Vault Integration for Airflow
ADR-0051: HashiCorp Vault Secrets Management
ADR-0053: Dynamic Secrets for Airflow Tasks

This package extends the official apache-airflow-providers-hashicorp with:
- Dynamic secrets operators (database, AWS STS, SSH signing)
- Lease management for automatic credential cleanup
- Integration with Qubinode deployment workflows

The official provider handles:
- VaultBackend: Secrets backend for connections/variables
- VaultHook: Connection management and authentication

Install the official provider:
    pip install apache-airflow-providers-hashicorp

References:
- https://airflow.apache.org/docs/apache-airflow-providers-hashicorp/stable/
- https://airflow.apache.org/docs/apache-airflow-providers-hashicorp/stable/secrets-backends/hashicorp-vault.html
"""

__version__ = "1.0.0"
__all__ = [
    # Dynamic secrets operators (Qubinode extensions)
    "VaultDynamicSecretsOperator",
    "VaultDatabaseCredsOperator",
    "VaultAWSCredsOperator",
    "VaultSSHSignOperator",
    "VaultLeaseRevokeOperator",
]


# Lazy imports to avoid loading hvac if not installed
def __getattr__(name):
    """Lazy load vault components."""
    if name in __all__:
        from . import operators

        return getattr(operators, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
