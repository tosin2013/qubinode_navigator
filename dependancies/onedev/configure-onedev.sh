#!/bin/bash

# Define the ports to be used by the Podman container
PORTS=(6610 6611)

# Function to open ports in firewalld
open_firewall_ports() {
    for PORT in "${PORTS[@]}"; do
        echo "Opening port $PORT in firewalld..."
        firewall-cmd --zone=public --add-port=${PORT}/tcp --permanent
    done
    echo "Reloading firewalld to apply changes..."
    firewall-cmd --reload
}

# Function to create Podman container and systemd service
create_podman_service() {
    local container_name="onedev-server"
    local service_path="/etc/systemd/system/"

    # Remove existing container if exists
    podman rm -f $container_name

    # Create container but do not start it
    mkdir -p /opt/onedev
    podman run --name $container_name -id --rm -v /opt/onedev:/opt/onedev -p ${PORTS[0]}:${PORTS[0]} -p ${PORTS[1]}:${PORTS[1]} docker.io/1dev/server:latest || exit $?

    # Generate systemd service file using podman generate
    podman generate systemd --new --files --name  $container_name 
    cp container-$container_name.service $service_path

    # Reload systemd to recognize new service
    systemctl daemon-reload
    systemctl enable container-$container_name.service
    systemctl start container-$container_name.service
}

# Main script execution
open_firewall_ports
create_podman_service
