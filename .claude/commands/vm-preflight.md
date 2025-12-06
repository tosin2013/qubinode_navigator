______________________________________________________________________

## description: Run preflight checks before VM creation allowed-tools: Bash(free:*), Bash(df:*), Bash(systemctl:*), Bash(virsh:*), Bash(cat:*), Bash(./scripts/preflight-check.sh:*) argument-hint: \[vm-config\]

# VM Preflight Checks

You are helping validate prerequisites for VM creation in Qubinode Navigator.

VM configuration to validate: $ARGUMENTS

Run preflight checks:
!`${QUBINODE_HOME:-$HOME/qubinode_navigator}/scripts/preflight-check.sh 2>/dev/null || echo "Preflight script not found"`

Check system resources:
!`free -h && df -h / /var/lib/libvirt 2>/dev/null | head -10`

Check libvirt status:
!`systemctl is-active libvirtd && virsh nodeinfo 2>/dev/null | head -10`

Check kcli configuration:
!`cat ~/.kcli/config.yml 2>/dev/null | head -20 || echo "No kcli config found"`

Validate:

1. Sufficient CPU cores available
1. Enough free memory
1. Adequate disk space in libvirt storage
1. Network bridges/pools configured
1. Required images downloaded

Report any blockers and how to resolve them.
