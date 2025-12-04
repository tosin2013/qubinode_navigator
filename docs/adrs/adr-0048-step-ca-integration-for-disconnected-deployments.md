# ADR-0048: Step-CA Integration for Disconnected Deployments

## Status

Proposed

## Date

2025-11-28

## Context

Qubinode Navigator needs to support disconnected/air-gapped deployments for:

- OpenShift clusters (via `ocp4-disconnected-helper`)
- Container registries (Harbor, Quay, mirror-registry)
- Kubernetes clusters
- Internal services requiring TLS

Currently, these deployments require manual certificate management or rely on external CAs. Step-CA provides an automated, internal PKI solution that integrates well with modern DevOps workflows.

### Research Findings (Context7)

**Step-CA Capabilities:**

- Online certificate authority for X.509 TLS and SSH certificates
- ACME protocol support (compatible with Certbot, Caddy, Traefik)
- Short-lived certificates for zero-trust architectures
- Federation support for multi-cluster environments
- Go SDK for programmatic certificate management
- Kubernetes integration via `autocert` controller

**Integration Patterns:**

1. **ACME Protocol** - Standard automated certificate workflows
1. **Bootstrap Functions** - Zero-config client/server setup with auto-renewal
1. **SDK Integration** - Fine-grained control for custom applications

**Kubernetes Integration Options:**

- `smallstep/autocert` - Automatic TLS injection into pods
- `cert-manager` - Native Kubernetes certificate management with Step-CA issuer

## Decision

Implement Step-CA as a core infrastructure component in Qubinode Navigator with the following architecture:

### Architecture

```
+------------------------------------------------------------------+
|                    Step-CA Integration Architecture               |
+------------------------------------------------------------------+

                    +-------------------+
                    |    Step-CA VM     |
                    |  (RHEL9/CentOS9)  |
                    +--------+----------+
                             |
              +--------------+--------------+
              |              |              |
              v              v              v
    +----------------+ +----------------+ +----------------+
    | Mirror Registry| | OpenShift      | | Kubernetes     |
    | (Harbor/Quay)  | | (Disconnected) | | (Internal)     |
    +----------------+ +----------------+ +----------------+
              |              |              |
              v              v              v
    +--------------------------------------------------+
    |              ACME / cert-manager                 |
    |         (Automatic Certificate Renewal)          |
    +--------------------------------------------------+
```

### Integration Points

#### 1. Mirror Registry (Harbor/Quay)

```yaml
# Harbor values.yaml
expose:
  tls:
    enabled: true
    certSource: secret
    secret:
      secretName: harbor-tls
      notarySecretName: notary-tls
```

Certificate obtained via:

```bash
step ca certificate registry.example.com registry.crt registry.key \
  --ca-url https://step-ca-server.example.com:443 \
  --provisioner acme
```

#### 2. OpenShift Disconnected Install

```yaml
# install-config.yaml
additionalTrustBundle: |
  -----BEGIN CERTIFICATE-----
  <Step-CA Root Certificate>
  -----END CERTIFICATE-----

imageContentSources:
- mirrors:
  - registry.example.com:5000/ocp4/openshift4
  source: quay.io/openshift-release-dev/ocp-release
```

#### 3. Kubernetes with cert-manager

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: step-ca-issuer
spec:
  acme:
    server: https://step-ca-server.example.com/acme/acme/directory
    privateKeySecretRef:
      name: step-ca-account-key
    solvers:
    - http01:
        ingress:
          class: nginx
```

#### 4. Kubernetes with autocert

```bash
# Install autocert controller
kubectl run autocert-init -it --rm \
  --image cr.smallstep.com/smallstep/autocert-init \
  --restart Never

# Enable namespace for auto-injection
kubectl label namespace default autocert.step.sm=enabled

# Pods automatically get TLS certificates
```

### DAG Workflow

```
step_ca_deployment DAG:
  1. validate_environment
     └── Check kcli, FreeIPA, network
  2. configure_kcli_profile
     └── Set up step-ca-server profile
  3. create_step_ca_vm
     └── Deploy RHEL9 VM via kcli
  4. wait_for_vm
     └── Poll until SSH available
  5. configure_step_ca
     └── Initialize CA, add ACME provisioner
  6. register_ca
     └── Add root CA to system trust
  7. validate_deployment
     └── Test certificate issuance
```

### Configuration Files

**Step-CA Config (`ca.json`):**

```json
{
  "root": "/etc/step-ca/certs/root_ca.crt",
  "crt": "/etc/step-ca/certs/intermediate_ca.crt",
  "key": "/etc/step-ca/secrets/intermediate_ca_key",
  "address": ":443",
  "dnsNames": ["step-ca-server.example.com"],
  "authority": {
    "provisioners": [
      {
        "type": "ACME",
        "name": "acme",
        "challenges": ["http-01", "dns-01", "tls-alpn-01"],
        "claims": {
          "maxTLSCertDuration": "2160h",
          "defaultTLSCertDuration": "720h"
        }
      },
      {
        "type": "JWK",
        "name": "admin",
        "encryptedKey": "..."
      }
    ]
  }
}
```

### Ansible Playbook Integration

Create `/root/kcli-pipelines/step-ca-server/ansible/deploy_step_ca.yaml`:

```yaml
---
- name: Deploy Step-CA Server
  hosts: step-ca-server
  become: yes
  vars:
    step_ca_domain: "{{ domain }}"
    step_ca_dns_ip: "{{ dns_ip }}"

  tasks:
    - name: Install Step CLI
      dnf:
        name: "https://dl.smallstep.com/cli/docs-ca-install/latest/step-cli_amd64.rpm"
        state: present
        disable_gpg_check: yes

    - name: Install Step CA
      dnf:
        name: "https://dl.smallstep.com/certificates/docs-ca-install/latest/step-ca_amd64.rpm"
        state: present
        disable_gpg_check: yes

    - name: Initialize Step CA
      command: >
        step ca init
        --dns=step-ca-server.{{ step_ca_domain }}
        --address=0.0.0.0:443
        --name="Internal CA for {{ step_ca_domain }}"
        --deployment-type=standalone
        --provisioner="admin@{{ step_ca_domain }}"
        --password-file=/etc/step/initial_password
      args:
        creates: /root/.step/config/ca.json

    - name: Add ACME provisioner
      command: step ca provisioner add acme --type ACME
      ignore_errors: yes

    - name: Create systemd service
      template:
        src: step-ca.service.j2
        dest: /etc/systemd/system/step-ca.service

    - name: Start Step CA service
      systemd:
        name: step-ca
        state: started
        enabled: yes
        daemon_reload: yes
```

## Consequences

### Positive

- **Automated PKI** - No manual certificate management
- **ACME Support** - Standard protocol, works with existing tools
- **Short-lived Certs** - Enhanced security with automatic renewal
- **Disconnected Ready** - Works in air-gapped environments
- **Multi-use** - Single CA for registry, OpenShift, Kubernetes, services

### Negative

- **Additional VM** - Requires dedicated Step-CA server
- **Complexity** - Another component to manage
- **Learning Curve** - Team needs to understand PKI concepts

### Risks

- **Single Point of Failure** - CA unavailability blocks certificate issuance
- **Key Security** - Root CA key must be protected
- **Certificate Expiry** - Must ensure renewal automation works

### Mitigations

- Deploy Step-CA with HA (future enhancement)
- Store root key in HSM or vault (production)
- Monitor certificate expiry with alerts
- Test renewal automation regularly

## Implementation Plan

### Phase 1: Basic Deployment (Current)

- [x] Create `step_ca_deployment.py` DAG
- [ ] Test DAG with RHEL9 VM
- [ ] Validate certificate issuance

### Phase 2: Registry Integration

- [ ] Update `registry_deployment.py` DAG to use Step-CA
- [ ] Document Harbor/Quay TLS configuration
- [ ] Test with `ocp4-disconnected-helper`

### Phase 3: Kubernetes Integration

- [ ] Create cert-manager issuer configuration
- [ ] Document autocert deployment
- [ ] Test with Kubernetes cluster

### Phase 4: OpenShift Integration

- [ ] Document `additionalTrustBundle` configuration
- [ ] Test disconnected OpenShift install
- [ ] Update `ocp_agent_installer.py` DAG

## Related DAGs

| DAG                     | Purpose                                                    |
| ----------------------- | ---------------------------------------------------------- |
| `step_ca_deployment.py` | Deploy Step-CA server VM                                   |
| `step_ca_operations.py` | Certificate operations (request, renew, revoke, bootstrap) |

## Documentation

- [Using Step-CA Guide](../../../kcli-pipelines/step-ca-server/docs/using-step-ca.md) - Comprehensive usage guide
- [DAG Roadmap](../../../kcli-pipelines/dags/DAG-ROADMAP.md) - All available DAGs

## References

- [Step-CA Documentation](https://smallstep.com/docs/step-ca)
- [Step-CA GitHub](https://github.com/smallstep/certificates)
- [Autocert for Kubernetes](https://github.com/smallstep/autocert)
- [cert-manager](https://cert-manager.io/)
- [ocp4-disconnected-helper](https://github.com/tosin2013/ocp4-disconnected-helper)
- [kcli-pipelines step-ca-server](https://github.com/tosin2013/kcli-pipelines/tree/main/step-ca-server)
