#!/bin/bash

# Function: configure_ssh
# Description: Configures SSH by generating an SSH key pair if it does not already exist
# and copying the public key to the local machine's authorized keys.
# 
# Steps:
# 1. Logs the start of the SSH configuration process.
# 2. Checks if the SSH private key file (~/.ssh/id_rsa) exists.
# 3. If the private key file does not exist:
#    a. Generates a new RSA SSH key pair with an empty passphrase.
#    b. If key generation fails, logs an error message and exits with status 1.
#    c. Copies the public key to the local machine's authorized keys using ssh-copy-id.
#    d. If copying the key fails, logs an error message and exits with status 1.
configure_ssh() {
    log_message "Configuring SSH..."
    if [ ! -f ~/.ssh/id_rsa ]; then
        if ! ssh-keygen -t rsa -N '' -f ~/.ssh/id_rsa; then
            log_message "Failed to generate SSH key"
            exit 1
        fi
        if ! ssh-copy-id "$USER@$(hostname -I | awk '{print $1}')"; then
            log_message "Failed to copy SSH key"
            exit 1
        fi
    fi
}
