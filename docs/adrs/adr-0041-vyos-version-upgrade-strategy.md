---
layout: default
title: ADR-0041 VyOS Version Upgrade Strategy
parent: Infrastructure & Deployment
grand_parent: Architectural Decision Records
nav_order: 41
---

# ADR-0041: VyOS Router Version Pinning and Upgrade Strategy

**Status:** Accepted  
**Date:** 2025-11-27  
**Decision Makers:** Platform Team, Network Team  
**Related ADRs:** ADR-0039 (FreeIPA/VyOS DAG Integration)

## Context and Problem Statement

The current VyOS router deployment in `kcli-pipelines/vyos-router/deploy.sh` uses a rolling release version:

```bash
VYOS_VERSION=1.5-rolling-202409250007
ISO_LOC=https://github.com/vyos/vyos-nightly-build/releases/download/${VYOS_VERSION}/vyos-${VYOS_VERSION}-generic-amd64.iso
```

**Problems with Current Approach:**
1. Rolling releases are snapshots that may contain bugs or breaking changes
2. Version `1.5-rolling-202409250007` is from September 2024 and is outdated
3. No defined upgrade path or testing procedure
4. Different environments may run different versions causing inconsistency
5. Rolling releases are not suitable for production-like environments

## Decision Drivers

* Ensure deployment stability and reproducibility
* Maintain consistent behavior across environments
* Enable controlled upgrade cycles with testing
* Support both development (rolling) and production (stable) use cases
* Minimize disruption to existing deployments

## Decision Outcome

**Chosen approach:** Implement a version pinning strategy with configurable release channels and a quarterly upgrade cadence.

### Version Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    VyOS Version Channels                         │
├─────────────────────────────────────────────────────────────────┤
│  Channel      │ Use Case           │ Update Frequency           │
├───────────────┼────────────────────┼────────────────────────────┤
│  stable       │ Production         │ Quarterly (after testing)  │
│  lts          │ Long-term support  │ Security patches only      │
│  rolling      │ Development/Test   │ Weekly (latest nightly)    │
└─────────────────────────────────────────────────────────────────┘
```

### Recommended Versions

| Channel | Version | Release Date | Notes |
|---------|---------|--------------|-------|
| **stable** | 1.5-rolling-202411* | Nov 2025 | Latest tested rolling |
| **lts** | 1.4.0 | When available | Long-term support |
| **rolling** | Latest nightly | Daily | For testing only |

### Configuration Approach

```yaml
# vyos-config.yaml
vyos:
  channel: stable  # stable, lts, or rolling
  version: "1.5-rolling-202411250007"  # Pinned version for stable
  auto_update: false
  download_url_template: "https://github.com/vyos/vyos-nightly-build/releases/download/{version}/vyos-{version}-generic-amd64.iso"
  
  # Version validation
  min_version: "1.4.0"
  max_version: "1.6.0"
  
  # Upgrade settings
  upgrade_window: "quarterly"
  test_before_upgrade: true
  rollback_on_failure: true
```

## Implementation Details

### 1. Update deploy.sh

```bash
#!/bin/bash
# vyos-router/deploy.sh

# Version configuration
VYOS_CHANNEL="${VYOS_CHANNEL:-stable}"
VYOS_VERSION_FILE="/opt/kcli-pipelines/vyos-router/versions.yaml"

# Get version based on channel
get_vyos_version() {
    case "$VYOS_CHANNEL" in
        stable)
            # Use pinned stable version
            VYOS_VERSION=$(yq eval '.vyos.stable.version' "$VYOS_VERSION_FILE")
            ;;
        lts)
            # Use LTS version when available
            VYOS_VERSION=$(yq eval '.vyos.lts.version' "$VYOS_VERSION_FILE")
            ;;
        rolling)
            # Fetch latest rolling release
            VYOS_VERSION=$(curl -s https://api.github.com/repos/vyos/vyos-nightly-build/releases/latest | jq -r '.tag_name')
            ;;
        *)
            echo "Unknown channel: $VYOS_CHANNEL"
            exit 1
            ;;
    esac
    
    echo "Using VyOS version: $VYOS_VERSION (channel: $VYOS_CHANNEL)"
}
```

### 2. Version Tracking File

```yaml
# vyos-router/versions.yaml
vyos:
  stable:
    version: "1.5-rolling-202411250007"
    tested_date: "2025-11-27"
    tested_by: "platform-team"
    notes: "Tested with FreeIPA integration"
    sha256: "abc123..."
    
  lts:
    version: "1.4.0"
    tested_date: "2025-11-01"
    notes: "Long-term support release"
    sha256: "def456..."
    
  rolling:
    # Always fetches latest
    auto_fetch: true
    
  deprecated:
    - version: "1.5-rolling-202409250007"
      reason: "Outdated, replaced by newer stable"
      deprecated_date: "2025-11-27"
```

### 3. Upgrade Procedure

```bash
#!/bin/bash
# scripts/upgrade-vyos.sh

# 1. Download new version
download_new_version() {
    NEW_VERSION="$1"
    wget -O "/tmp/vyos-${NEW_VERSION}.iso" \
        "https://github.com/vyos/vyos-nightly-build/releases/download/${NEW_VERSION}/vyos-${NEW_VERSION}-generic-amd64.iso"
}

# 2. Test in isolated environment
test_new_version() {
    # Create test VM
    # Run connectivity tests
    # Verify DHCP, routing, NAT
}

# 3. Update version file
update_version_file() {
    yq eval -i ".vyos.stable.version = \"$NEW_VERSION\"" versions.yaml
    yq eval -i ".vyos.stable.tested_date = \"$(date +%Y-%m-%d)\"" versions.yaml
}

# 4. Commit and push
commit_version_update() {
    git add versions.yaml
    git commit -m "chore(vyos): upgrade stable to $NEW_VERSION"
    git push
}
```

### 4. VyOS Configuration Script Update

Update `vyos-config-1.5.sh` to `vyos-config.sh` with version detection:

```bash
#!/bin/vbash
# vyos-config.sh - Compatible with VyOS 1.4+ and 1.5+

source /opt/vyatta/etc/functions/script-template

# Detect VyOS version
VYOS_VERSION=$(cat /etc/vyos-release 2>/dev/null | grep -oP 'VyOS \K[0-9.]+' || echo "1.5")

configure

# Version-specific configuration
if [[ "$VYOS_VERSION" == "1.4"* ]]; then
    # VyOS 1.4 syntax
    set nat source rule 10 outbound-interface 'eth0'
else
    # VyOS 1.5+ syntax
    set nat source rule 10 outbound-interface name 'eth0'
fi

# ... rest of configuration
```

## Upgrade Schedule

| Quarter | Activity |
|---------|----------|
| Q1 | Review available releases, select candidate |
| Q1+2w | Test candidate in dev environment |
| Q1+4w | Deploy to staging, run integration tests |
| Q2 start | Update stable version, notify users |

## Positive Consequences

* **Stability**: Pinned versions ensure consistent behavior
* **Reproducibility**: Same version across all environments
* **Controlled Updates**: Quarterly review prevents surprise breakages
* **Rollback Capability**: Previous versions documented for rollback
* **Flexibility**: Multiple channels for different use cases

## Negative Consequences

* **Maintenance Overhead**: Quarterly version reviews required
* **Potential Lag**: May miss security fixes between updates
* **Storage**: Multiple ISO versions may need caching

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Security vulnerability in pinned version | High | Monitor VyOS security advisories, emergency updates |
| Breaking changes in new version | Medium | Thorough testing before promotion to stable |
| ISO download unavailable | Low | Cache ISOs locally, mirror to internal storage |

## References

* [VyOS Nightly Builds](https://github.com/vyos/vyos-nightly-build/releases)
* [VyOS Documentation](https://docs.vyos.io/)
* [VyOS Release Notes](https://docs.vyos.io/en/latest/changelog/)
* Current script: `/root/kcli-pipelines/vyos-router/deploy.sh`

---

**This ADR ensures stable and predictable VyOS deployments! 🛡️**
