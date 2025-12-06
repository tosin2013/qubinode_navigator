______________________________________________________________________

## description: Create a new virtual machine allowed-tools: Bash(kcli:*), Bash(podman-compose:*), Bash(docker-compose:\*) argument-hint: \[vm-specs\]

# Create Virtual Machine

You are helping create a new Qubinode Navigator virtual machine.

VM requirements: $ARGUMENTS

First, check available images:
!`kcli list images 2>/dev/null | head -20`

Check available plans (predefined VM configurations):
!`kcli list plan 2>/dev/null`

Before creating, verify:

1. Sufficient resources (CPU, memory, disk)
1. Network availability
1. Image exists or can be downloaded

IMPORTANT: Creating VMs consumes system resources. Confirm specifications with the user before executing.

To create via kcli directly:

```bash
kcli create vm <name> -i <image> -P memory=<MB> -P cpus=<N> -P disks=['{"size": <GB>}']
```

Or trigger the appropriate Airflow DAG for managed creation:
!`cd ${QUBINODE_HOME:-$HOME/qubinode_navigator}/airflow && podman-compose exec -T airflow-scheduler airflow dags list | grep -i vm`

Provide:

1. Recommended specifications based on use case
1. The exact command or DAG to use
1. Expected creation time
1. Post-creation verification steps
