#!/bin/bash

# Function to deploy KVM host
deploy_kvmhost() {
    log_message "Deploying KVM Host..."
    eval $(ssh-agent)
    ssh-add ~/.ssh/id_rsa
    cd "/opt/qubinode_navigator"
    if ! ansible-navigator run ansible-navigator/setup_kvmhost.yml --vault-password-file ~/.vault_password -m stdout; then
        log_message "Failed to deploy KVM host"
        exit 1
    fi
}
