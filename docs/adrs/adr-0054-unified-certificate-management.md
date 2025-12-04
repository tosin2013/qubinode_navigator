# ADR-0054: Unified Certificate Management

## Status

Accepted

## Date

2025-12-01

## Context

Qubinode Navigator manages infrastructure across various environments:

- **Disconnected/air-gapped** - No internet access, need internal PKI
- **Hybrid** - Some services internal, some public-facing
- **Cloud/public** - Services exposed to internet needing trusted certificates

Different certificate authorities (CAs) serve different needs:

| CA                | Best For                                     | Trust                             | Auto-Renewal        |
| ----------------- | -------------------------------------------- | --------------------------------- | ------------------- |
| **FreeIPA CA**    | Domain-joined hosts, Kerberos environments   | Private (enterprise PKI)          | Yes (certmonger)    |
| **Step-CA**       | Internal services, disconnected environments | Private (must distribute root CA) | Yes (ACME)          |
| **Vault PKI**     | Dynamic/short-lived certs, microservices     | Private (must distribute root CA) | Yes (via operators) |
| **Let's Encrypt** | Public-facing services                       | Public (trusted by browsers)      | Yes (ACME/certbot)  |

Currently, certificate management is fragmented:

- Step-CA DAGs exist but require manual intervention
- Vault SSH signing is available but not PKI
- No Let's Encrypt integration
- No unified interface for requesting certificates

## Decision

Implement a **unified certificate management system** that:

1. **Single entry point** - One script/DAG to request certificates from any CA
1. **Automatic CA selection** - Choose appropriate CA based on use case
1. **Service-aware installation** - Automatically configure certificates for the target service
1. **Automatic renewal** - Set up renewal before expiration

### Architecture

```
+------------------------------------------------------------------+
|                 Unified Certificate Management                    |
+------------------------------------------------------------------+

                    +------------------------+
                    |   qubinode-cert        |
                    |   (Universal CLI)      |
                    +------------------------+
                              |
     +------------+-----------+-----------+------------+
     |            |           |           |            |
     v            v           v           v            v
+---------+ +---------+ +----------+ +----------+ +--------+
| FreeIPA | | Step-CA | | Vault    | | Let's    | | Self-  |
| CA      | | (ACME)  | | PKI      | | Encrypt  | | Signed |
+---------+ +---------+ +----------+ +----------+ +--------+
        |                     |                     |
        +---------------------+---------------------+
                              |
                    +------------------------+
                    |  Certificate Store     |
                    |  /etc/qubinode/certs/  |
                    +------------------------+
                              |
        +---------------------+---------------------+
        |                     |                     |
        v                     v                     v
+---------------+    +----------------+    +------------------+
|    Nginx      |    |    Harbor      |    |   PostgreSQL     |
+---------------+    +----------------+    +------------------+
```

### CA Selection Logic

```
qubinode-cert request <hostname> --service <service>

1. Is hostname publicly resolvable AND port 80/443 accessible?
   └── Yes → Let's Encrypt (free, trusted)
   └── No → Continue

2. Is host joined to FreeIPA domain?
   └── Yes → FreeIPA CA (enterprise PKI, certmonger)
   └── No → Continue

3. Is Vault PKI configured AND service needs short-lived certs?
   └── Yes → Vault PKI (dynamic, auto-revoke)
   └── No → Continue

4. Is Step-CA available?
   └── Yes → Step-CA (internal PKI)
   └── No → Continue

5. Generate self-signed certificate (fallback)
   └── Warn user about trust implications

Override: --ca=freeipa|step-ca|vault|letsencrypt|self-signed
```

### Universal Certificate Request Script

**Location**: `/usr/local/bin/qubinode-cert`

```bash
qubinode-cert request <hostname> [options]
  --ca           Force specific CA (step-ca, vault, letsencrypt)
  --service      Target service (nginx, harbor, postgresql, haproxy, httpd, generic)
  --san          Additional Subject Alternative Names (comma-separated)
  --duration     Certificate duration (default: 90d for LE, 30d for internal)
  --output       Output directory (default: /etc/qubinode/certs/<hostname>/)
  --install      Auto-install certificate for the service
  --renew-hook   Command to run after renewal (e.g., "systemctl reload nginx")

qubinode-cert renew [--all | <hostname>]
  Renew certificates before expiration

qubinode-cert list
  List all managed certificates with expiry dates

qubinode-cert revoke <hostname>
  Revoke and remove certificate
```

### Certificate Storage Structure

```
/etc/qubinode/certs/
├── ca/
│   ├── step-ca-root.crt      # Step-CA root certificate
│   ├── vault-root.crt        # Vault PKI root certificate
│   └── ca-bundle.crt         # Combined CA bundle
├── <hostname>/
│   ├── cert.pem              # Certificate
│   ├── key.pem               # Private key
│   ├── chain.pem             # CA chain
│   ├── fullchain.pem         # Cert + chain (for nginx)
│   ├── .metadata.json        # CA source, expiry, service, renewal info
│   └── .renew-hook.sh        # Renewal hook script
└── inventory.json            # All managed certificates
```

### Service Integration

Each service has a handler that knows how to install certificates:

| Service    | Cert Location                   | Key Location                    | Reload Command              |
| ---------- | ------------------------------- | ------------------------------- | --------------------------- |
| nginx      | /etc/nginx/ssl/cert.pem         | /etc/nginx/ssl/key.pem          | systemctl reload nginx      |
| haproxy    | /etc/haproxy/certs/combined.pem | (combined)                      | systemctl reload haproxy    |
| httpd      | /etc/pki/tls/certs/server.crt   | /etc/pki/tls/private/server.key | systemctl reload httpd      |
| harbor     | /data/cert/server.crt           | /data/cert/server.key           | docker-compose restart      |
| postgresql | /var/lib/pgsql/data/server.crt  | /var/lib/pgsql/data/server.key  | systemctl reload postgresql |
| generic    | /etc/qubinode/certs/<hostname>/ | (same dir)                      | (none)                      |

### Automatic Renewal

A systemd timer runs daily to check and renew certificates:

```ini
# /etc/systemd/system/qubinode-cert-renew.timer
[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Renewal triggers:

- Let's Encrypt: 30 days before expiry
- Step-CA: 7 days before expiry
- Vault PKI: 1 day before expiry (short-lived by design)

### Airflow DAG Integration

**`certificate_provisioning` DAG** provides:

- Bulk certificate requests for multiple hosts
- Certificate inventory reporting
- Expiry alerting
- Integration with VM deployment DAGs

### Implementation Components

1. **`/usr/local/bin/qubinode-cert`** - Universal CLI script
1. **`/opt/qubinode/cert-handlers/`** - Service-specific handlers
1. **`/etc/qubinode/cert-config.yaml`** - CA configuration
1. **Airflow DAG** - `certificate_provisioning.py`
1. **Ansible role** - `qubinode.certificate` for fleet management

## Configuration

**`/etc/qubinode/cert-config.yaml`**:

```yaml
# Certificate Authority Configuration
ca:
  # Step-CA (internal PKI)
  step-ca:
    enabled: true
    url: https://step-ca-server.example.com:443
    fingerprint: "abc123..."  # Auto-discovered if not set
    provisioner: acme
    default_duration: 720h  # 30 days

  # Vault PKI
  vault:
    enabled: true
    url: http://localhost:8200
    mount_point: pki
    role: qubinode-issuer
    default_duration: 24h  # Short-lived

  # Let's Encrypt
  letsencrypt:
    enabled: true
    email: admin@example.com
    staging: false  # Use staging for testing
    challenge: http-01  # or dns-01

# Default settings
defaults:
  ca: auto  # auto-select based on environment
  output_dir: /etc/qubinode/certs
  renewal_days: 30

# Service configurations
services:
  nginx:
    cert_path: /etc/nginx/ssl/cert.pem
    key_path: /etc/nginx/ssl/key.pem
    chain_path: /etc/nginx/ssl/chain.pem
    reload_cmd: systemctl reload nginx
    user: nginx
    group: nginx
    mode: "0640"
```

## Consequences

### Positive

- **Unified interface** - One command for all certificate needs
- **Flexibility** - Right CA for each use case
- **Automation** - Auto-renewal prevents expiry outages
- **Service-aware** - Correct installation for each service
- **Auditable** - Central inventory of all certificates

### Negative

- **Complexity** - Multiple CAs to maintain
- **Dependencies** - Requires Step-CA VM, Vault, and/or internet access
- **Learning curve** - Users need to understand when to use each CA

### Risks

- **CA unavailability** - If all CAs are down, no new certificates
- **Key security** - Private keys stored on filesystem
- **Renewal failures** - Silent failures could cause outages

### Mitigations

- CA health monitoring in Airflow
- Expiry alerting (7 days warning)
- Private keys with restricted permissions (0600)
- Renewal logging and notification

## Implementation Plan

### Phase 1: Universal CLI Script

- [ ] Create `qubinode-cert` script
- [ ] Implement Step-CA backend
- [ ] Implement Let's Encrypt backend (certbot wrapper)
- [ ] Create service handlers

### Phase 2: Vault PKI Integration

- [ ] Add Vault PKI secrets engine setup to `setup-vault.sh`
- [ ] Implement Vault PKI backend in `qubinode-cert`
- [ ] Create Vault PKI Airflow operators

### Phase 3: Airflow Integration

- [ ] Create `certificate_provisioning.py` DAG
- [ ] Add certificate tasks to VM deployment DAGs
- [ ] Create expiry monitoring DAG

### Phase 4: Ansible Role

- [ ] Create `qubinode.certificate` role
- [ ] Integrate with existing deployment playbooks
- [ ] Add to FreeIPA/Harbor/OpenShift deployments

## Related ADRs

- ADR-0039: FreeIPA and VyOS Airflow DAG Integration
- ADR-0048: Step-CA Integration for Disconnected Deployments
- ADR-0051: HashiCorp Vault Secrets Management
- ADR-0053: Dynamic Secrets for Airflow Tasks
- ADR-0055: Zero-Friction Infrastructure Services

## References

- [Step-CA Documentation](https://smallstep.com/docs/step-ca)
- [Vault PKI Secrets Engine](https://developer.hashicorp.com/vault/docs/secrets/pki)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Certbot Documentation](https://certbot.eff.org/docs/)
