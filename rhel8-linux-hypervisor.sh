#!/bin/bash

# =============================================================================
# RHEL 8 Linux Hypervisor Setup - The "Legacy Enterprise Infrastructure Architect"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This is the specialized RHEL 8 hypervisor deployment script that implements enterprise-grade
# infrastructure setup for legacy RHEL 8 environments. It provides backward compatibility
# while maintaining security and reliability standards for older enterprise deployments.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script implements a comprehensive RHEL 8 deployment pipeline:
# 1. [PHASE 1]: Legacy Environment Validation - Validates RHEL 8 system and prerequisites
# 2. [PHASE 2]: Compatibility Setup - Configures RHEL 8 specific packages and subscriptions
# 3. [PHASE 3]: Security Configuration - Implements security hardening for RHEL 8
# 4. [PHASE 4]: Storage Management - Sets up LVM and storage pools for RHEL 8
# 5. [PHASE 5]: Network Configuration - Configures legacy network interfaces and bridges
# 6. [PHASE 6]: Vault Integration - Implements secure credential management
# 7. [PHASE 7]: Virtualization Platform - Deploys KVM/libvirt for RHEL 8 environment
# 8. [PHASE 8]: Legacy Tool Integration - Configures tools compatible with RHEL 8
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [Legacy OS Handler]: Called by setup.sh when RHEL 8 is detected
# - [Backward Compatibility]: Maintains support for existing RHEL 8 deployments
# - [Enterprise Integration]: Implements RHEL subscription management for RHEL 8
# - [Security Architecture]: Implements ADR-0004 vault integration for legacy systems
# - [Container Execution]: Uses ADR-0001 container-first model with RHEL 8 compatibility
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Legacy Support]: Maintains compatibility with older RHEL 8 packages and features
# - [Enterprise Security]: RHEL subscription management and enterprise authentication
# - [Backward Compatibility]: Ensures existing RHEL 8 deployments continue to work
# - [Security-First]: All credentials managed through HashiCorp Vault
# - [Migration Path]: Provides upgrade path to RHEL 9 when ready
#
# 💡 WHEN TO MODIFY THIS SCRIPT (for future LLMs):
# - [Package Updates]: Update RHEL 8 specific package lists and compatibility fixes
# - [Security Patches]: Apply RHEL 8 specific security updates and configurations
# - [Migration Support]: Add features to support migration to RHEL 9
# - [Legacy Fixes]: Address RHEL 8 specific issues and compatibility problems
# - [End-of-Life Planning]: Prepare deprecation notices and migration guidance
#
# 🚨 IMPORTANT FOR LLMs: This script supports legacy RHEL 8 systems and requires
# RHEL subscription. It implements older package versions and configurations.
# Consider migration to RHEL 9 for new deployments. Changes affect legacy infrastructure.

# Uncomment for debugging
#export PS4='+(${BASH_SOURCE}:${LINENO}): ${FUNCNAME[0]:+${FUNCNAME[0]}(): }'
#set -x

# 🔧 CONFIGURATION CONSTANTS FOR LLMs:
KVM_VERSION=latest  # Container image version compatible with RHEL 8
export ANSIBLE_SAFE_VERSION="0.0.14"  # AnsibleSafe version for RHEL 8 compatibility

export GIT_REPO="https://github.com/Qubinode/qubinode_navigator.git"

# Root privilege validation (required for RHEL 8 system configuration)
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root"
    exit 1
fi

# =============================================================================
# QUBINODE_HOME Path Detection
# =============================================================================
# Auto-detect the Qubinode Navigator installation directory
# Priority: 1. Existing QUBINODE_HOME env var, 2. Script location, 3. Default /opt
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export QUBINODE_HOME="${QUBINODE_HOME:-$SCRIPT_DIR}"

# Validate qubinode_navigator directory structure
if [[ ! -d "$QUBINODE_HOME/inventories" ]] && [[ ! -d "$QUBINODE_HOME/config" ]]; then
    echo "Warning: QUBINODE_HOME ($QUBINODE_HOME) does not appear to be a valid qubinode_navigator directory"
    echo "Expected to find inventories/ or config/ directories"
    # Try common fallback locations
    if [[ -d "/root/qubinode_navigator/inventories" ]]; then
        export QUBINODE_HOME="/root/qubinode_navigator"
        echo "Using fallback location: $QUBINODE_HOME"
    elif [[ -d "/opt/qubinode_navigator/inventories" ]]; then
        export QUBINODE_HOME="/opt/qubinode_navigator"
        echo "Using fallback location: $QUBINODE_HOME"
    fi
fi

echo "Using QUBINODE_HOME: $QUBINODE_HOME"
# =============================================================================

if [ -f ${QUBINODE_HOME}/.env ];
then
    source ${QUBINODE_HOME}/.env
fi

if [ -z "$CICD_PIPELINE" ]; then
  export CICD_PIPELINE="false"
  export INVENTORY="localhost"
fi
echo "CICD_PIPELINE is set to $CICD_PIPELINE"

if [ -z "$GUID" ]; then
  export GUID="$(uuidgen | cut -c 1-5)"
fi

if [ -z "$USE_HASHICORP_VAULT" ]; then
  export USE_HASHICORP_VAULT="false"
else
    if [[ -z "$VAULT_ADDRESS" && -z "$VAULT_ADDRESS" && -z ${SECRET_PATH} ]]; then
      echo "VAULT enviornment variables are not passed  is not set"
      exit 1
    fi
fi

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
        #/usr/local/bin/ansible-navigator inventory --list -m stdout --penv GUID  --vault-password-file "$HOME"/.vault_password
    else
        echo "Qubinode Installer does not exist"
    fi
}

function install_packages() {
    # Check if packages are already installed
    echo "Installing packages"
    echo "*******************"
    for package in openssl-devel bzip2-devel libffi-devel wget vim podman ncurses-devel sqlite-devel firewalld make gcc git unzip sshpass lvm2 leapp-upgrade cockpit-leapp java-11-openjdk; do
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
    sudo dnf install https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm -y
    sudo dnf -y groupinstall "Development Tools"

    #==============================================================================
    # Non-root podman hacks
    sudo chmod 4755 /usr/bin/newgidmap
    sudo chmod 4755 /usr/bin/newuidmap

    sudo dnf reinstall -yq shadow-utils

    cat > /tmp/xdg_runtime_dir.sh <<EOF
    export XDG_RUNTIME_DIR="\$HOME/.run/containers"
EOF

    sudo mv /tmp/xdg_runtime_dir.sh /etc/profile.d/xdg_runtime_dir.sh
    sudo chmod a+rx /etc/profile.d/xdg_runtime_dir.sh
    sudo cp /etc/profile.d/xdg_runtime_dir.sh /etc/profile.d/xdg_runtime_dir.zsh


    cat > /tmp/ping_group_range.conf <<EOF
    net.ipv4.ping_group_range=0 2000000
EOF
    sudo mv /tmp/ping_group_range.conf /etc/sysctl.d/ping_group_range.conf

    sudo sysctl --system
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
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')

    # Check if the version is 3.6.8
    if [ "$PYTHON_VERSION" == "3.6.8" ]; then
        echo "Python version is 3.6.8. Upgrading..."

        # Enable the Python 3.9 Module
        sudo dnf module install -y python39
        sudo dnf install -y python39 python39-devel python39-pip
        sudo dnf module enable -y python39

        # Make sure the Python 3.6 Module is disabled
        sudo dnf module disable -y python36

        # Set the default Python version to 3.9
        sudo alternatives --set python /usr/bin/python3.9
        sudo alternatives --set python3 /usr/bin/python3.9

        #sudo dnf install python3-pip -y

        curl -sSL https://raw.githubusercontent.com/ansible/ansible-navigator/v3.6.0/requirements.txt| sudo python3 -m pip install -r /dev/stdin
        sudo python3 -m pip install -r $HOME/qubinode_navigator/bash-aliases/bastion-requirements.txt
    else
        echo "Python version ${PYTHON_VERSION}. Continuing..."
    fi

    if ! command -v ansible-navigator &> /dev/null
    then
        # - For Ansible-Navigator
        curl -sSL https://raw.githubusercontent.com/ansible/ansible-navigator/v3.6.0/requirements.txt | sudo python3 -m pip install -r /dev/stdin
        sudo python3 -m pip install -r $HOME/qubinode_navigator/bash-aliases/bastion-requirements.txt
    else
        echo "ansible-navigator is already installed"
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
        sudo usermod -aG users $USER
        sudo chown -R root:users /opt
        sudo chmod -R g+w /opt
        git clone ${GIT_REPO}
        # Create symlink to allow access from /opt if installed in /root
        if [ "$QUBINODE_HOME" = "/root/qubinode_navigator" ] && [ ! -e /opt/qubinode_navigator ]; then
            ln -s ${QUBINODE_HOME} /opt/qubinode_navigator
        fi
    fi
    cd "${QUBINODE_HOME}"
    sudo pip3 install -r requirements.txt
    echo "Current DNS Server: $(cat /etc/resolv.conf | grep nameserver | awk '{print $2}' | head -1)"
    echo "Load variables"
    echo "**************"
    if [ $CICD_PIPELINE == "false" ];
    then
        read -t 360 -p "Press Enter to continue, or wait 5 minutes for the script to continue automatically" || true
        python3 load-variables.py
    else
        if [[ -z "$ENV_USERNAME" && -z "$DOMAIN" && -z "$FORWARDER" && -z "$INTERFACE" ]]; then
            echo "Error: One or more environment variables are not set"
            exit 1
        fi

        python3 load-variables.py --username ${ENV_USERNAME} --domain ${DOMAIN} --forwarder ${FORWARDER} --interface ${INTERFACE} || exit $?
    fi

}

function configure_ssh() {
    echo "Configuring SSH"
    echo "****************"
    if [ -f /home/lab-user/.ssh/id_rsa ]; then
        echo "SSH key already exists"
    else
        IP_ADDRESS=$(hostname -I | awk '{print $1}')
        ssh-keygen -f /home/lab-user/.ssh/id_rsa -t rsa -N ''
        if [ $CICD_PIPELINE == "true" ];
        then
            sudo ssh-keygen -f /root/.ssh/id_rsa -t rsa -N ''
            sshpass -p "$SSH_PASSWORD" ssh-copy-id -o StrictHostKeyChecking=no lab-user@${IP_ADDRESS} || exit $?
            sshpass -p "$SSH_PASSWORD" ssh-copy-id  -i /home/lab-user/.ssh/id_rsa -o StrictHostKeyChecking=no lab-user@${IP_ADDRESS} || exit $?
        else
            sudo ssh-keygen -f /root/.ssh/id_rsa -t rsa -N ''
            ssh-copy-id lab-user@"${IP_ADDRESS}"
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
      - ${QUBINODE_HOME}/inventories/${INVENTORY}
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
    if [ ! -f ${QUBINODE_HOME}/ansible_vault_setup.sh ];
    then
        cd "${QUBINODE_HOME}"
        curl -OL https://gist.githubusercontent.com/tosin2013/022841d90216df8617244ab6d6aceaf8/raw/92400b9e459351d204feb67b985c08df6477d7fa/ansible_vault_setup.sh
        chmod +x ansible_vault_setup.sh
    fi
    rm -f ~/.vault_password
    sudo rm -rf /root/password
    if [ $CICD_PIPELINE == "true" ];
    then
        if [ -z "$SSH_PASSWORD" ]; then
            echo "SSH_PASSWORD enviornment variable is not set"
            exit 1
        fi
        echo "$SSH_PASSWORD" > ~/.vault_password
        sudo cp ~/.vault_password /root/.vault_password
        sudo cp ~/.vault_password /home/lab-user/.vault_password
        cd "${QUBINODE_HOME}"
        bash  ./ansible_vault_setup.sh
    else
        cd "${QUBINODE_HOME}"
        bash  ./ansible_vault_setup.sh
    fi


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
            cp /tmp/config.yml ${QUBINODE_HOME}/inventories/${INVENTORY}/group_vars/control/vault.yml
            /usr/local/bin/ansiblesafe -f ${QUBINODE_HOME}/inventories/${INVENTORY}/group_vars/control/vault.yml -o 1
        else
            echo "Error: config.yml file not found"
            exit 1
        fi
    else
        /usr/local/bin/ansiblesafe -f ${QUBINODE_HOME}/inventories/${INVENTORY}/group_vars/control/vault.yml
    fi
    generate_inventory /root
}

function test_inventory() {
    echo "Testing Ansible Inventory"
    echo "*************************"
    /usr/local/bin/ansible-navigator inventory --list -m stdout --vault-password-file "$HOME"/.vault_password | tee $HOME/inventory.log >/dev/null 2>&1 || exit 1
}

function deploy_kvmhost() {
    echo "Deploying KVM Host"
    echo "******************"
    eval $(ssh-agent)
    ssh-add ~/.ssh/id_rsa
    cd "$HOME"/qubinode_navigator
    sudo mkdir -p /home/runner/.vim/autoload
    sudo chown -R lab-user:wheel /home/runner/.vim/autoload
    sudo chmod 777 -R /home/runner/.vim/autoload
    sudo -E /usr/local/bin/ansible-navigator run ansible-navigator/setup_kvmhost.yml --extra-vars "admin_user=lab-user"  --penv GUID \
        --vault-password-file "$HOME"/.vault_password -m stdout --penv GUID || exit 1
}

function configure_onedev(){
    if [ "$(pwd)" != "${QUBINODE_HOME}" ]; then
        echo "Current directory is not ${QUBINODE_HOME}."
        echo "Changing to ${QUBINODE_HOME}..."
        cd "${QUBINODE_HOME}"
    else
        echo "Current directory is ${QUBINODE_HOME}."
    fi
    echo "Configuring OneDev"
    echo "******************"
    ./dependancies/onedev/configure-onedev.sh
}


function configure_bash_aliases() {
    echo "Configuring bash aliases"
    echo "************************"
    if [ "$(pwd)" != "${QUBINODE_HOME}" ]; then
        echo "Current directory is not ${QUBINODE_HOME}."
        echo "Changing to ${QUBINODE_HOME}..."
        cd "${QUBINODE_HOME}"
    else
        echo "Current directory is ${QUBINODE_HOME}."
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
    if [ "$(pwd)" != "${QUBINODE_HOME}" ]; then
        echo "Current directory is not ${QUBINODE_HOME}."
        echo "Changing to ${QUBINODE_HOME}..."
        cd "${QUBINODE_HOME}"
    else
        echo "Current directory is ${QUBINODE_HOME}."
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
    install_packages
    configure_ssh || exit $?
    confiure_lvm_storage
    configure_python
    configure_firewalld
    configure_groups
    configure_navigator
    configure_ansible_vault_setup
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
