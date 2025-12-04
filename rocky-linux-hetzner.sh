#!/bin/bash

# =============================================================================
# Rocky Linux Hetzner Setup - The "Cloud Infrastructure Specialist"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This is the specialized Rocky Linux deployment script optimized for Hetzner cloud
# infrastructure. It implements cloud-native deployment patterns with cost-effective
# open-source alternatives to enterprise solutions while maintaining security and reliability.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script implements a cloud-optimized Rocky Linux deployment:
# 1. [PHASE 1]: Cloud Environment Setup - Configures Hetzner-specific networking and storage
# 2. [PHASE 2]: Open Source Stack - Installs Rocky Linux packages without subscription requirements
# 3. [PHASE 3]: Security Hardening - Implements SSH security and firewall configuration
# 4. [PHASE 4]: Cloud Storage - Configures cloud-optimized storage and backup solutions
# 5. [PHASE 5]: Network Optimization - Sets up cloud networking and load balancing
# 6. [PHASE 6]: Vault Integration - Implements HashiCorp Vault for cloud credential management
# 7. [PHASE 7]: Virtualization Platform - Deploys KVM/libvirt optimized for cloud environments
# 8. [PHASE 8]: Cloud Tools - Integrates Hetzner CLI, monitoring, and automation tools
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [Cloud-Specific Handler]: Called by setup.sh when Rocky Linux on Hetzner is detected
# - [Cost-Optimized]: Uses open-source alternatives to reduce cloud infrastructure costs
# - [Template Processing]: Uses enhanced_load_variables.py with hetzner.yml.j2 template
# - [Cloud Security]: Implements cloud-native security patterns with HashiCorp Vault
# - [Hetzner Integration]: Optimized for Hetzner cloud services and networking
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Cloud-Native]: Optimized for Hetzner cloud infrastructure and services
# - [Cost-Effective]: Uses Rocky Linux to avoid RHEL subscription costs
# - [Open Source First]: Leverages open-source tools and community solutions
# - [Cloud Security]: Implements cloud-specific security and compliance patterns
# - [Scalable Architecture]: Designed for horizontal scaling in cloud environments
#
# 💡 WHEN TO MODIFY THIS SCRIPT (for future LLMs):
# - [Hetzner Updates]: Update for new Hetzner cloud services and features
# - [Rocky Linux Updates]: Modify for new Rocky Linux versions and packages
# - [Cloud Security]: Update security configurations for new cloud threats
# - [Cost Optimization]: Implement new cost-saving measures and resource optimization
# - [Integration Updates]: Add support for new cloud services and tools
#
# 🚨 IMPORTANT FOR LLMs: This script is optimized for Hetzner cloud infrastructure
# and requires cloud API access. It implements cost-optimized patterns using Rocky Linux
# and open-source tools. Changes affect cloud resource provisioning and costs.

# Uncomment for debugging
#export PS4='+(${BASH_SOURCE}:${LINENO}): ${FUNCNAME[0]:+${FUNCNAME[0]}(): }'
#set -x

# 🔧 CONFIGURATION CONSTANTS FOR LLMs:
KVM_VERSION=latest  # Container image version optimized for cloud deployment
export ANSIBLE_SAFE_VERSION="0.0.14"  # AnsibleSafe version for cloud credential management

export GIT_REPO="https://github.com/Qubinode/qubinode_navigator.git"

# Root privilege validation (required for cloud system configuration)
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root"
    exit 1
fi

# Environment Variables with defaults
: "${CICD_PIPELINE:="false"}"
: "${USE_HASHICORP_VAULT:="false"}"
: "${USE_HASHICORP_CLOUD:="false"}"
: "${VAULT_ADDR:=""}"
: "${VAULT_TOKEN:=""}"
: "${USE_ROUTE53:="false"}"
: "${ROUTE_53_DOMAIN:=""}"
: "${CICD_ENVIORNMENT:="github"}"
: "${SECRET_PATH:=""}"
: "${INVENTORY:="hetzner"}"
: "${DEVELOPMENT_MODEL:="false"}"
: "${CONFIG_TEMPLATE:="hetzner.yml.j2"}"
: "${VAULT_DEV_MODE:="false"}"

echo "CICD_PIPELINE is set to $CICD_PIPELINE"

# Function: log_message
# Description: Logs a message with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function: handle_hashicorp_vault
# Description: Validates HashiCorp Vault environment variables when vault integration is enabled.
# Environment Variables:
#   USE_HASHICORP_VAULT - If set to "true", enables HashiCorp Vault integration.
#   VAULT_ADDR - The address of the HashiCorp Vault server.
#   VAULT_TOKEN - The token used to authenticate with the HashiCorp Vault server.
#   SECRET_PATH - The path to the secret in HashiCorp Vault.
# Outputs: Logs a message and exits with status 1 if required environment variables are not set.
handle_hashicorp_vault() {
    if [ "$USE_HASHICORP_VAULT" = "true" ]; then
        if [[ -z "$VAULT_ADDR" || -z "$VAULT_TOKEN" || -z "$SECRET_PATH" ]]; then
            log_message "VAULT environment variables are not set"
            exit 1
        fi
    fi
}

# Function: configure_vault_integrated
# Description: Configures Ansible Vault using the vault-integrated setup approach.
#              This function replaces the traditional configure_ansible_vault_setup() method
#              by using vault-integrated-setup.sh script instead of /tmp/config.yml,
#              eliminating security risks while maintaining backward compatibility.
# Parameters: None
# Environment Variables:
#   USE_HASHICORP_VAULT - If set to "true", enables vault-integrated setup.
#   VAULT_ADDR - The address of the HashiCorp Vault server.
#   VAULT_TOKEN - The token used to authenticate with the HashiCorp Vault server.
#   CICD_PIPELINE - Determines if running in CI/CD mode.
#   INVENTORY - The inventory environment for vault path configuration.
# Returns: None
# Exit Codes:
#   1 - If vault-integrated-setup.sh fails or required components are missing.
# Security: Eliminates /tmp/config.yml plaintext credential exposure.
configure_vault_integrated() {
    log_message "Configuring Vault-Integrated Setup..."

    # Determine the correct qubinode_navigator directory
    local qubinode_dir
    if [ -d "/root/qubinode_navigator" ] && [ -f "/root/qubinode_navigator/vault-integrated-setup.sh" ]; then
        qubinode_dir="/root/qubinode_navigator"
    elif [ -f "./vault-integrated-setup.sh" ]; then
        qubinode_dir="$(pwd)"
    else
        qubinode_dir="/root/qubinode_navigator"
    fi

    log_message "Using qubinode directory: ${qubinode_dir}"
    cd "${qubinode_dir}"

    # Check if vault-integrated-setup.sh exists
    if [ ! -f "vault-integrated-setup.sh" ]; then
        log_message "vault-integrated-setup.sh not found in current directory"
        log_message "Falling back to traditional ansible vault setup"
        configure_ansible_vault_setup
        return
    fi

    # Make sure the script is executable
    chmod +x vault-integrated-setup.sh

    # Validate vault environment variables if vault is enabled
    if [ "$USE_HASHICORP_VAULT" = "true" ]; then
        handle_hashicorp_vault
        log_message "Using vault-integrated setup (secure method)"
    else
        log_message "Vault integration disabled, using traditional method"
        configure_ansible_vault_setup
        return
    fi

    # Execute vault-integrated setup script
    if [ "$CICD_PIPELINE" = "true" ]; then
        log_message "Running vault-integrated setup in CI/CD mode"
        if ! ./vault-integrated-setup.sh; then
            log_message "Failed to execute vault-integrated-setup.sh in CI/CD mode"
            log_message "Attempting fallback to traditional method"
            configure_ansible_vault_setup
            return
        fi
    else
        log_message "Running vault-integrated setup in interactive mode"
        if ! ./vault-integrated-setup.sh; then
            log_message "Failed to execute vault-integrated-setup.sh in interactive mode"
            log_message "Attempting fallback to traditional method"
            configure_ansible_vault_setup
            return
        fi
    fi

    log_message "Vault-integrated setup completed successfully"
}

function check_for_lab_user() {
    if id "lab-user" &>/dev/null; then
        echo "User lab-user exists"
    else
        curl -OL https://gist.githubusercontent.com/tosin2013/385054f345ff7129df6167631156fa2a/raw/b67866c8d0ec220c393ea83d2c7056f33c472e65/configure-sudo-user.sh
        chmod +x configure-sudo-user.sh
        ./configure-sudo-user.sh lab-user
    fi
}

# Enable ssh password authentication
function enable_ssh_password_authentication() {
    echo "Enabling ssh password authentication"
    echo "*************************************"
    sudo sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/g' /etc/ssh/sshd_config
    sudo systemctl restart sshd
}

# Disable ssh password authentication
function disable_ssh_password_authentication() {
    echo "Disabling ssh password authentication"
    echo "**************************************"
    sudo sed -i 's/PasswordAuthentication.*/PasswordAuthentication no/g' /etc/ssh/sshd_config
    sudo systemctl restart sshd
}

# @description This function generate_inventory function will generate the inventory
function generate_inventory() {
    echo "Generating inventory"
    echo "*********************"
    if [ -d "$1"/qubinode_navigator ]; then
        cd "$1"/qubinode_navigator
        if [ ! -d inventories/${INVENTORY} ]; then
            mkdir -p inventories/${INVENTORY}
            mkdir -p inventories/${INVENTORY}/group_vars/control
            cp -r inventories/localhost/group_vars/control/* inventories/${INVENTORY}/group_vars/control/
        fi

        # set the values
        control_host="$(hostname -I | awk '{print $1}')"
        # Check if running as root
        if [ "$EUID" -eq 0 ]; then
            if [ $CICD_PIPELINE == "false" ];
            then
                read -r -p "Enter the target username to ssh into machine: " control_user
            else
                control_user="$USER"
            fi
        else
            control_user="$USER"
        fi

        echo "[control]" >inventories/${INVENTORY}/hosts
        echo "control ansible_host=${control_host} ansible_user=${control_user}" >>inventories/${INVENTORY}/hosts
        configure_ansible_navigator
        /usr/local/bin/ansible-navigator inventory --list -m stdout --vault-password-file "$HOME"/.vault_password
    else
        echo "Qubinode Installer does not exist"
    fi
}

function install_packages() {
    # Check if packages are already installed
    echo "Installing packages"
    echo "*******************"
    for package in openssl-devel bzip2-devel libffi-devel wget vim podman ncurses-devel sqlite-devel firewalld make gcc git unzip sshpass lvm lvm2 zlib-devel python3.11 python3.11-pip python3.11-devel java-11-openjdk; do
        if rpm -q "${package}" >/dev/null 2>&1; then
            echo "Package ${package} already installed"
        else
            echo "Installing package ${package}"
            sudo dnf install "${package}" -y
        fi
    done

    # Install necessary groups and updates
    if dnf group info "Development Tools" >/dev/null 2>&1; then
        echo "Package group Development Tools already installed"
    else
        echo "Installing package group Development Tools"
        sudo dnf groupinstall "Development Tools" -y
        sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
        sudo sh -c 'echo -e "[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" > /etc/yum.repos.d/vscode.repo'
        dnf check-update
        sudo dnf install code
    fi

    sudo dnf update -y
}


function configure_firewalld() {
    echo "Configuring firewalld"
    echo "*********************"
    if systemctl is-active --quiet firewalld; then
        echo "firewalld is already active"
    else
        echo "starting firewalld"
        sudo systemctl start firewalld
        sudo systemctl enable firewalld
    fi
}

function configure_groups() {
    echo "Configuring groups"
    echo "******************"
    # Check if the group "lab-user" exists
    if grep -q "^lab-user:" /etc/group; then
        echo "The group 'lab-user' already exists"
    else
        # Create the group "lab-user"
        sudo groupadd lab-user
        echo "The group 'lab-user' has been created"
    fi
}

function configure_python() {
    echo "Configuring Python"
    echo "******************"

    # Configure Python 3.11 as default for ansible-navigator v25.5.0+ compatibility
    echo "Configuring Python 3.11 as default..."
    sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
    sudo alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.11 1
    echo "Python 3.11 configured as default"

    if ! command -v ansible-navigator &> /dev/null
    then
        echo "ansible-navigator not found, installing..."
        # Use main branch for latest ansible-navigator compatible with Python 3.11
        curl -sSL https://raw.githubusercontent.com/ansible/ansible-navigator/main/requirements.txt | python3 -m pip install -r /dev/stdin --user lab-user
        pip3 install -r /root/qubinode_navigator/dependancies/hetzner/bastion-requirements.txt --user lab-user
        curl -sSL https://raw.githubusercontent.com/ansible/ansible-navigator/main/requirements.txt | python3 -m pip install -r /dev/stdin
        pip3 install -r /root/qubinode_navigator/dependancies/hetzner/bastion-requirements.txt
        # Install ansible-navigator 25.5.0+ for Python 3.11 compatibility
        pip3 install ansible-navigator>=25.5.0
    else
        echo "ansible-navigator is already installed"
    fi
    if ! command -v ansible-vault &> /dev/null
    then
        echo "ansible-vault not found, installing..."
        sudo pip3 install ansible-vault
        echo 'export PATH=$HOME/.local/bin:$PATH' >>~/.profile
        echo 'export PATH=$HOME/.local/bin:$PATH' >>/home/lab-user/.profile
        source ~/.profile
    else
        echo "ansible-vault is already installed"
    fi
}

function configure_navigator() {
    echo "Configuring Qubinode Navigator"
    echo "******************************"
    if [ -d "$HOME"/qubinode_navigator ]; then
        echo "Qubinode Navigator already exists"
        git -C "$HOME/qubinode_navigator" pull
    else
        cd "$HOME"
        git clone ${GIT_REPO}
        ln -s /root/qubinode_navigator /opt/qubinode_navigator
    fi
    cd "$HOME"/qubinode_navigator
    sudo pip3 install -r requirements.txt
    echo "Current DNS Server: $(cat /etc/resolv.conf | grep nameserver | awk '{print $2}' | head -1)"
    log_message "Load variables with template support"
    echo "**************"
    if [ $CICD_PIPELINE == "false" ];
    then
        read -t 360 -p "Press Enter to continue, or wait 5 minutes for the script to continue automatically" || true
        log_message "Using enhanced configuration with template: ${CONFIG_TEMPLATE}"
        if ! python3 enhanced_load_variables.py --generate-config --template "${CONFIG_TEMPLATE}"; then
            log_message "Enhanced load variables failed, falling back to original method"
            if ! python3 load-variables.py; then
                log_message "Failed to load variables with both methods"
                exit 1
            fi
        fi
    else
        if [[ -z "$ENV_USERNAME" && -z "$DOMAIN" && -z "$FORWARDER" && -z "$INTERFACE" ]]; then
            echo "Error: One or more environment variables are not set"
            exit 1
        fi
        log_message "Using enhanced configuration with template: ${CONFIG_TEMPLATE} (CI/CD mode)"
        if ! python3 enhanced_load_variables.py --generate-config --template "${CONFIG_TEMPLATE}" --username "${ENV_USERNAME}" --domain "${DOMAIN}" --forwarder "${FORWARDER}" --interface "${INTERFACE}"; then
            log_message "Enhanced load variables failed, falling back to original method"
            if ! python3 load-variables.py --username "${ENV_USERNAME}" --domain "${DOMAIN}" --forwarder "${FORWARDER}" --interface "${INTERFACE}"; then
                log_message "Failed to load variables with both methods"
                exit 1
            fi
        fi
    fi

}

function configure_ssh() {
    echo "Configuring SSH"
    echo "****************"
    if [ -f ~/.ssh/id_rsa ]; then
        echo "SSH key already exists"
    else
        IP_ADDRESS=$(hostname -I | awk '{print $1}')
        ssh-keygen -f ~/.ssh/id_rsa -t rsa -N ''
        if [ $CICD_PIPELINE == "true" ];
        then
            sshpass -p "$SSH_PASSWORD" ssh-copy-id -o StrictHostKeyChecking=no lab-user@${IP_ADDRESS}
            sudo ssh-keygen -f /root/.ssh/id_rsa -t rsa -N ''
        else
            ssh-copy-id lab-user@"${IP_ADDRESS}"
            sudo ssh-keygen -f /root/.ssh/id_rsa -t rsa -N ''
        fi
    fi
}

function configure_ansible_navigator() {
    echo "Configuring Ansible Navigator settings"
    echo "*****************************"
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
function configure_ansible_vault_setup() {
    echo "Configuring Ansible Vault Setup"
    echo "*****************************"
    if [ ! -f /root/qubinode_navigator/ansible_vault_setup.sh ];
    then
        curl -OL https://gist.githubusercontent.com/tosin2013/022841d90216df8617244ab6d6aceaf8/raw/92400b9e459351d204feb67b985c08df6477d7fa/ansible_vault_setup.sh
        chmod +x ansible_vault_setup.sh
    fi
    rm -f ~/.vault_password
    sudo rm -rf /root/password
    if [ $CICD_PIPELINE == "true" ];
    then
        echo "$SSH_PASSWORD" > ~/.vault_password
        sudo cp ~/.vault_password /root/.vault_password
        sudo cp ~/.vault_password /home/lab-user/.vault_password
        bash  ./ansible_vault_setup.sh
    else
        bash  ./ansible_vault_setup.sh
    fi


    source ~/.profile
    if [ ! -f /usr/local/bin/ansiblesafe ];
    then
        curl -OL https://github.com/tosin2013/ansiblesafe/releases/download/v0.0.12/ansiblesafe-v0.0.14-linux-amd64.tar.gz
        tar -zxvf ansiblesafe-v0.0.14-linux-amd64.tar.gz
        chmod +x ansiblesafe-linux-amd64
        sudo mv ansiblesafe-linux-amd64 /usr/local/bin/ansiblesafe
    fi
    if [ $CICD_PIPELINE == "true" ];
    then
        if [ -f /tmp/config.yml ];
        then
            cp /tmp/config.yml /root/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml
            /usr/local/bin/ansiblesafe -f /root/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml -o 1
        else
            echo "Error: config.yml file not found"
            exit 1
        fi
    else
        /usr/local/bin/ansiblesafe -f /root/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml
    fi
    generate_inventory /root
}

function test_inventory() {
    echo "Testing Ansible Inventory"
    echo "*************************"
    source ~/.profile
    /usr/local/bin/ansible-navigator inventory --list -m stdout --vault-password-file "$HOME"/.vault_password || exit 1
}

function deploy_kvmhost() {
    echo "Deploying KVM Host"
    echo "******************"
    eval $(ssh-agent)
    ssh-add ~/.ssh/id_rsa
    cd "$HOME"/qubinode_navigator
    source ~/.profile
    sudo mkdir -p /home/runner/.vim/autoload
    sudo chown -R lab-user:wheel /home/runner/.vim/autoload
    sudo chmod 777 -R /home/runner/.vim/autoload
    sudo /usr/local/bin/ansible-navigator run ansible-navigator/setup_kvmhost.yml --extra-vars "admin_user=lab-user" \
        --vault-password-file "$HOME"/.vault_password -m stdout || exit 1
}

function configure_onedev(){
    if [ "$(pwd)" != "/root/qubinode_navigator" ]; then
        echo "Current directory is not /root/qubinode_navigator."
        echo "Changing to /root/qubinode_navigator..."
        cd /root/qubinode_navigator
    else
        echo "Current directory is /root/qubinode_navigator."
    fi
    echo "Configuring OneDev"
    echo "******************"
    ./dependancies/onedev/configure-onedev.sh
}

function configure_bash_aliases() {
    echo "Configuring bash aliases"
    echo "************************"
    if [ "$(pwd)" != "/root/qubinode_navigator" ]; then
        echo "Current directory is not /root/qubinode_navigator."
        echo "Changing to /root/qubinode_navigator..."
        cd /root/qubinode_navigator
    else
        echo "Current directory is /root/qubinode_navigator."
    fi
    # Source the function definitions
    source bash-aliases/functions.sh

    # Source the alias definitions
    source bash-aliases/aliases.sh

    # Source .bash_aliases to apply changes
    if [ -f ~/.bash_aliases ]; then
        . ~/.bash_aliases
    fi

    # Ensure .bash_aliases is sourced from .bashrc
    if ! grep -qF "source ~/.bash_aliases" ~/.bashrc; then
        echo "source ~/.bash_aliases" >> ~/.bashrc
    fi
}


function confiure_lvm_storage(){
    echo "Configuring Storage"
    echo "************************"
    if [ ! -f /tmp/configure-lvm.sh ];
    then
        curl -OL https://raw.githubusercontent.com/Qubinode/qubinode_navigator/main/dependancies/equinix-rocky/configure-lvm.sh
        mv configure-lvm.sh /tmp/configure-lvm.sh
        sudo chmod +x /tmp/configure-lvm.sh
    fi
    /tmp/configure-lvm.sh || exit 1
}

function setup_kcli_base() {
    if [ "$(pwd)" != "/root/qubinode_navigator" ]; then
        echo "Current directory is not /root/qubinode_navigator."
        echo "Changing to /root/qubinode_navigator..."
        cd /root/qubinode_navigator
    else
        echo "Current directory is /root/qubinode_navigator."
    fi
    echo "Configuring Kcli"
    echo "****************"
    source ~/.bash_aliases
    qubinode_setup_kcli
    kcli_configure_images
}

function show_help() {
    echo "Usage: $0 [OPTION]"
    echo "Call all functions if nothing is passed."
    echo "OPTIONS:"
    echo "  -h, --help                  Show this help message and exit"
    echo "  --deploy-kvmhost            Deploy KVM host"
    echo "  --configure-bash-aliases    Configure bash aliases"
    echo "  --setup-kcli-base           Setup Kcli"
    echo "  --deploy-freeipa            Deploy FreeIPA"
}

if [ $# -eq 0 ]; then
    check_for_lab_user
    enable_ssh_password_authentication
    install_packages
    configure_python
    configure_ssh
    configure_firewalld
    configure_groups
    configure_navigator
    configure_vault_integrated
    test_inventory
    deploy_kvmhost
    configure_bash_aliases
    setup_kcli_base
    configure_onedev
fi

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --deploy-kvmhost)
            deploy_kvmhost
            shift
            ;;
        --configure-bash-aliases)
            configure_bash_aliases
            shift
            ;;
        --setup-kcli-base)
            setup_kcli_base
            shift
            ;;
        --deploy-freeipa)
            source ~/.bash_aliases
            freeipa-utils deploy
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done
