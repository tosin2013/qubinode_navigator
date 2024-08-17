---
layout: default
title:  Configure Cockpit Ssl
parent: Developer Documentation
nav_order: 1
---

### Structure

The script is divided into several major functions or classes, each responsible for a specific aspect of the certificate management process:

* `decrypt_vault`: Decrypts the vault file using ansiblesafe to access AWS credentials.
* `extract_credentials`: Extracts the required AWS credentials (AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY) from the vault file using yq.
* `re_encrypt_vault`: Re-encrypts the vault file after extracting the credentials.
* `define_constants`: Defines constants for container runtime, Cockpit domain, and certificate directory.
* `enable_cockpit_service`: Enables the Cockpit service if it's not already enabled.
* `obtain_certificates`: Runs Certbot to obtain SSL certificates using Route53 based on the container runtime (Docker or Podman).
* `update_cockpit_service`: Combines the server certificate and intermediate cert chain, copies over the key, sets proper permissions, and restarts the Cockpit service.

### Key Code Snippets

The script uses several key code snippets to achieve its goals. For example:

* The `decrypt_vault` function uses the following command to decrypt the vault file: `ansiblesafe -d ${VULT_DIR}/vault.json`
* The `extract_credentials` function extracts the AWS credentials using the following yq command: `yq e '.aws_access_key_id' ${VULT_DIR}/vault.json`

### External Dependencies

The script relies on several external dependencies to function correctly:

* Ansible safe (ansiblesafe) for decrypting and re-encrypting the vault file
* Certbot for obtaining SSL certificates using Route53
* Docker or Podman for running containers
* Cockpit service for managing containerized applications

### Input and Output Formats

The script accepts several input formats, including:

* Command-line arguments: The script can be run from the command line with various options and flags.
* Configuration files: The script reads configuration files to determine the certificate management process.

The script outputs a message indicating that the Cockpit SSL certificates have been updated successfully, along with the new Cockpit URL.

### Best Practices

When modifying or extending the script, follow these best practices:

* Use clear and concise variable names and function names.
* Follow coding conventions and style guidelines to ensure consistency throughout the codebase.
* Test the script thoroughly before deploying it in production environments.

### References

For further information on the Qubinode Navigator script, refer to the following resources:

* Ansible safe documentation: <https://docs.ansible.com/ansible-safe/>
* Certbot documentation: <https://certbot.eff.org/docs/>
* Cockpit service documentation: <https://cockpit-project.org/documentation/>
