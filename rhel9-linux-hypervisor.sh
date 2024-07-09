#!/bin/bash

set -euo pipefail

# Global variables
readonly KVM_VERSION="0.8.0"
readonly ANSIBLE_SAFE_VERSION="0.0.7"
readonly GIT_REPO="https://github.com/tosin2013/qubinode_navigator.git"

# Set default values for environment variables if they are not already set
: "${CICD_PIPELINE:="false"}"
: "${USE_HASHICORP_VAULT:="false"}"
: "${VAULT_ADDRESS:=""}"
: "${VAULT_TOKEN:=""}"
: "${SECRET_PATH:=""}"
: "${INVENTORY:="localhost"}"

# Function to log messages
log_message() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if the script is run as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_message "Please run as root"
        exit 1
    fi
}

# Function to handle HashiCorp Vault flag
handle_hashicorp_vault() {
    if [ "$USE_HASHICORP_VAULT" = "true" ]; then
        if [[ -z "$VAULT_ADDRESS" || -z "$VAULT_TOKEN" || -z "$SECRET_PATH" ]]; then
            log_message "VAULT environment variables are not set"
            exit 1
        fi
    fi
}

# Function to install packages
install_packages() {
    log_message "Installing required packages..."
    local packages=(openssl-devel bzip2-devel libffi-devel wget vim podman ncurses-devel sqlite-devel firewalld make gcc git unzip sshpass lvm2 python3 python3-pip)
    for package in "${packages[@]}"; do
        if ! rpm -q "$package" &>/dev/null; then
            dnf install -y "$package"
        fi
    done
    dnf groupinstall -y "Development Tools"
    dnf update -y
}

# Function to clone the repository
clone_repository() {
    if [ ! -d "$HOME/qubinode_navigator" ]; then
        log_message "Cloning qubinode_navigator repository..."
        git clone "$GIT_REPO" "$HOME/qubinode_navigator"
    fi
}

# Function to configure Ansible Navigator
configure_ansible_navigator() {
    if ! command -v ansible-navigator &>/dev/null; then
        log_message "Installing ansible-navigator..."
        pip3 install ansible-navigator --user
        echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.profile
        source ~/.profile
    fi
    log_message "Configuring ansible-navigator..."
    cd "$HOME/qubinode_navigator"
    pip3 install -r requirements.txt

    log_message "Configuring Ansible Navigator settings"
    cat >~/.ansible-navigator.yml <<EOF
---
ansible-navigator:
  ansible:
    inventory:
      entries:
      - /root/qubinode_navigator/inventories/${INVENTORY}
  execution-environment:
    container-engine: podman
    enabled: true
    image: quay.io/qubinode/qubinode-installer:${KVM_VERSION}
    pull:
      policy: missing
  logging:
    append: true
    file: /tmp/navigator/ansible-navigator.log
    level: debug
  playbook-artifact:
    enable: false
EOF
}

# Function to configure Ansible Vault
configure_ansible_vault() {
    log_message "Configuring Ansible Vault..."
    if ! command -v ansiblesafe &>/dev/null; then
        local ansiblesafe_url="https://github.com/tosin2013/ansiblesafe/releases/download/v${ANSIBLE_SAFE_VERSION}/ansiblesafe-v${ANSIBLE_SAFE_VERSION}-linux-amd64.tar.gz"
        curl -OL "$ansiblesafe_url"
        tar -zxvf "ansiblesafe-v${ANSIBLE_SAFE_VERSION}-linux-amd64.tar.gz"
        chmod +x ansiblesafe-linux-amd64
        mv ansiblesafe-linux-amd64 /usr/local/bin/ansiblesafe
    fi
    if [ ! -f "$HOME/qubinode_navigator/ansible_vault_setup.sh" ]; then
        curl -OL https://gist.githubusercontent.com/tosin2013/022841d90216df8617244ab6d6aceaf8/raw/92400b9e459351d204feb67b985c08df6477d7fa/ansible_vault_setup.sh
        chmod +x ansible_vault_setup.sh
    fi
    rm -f ~/.vault_password
    ./ansible_vault_setup.sh
}

# Function to generate inventory
generate_inventory() {
    log_message "Generating inventory..."
    if [ ! -d "$HOME/qubinode_navigator/inventories/$INVENTORY" ]; then
        mkdir -p "$HOME/qubinode_navigator/inventories/$INVENTORY/group_vars/control"
    fi
    local control_host="$(hostname -I | awk '{print $1}')"
    local control_user="$USER"
    echo "[control]" > "$HOME/qubinode_navigator/inventories/$INVENTORY/hosts"
    echo "control ansible_host=$control_host ansible_user=$control_user" >> "$HOME/qubinode_navigator/inventories/$INVENTORY/hosts"
    ansible-navigator inventory --list -m stdout --vault-password-file ~/.vault_password
}

# Function to configure SSH
configure_ssh() {
    log_message "Configuring SSH..."
    if [ ! -f ~/.ssh/id_rsa ]; then
        ssh-keygen -t rsa -N '' -f ~/.ssh/id_rsa
        ssh-copy-id "$USER@$(hostname -I | awk '{print $1}')"
    fi
}

# Function to configure firewalld
configure_firewalld() {
    log_message "Configuring firewalld..."
    systemctl start firewalld
    systemctl enable firewalld
}

# Function to deploy KVM host
deploy_kvmhost() {
    log_message "Deploying KVM Host..."
    eval $(ssh-agent)
    ssh-add ~/.ssh/id_rsa
    cd "$HOME/qubinode_navigator"
    ansible-navigator run ansible-navigator/setup_kvmhost.yml --vault-password-file ~/.vault_password -m stdout
}

# Main function
main() {
    check_root
    handle_hashicorp_vault
    install_packages
    configure_firewalld
    clone_repository
    configure_ansible_navigator
    configure_ansible_vault
    generate_inventory
    configure_ssh
    deploy_kvmhost
}

main "$@"
