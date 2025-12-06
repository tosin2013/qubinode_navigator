______________________________________________________________________

## description: Get detailed information about a specific VM allowed-tools: Bash(kcli:\*) argument-hint: \[vm-name\]

# VM Information: $1

You are helping inspect a Qubinode Navigator virtual machine.

Get VM details:
!`kcli info vm $1 2>/dev/null || echo "VM not found or kcli unavailable"`

Check VM console access:
!`kcli console $1 --url 2>/dev/null || echo "Console URL unavailable"`

Provide:

1. VM specifications (CPU, memory, disk)
1. Network configuration and IP addresses
1. Storage volumes attached
1. How to SSH into the VM
1. Associated Airflow DAGs that manage this VM
1. Troubleshooting tips if VM is unhealthy
