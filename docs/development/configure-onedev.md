---
layout: default
title:  Configure Onedev
parent: Developer Documentation
nav_order: 1
---

# Configure Onedev

The `qubinode_navigator.sh` script is a Bash shell script that configures and runs the OneDev server on a Qubinode device. This document provides an overview of the script's functionality, structure, and key components.

[Full Script](https://github.com/tosin2013/qubinode_navigator/blob/main/dependancies/onedev/configure-onedev.sh)

## Purpose and Overview

The `qubinode_navigator.sh` script is part of the Qubinode project, which aims to provide a comprehensive solution for managing and navigating Qubinode devices. The script's primary purpose is to configure and run the OneDev server on a Qubinode device, allowing users to access and manage their data.

## Script Structure

The script consists of two main functions: `open_firewall_ports` and `create_podman_service`. The `open_firewall_ports` function opens specific ports in firewalld to allow incoming connections to the OneDev server. The `create_podman_service` function creates a new Podman container named "onedev-server" and maps it to the `/opt/onedev` directory on the host machine.

## Key Code Snippets

The script uses the following key code snippets:

* `firewall-cmd --reload`: This command reloads the firewalld configuration to apply changes made by the script.
* `podman rm -f $container_name`: This command removes any existing container with the name "onedev-server".
* `podman run --name $container_name -id --rm -v /opt/onedev:/opt/onedev -p ${PORTS[0]}:${PORTS[0]} -p ${PORTS[1]}:${PORTS[1]} docker.io/1dev/server:latest`: This command creates a new Podman container and maps it to the `/opt/onedev` directory on the host machine.
* `podman generate systemd --new --files --name  $container_name`: This command generates a systemd service file using `podman generate`.
* `systemctl daemon-reload`: This command reloads the systemd daemon to recognize new services.

## External Dependencies

The script relies on the following external dependencies:

* Podman: A container runtime that allows users to run and manage containers.
* Docker Hub: A registry of Docker images, including the OneDev image used by the script.
* firewalld: A firewall management tool that provides a command-line interface for configuring and managing firewalls.

## Best Practices

When modifying or extending the script, follow these best practices:

* Use clear and concise variable names and function names to make the code easy to read and understand.
* Follow coding conventions and style guidelines, such as using consistent indentation and spacing.
* Test the script thoroughly before deploying it in production environments.

## References

For more information on the Qubinode project and its components, refer to the following resources:

* [Qubinode documentation](https://qubinode.com/docs/)
* [Podman documentation](https://podman.io/documentation/)

```

Please let me know if these changes meet your requirements.