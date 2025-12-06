#!/bin/bash

# =============================================================================
# Qubinode Navigator Setup - The "Mission Control Center"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This is the primary entry point script that orchestrates the complete setup and
# deployment of Qubinode Navigator infrastructure across multiple Linux distributions.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script follows a systematic deployment workflow:
# 1. [PHASE 1]: Environment Detection - Identifies OS type and validates prerequisites
# 2. [PHASE 2]: System Preparation - Installs packages, configures SSH, firewall, and storage
# 3. [PHASE 3]: Navigator Setup - Clones repository, configures Python environment
# 4. [PHASE 4]: Security Configuration - Sets up Ansible Vault with HashiCorp integration
# 5. [PHASE 5]: Infrastructure Deployment - Deploys KVM host and configures virtualization
# 6. [PHASE 6]: Tool Integration - Sets up bash aliases, kcli, and external services
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [Primary Entry Point]: Called by users via curl or direct execution
# - [OS-Specific Delegation]: Routes to rhel8-linux-hypervisor.sh, rhel9-linux-hypervisor.sh, or rocky-linux-hetzner.sh
# - [Configuration Bridge]: Integrates with load-variables.py and enhanced_load_variables.py
# - [Security Integration]: Works with vault-integrated-setup.sh for credential management
# - [Container Orchestration]: Configures ansible-navigator with podman containers
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Universal Compatibility]: Detects and adapts to RHEL8/9, Rocky Linux, CentOS, and Fedora
# - [Container-First Approach]: Uses podman and ansible-navigator per ADR-0001
# - [Security-First Design]: Integrates HashiCorp Vault and AnsibleSafe per ADR-0004
# - [Modular Architecture]: Each function handles a specific deployment phase
# - [Idempotent Operations]: Can be run multiple times safely without side effects
#
# 💡 WHEN TO MODIFY THIS SCRIPT (for future LLMs):
# - [New OS Support]: Add detection logic in get_rhel_version() and configure_os()
# - [Package Updates]: Modify install_packages() for new dependencies
# - [Security Enhancements]: Update configure_vault() for new vault integrations
# - [Container Changes]: Modify configure_navigator() for new ansible-navigator versions
# - [Infrastructure Updates]: Update deploy_kvmhost() for new virtualization requirements
#
# 🚨 IMPORTANT FOR LLMs: This script requires root privileges and modifies system-wide
# configurations. It integrates with external services (GitHub, HashiCorp Vault) and
# creates persistent infrastructure. Changes here affect the entire deployment pipeline.

#github-action genshdoc

# @setting-header setup.sh quickstart script for qubinode_navigator
# @setting ./setup.sh
# Uncomment for debugging
#export PS4='+(${BASH_SOURCE}:${LINENO}): ${FUNCNAME[0]:+${FUNCNAME[0]}(): }'
#set -x

# 📊 GLOBAL VARIABLES (shared with other scripts):
# @global ANSIBLE_SAFE_VERSION this is the ansible safe version
# @global INVENTORY this is the inventory file name and path Example: inventories/localhost
export ANSIBLE_SAFE_VERSION="0.0.14"
export GIT_REPO="https://github.com/Qubinode/qubinode_navigator.git"
if [ -z "$CICD_PIPELINE" ]; then
  export CICD_PIPELINE="false"
  export INVENTORY="localhost"
fi

if [ -z "$USE_HASHICORP_VAULT" ]; then
  export USE_HASHICORP_VAULT="false"
else
    if [[ -z "$VAULT_ADDRESS" && -z "$VAULT_ADDRESS" && -z ${SECRET_PATH} ]]; then
      echo "VAULT enviornment variables are not passed  is not set"
      exit 1
    fi
fi

# OS Detection Engine - The "System Scanner"
function get_rhel_version() {
# 🎯 FOR LLMs: This function acts as the primary OS detection mechanism that determines
# which deployment path to follow. It's the first critical decision point in the setup process.
# 🔄 WORKFLOW:
# 1. Reads /etc/redhat-release file to identify OS type and version
# 2. Sets BASE_OS environment variable for downstream script selection
# 3. Provides fallback error handling for unsupported systems
# 📊 INPUTS/OUTPUTS:
# - INPUT: /etc/redhat-release file content
# - OUTPUT: BASE_OS environment variable (RHEL9, RHEL8, ROCKY8, CENTOS9, etc.)
# ⚠️  SIDE EFFECTS: Sets global BASE_OS variable used by configure_os() and other functions

  if cat /etc/redhat-release  | grep "Red Hat Enterprise Linux release 9.[0-9]" > /dev/null 2>&1; then
    export BASE_OS="RHEL9"
  elif cat /etc/redhat-release  | grep "Red Hat Enterprise Linux release 8.[0-9]" > /dev/null 2>&1; then
      export BASE_OS="RHEL8"
  elif cat /etc/redhat-release  | grep "Rocky Linux release 8.[0-9]" > /dev/null 2>&1; then
    export BASE_OS="ROCKY8"
  elif cat /etc/redhat-release  | grep 7.[0-9] > /dev/null 2>&1; then
    export BASE_OS="RHEL7"
  elif cat /etc/redhat-release  | grep "CentOS Stream release 9" > /dev/null 2>&1; then
    export BASE_OS="CENTOS9"
  elif cat /etc/redhat-release  | grep "CentOS Stream release 8" > /dev/null 2>&1; then
    export BASE_OS="CENTOS8"
  elif cat /etc/redhat-release  | grep "Fedora" > /dev/null 2>&1; then
    export BASE_OS="FEDORA"
  else
    echo "Operating System not supported"
    echo "You may put a pull request to add support for your OS"
  fi
  echo ${BASE_OS}

}

# Package Installation Manager - The "Supply Chain Coordinator"
function install_packages() {
# 🎯 FOR LLMs: This function ensures all required system packages are installed for
# Qubinode Navigator to function properly. It's idempotent and handles both individual
# packages and package groups.
# 🔄 WORKFLOW:
# 1. Iterates through essential packages list checking installation status
# 2. Installs missing packages using dnf package manager
# 3. Installs Development Tools group for compilation requirements
# 4. Adds Visual Studio Code repository and installs VS Code
# 5. Performs system update to ensure latest versions
# 📊 INPUTS/OUTPUTS:
# - INPUT: Predefined package list and system package database
# - OUTPUT: Fully configured system with all required packages
# ⚠️  SIDE EFFECTS: Modifies system packages, adds repositories, requires sudo privileges

    # Check if packages are already installed
    echo "Installing packages"
    echo "*******************"

    # 🔧 CONFIGURATION CONSTANTS FOR LLMs:
    # Core packages required for containerized Ansible execution and system management
    for package in openssl-devel bzip2-devel libffi-devel wget vim podman ncurses-devel sqlite-devel firewalld make gcc git unzip sshpass lvm lvm2 python3 python3-pip leapp-upgrade cockpit-leapp; do
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
        # Add Microsoft VS Code repository for development environment
        sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
        sudo sh -c 'echo -e "[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" > /etc/yum.repos.d/vscode.repo'
        dnf check-update
        sudo dnf install code -y
    fi

    sudo dnf update -y

}

# Repository Manager - The "Code Librarian"
function get_qubinode_navigator() {
# 🎯 FOR LLMs: This function manages the Qubinode Navigator repository, ensuring the latest
# code is available and properly linked for system-wide access.
# 🔄 WORKFLOW:
# 1. Checks if repository already exists in target directory
# 2. Updates existing repository or clones new one from GitHub
# 3. Creates symbolic link for system-wide access at /opt/qubinode_navigator
# 📊 INPUTS/OUTPUTS:
# - INPUT: $1 (target directory), GIT_REPO environment variable
# - OUTPUT: Cloned/updated repository with system symlink
# ⚠️  SIDE EFFECTS: Creates directories, modifies filesystem, requires network access

    echo "Cloning qubinode_navigator"
    if [ -d $1/qubinode_navigator ]; then
        echo "Qubinode Installer already exists"
        git -C "$1/qubinode_navigator" pull
    else
        cd "$1" || exit 1
        git clone ${GIT_REPO}
        sudo ln -sf "$1/qubinode_navigator" /opt/qubinode_navigator
    fi
}

# Ansible Navigator Configurator - The "Container Orchestrator"
function configure_navigator() {
# 🎯 FOR LLMs: This function configures ansible-navigator for containerized Ansible execution
# following ADR-0001 container-first execution model. It sets up the execution environment
# and inventory paths for consistent deployments.
# 🔄 WORKFLOW:
# 1. Installs ansible-navigator and dependencies via pip
# 2. Creates ~/.ansible-navigator.yml configuration file
# 3. Configures container engine (podman), execution environment image
# 4. Sets up inventory paths and logging configuration
# 📊 INPUTS/OUTPUTS:
# - INPUT: System Python environment, INVENTORY environment variable
# - OUTPUT: Configured ansible-navigator ready for containerized execution
# ⚠️  SIDE EFFECTS: Installs Python packages, creates configuration files

    echo "Configuring ansible navigator"
    echo "****************"
    if [ -d $1/qubinode_navigator ]; then
        cd $1/qubinode_navigator
        if ! command -v ansible-navigator &> /dev/null; then
            if [ ${BASE_OS}  == "RHEL8" ]; then
                # Enable the Python 3.9 Module
                sudo dnf module install -y python39
                sudo dnf install -y python39 python39-devel python39-pip
                sudo dnf module enable -y python39

                # Make sure the Python 3.6 Module is disabled
                sudo dnf module disable -y python36

                # Set the default Python version to 3.9
                sudo alternatives --set python /usr/bin/python3.9
                sudo alternatives --set python3 /usr/bin/python3.9

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

                # Install needed Pip modules
                # - For Ansible-Navigator
                curl -sSL https://raw.githubusercontent.com/ansible/ansible-navigator/main/requirements.txt | sudo python3 -m pip install -r /dev/stdin
                sudo python3 -m pip install -r $HOME/qubinode_navigator/bash-aliases/bastion-requirements.txt
            else
                make install-ansible-navigator
            fi

            make copy-navigator
            # Update ansible-navigator.yml with actual repository location
            local qubinode_path="$MY_DIR/qubinode_navigator"
            sed -i "s|/home/admin/qubinode_navigator/inventories/localhost|${qubinode_path}/inventories/${INVENTORY}|g" ~/.ansible-navigator.yml
        fi
    else
        echo "Qubinode Installer does not exist"
    fi
    cd $1/qubinode_navigator
    sudo pip3 install -r requirements.txt
    echo "Load variables"
    echo "**************"
    if [ $CICD_PIPELINE == "false" ];
    then
        python3 load-variables.py
    else
        if [[ -z "$ENV_USERNAME" && -z "$DOMAIN" && -z "$FORWARDER" && -z "$ACTIVE_BRIDGE" && -z "$INTERFACE" && -z "$DISK" ]]; then
            echo "Error: One or more environment variables are not set"
            exit 1
        fi
        python3 load-variables.py --username ${ENV_USERNAME} --domain ${DOMAIN} --forwarder ${FORWARDER} --bridge ${ACTIVE_BRIDGE} --interface ${INTERFACE} --disk ${DISK}
    fi
}

# @description This function configure_vault function will configure the ansible-vault it will download ansible vault and ansiblesafe
function configure_vault() {
    echo "Configuring vault using ansible safe"
    echo "****************"
    if [ -d $1/qubinode_navigator ]; then
        cd $1/qubinode_navigator
        if ! command -v ansible-vault &> /dev/null; then
            sudo dnf install ansible-core -y
        fi
        if ! command -v ansiblesafe &> /dev/null; then
            curl -OL https://github.com/tosin2013/ansiblesafe/releases/download/v0.0.12/ansiblesafe-v0.0.14-linux-amd64.tar.gz
            tar -zxvf ansiblesafe-v0.0.14-linux-amd64.tar.gz
            chmod +x ansiblesafe-linux-amd64
            sudo mv ansiblesafe-linux-amd64 /usr/local/bin/ansiblesafe
        fi
        echo "Configure Ansible Vault password file"
        echo "****************"

        if [ ! -f ~/qubinode_navigator/ansible_vault_setup.sh ];
        then
            curl -OL https://gist.githubusercontent.com/tosin2013/022841d90216df8617244ab6d6aceaf8/raw/92400b9e459351d204feb67b985c08df6477d7fa/ansible_vault_setup.sh
            chmod +x ansible_vault_setup.sh
        fi
        rm -f ~/.vault_password
        sudo rm -rf /root/.vault_password

        if [ $USE_HASHICORP_VAULT == "true" ];
        then
            echo "$SSH_PASSWORD" > ~/.vault_password
            sudo cp ~/.vault_password /root/.vault_password
            bash  ./ansible_vault_setup.sh
            if [ $(id -u) -ne 0 ]; then
                if [ ! -f /home/${USER}/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml ];
                then
                    ansiblesafe -f /home/${USER}/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml -o 4
                    ansiblesafe -f /home/${USER}/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml -o 1
                fi
            else
                local vault_file="$1/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml"
                if [ ! -f "$vault_file" ];
                then
                    ansiblesafe -f "$vault_file" -o 4
                    ansiblesafe -f "$vault_file" -o 1
                fi
            fi
        else
            read -t 360 -p "Press Enter to continue, or wait 5 minutes for the script to continue automatically" || true
            bash  ./ansible_vault_setup.sh
            local vault_file="$1/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml"
            if [ ! -f "$vault_file" ];
            then
                ansiblesafe -f "$vault_file"
            fi
        fi
        #ansible-navigator inventory --list -m stdout --vault-password-file $HOME/.vault_password
    else
        echo "Qubinode Installer does not exist"
    fi
}

# @description This function generate_inventory function will generate the inventory
function generate_inventory(){
    echo "Generating inventory"
    echo "****************"
    if [ -d $1/qubinode_navigator ]; then
        cd $1/qubinode_navigator
        if [ ! -d inventories/${INVENTORY} ]; then
            mkdir -p inventories/${INVENTORY}
            mkdir -p inventories/${INVENTORY}/group_vars/control
            cp -r inventories/${INVENTORY}/group_vars/control/* inventories/${INVENTORY}/group_vars/control/
        fi
        sed -i 's|export CURRENT_INVENTORY="localhost"|export CURRENT_INVENTORY="'${INVENTORY}'"|g' bash-aliases/random-functions.sh
        # set the values
        control_host="$(hostname -I | awk '{print $1}')"
        # Check if running as root
        if [ "$EUID" -eq 0 ]; then
            read -p "Enter the target username to ssh into machine: " control_user
        else
            control_user="$USER"
        fi

        echo "[control]" > inventories/${INVENTORY}/hosts
        echo "control ansible_host=${control_host} ansible_user=${control_user}" >> inventories/${INVENTORY}/hosts
        if ! command -v ansible-navigator &> /dev/null; then
            sudo pip3 install ansible-navigator
            whereis ansible-navigator
            ANSIBLE_NAVIAGATOR=$(whereis ansible-navigator | awk '{print $2}')
        else
            ANSIBLE_NAVIAGATOR="ansible-navigator "
        fi
        ${ANSIBLE_NAVIAGATOR} inventory --list -m stdout --vault-password-file $HOME/.vault_password
    else
        echo "Qubinode Installer does not exist"
    fi
}

# @description This function configure_ssh function will configure the ssh
function configure_ssh(){
    echo "Configuring SSH"
    echo "****************"
    if [ -f ~/.ssh/id_rsa ]; then
        echo "SSH key already exists"
    else
        IP_ADDRESS=$(hostname -I | awk '{print $1}')
        ssh-keygen -f ~/.ssh/id_rsa -t rsa -N ''
        # Check if running as root
        if [ $CICD_PIPELINE == "true" ];
        then
            if [ "$EUID" -eq 0 ]; then
                sshpass -p "$SSH_PASSWORD" ssh-copy-id -o StrictHostKeyChecking=no $control_user@${IP_ADDRESS}
            else
                sshpass -p "$SSH_PASSWORD" ssh-copy-id -o StrictHostKeyChecking=no $USER@${IP_ADDRESS}
                sudo ssh-keygen -f /root/.ssh/id_rsa -t rsa -N ''
            fi
        else
            if [ "$EUID" -eq 0 ]; then
                read -p "Enter the target username to ssh into machine: " control_user
                ssh-copy-id $control_user@${IP_ADDRESS}
            else
                ssh-copy-id $USER@${IP_ADDRESS}
                sudo ssh-keygen -f /root/.ssh/id_rsa -t rsa -N ''
            fi
        fi
    fi
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

function configure_onedev(){
    local qubinode_dir="$MY_DIR/qubinode_navigator"
    if [ "$(pwd)" != "$qubinode_dir" ]; then
        echo "Current directory is not $qubinode_dir."
        echo "Changing to $qubinode_dir..."
        cd "$qubinode_dir" || exit 1
    else
        echo "Current directory is $qubinode_dir."
    fi
    echo "Configuring OneDev"
    echo "******************"
    ./dependancies/onedev/configure-onedev.sh
}

# @description This configure_os function will get the base os and install the required packages
function configure_os(){
    if [ ${1} == "ROCKY8" ]; then
        sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make sshpass -y
    elif [ ${1} == "FEDORA" ]; then
        sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make  sshpass -y
    elif [ ${1} == "UBUNTU" ]; then
        sudo apt install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make  sshpass -y
    elif [ ${1} == "CENTOS8" ]; then
        sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make sshpass -y
    elif [ ${1} == "RHEL9" ]; then
        sudo dnf update -y
        sudo dnf install git vim unzip wget bind-utils python3.11 python3.11-pip python3.11-devel tar util-linux-user gcc podman ansible-core make sshpass -y
        # Set Python 3.11 as default for ansible-navigator v25.5.0+ compatibility
        sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
        sudo alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.11 1
    elif [ ${1} == "CENTOS9" ]; then
        sudo dnf update -y
        sudo dnf install git vim unzip wget bind-utils python3.11 python3.11-pip python3.11-devel tar util-linux-user gcc podman ansible-core make sshpass -y
        # Set Python 3.11 as default for ansible-navigator v25.5.0+ compatibility
        sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
        sudo alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.11 1
    elif [ ${1} == "RHEL10" ]; then
        sudo dnf update -y
        sudo dnf install git vim unzip wget bind-utils python3 python3-pip python3-devel tar util-linux-user gcc podman ansible-core make sshpass -y
        # Python 3.12 is the default in RHEL 10, no alternatives needed
        echo "Using Python 3.12 (default in RHEL 10)"
    elif [ ${1} == "CENTOS10" ]; then
        sudo dnf update -y
        sudo dnf install git vim unzip wget bind-utils python3 python3-pip python3-devel tar util-linux-user gcc podman ansible-core make sshpass -y
        # Python 3.12 is the default in CentOS Stream 10, no alternatives needed
        echo "Using Python 3.12 (default in CentOS Stream 10)"
    fi
}

function test_inventory(){
    echo "Testing inventory"
    echo "****************"
    if [ -d $1/qubinode_navigator ]; then
        cd $1/qubinode_navigator
        if ! command -v ansible-navigator &> /dev/null; then
            ANSIBLE_NAVIAGATOR=$(whereis ansible-navigator | awk '{print $2}')
        else
            ANSIBLE_NAVIAGATOR="ansible-navigator "
        fi
        ${ANSIBLE_NAVIAGATOR}  inventory --list -m stdout --vault-password-file $HOME/.vault_password || exit 1
    else
        echo "Qubinode Installer does not exist"
    fi
}



function deploy_kvmhost() {
    echo "Deploying KVM Host"
    echo "******************"
    eval $(ssh-agent)
    ssh-add ~/.ssh/id_rsa
    cd "$MY_DIR"/qubinode_navigator || exit 1
    if ! command -v ansible-navigator &> /dev/null; then
        ANSIBLE_NAVIAGATOR=$(whereis ansible-navigator | awk '{print $2}')
    else
        ANSIBLE_NAVIAGATOR="ansible-navigator"
    fi
    ${ANSIBLE_NAVIAGATOR} run ansible-navigator/setup_kvmhost.yml \
        --vault-password-file "$HOME"/.vault_password -m stdout || exit 1
}

function configure_bash_aliases() {
    echo "Configuring bash aliases"
    echo "************************"
    local qubinode_dir="$MY_DIR/qubinode_navigator"
    if [ "$(pwd)" != "$qubinode_dir" ]; then
        echo "Current directory is not $qubinode_dir."
        echo "Changing to $qubinode_dir..."
        cd "$qubinode_dir" || exit 1
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

function setup_kcli_base() {
    local qubinode_dir="$MY_DIR/qubinode_navigator"
    if [ "$(pwd)" != "$qubinode_dir" ]; then
        echo "Current directory is not $qubinode_dir."
        echo "Changing to $qubinode_dir..."
        cd "$qubinode_dir" || exit 1
    else
        echo "Current directory is $qubinode_dir."
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

get_rhel_version


if [  $BASE_OS == "ROCKY8" ];
then
  echo "Please run the rocky-linux-hypervisor.sh script"
  exit 1
fi

# Set working directory - use script's actual location rather than user home
# This ensures the script works correctly whether run directly or via sudo
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# If script is at /path/to/qubinode_navigator/scripts/development/setup.sh,
# SCRIPT_DIR is /path/to/qubinode_navigator/scripts/development
# MY_DIR should be /path/to (two levels up from SCRIPT_DIR: ../scripts/.. = /)
MY_DIR="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"

if [ $# -eq 0 ]; then
    configure_os  $BASE_OS
    install_packages
    configure_ssh
    configure_firewalld
    get_qubinode_navigator $MY_DIR
    configure_navigator $MY_DIR
    configure_vault $MY_DIR
    generate_inventory $MY_DIR
    test_inventory $MY_DIR
    deploy_kvmhost
    configure_bash_aliases $MY_DIR
    setup_kcli_base  $MY_DIR
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
            configure_bash_aliases  $MY_DIR
            shift
            ;;
        --setup-kcli-base)
            setup_kcli_base  $MY_DIR
            shift
            ;;
        --deploy-freeipa)
            freeipa-utils deploy
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done
