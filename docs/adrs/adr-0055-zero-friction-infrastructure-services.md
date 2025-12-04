______________________________________________________________________

## layout: default title: ADR-0055 Zero-Friction Infrastructure Services parent: Infrastructure & Deployment grand_parent: Architectural Decision Records nav_order: 55

# ADR-0055: Zero-Friction Infrastructure Services

**Status:** Accepted
**Date:** 2025-12-01
**Decision Makers:** Platform Team, DevOps Team
**Related ADRs:** ADR-0039 (FreeIPA), ADR-0048 (Step-CA), ADR-0054 (Certificate Management)

## Context and Problem Statement

Developers deploying VMs and services in Qubinode environments currently need to:

1. Manually request certificates from Step-CA, Vault, or FreeIPA
1. Manually add DNS entries to FreeIPA
1. Configure each service to use the certificates
1. Remember to clean up DNS and certificates when services are removed

This creates friction and leads to inconsistent infrastructure state.

**Goal:** When infrastructure services (FreeIPA + Step-CA) are deployed, developers should **never need to think about** DNS or certificates - they should "just work."

## Decision Drivers

- Eliminate manual DNS and certificate management
- Automatic registration on VM creation
- Automatic cleanup on VM destruction
- Support multiple CA backends (FreeIPA CA, Step-CA, Vault PKI, Let's Encrypt)
- Support multiple DNS backends (FreeIPA, Route53, Cloudflare)
- Idempotent operations (safe to run multiple times)
- Works in disconnected environments

## Decision Outcome

**Chosen approach:** Implement automatic infrastructure service integration with:

1. **qubinode-dns** - CLI for DNS management via FreeIPA
1. **qubinode-cert** - CLI for certificate management (already exists from ADR-0054)
1. **Auto-registration hooks** - Triggered on VM create/destroy
1. **Ansible roles** - For fleet-wide operations
1. **Airflow DAGs** - For orchestrated workflows

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        VM Lifecycle Events                               │
│                                                                          │
│   kcli create vm myservice  ──────►  post-create hook                    │
│                                           │                              │
│                                           ▼                              │
│                              ┌────────────────────────┐                  │
│                              │  qubinode-infra-hook   │                  │
│                              └────────────────────────┘                  │
│                                     │         │                          │
│                        ┌────────────┘         └────────────┐             │
│                        ▼                                   ▼             │
│               ┌─────────────────┐                 ┌─────────────────┐    │
│               │  qubinode-dns   │                 │  qubinode-cert  │    │
│               │  - add A record │                 │  - request cert │    │
│               │  - add PTR      │                 │  - install      │    │
│               └────────┬────────┘                 └────────┬────────┘    │
│                        │                                   │             │
│          ┌─────────────┼───────────────────────────────────┼──────┐      │
│          ▼             ▼                                   ▼      ▼      │
│     ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐ │
│     │ FreeIPA │   │ Route53 │   │ Step-CA │   │ FreeIPA │   │  Vault  │ │
│     │   DNS   │   │   DNS   │   │         │   │   CA    │   │   PKI   │ │
│     └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## Implementation

### 1. DNS Management CLI (qubinode-dns)

```bash
# Add DNS record
qubinode-dns add myservice.example.com 192.168.122.100

# Add with reverse PTR
qubinode-dns add myservice.example.com 192.168.122.100 --ptr

# Add CNAME
qubinode-dns add-cname www.example.com myservice.example.com

# Add SRV record
qubinode-dns add-srv _ldap._tcp.example.com ldap.example.com 389

# Remove record
qubinode-dns remove myservice.example.com

# List records
qubinode-dns list example.com

# Sync from inventory
qubinode-dns sync-inventory
```

### 2. FreeIPA DNS Operations

FreeIPA provides DNS management via:

- **ipa dnsrecord-add** - Add records
- **ipa dnsrecord-del** - Remove records
- **ipa dnsrecord-find** - List records
- **ipa dnszone-add** - Create zones

Requirements:

- Kerberos ticket (kinit admin)
- FreeIPA domain membership or admin credentials

### 3. Auto-Registration Hooks

#### kcli Post-Create Hook

```bash
# /etc/kcli/hooks.d/post-create.sh
#!/bin/bash
VM_NAME="$1"
VM_IP="$2"
DOMAIN="${QUBINODE_DOMAIN:-example.com}"

# Register DNS
qubinode-dns add "${VM_NAME}.${DOMAIN}" "$VM_IP" --ptr

# Request certificate
qubinode-cert request "${VM_NAME}.${DOMAIN}" \
  --san "$VM_NAME" \
  --san "$VM_IP" \
  --install
```

#### kcli Pre-Delete Hook

```bash
# /etc/kcli/hooks.d/pre-delete.sh
#!/bin/bash
VM_NAME="$1"
DOMAIN="${QUBINODE_DOMAIN:-example.com}"

# Remove DNS
qubinode-dns remove "${VM_NAME}.${DOMAIN}"

# Revoke certificate (optional)
qubinode-cert revoke "${VM_NAME}.${DOMAIN}" || true
```

### 4. Ansible Role Integration

```yaml
# playbook.yml - Zero-touch VM setup
- hosts: newvm
  roles:
    - role: qubinode_dns
      vars:
        dns_action: add
        dns_hostname: "{{ inventory_hostname }}"
        dns_ip: "{{ ansible_default_ipv4.address }}"
        dns_create_ptr: true

    - role: qubinode_certificate
      vars:
        cert_hostname: "{{ inventory_hostname }}"
        cert_ca: auto
        cert_service: "{{ service_type | default('generic') }}"
        cert_install: true
```

### 5. Certificate Authority Selection

| Environment        | CA Selection        | Use Case                      |
| ------------------ | ------------------- | ----------------------------- |
| Internal + FreeIPA | FreeIPA CA (Dogtag) | Domain-joined hosts           |
| Internal + Step-CA | Step-CA (ACME)      | Container/ephemeral workloads |
| Internal + Vault   | Vault PKI           | Short-lived dynamic certs     |
| Public             | Let's Encrypt       | Public-facing services        |
| Disconnected       | FreeIPA or Step-CA  | Air-gapped environments       |

### 6. DNS Provider Selection

| Environment | DNS Provider   | Configuration        |
| ----------- | -------------- | -------------------- |
| Internal    | FreeIPA        | Default for Qubinode |
| AWS         | Route53        | Via AWS credentials  |
| Cloudflare  | Cloudflare API | Via API token        |
| Generic     | nsupdate       | RFC 2136 dynamic DNS |

## Use Cases

### Use Case 1: Deploy New Service VM

```bash
# Developer deploys VM
kcli create vm myapi -i centos9stream -P memory=4096

# Automatically triggered:
# 1. DNS: myapi.example.com -> 192.168.122.X (A + PTR)
# 2. Certificate: myapi.example.com cert installed

# Developer configures service
ssh cloud-user@myapi.example.com
sudo systemctl start myapi
# Certificate already at /etc/qubinode/certs/myapi.example.com/
```

### Use Case 2: Deploy OpenShift Cluster

```bash
# Trigger deployment DAG
airflow dags trigger ocp_agent_deployment \
  --conf '{"cluster_name": "ocp4", "domain": "example.com"}'

# Automatically created:
# DNS: api.ocp4.example.com, *.apps.ocp4.example.com
# Certificates: API server, ingress wildcard
```

### Use Case 3: Bulk VM Provisioning

```yaml
# inventory.yml
all:
  hosts:
    web1.example.com:
      ansible_host: 192.168.122.101
      service_type: nginx
    web2.example.com:
      ansible_host: 192.168.122.102
      service_type: nginx
    db1.example.com:
      ansible_host: 192.168.122.103
      service_type: postgresql
```

```bash
# Single command provisions all DNS + certs
ansible-playbook -i inventory.yml qubinode-infra-setup.yml
```

### Use Case 4: VM Destruction Cleanup

```bash
# Delete VM
kcli delete vm myapi -y

# Automatically triggered:
# 1. DNS: myapi.example.com removed
# 2. Certificate: revoked (if supported by CA)
# 3. Inventory: updated
```

## Configuration

### Global Configuration (/etc/qubinode/infra.conf)

```ini
[general]
domain = example.com
auto_dns = true
auto_cert = true

[dns]
provider = freeipa
freeipa_server = ipa.example.com
freeipa_realm = EXAMPLE.COM
# Or for cloud
# provider = route53
# route53_zone_id = Z1234567890

[ca]
provider = auto
step_ca_url = https://step-ca.example.com:443
vault_addr = http://vault.example.com:8200
freeipa_ca = true

[hooks]
enabled = true
on_create = /etc/qubinode/hooks/post-create.sh
on_delete = /etc/qubinode/hooks/pre-delete.sh
```

## Integration Points

### FreeIPA Integration

```python
# Using python-freeipa library
from python_freeipa import Client

client = Client('ipa.example.com', version='2.245')
client.login('admin', 'password')

# Add DNS record
client.dnsrecord_add('example.com', 'myservice', a_part_ip_address='192.168.122.100')

# Add reverse PTR
client.dnsrecord_add('122.168.192.in-addr.arpa', '100', ptrrecord='myservice.example.com.')
```

### Step-CA Integration

```bash
# Already integrated via qubinode-cert
step ca certificate myservice.example.com cert.pem key.pem \
  --ca-url https://step-ca.example.com:443 \
  --provisioner acme
```

### Vault Integration

```bash
# PKI certificate
vault write pki/issue/qubinode-issuer \
  common_name="myservice.example.com" \
  ttl="720h"
```

## Implementation Phases

### Phase 1: DNS CLI and Ansible Role

- [ ] Create `qubinode-dns` CLI script
- [ ] Create `qubinode_dns` Ansible role
- [ ] Add FreeIPA DNS operations
- [ ] Add Route53 support (optional)

### Phase 2: Auto-Registration Hooks

- [ ] Create kcli hook scripts
- [ ] Integrate with VM lifecycle
- [ ] Add inventory synchronization

### Phase 3: Airflow DAG Integration

- [ ] Create `dns_management` DAG
- [ ] Add DNS tasks to existing deployment DAGs
- [ ] Create `infrastructure_sync` DAG

### Phase 4: FreeIPA CA Integration

- [ ] Add FreeIPA CA to qubinode-cert
- [ ] Support ipa-getcert for enrollment
- [ ] Auto-renewal via certmonger

## Success Criteria

1. Developer can deploy VM without manual DNS/cert steps
1. DNS entries created within 30 seconds of VM boot
1. Certificates issued within 60 seconds of VM boot
1. Cleanup happens automatically on VM deletion
1. Works in disconnected environments with FreeIPA only

## Risks and Mitigations

| Risk                    | Impact              | Mitigation                         |
| ----------------------- | ------------------- | ---------------------------------- |
| FreeIPA unavailable     | DNS/cert fails      | Graceful fallback, retry logic     |
| Hook execution failure  | Inconsistent state  | Idempotent operations, manual sync |
| Certificate CA mismatch | Trust issues        | Clear CA selection logic           |
| DNS propagation delay   | Service unreachable | Health checks, TTL tuning          |

## References

- ADR-0039: FreeIPA and VyOS Airflow DAG Integration
- ADR-0048: Step-CA Integration for Disconnected Deployments
- ADR-0054: Unified Certificate Management
- [FreeIPA DNS Documentation](https://www.freeipa.org/page/DNS)
- [FreeIPA PKI Documentation](https://www.freeipa.org/page/PKI)
- [kcli Documentation](https://kcli.readthedocs.io/)

______________________________________________________________________

**Zero-friction infrastructure: Deploy VMs, get DNS and certificates automatically!**
