# Qubinode DNS Role

Ansible role for unified DNS management supporting multiple providers.

**ADR-0055: Zero-Friction Infrastructure Services**

## Supported DNS Providers

| Provider     | Use Case              | Authentication |
| ------------ | --------------------- | -------------- |
| **FreeIPA**  | Internal environments | Kerberos       |
| **nsupdate** | RFC 2136 dynamic DNS  | TSIG key       |

## Requirements

- Ansible 2.9+
- One of:
  - FreeIPA client (ipa-client) with valid Kerberos ticket
  - nsupdate with TSIG key

## Role Variables

### DNS Action

```yaml
dns_action: add  # add, remove, sync
```

### Record Parameters

```yaml
dns_hostname: "{{ inventory_hostname }}"
dns_ip: "{{ ansible_default_ipv4.address }}"
dns_domain: example.com
dns_ttl: 3600
dns_create_ptr: true
```

### FreeIPA Configuration

```yaml
dns_provider: freeipa
freeipa_server: ipa.example.com
freeipa_admin: admin
freeipa_admin_password: ""  # Optional - will prompt if not set
```

### nsupdate Configuration

```yaml
dns_provider: nsupdate
dns_server: 127.0.0.1
nsupdate_key: /path/to/key.private
```

### Additional Records

```yaml
# CNAME aliases
dns_aliases:
  - www.example.com
  - api.example.com

# SRV records
dns_srv_records:
  - service: "_ldap._tcp"
    target: ldap.example.com
    port: 389
    priority: 10
    weight: 100
```

## Example Playbooks

### Add DNS Record

```yaml
- hosts: webservers
  roles:
    - role: qubinode_dns
      vars:
        dns_action: add
        dns_hostname: "{{ inventory_hostname }}"
        dns_ip: "{{ ansible_default_ipv4.address }}"
        dns_create_ptr: true
```

### Remove DNS Record

```yaml
- hosts: webservers
  roles:
    - role: qubinode_dns
      vars:
        dns_action: remove
        dns_hostname: "{{ inventory_hostname }}"
```

### Add DNS with CNAME Aliases

```yaml
- hosts: webservers
  roles:
    - role: qubinode_dns
      vars:
        dns_hostname: web.example.com
        dns_ip: 192.168.122.100
        dns_aliases:
          - www.example.com
          - www2.example.com
```

### Sync DNS from Certificate Inventory

```yaml
- hosts: localhost
  roles:
    - role: qubinode_dns
      vars:
        dns_action: sync
        cert_inventory_file: /etc/qubinode/certs/inventory.json
```

### Combined with Certificate Role

```yaml
- hosts: newvm
  roles:
    # First add DNS
    - role: qubinode_dns
      vars:
        dns_action: add
        dns_hostname: "{{ inventory_hostname }}"
        dns_ip: "{{ ansible_default_ipv4.address }}"
        dns_create_ptr: true

    # Then request certificate
    - role: qubinode_certificate
      vars:
        cert_hostname: "{{ inventory_hostname }}"
        cert_ca: auto
        cert_service: nginx
```

## License

Apache-2.0

## Author

Qubinode Navigator Team
