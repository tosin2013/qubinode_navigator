______________________________________________________________________

## layout: default title: ADR-0043 Airflow Container Host Network Access parent: Infrastructure & Deployment grand_parent: Architectural Decision Records nav_order: 43

# ADR-0043: Airflow Container Host Network Access for VM Connectivity

**Status:** Accepted
**Date:** 2025-11-27
**Decision Makers:** Platform Team, DevOps Team
**Related ADRs:** ADR-0039 (FreeIPA/VyOS DAG Integration), ADR-0036 (Airflow Integration)

## Context and Problem Statement

During testing of the FreeIPA deployment DAG, we discovered that the Airflow containers running in Podman cannot reach VMs on the libvirt networks (e.g., 192.168.122.0/24). This is because:

1. **Podman default network**: Containers run on `10.88.0.0/16` (podman0 bridge)
1. **Libvirt network**: VMs run on `192.168.122.0/24` (virbr0 bridge)
1. **Network isolation**: No routing exists between these networks by default

**Observed Behavior:**

```
# From host - works
$ ping 192.168.122.116
PING 192.168.122.116: 3 packets transmitted, 3 received, 0% packet loss

# From Airflow container - fails
$ podman exec airflow_airflow-scheduler_1 python3 -c "import socket; s=socket.socket(); s.connect(('192.168.122.116', 22))"
ConnectionRefusedError: [Errno 111] Connection refused
```

**Impact:**

- DAGs cannot verify VM connectivity (SSH, HTTP, etc.)
- DAGs cannot run post-deployment configuration on VMs
- VyOS router configuration will face the same issue
- Any DAG that needs to interact with deployed VMs is affected

## Decision Drivers

- Enable Airflow DAGs to verify and configure deployed VMs
- Maintain security boundaries where appropriate
- Support both FreeIPA and VyOS deployment workflows
- Minimize changes to existing infrastructure
- Ensure solution works with rootless Podman where possible

## Considered Options

### Option 1: Host Network Mode (Recommended)

Run Airflow containers with `--network=host` to share the host's network namespace.

**Pros:**

- Full access to all host networks including libvirt
- Simple configuration change
- No routing or firewall changes needed
- Works with all VM networks automatically

**Cons:**

- Reduced network isolation
- Port conflicts possible (mitigated by using non-standard ports)
- Security implications (containers share host network)

### Option 2: Macvlan Network

Create a macvlan network that bridges containers directly to the libvirt network.

**Pros:**

- Containers get IPs on the VM network
- Better isolation than host network
- VMs and containers on same L2 segment

**Cons:**

- Complex setup
- May not work with all network configurations
- Requires specific NIC configuration

### Option 3: Add Routes Between Networks

Add static routes between podman0 and virbr0 networks.

**Pros:**

- Maintains network separation
- Targeted connectivity

**Cons:**

- Requires firewall rule changes
- May need iptables/nftables modifications
- Complex to maintain across reboots

### Option 4: Skip Network Checks in DAGs

Modify DAGs to skip connectivity verification and rely on virsh/kcli status only.

**Pros:**

- No infrastructure changes
- Works with current setup

**Cons:**

- Cannot verify actual VM accessibility
- Cannot run remote configuration tasks
- Limits DAG functionality significantly

## Decision Outcome

**Chosen option:** Option 1 - Host Network Mode for Airflow containers

This provides the simplest and most complete solution, enabling full VM network access with minimal configuration changes.

### Implementation

#### 1. Update docker-compose.yaml / podman-compose.yaml

```yaml
# airflow/docker-compose.yaml
version: '3.8'

x-airflow-common: &airflow-common
  image: ${AIRFLOW_IMAGE:-qubinode/airflow:latest}
  environment:
    - AIRFLOW__CORE__EXECUTOR=LocalExecutor
    # ... other env vars
  volumes:
    - ./dags:/opt/airflow/dags
    - ./logs:/opt/airflow/logs
    - ./plugins:/opt/airflow/plugins
    - /var/run/libvirt/libvirt-sock:/var/run/libvirt/libvirt-sock:ro
  # KEY CHANGE: Use host network
  network_mode: host
  # Alternative for specific services only:
  # networks:
  #   - airflow-net
  #   - host  # if supported

services:
  airflow-webserver:
    <<: *airflow-common
    command: webserver
    # With host network, specify the port explicitly
    # Access via http://localhost:8888

  airflow-scheduler:
    <<: *airflow-common
    command: scheduler

  # ... other services
```

#### 2. Alternative: Podman Pod with Host Network

```bash
# Create pod with host network
podman pod create --name airflow-pod --network=host

# Run containers in the pod
podman run -d --pod airflow-pod \
  --name airflow-scheduler \
  -v ./dags:/opt/airflow/dags \
  -v /var/run/libvirt/libvirt-sock:/var/run/libvirt/libvirt-sock:ro \
  qubinode/airflow:latest scheduler

podman run -d --pod airflow-pod \
  --name airflow-webserver \
  -v ./dags:/opt/airflow/dags \
  qubinode/airflow:latest webserver
```

#### 3. Systemd Service Update

```ini
# /etc/systemd/system/airflow.service
[Unit]
Description=Airflow via Podman
After=network.target libvirtd.service

[Service]
Type=simple
ExecStart=/usr/bin/podman-compose -f /opt/airflow/docker-compose.yaml up
ExecStop=/usr/bin/podman-compose -f /opt/airflow/docker-compose.yaml down
Restart=always

[Install]
WantedBy=multi-user.target
```

### Network Architecture After Change

```
┌─────────────────────────────────────────────────────────────────┐
│                         Host System                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Airflow Containers (host network)            │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │   │
│  │  │  Scheduler  │  │  Webserver  │  │  MCP Server │       │   │
│  │  │  (no port)  │  │  :8888      │  │  :8889      │       │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              │ Direct access to all interfaces   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Host Network Stack                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │   │
│  │  │   virbr0    │  │   virbr1    │  │    eth0     │       │   │
│  │  │192.168.122.1│  │192.168.49.1 │  │  (external) │       │   │
│  │  └──────┬──────┘  └──────┬──────┘  └─────────────┘       │   │
│  └─────────┼────────────────┼───────────────────────────────┘   │
│            │                │                                    │
│            ▼                ▼                                    │
│  ┌─────────────────┐  ┌─────────────────┐                       │
│  │   FreeIPA VM    │  │   VyOS Router   │                       │
│  │ 192.168.122.116 │  │ 192.168.122.x   │                       │
│  │                 │  │ 192.168.49.1    │                       │
│  └─────────────────┘  └─────────────────┘                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Security Considerations

| Concern           | Mitigation                                                     |
| ----------------- | -------------------------------------------------------------- |
| Port exposure     | Use firewall rules to restrict access to Airflow ports         |
| Container escape  | Host network doesn't increase escape risk, only network access |
| Service conflicts | Use non-standard ports (8888, 8889)                            |
| External access   | Bind services to localhost or specific interfaces              |

### Firewall Rules (Optional)

```bash
# Restrict Airflow webserver to localhost only
firewall-cmd --add-rich-rule='rule family="ipv4" source address="127.0.0.1" port port="8888" protocol="tcp" accept'
firewall-cmd --add-rich-rule='rule family="ipv4" port port="8888" protocol="tcp" reject'

# Or use iptables
iptables -A INPUT -p tcp --dport 8888 -s 127.0.0.1 -j ACCEPT
iptables -A INPUT -p tcp --dport 8888 -j DROP
```

## Positive Consequences

- **Full VM Access**: DAGs can verify and configure any VM on any libvirt network
- **Simplified Networking**: No complex routing or bridge configuration
- **VyOS Support**: VyOS router DAG will work with all its networks (1924-1928)
- **Future Proof**: Any new libvirt networks automatically accessible

## Negative Consequences

- **Reduced Isolation**: Containers share host network namespace
- **Port Management**: Must ensure no port conflicts with host services
- **Security Surface**: Slightly increased attack surface

## Implementation Plan

### Phase 1: Update Compose Configuration (Immediate)

- [ ] Modify `docker-compose.yaml` to use `network_mode: host`
- [ ] Update port bindings documentation
- [ ] Test Airflow services start correctly

### Phase 2: Update DAGs (Immediate)

- [ ] Re-enable SSH connectivity checks in FreeIPA DAG
- [ ] Add connectivity verification to VyOS DAG
- [ ] Test end-to-end deployment workflows

### Phase 3: Security Hardening (Week 1)

- [ ] Add firewall rules for Airflow ports
- [ ] Document security implications
- [ ] Update deployment documentation

### Phase 4: Documentation (Week 1)

- [ ] Update Airflow setup guide
- [ ] Document network architecture
- [ ] Add troubleshooting section

## Verification

After implementing host network mode:

```bash
# Verify container can reach VM
podman exec airflow_airflow-scheduler_1 python3 -c \
  "import socket; s=socket.socket(); s.connect(('192.168.122.116', 22)); print('SSH reachable')"

# Verify kcli works
podman exec airflow_airflow-scheduler_1 kcli list vm

# Verify virsh works
podman exec airflow_airflow-scheduler_1 virsh -c qemu:///system list
```

## References

- [Podman Networking Documentation](https://docs.podman.io/en/latest/markdown/podman-run.1.html#network-mode-net)
- [Libvirt Networking](https://wiki.libvirt.org/Networking.html)
- ADR-0036: Apache Airflow Workflow Orchestration Integration
- ADR-0039: FreeIPA and VyOS Airflow DAG Integration

______________________________________________________________________

**This ADR enables Airflow to fully manage VM lifecycle including post-deployment configuration! 🌐**
