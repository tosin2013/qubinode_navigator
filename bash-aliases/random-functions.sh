#!/bin/bash
#github-action genshdoc

# @description This function will check for the existence of the yq binary
function dependency_check() {
    if ! yq -v  &> /dev/null
    then
        VERSION=v4.30.6
        BINARY=yq_linux_amd64
        sudo wget https://github.com/mikefarah/yq/releases/download/${VERSION}/${BINARY} -O /usr/bin/yq &&\
        sudo chmod +x /usr/bin/yq
    fi
}

# @description This function will set the variables for the installer
# ANSIBLE_SAFE_VERSION - The version of the ansiblesafe binary
# ANSIBLE_VAULT_FILE - The location of the vault file
# KCLI_CONFIG_DIR - The location of the kcli config directory
# KCLI_CONFIG_FILE - The location of the kcli config file
# PROFILES_FILE - The name of the kcli profiles file
# SECURE_DEPLOYMENT - The value of the secure deployment variable
# INSTALL_RHEL_IMAGES - Set the vault to true if you want to install the RHEL images
function set_variables() {
    export ANSIBLE_SAFE_VERSION="0.0.4"
    export ANSIBLE_VAULT_FILE="$HOME/quibinode_navigator/inventories/localhost/group_vars/control/vault.yml"
    KCLI_CONFIG_DIR="${HOME}/.kcli"
    KCLI_CONFIG_FILE="${KCLI_CONFIG_DIR}/profiles.yml"
    PROFILES_FILE="kcli-profiles.yml"
    SECURE_DEPLOYMENT="false"
    INSTALL_RHEL_IMAGES="false"
}