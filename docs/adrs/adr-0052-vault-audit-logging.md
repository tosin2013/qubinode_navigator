# ADR-0052: Vault Audit Logging and Centralized Audit Trails

## Status

Accepted

## Date

2025-12-01

## Context

Enterprise compliance frameworks (SOC 2, PCI DSS, HIPAA, GDPR) require:

1. **Tamper-evident audit records** of all access to sensitive data
1. **End-to-end traceability** of who accessed what secrets and when
1. **Retention policies** for audit logs
1. **Alerting** on suspicious access patterns

ADR-0051 establishes HashiCorp Vault as our secrets management solution. This ADR defines the audit logging strategy to meet compliance requirements.

### Current State

Without centralized audit logging:

- No visibility into which DAGs accessed which secrets
- Cannot correlate secret access with deployment failures
- Manual compliance reporting is time-consuming and error-prone
- Security incidents lack forensic data

## Decision

Configure Vault audit devices to capture all requests and responses, forwarding logs to a centralized logging system for analysis, alerting, and compliance reporting.

### Audit Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    HashiCorp Vault                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Audit Device                            │   │
│  │  - Request: path, operation, accessor, timestamp         │   │
│  │  - Response: status, errors                              │   │
│  │  - Metadata: client IP, auth method, policies            │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                           │
                           │ syslog / file / socket
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Log Aggregation (Loki / ELK / Splunk)              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Parsing    │  │  Indexing   │  │  Retention  │             │
│  │  & Enrich   │  │  & Search   │  │  Policy     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   ┌────────────┐   ┌────────────┐   ┌────────────┐
   │  Grafana   │   │  Alerting  │   │ Compliance │
   │ Dashboards │   │  (PagerDuty│   │  Reports   │
   │            │   │   Slack)   │   │            │
   └────────────┘   └────────────┘   └────────────┘
```

### Audit Log Format

Vault audit logs are JSON-formatted with the following key fields:

```json
{
  "time": "2025-12-01T19:30:00.000Z",
  "type": "request",
  "auth": {
    "client_token": "hmac-sha256:abc123...",
    "accessor": "auth_approle_abc123",
    "display_name": "approle-airflow-scheduler",
    "policies": ["airflow-read", "default"],
    "token_policies": ["airflow-read"],
    "metadata": {
      "role_name": "airflow-scheduler"
    },
    "entity_id": "entity-uuid",
    "token_type": "service"
  },
  "request": {
    "id": "request-uuid",
    "operation": "read",
    "client_token": "hmac-sha256:abc123...",
    "path": "qubinode/secrets/airflow/connections/postgres_default",
    "remote_address": "10.0.0.50",
    "wrap_ttl": 0,
    "headers": {}
  },
  "response": {
    "data": {
      "keys": ["conn_uri"]  // Only key names, not values
    }
  }
}
```

### Audit Device Configuration

```hcl
# Enable file audit device (primary)
vault audit enable file file_path=/var/log/vault/audit.log

# Enable syslog audit device (for log aggregation)
vault audit enable syslog tag="vault" facility="LOCAL0"

# Configure log rotation
vault write sys/audit/file/tune \
  log_raw=false \
  hmac_accessor=true
```

### Log Retention Policy

| Environment | Retention Period | Storage Class         |
| ----------- | ---------------- | --------------------- |
| Development | 30 days          | Standard              |
| Staging     | 90 days          | Standard              |
| Production  | 1 year           | Archive after 90 days |
| Compliance  | 7 years          | Cold storage          |

### Alerting Rules

| Alert                  | Condition                                    | Severity | Action             |
| ---------------------- | -------------------------------------------- | -------- | ------------------ |
| Root Token Usage       | `auth.policies contains "root"`              | Critical | Page on-call       |
| Policy Denied          | `error.message contains "permission denied"` | Warning  | Slack notification |
| Unusual Access Pattern | >100 requests/min from single accessor       | High     | Investigate        |
| After-Hours Access     | Production access outside business hours     | Medium   | Log for review     |
| Failed Auth Attempts   | >5 failed auths from same IP in 5 min        | High     | Block IP, alert    |

### Compliance Dashboard Metrics

1. **Secret Access Frequency**: Which secrets are accessed most often
1. **Accessor Activity**: Which services/users access secrets
1. **Policy Violations**: Denied requests by path and accessor
1. **Token Lifecycle**: Token creation, renewal, revocation rates
1. **Auth Method Usage**: AppRole vs OIDC vs other methods

## Consequences

### Positive

- **Full Visibility**: Complete audit trail of all Vault operations
- **Compliance Ready**: Meets SOC 2, PCI DSS audit requirements
- **Forensic Capability**: Can reconstruct events during security incidents
- **Anomaly Detection**: Alerting on suspicious access patterns
- **Correlation**: Link secret access to DAG runs and deployments

### Negative

- **Log Volume**: High-traffic environments generate significant log data
- **Sensitive Data in Logs**: Request paths may reveal secret structure
- **Performance Impact**: Audit logging adds latency to Vault operations
- **Storage Costs**: Long-term retention requires substantial storage

### Mitigations

| Concern        | Mitigation                                         |
| -------------- | -------------------------------------------------- |
| Log volume     | Sampling for non-sensitive paths; tiered retention |
| Sensitive data | HMAC hashing of tokens/values; path sanitization   |
| Performance    | Async logging; dedicated audit storage             |
| Storage costs  | Compression; lifecycle policies; cold storage      |

## Implementation

### Phase 1: Basic Audit Logging

```bash
# Enable file audit device
vault audit enable file file_path=/var/log/vault/audit.log

# Verify audit device is active
vault audit list
```

### Phase 2: Log Forwarding

```yaml
# Promtail configuration for Loki
scrape_configs:
  - job_name: vault-audit
    static_configs:
      - targets:
          - localhost
        labels:
          job: vault-audit
          __path__: /var/log/vault/audit.log
    pipeline_stages:
      - json:
          expressions:
            time: time
            type: type
            path: request.path
            operation: request.operation
            accessor: auth.accessor
            policies: auth.policies
      - labels:
          type:
          operation:
```

### Phase 3: Alerting Rules

```yaml
# Grafana alerting rule
groups:
  - name: vault-security
    rules:
      - alert: VaultRootTokenUsed
        expr: |
          count_over_time({job="vault-audit"}
            |= "root"
            | json
            | auth_policies =~ ".*root.*"[5m]) > 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Root token used in Vault"
```

## References

- [Vault Audit Devices](https://developer.hashicorp.com/vault/docs/audit)
- [Vault Telemetry](https://developer.hashicorp.com/vault/docs/internals/telemetry)
- [SOC 2 Audit Requirements](https://www.aicpa.org/soc2)
- [ADR-0051: HashiCorp Vault Secrets Management](./adr-0051-hashicorp-vault-secrets-management.md)
