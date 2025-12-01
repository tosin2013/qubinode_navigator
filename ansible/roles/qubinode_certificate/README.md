# Qubinode Certificate Role

Ansible role for unified certificate management supporting multiple Certificate Authorities.

**ADR-0054: Unified Certificate Management**

## Supported CAs

| CA | Use Case | Trust |
|----|----------|-------|
| **Step-CA** | Internal/disconnected environments | Private |
| **Vault PKI** | Dynamic short-lived certificates | Private |
| **Let's Encrypt** | Public-facing services | Public (trusted) |

## Requirements

- Ansible 2.9+
- One of:
  - Step-CA server accessible
  - Vault with PKI secrets engine configured
  - Internet access for Let's Encrypt + certbot installed

## Role Variables

### CA Selection

```yaml
cert_ca: auto  # auto, step-ca, vault, letsencrypt
```

### Certificate Parameters

```yaml
cert_hostname: "{{ inventory_hostname }}"
cert_san_list: []  # Additional SANs
cert_duration: ""  # e.g., 720h, 30d
cert_service: generic  # nginx, haproxy, httpd, harbor, postgresql, registry, generic
cert_install: true
cert_reload_service: true
```

### Step-CA Configuration

```yaml
step_ca_url: "https://step-ca-server.example.com:443"
step_ca_fingerprint: ""  # Auto-discovered if empty
step_ca_provisioner: acme
```

### Vault PKI Configuration

```yaml
vault_addr: "http://localhost:8200"
vault_token: ""  # Required
vault_pki_mount: pki
vault_pki_role: qubinode-issuer
```

### Let's Encrypt Configuration

```yaml
letsencrypt_email: "admin@example.com"  # Required
letsencrypt_staging: false
letsencrypt_webroot: ""  # Empty = standalone mode
```

### CA Root Installation

```yaml
install_ca_root: false
ca_root_sources:
  - step-ca
  - vault
```

### Auto-Renewal

```yaml
cert_enable_renewal_timer: false
cert_renewal_days: 30
```

## Example Playbooks

### Request Certificate for Nginx

```yaml
- hosts: webservers
  roles:
    - role: qubinode_certificate
      vars:
        cert_hostname: www.example.com
        cert_service: nginx
        cert_ca: auto
        cert_install: true
```

### Internal Service with Step-CA

```yaml
- hosts: internal_services
  roles:
    - role: qubinode_certificate
      vars:
        cert_hostname: "{{ inventory_hostname }}"
        cert_service: nginx
        cert_ca: step-ca
        step_ca_url: https://step-ca-server.internal:443
        cert_san_list:
          - "{{ ansible_hostname }}"
          - "{{ ansible_default_ipv4.address }}"
```

### Public Website with Let's Encrypt

```yaml
- hosts: public_web
  roles:
    - role: qubinode_certificate
      vars:
        cert_hostname: www.example.com
        cert_ca: letsencrypt
        letsencrypt_email: admin@example.com
        cert_service: nginx
        cert_san_list:
          - example.com
```

### Short-Lived Vault Certificate

```yaml
- hosts: microservices
  roles:
    - role: qubinode_certificate
      vars:
        cert_hostname: api.internal
        cert_ca: vault
        vault_addr: http://vault.internal:8200
        vault_token: "{{ vault_token }}"
        cert_duration: 1h
        cert_service: generic
```

### Install CA Roots on All Hosts

```yaml
- hosts: all
  roles:
    - role: qubinode_certificate
      vars:
        install_ca_root: true
        ca_root_sources:
          - step-ca
          - vault
        step_ca_url: https://step-ca-server.internal:443
        vault_addr: http://vault.internal:8200
```

### Enable Auto-Renewal

```yaml
- hosts: webservers
  roles:
    - role: qubinode_certificate
      vars:
        cert_hostname: www.example.com
        cert_service: nginx
        cert_enable_renewal_timer: true
        cert_renewal_days: 30
```

### Bulk Certificate Provisioning

```yaml
- hosts: all
  tasks:
    - name: Request certificates for all hosts
      ansible.builtin.include_role:
        name: qubinode_certificate
      vars:
        cert_hostname: "{{ inventory_hostname }}"
        cert_service: "{{ hostvars[inventory_hostname].cert_service | default('generic') }}"
        cert_ca: step-ca
        step_ca_url: https://step-ca.internal:443
```

## Supported Services

| Service | Certificate Location | Auto-Reload |
|---------|---------------------|-------------|
| nginx | /etc/nginx/ssl/ | Yes |
| haproxy | /etc/haproxy/certs/combined.pem | Yes |
| httpd | /etc/pki/tls/ | Yes |
| harbor | /data/cert/ | Yes |
| postgresql | $PGDATA/ | Yes |
| registry | /etc/docker/certs.d/<hostname>/ | No |
| generic | /etc/qubinode/certs/<hostname>/ | No |

## Directory Structure

```
/etc/qubinode/certs/
├── ca/
│   ├── step-ca-root.crt
│   ├── vault-root.crt
│   └── ca-bundle.crt
├── <hostname>/
│   ├── cert.pem
│   ├── key.pem
│   ├── chain.pem
│   ├── fullchain.pem
│   ├── .metadata.json
│   └── .renew-hook.sh
└── inventory.json
```

## License

Apache-2.0

## Author

Qubinode Navigator Team
