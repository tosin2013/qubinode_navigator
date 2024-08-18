---
layout: default
title:  RHEL 9 Equinix Server Vault
parent: GitHub Actions
nav_order: 4
---

This document provides a detailed guide on how to configure a RHEL 9 server on Equinix using GitHub Actions. The workflow is designed to automate the setup process, ensuring that the server is configured with the necessary environment variables and software.

## Workflow Overview

The workflow is triggered by either a `repository_dispatch` event or a manual `workflow_dispatch` event. It includes the following steps:

1. **Set Environment Variables**: Depending on the trigger type, the workflow sets the necessary environment variables such as `TARGET_SERVER`, `DOMAIN`, `FORWARDER`, `HOSTNAME`, `CICD_ENVIORNMENT`, `USE_ROUTE53`, `ZONE_NAME`, and `GUID`.

2. **Configure RHEL 9 Equinix Server**: This step uses the `appleboy/ssh-action` to SSH into the target server and perform the following tasks:
   - Install Git if not already installed.
   - Clone or update the `qubinode_navigator` repository.
   - Set up the environment variables in the `.env` file.
   - Execute the `rhel9-linux-hypervisor.sh` script to configure the server.

3. **Restart Workflow on Failure**: If the configuration step fails, the workflow sends a repository dispatch event to restart the workflow with the same inputs.

## Inputs

The workflow accepts the following inputs:

- `hostname`: The hostname of the server.
- `target_server`: The target server to configure.
- `forwarder`: The DNS forwarder IP address.
- `domain`: The domain name.
- `cicd_env`: The CI/CD environment.
- `use_route53`: Whether to use Route53 for DNS.
- `zone_name`: The Route53 zone name.
- `guid`: A unique identifier.
- `ollama`: A boolean flag for Ollama workload.

## Environment Variables

The following environment variables are set during the workflow:

- `TARGET_SERVER`: The target server to configure.
- `DOMAIN`: The domain name.
- `FORWARDER`: The DNS forwarder IP address.
- `CICD_ENVIORNMENT`: The CI/CD environment.
- `USE_ROUTE53`: Whether to use Route53 for DNS.
- `ZONE_NAME`: The Route53 zone name.
- `ACTIVE_BRIDGE`: Whether to use an active bridge (default is `false`).
- `INTERFACE`: The network interface (default is `bond0`).
- `GUID`: A unique identifier.

## Secrets

The workflow uses the following secrets:

- `USERNAME`: The SSH username.
- `KEY`: The SSH key.
- `PORT`: The SSH port.
- `SSH_PASSWORD`: The SSH password.
- `HCP_PROJECT_ID`: The HashiCorp Cloud Platform project ID.
- `HCP_ORG_ID`: The HashiCorp Cloud Platform organization ID.
- `HCP_CLIENT_SECRET`: The HashiCorp Cloud Platform client secret.
- `HCP_CLIENT_ID`: The HashiCorp Cloud Platform client ID.
- `APP_NAME`: The application name.
- `EMAIL`: The email address.
- `PAT`: The GitHub personal access token for dispatching events.

## Usage

To use this workflow, ensure that the necessary inputs and secrets are provided. Trigger the workflow either manually via `workflow_dispatch` or automatically via `repository_dispatch`.

## Troubleshooting

If the workflow fails, it will automatically dispatch a restart event with the same inputs. Monitor the workflow logs for any errors and ensure that all secrets and inputs are correctly configured.
