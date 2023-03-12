#!/bin/bash

function depenacy_check() {
    if ! yq -v  &> /dev/null
    then
        VERSION=v4.30.6
        BINARY=yq_linux_amd64
        sudo wget https://github.com/mikefarah/yq/releases/download/${VERSION}/${BINARY} -O /usr/bin/yq &&\
        sudo chmod +x /usr/bin/yq
    fi
}

function set_variables() {
    export ANSIBLE_SAFE_VERSION="0.0.4"
    export ANSIBLE_VAULT_FILE="$HOME/quibinode_navigator/inventories/localhost/group_vars/control/vault.yml"
    KCLI_CONFIG_DIR="${HOME}/.kcli"
    KCLI_CONFIG_FILE="${KCLI_CONFIG_DIR}/profiles.yml"
    PROFILES_FILE="kcli-profiles.yml"
    SECURE_DEPLOYMENT="false"
    INSTALL_RHEL_IMAGES="false"
}