#!/bin/bash
# Uncomment for debugging
export PS4='+(${BASH_SOURCE}:${LINENO}): ${FUNCNAME[0]:+${FUNCNAME[0]}(): }'
set -x

KVM_VERSION=0.4.0
export ANSIBLE_SAFE_VERSION="0.0.5"
export INVENTORY="localhost"

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root"
    exit 1
fi

if [ -z "$CICD_PIPELINE" ]; then
  export CICD_PIPELINE="false"
  exit 1
fi
echo "CICD_PIPELINE is set to $CICD_PIPELINE" 


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
            read -r -p "Enter the target username to ssh into machine: " control_user
        else
            control_user="$USER"
        fi

        echo "[control]" >inventories/${INVENTORY}/hosts
        echo "control ansible_host=${control_host} ansible_user=${control_user}" >>inventories/${INVENTORY}/hosts
        configure_ansible_navigator
        ansible-navigator inventory --list -m stdout --vault-password-file "$HOME"/.vault_password
    else
        echo "Qubinode Installer does not exist"
    fi
}

function install_packages() {
    # Check if packages are already installed
    echo "Installing packages"
    echo "*******************"
    for package in openssl-devel bzip2-devel libffi-devel wget vim podman ncurses-devel sqlite-devel firewalld make gcc git unzip sshpass; do
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
    if which python3 >/dev/null; then
        echo "Python is installed"
        source ~/.profile
    else
        # Download Python 3.11 source code
        VERSION=3.11.2
        wget https://www.python.org/ftp/python/$VERSION/Python-$VERSION.tgz
        tar -xzf Python-$VERSION.tgz

        # Install Python 3.11
        cd Python-$VERSION
        ./configure --enable-loadable-sqlite-extensions --enable-optimizations
        sudo make altinstall

        # Verify Python 3.11 installation
        python3.11 --version
        pip3.11 --version

        sudo ln /usr/local/bin/python3.11 /usr/bin/python3
        sudo ln /usr/local/bin/python3.11 /usr/bin/python3.11
        sudo ln /usr/local/bin/pip3.11 /usr/bin/pip3

        sudo pip3 install setuptools-rust
        sudo pip3 install --user ansible-core
        sudo pip3 install --upgrade --user ansible
        sudo pip3 install ansible-navigator
        sudo pip3 install firewall
        sudo pip3 install pyyaml
        sudo pip3 install ansible-vault
        echo 'export PATH=$HOME/.local/bin:$PATH' >>~/.profile
        source ~/.profile
    fi
}

function configure_navigator() {
    echo "Configuring Qubinode Navigator"
    echo "******************************"
    if [ -d "$HOME"/qubinode_navigator ]; then
        echo "Qubinode Navigator already exists"
    else
        cd "$HOME"
        git clone https://github.com/tosin2013/qubinode_navigator.git
    fi
    cd "$HOME"/qubinode_navigator
    sudo pip3 install -r requirements.txt

    echo "Current DNS Server: $(cat /etc/resolv.conf | grep nameserver | awk '{print $2}' | head -1)"
    echo "Load variables"
    echo "**************"
    if [ $CICD_PIPELINE == "false" ];
    then
        read -t 360 -p "Press Enter to continue, or wait 5 minutes for the script to continue automatically" || true
        python3 load-variables.py
    else 
        if [[ -z "$ENV_USERNAME" && -z "$DOMAIN" && -z "$FORWARDER" && -z "$ACTIVE_BRIDGE" && -z "$INTERFACE" && -z "$DISK" ]]; then
            echo "Error: One or more environment variables are not set"
            exit 1
        fi
        python3 load-variables.py --username ${ENV_USERNAME} --domain ${DOMAIN} --forwarder ${FORWARDER} --bridge ${ACTIVE_BRIDGE} --interface ${INTERFACE} --disk ${DISK}
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
        else
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
    inventories:    
      - /root/qubinode_navigator/inventories/localhost
  logging:
    level: debug
    append: true
    file: /tmp/navigator/ansible-navigator.log
  playbook-artifact:
    enable: false
  execution-environment:
    container-engine: podman
    enabled: true
    pull-policy: missing
    image: quay.io/qubinode/qubinode-installer:${KVM_VERSION}
    environment-variables:
      pass:
        - USER
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
    if [ $CICD_PIPELINE == "true" ];
    then    
        echo "$SSH_PASSWORD" > ~/.vault_password
        bash  ./ansible_vault_setup.sh
    else 
        bash  ./ansible_vault_setup.sh
    fi 

    
    source ~/.profile
    curl -OL https://github.com/tosin2013/ansiblesafe/releases/download/v${ANSIBLE_SAFE_VERSION}/ansiblesafe-v${ANSIBLE_SAFE_VERSION}-linux-amd64.tar.gz
    tar -zxvf ansiblesafe-v${ANSIBLE_SAFE_VERSION}-linux-amd64.tar.gz
    chmod +x ansiblesafe-linux-amd64
    sudo mv ansiblesafe-linux-amd64 /usr/local/bin/ansiblesafe

    ansiblesafe -f /root/qubinode_navigator/inventories/localhost/group_vars/control/vault.yml
    generate_inventory /root
}

function test_inventory() {
    echo "Testing Ansible Inventory"
    echo "*************************"
    ansible-navigator inventory --list -m stdout --vault-password-file "$HOME"/.vault_password || exit 1
}

function deploy_kvmhost() {
    echo "Deploying KVM Host"
    echo "******************"
    eval $(ssh-agent)
    ssh-add ~/.ssh/id_rsa
    cd "$HOME"/qubinode_navigator
    source ~/.profile
    ansible-navigator run ansible-navigator/setup_kvmhost.yml \
        --vault-password-file "$HOME"/.vault_password -m stdout || exit 1
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
    if [ -f ~/.bash_aliases ]; then
        echo "bash_aliases already exists"
    else
        ./bash-aliases/setup-commands.sh || exit 1
    fi
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
    kcli-utils setup
    kcli-utils configure-images
    kcli-utils check-kcli-plan
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
    configure_ssh
    install_packages
    configure_python
    configure_firewalld
    configure_groups
    configure_navigator
    configure_ansible_vault_setup
    test_inventory
    deploy_kvmhost
    configure_bash_aliases
    setup_kcli_base
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
