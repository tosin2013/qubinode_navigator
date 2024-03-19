#!/bin/bash

# Define the ports to be used by the Podman container
PORTS=(6610 6611)

# Function to open ports in firewalld
open_firewall_ports() {
    for PORT in "${PORTS[@]}"; do
        echo "Opening port $PORT in firewalld..."
        firewall-cmd --zone=public --add-port=${PORT}/tcp --permanent
    done

    # Reload firewalld to apply the changes
    echo "Reloading firewalld to apply changes..."
    firewall-cmd --reload
}

# Function to run the Podman container
run_podman_container() {
    echo "Running the Podman container..."
    mkdir -p $HOME/onedev
    podman run -id --rm -v $(pwd)/onedev:/opt/onedev -p ${PORTS[0]}:${PORTS[0]} -p ${PORTS[1]}:${PORTS[1]} 1dev/server
}

# Main script execution starts here
#mkdir -p $HOME/agent/work
#podman run -t -v $(pwd)/agent/work:/agent/work -e serverUrl=http://139.178.94.45:6610 -e agentToken=ca261107-f24e-4c24-98be-bf8b3510dd89 -h myagent 1dev/agent

# Step 1: Open necessary ports in firewalld
open_firewall_ports

# Step 2: Run the Podman container
# Note: This will run in the foreground, so the script will not proceed until the container is stopped
run_podman_container
