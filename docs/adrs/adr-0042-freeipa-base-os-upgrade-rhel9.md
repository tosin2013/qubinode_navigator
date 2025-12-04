______________________________________________________________________

## layout: default title: ADR-0042 FreeIPA Base OS Upgrade to RHEL 9 parent: Infrastructure & Deployment grand_parent: Architectural Decision Records nav_order: 42

# ADR-0042: FreeIPA Workshop Deployer Base OS Upgrade to RHEL 9

**Status:** Accepted
**Date:** 2025-11-27
**Decision Makers:** Platform Team, Identity Team
**Related ADRs:** ADR-0039 (FreeIPA/VyOS DAG Integration)

## Context and Problem Statement

The `freeipa-workshop-deployer` repository currently supports:

- **RHEL 8** (Enterprise) - End of Maintenance Support: May 2024, End of Extended Life: May 2029
- **CentOS 8 Stream** (Community) - End of Life: May 2024 (already EOL)

From the current `1_kcli/create.sh`:

```bash
if [ "$COMMUNITY_VERSION" == "true" ]; then
  export IMAGE_NAME=centos8stream
  export TEMPLATE_NAME=template-centos.yaml
elif [ "$COMMUNITY_VERSION" == "false" ]; then
  export IMAGE_NAME=rhel8
  export TEMPLATE_NAME=template.yaml
fi
```

**Problems:**

1. CentOS 8 Stream is already end-of-life (May 2024)
1. RHEL 8 is in maintenance mode with limited updates
1. FreeIPA on RHEL 9 has improved features and security
1. Python 3.9+ and newer OpenSSL required for modern integrations
1. Bootstrap script already references RHEL 9.5 as primary platform

## Decision Drivers

- Align with supported OS lifecycle
- Leverage RHEL 9 security improvements
- Support modern Python and cryptography requirements
- Maintain community (CentOS) and enterprise (RHEL) options
- Minimize disruption to existing deployments

## Decision Outcome

**Chosen approach:** Migrate to RHEL 9 / CentOS 9 Stream as primary platform while maintaining RHEL 8 support during transition period.

### Migration Timeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    OS Migration Timeline                         │
├─────────────────────────────────────────────────────────────────┤
│  Phase 1 (Now - Q1 2026)                                        │
│  ├── Add RHEL 9 / CentOS 9 Stream support                       │
│  ├── Update bootstrap.sh (already done)                         │
│  ├── Update kcli templates                                      │
│  └── Test FreeIPA installation on new OS                        │
├─────────────────────────────────────────────────────────────────┤
│  Phase 2 (Q1 2026 - Q2 2026)                                    │
│  ├── Make RHEL 9 the default                                    │
│  ├── Deprecation notice for RHEL 8                              │
│  └── Update documentation                                       │
├─────────────────────────────────────────────────────────────────┤
│  Phase 3 (Q3 2026+)                                             │
│  ├── Remove RHEL 8 / CentOS 8 support                           │
│  └── Add CentOS 10 Stream support                               │
└─────────────────────────────────────────────────────────────────┘
```

### Supported OS Matrix

| OS Version       | Status      | Support Until | Default           |
| ---------------- | ----------- | ------------- | ----------------- |
| RHEL 9.x         | **Primary** | 2032          | ✅ Yes            |
| CentOS 9 Stream  | **Primary** | 2027          | Community default |
| CentOS 10 Stream | Planned     | 2030+         | Future            |
| RHEL 8.x         | Deprecated  | 2029          | Legacy only       |
| CentOS 8 Stream  | **Removed** | EOL           | ❌ No             |

## Implementation Details

### 1. Update create.sh

```bash
#!/bin/bash
# 1_kcli/create.sh - Updated for RHEL 9

COMMUNITY_VERSION="$(echo -e "${COMMUNITY_VERSION}" | tr -d '[:space:]')"
OS_VERSION="${OS_VERSION:-9}"  # Default to version 9

echo "COMMUNITY_VERSION is set to: $COMMUNITY_VERSION"
echo "OS_VERSION is set to: $OS_VERSION"

if [ "$COMMUNITY_VERSION" == "true" ]; then
    case "$OS_VERSION" in
        9)
            export IMAGE_NAME=centos9stream
            export TEMPLATE_NAME=template-centos9.yaml
            export LOGIN_USER=cloud-user
            ;;
        10)
            export IMAGE_NAME=centos10stream
            export TEMPLATE_NAME=template-centos10.yaml
            export LOGIN_USER=cloud-user
            ;;
        8)
            echo "WARNING: CentOS 8 Stream is EOL. Consider upgrading to CentOS 9 Stream."
            export IMAGE_NAME=centos8stream
            export TEMPLATE_NAME=template-centos.yaml
            export LOGIN_USER=centos
            ;;
        *)
            echo "Unsupported OS version: $OS_VERSION"
            exit 1
            ;;
    esac
elif [ "$COMMUNITY_VERSION" == "false" ]; then
    case "$OS_VERSION" in
        9)
            export IMAGE_NAME=rhel9
            export TEMPLATE_NAME=template-rhel9.yaml
            export LOGIN_USER=cloud-user
            ;;
        8)
            echo "WARNING: RHEL 8 is in maintenance mode. Consider upgrading to RHEL 9."
            export IMAGE_NAME=rhel8
            export TEMPLATE_NAME=template.yaml
            export LOGIN_USER=cloud-user
            ;;
        *)
            echo "Unsupported OS version: $OS_VERSION"
            exit 1
            ;;
    esac
fi

echo "IMAGE_NAME: $IMAGE_NAME"
echo "TEMPLATE_NAME: $TEMPLATE_NAME"
echo "LOGIN_USER: $LOGIN_USER"
```

### 2. New Template for RHEL 9 / CentOS 9

```yaml
# template-rhel9.yaml / template-centos9.yaml
  image: {{ image }}
{% if rhnregister %}
  rhnregister: true
{% endif %}
{% if rhnorg %}
  rhnorg: {{ rhnorg }}
{% endif %}
{% if rhnactivationkey %}
  rhnactivationkey: {{ rhnactivationkey }}
{% endif %}
  numcpus: {{ numcpus }}
  memory: {{ memory }}
  disks:
    - size: {{ disk_size }}
  {% if reservedns %}
  reservedns: true
  {% endif %}
  nets:
    - name: {{ net_name }}
  dns: {{ reservedns }}
  cmds:
    # RHEL 9 / CentOS 9 specific commands
    - nmcli connection modify "cloud-init eth0" ipv4.dns {{ reservedns }}
    - nmcli connection down "cloud-init eth0" && nmcli connection up "cloud-init eth0"
    - echo {{ user_password }} | passwd --stdin root
    - useradd {{ user }}
    - usermod -aG wheel {{ user }}
    - echo "{{ user }} ALL=(root) NOPASSWD:ALL" | tee -a /etc/sudoers.d/{{ user }}
    - echo {{ user_password }} | passwd --stdin {{ user }}
    # RHEL 9 specific: subscription-manager for enterprise
{% if rhnregister %}
    - subscription-manager refresh
    - subscription-manager attach --auto
{% endif %}
    # Install prerequisites
    - dnf install -y git vim unzip wget tar python3 python3-pip util-linux-user tmux
    # RHEL 9 has Python 3.9+ by default
    - python3 --version
```

### 3. Update bootstrap.sh

The bootstrap.sh already checks for RHEL 9:

```bash
# Check RHEL version
if [ -f /etc/redhat-release ]; then
    RHEL_VERSION=$(cat /etc/redhat-release | grep -oP '(?<=release )\d+\.\d+')
    MAJOR_VERSION=$(echo $RHEL_VERSION | cut -d. -f1)
    if [ "$MAJOR_VERSION" != "9" ]; then
        echo -e "${RED}This script requires RHEL 9.x${NC}"
        exit 1
    fi
fi
```

### 4. Update vars.sh Example

```bash
# example.vars.sh - Updated defaults
# OS Configuration
export COMMUNITY_VERSION="${COMMUNITY_VERSION:-false}"
export OS_VERSION="${OS_VERSION:-9}"  # Default to RHEL/CentOS 9

# Image names based on OS
# RHEL 9: rhel9
# CentOS 9 Stream: centos9stream
# CentOS 10 Stream: centos10stream (future)
```

### 5. FreeIPA Package Differences

| Component | RHEL 8 | RHEL 9  |
| --------- | ------ | ------- |
| Python    | 3.6    | 3.9+    |
| OpenSSL   | 1.1.1  | 3.0+    |
| FreeIPA   | 4.9.x  | 4.10.x+ |
| Samba     | 4.14   | 4.17+   |
| BIND      | 9.11   | 9.16+   |

### 6. Ansible Playbook Updates

```yaml
# 2_ansible_config/roles/freeipa/tasks/main.yml
- name: Install FreeIPA server packages (RHEL 9)
  dnf:
    name:
      - ipa-server
      - ipa-server-dns
      - ipa-server-trust-ad  # Optional: AD trust
    state: present
  when: ansible_distribution_major_version == "9"

- name: Install FreeIPA server packages (RHEL 8 - Legacy)
  dnf:
    name:
      - ipa-server
      - ipa-server-dns
    state: present
  when: ansible_distribution_major_version == "8"
```

## Testing Requirements

### Pre-Migration Testing

1. **Fresh Installation Test**

   - Deploy FreeIPA on CentOS 9 Stream
   - Verify all services start correctly
   - Test user/group management
   - Test DNS resolution

1. **Integration Testing**

   - Test with VyOS router (DNS forwarding)
   - Test with OpenShift integration
   - Test Kerberos authentication

1. **Performance Testing**

   - Compare LDAP query performance
   - Measure DNS resolution times
   - Check memory/CPU usage

### Migration Testing

1. **In-place Upgrade** (if supported)

   - Document upgrade procedure
   - Test data preservation

1. **Side-by-Side Migration**

   - Deploy new RHEL 9 FreeIPA
   - Migrate data from RHEL 8
   - Verify replication

## Positive Consequences

- **Security**: RHEL 9 has improved security features (SELinux, crypto policies)
- **Performance**: Newer kernel and libraries improve performance
- **Support**: Full vendor support until 2032
- **Features**: Access to latest FreeIPA features
- **Compatibility**: Better integration with modern tools

## Negative Consequences

- **Migration Effort**: Existing deployments need migration
- **Testing**: Comprehensive testing required
- **Documentation**: All docs need updating
- **Training**: Team needs RHEL 9 familiarity

## Risks and Mitigations

| Risk                             | Impact | Mitigation                               |
| -------------------------------- | ------ | ---------------------------------------- |
| Breaking changes in FreeIPA      | High   | Thorough testing, staged rollout         |
| Ansible playbook incompatibility | Medium | Version-specific tasks                   |
| User confusion during transition | Low    | Clear documentation, deprecation notices |

## References

- [RHEL 9 Release Notes](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9)
- [FreeIPA on RHEL 9](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/installing_identity_management)
- [CentOS Stream Lifecycle](https://www.centos.org/centos-stream/)
- Current deployer: `/root/freeipa-workshop-deployer/`

______________________________________________________________________

**This ADR ensures FreeIPA deployments remain on supported, secure platforms! 🔐**
