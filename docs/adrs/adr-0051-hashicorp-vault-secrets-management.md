# ADR-0051: HashiCorp Vault Integration for Centralized Secrets Management

## Status

Accepted

## Date

2025-12-01

## Context

Qubinode Navigator manages multiple services (Airflow, API, CLI, VMs) that require access to secrets such as database credentials, API keys, cloud provider credentials, and SSH keys. Currently, secrets are managed through:

- Environment variables in docker-compose files
- Ansible vault for playbook secrets
- Manual configuration of Airflow connections/variables
- SSH keys mounted from host filesystem

This approach has several problems:

1. **Security Risk**: Secrets scattered across multiple locations increase attack surface
1. **Inconsistency**: Dev/staging/prod environments may have configuration drift
1. **Manual Rotation**: No automated credential rotation
1. **Audit Gap**: Difficult to track who accessed what secrets and when
1. **Compliance**: Enterprise environments require centralized secrets management (SOC 2, PCI DSS)

HashiCorp Vault provides a unified solution for secrets management with features aligned to our requirements:

- Centralized storage with fine-grained access control
- Dynamic secrets with automatic expiration
- Audit logging for compliance
- Integration with Kubernetes, Ansible, and Airflow

## Decision

Adopt HashiCorp Vault as the single source of truth for secrets management across all Qubinode Navigator components.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    HashiCorp Vault Cluster                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  KV v2      │  │  Database   │  │  AWS/Cloud  │             │
│  │  Secrets    │  │  Secrets    │  │  Secrets    │             │
│  │  Engine     │  │  Engine     │  │  Engine     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│         │                │                │                      │
│         └────────────────┼────────────────┘                      │
│                          │                                       │
│              ┌───────────┴───────────┐                          │
│              │   Vault Policies &    │                          │
│              │   Auth Methods        │                          │
│              └───────────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│   Airflow     │  │   Ansible     │  │   CLI/API     │
│   (AppRole)   │  │   (AppRole)   │  │   (OIDC/JWT)  │
└───────────────┘  └───────────────┘  └───────────────┘
```

### Path Structure

```
qubinode/
├── config/                    # Non-sensitive configuration (KV v2)
│   ├── dev/
│   │   ├── airflow/
│   │   └── api/
│   ├── staging/
│   └── prod/
├── secrets/                   # Sensitive secrets (KV v2)
│   ├── airflow/
│   │   ├── connections/       # Airflow connection strings
│   │   ├── variables/         # Airflow variables
│   │   └── fernet-key
│   ├── database/
│   │   ├── postgres/
│   │   └── redis/
│   ├── cloud/
│   │   ├── aws/
│   │   ├── gcp/
│   │   └── azure/
│   └── ssh/
│       └── vm-deploy-key
└── dynamic/                   # Dynamic secrets engines
    ├── database/              # PostgreSQL dynamic credentials
    └── aws/                   # AWS STS credentials
```

### Authentication Methods

| Component                | Auth Method | Policy              |
| ------------------------ | ----------- | ------------------- |
| Airflow Scheduler/Worker | AppRole     | `airflow-read`      |
| Airflow DAGs (runtime)   | AppRole     | `airflow-dag-{env}` |
| Ansible Playbooks        | AppRole     | `ansible-deploy`    |
| CLI Users                | OIDC/LDAP   | `operator-{team}`   |
| CI/CD Pipeline           | JWT/GitHub  | `ci-deploy-{env}`   |

### Airflow Integration

The Vault provider will be implemented as an Airflow plugin that:

1. **Secrets Backend**: Replaces default secrets backend to fetch connections/variables from Vault
1. **VaultOperator**: Operator for DAGs to read/write secrets
1. **VaultHook**: Hook for custom secret operations
1. **Dynamic Credentials**: Request short-lived credentials for database/cloud operations

```python
# Example: Airflow DAG using Vault dynamic secrets
from qubinode.vault import VaultOperator

with DAG('deploy_vm') as dag:
    get_aws_creds = VaultOperator(
        task_id='get_aws_credentials',
        vault_path='dynamic/aws/creds/deploy-role',
        output_key='aws_creds'
    )

    deploy = KcliOperator(
        task_id='deploy_vm',
        # Credentials automatically injected from Vault
    )
```

## Consequences

### Positive

- **Single Source of Truth**: All secrets centrally managed with consistent access patterns
- **Dynamic Secrets**: Short-lived credentials reduce blast radius of compromise
- **Audit Trail**: Complete visibility into who accessed what secrets and when
- **Automated Rotation**: Vault handles credential rotation automatically
- **Environment Consistency**: Same code works across dev/staging/prod with environment-specific paths
- **Compliance Ready**: Meets enterprise security requirements (SOC 2, PCI DSS, HIPAA)

### Negative

- **Additional Infrastructure**: Requires running and maintaining Vault cluster
- **Complexity**: Learning curve for Vault concepts (policies, auth methods, engines)
- **Availability Dependency**: Vault downtime impacts all secret-dependent operations
- **Migration Effort**: Existing secrets must be migrated to Vault

### Risks & Mitigations

| Risk                   | Mitigation                                          |
| ---------------------- | --------------------------------------------------- |
| Vault unavailability   | Deploy HA cluster; implement caching in clients     |
| Misconfigured policies | Infrastructure-as-code for policies; review process |
| Secret sprawl in Vault | Path conventions; periodic audit of unused secrets  |
| Performance impact     | Connection pooling; response caching with TTL       |

## Alternatives Considered

### 1. Continue with Environment Variables + Ansible Vault

- **Pros**: No new infrastructure; familiar tooling
- **Cons**: No dynamic secrets; limited audit; manual rotation

### 2. Kubernetes Secrets + External Secrets Operator

- **Pros**: Native K8s integration
- **Cons**: Requires K8s; limited to K8s workloads; no dynamic secrets

### 3. AWS Secrets Manager / Azure Key Vault

- **Pros**: Managed service; cloud-native
- **Cons**: Cloud vendor lock-in; breaks multi-cloud neutrality; per-secret costs

### 4. CyberArk / Thycotic

- **Pros**: Enterprise PAM features
- **Cons**: High cost; heavyweight for our use case

## Implementation Plan

### Phase 1: Foundation (Week 1-2)

- [ ] Deploy Vault server (dev mode initially, then HA)
- [ ] Configure KV v2 secrets engine
- [ ] Set up AppRole auth for Airflow
- [ ] Create base policies

### Phase 2: Airflow Integration (Week 3-4)

- [ ] Implement Vault secrets backend for Airflow
- [ ] Create VaultOperator and VaultHook
- [ ] Migrate existing Airflow connections to Vault
- [ ] Update DAGs to use Vault-backed connections

### Phase 3: Dynamic Secrets (Week 5-6)

- [ ] Configure database secrets engine for PostgreSQL
- [ ] Configure AWS secrets engine for cloud deployments
- [ ] Update deployment DAGs to use dynamic credentials

### Phase 4: Audit & Compliance (Week 7-8)

- [ ] Enable audit logging
- [ ] Set up log forwarding to centralized logging
- [ ] Create compliance reports
- [ ] Document runbooks

## References

- [HashiCorp Vault Documentation](https://developer.hashicorp.com/vault/docs)
- [Airflow Secrets Backend](https://airflow.apache.org/docs/apache-airflow/stable/security/secrets/secrets-backend/index.html)
- [Vault Database Secrets Engine](https://developer.hashicorp.com/vault/docs/secrets/databases)
- [ADR-0049: Multi-Agent LLM Memory Architecture](./adr-0049-multi-agent-llm-memory-architecture.md) (RAG store uses pgvector)
- [ADR-0050: Hybrid Host-Container Architecture](./adr-0050-hybrid-host-container-architecture.md)
