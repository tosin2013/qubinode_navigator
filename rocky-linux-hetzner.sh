#!/bin/bash
# Uncomment for debugging
#export PS4='+(${BASH_SOURCE}:${LINENO}): ${FUNCNAME[0]:+${FUNCNAME[0]}(): }'
#set -x

KVM_VERSION=0.8.0
export ANSIBLE_SAFE_VERSION="0.0.7"

export GIT_REPO="https://github.com/tosin2013/qubinode_navigator.git"
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root"
    exit 1
fi

if [ -z "$CICD_PIPELINE" ]; then
export CICD_PIPELINE="false"
export INVENTORY="hetzner"
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
        sed -i 's|export CURRENT_INVENTORY="localhost"|export CURRENT_INVENTORY="'${INVENTORY}'"|g' bash-aliases/random-functions.sh
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
    for package in openssl-devel bzip2-devel libffi-devel wget vim podman ncurses-devel sqlite-devel firewalld make gcc git unzip sshpass lvm lvm2 zlib-devel python3-pip; do
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

    if ! command -v ansible-navigator &> /dev/null
    then
        echo "ansible-navigator not found, installing..."
        curl -sSL https://raw.githubusercontent.com/ansible/ansible-navigator/fix/devel-testing/requirements.txt | python3 -m pip install -r /dev/stdin --user lab-user
        pip3 install -r /root/qubinode_navigator/dependancies/hetzner/bastion-requirements.txt --user lab-user
        curl -sSL https://raw.githubusercontent.com/ansible/ansible-navigator/fix/devel-testing/requirements.txt | python3 -m pip install -r /dev/stdin
        pip3 install -r /root/qubinode_navigator/dependancies/hetzner/bastion-requirements.txt
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
    else
        cd "$HOME"
        git clone ${GIT_REPO}
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
        if [[ -z "$ENV_USERNAME" && -z "$DOMAIN" && -z "$FORWARDER" && -z "$INTERFACE" ]]; then
            echo "Error: One or more environment variables are not set"
            exit 1
        fi
        python3 load-variables.py --username ${ENV_USERNAME} --domain ${DOMAIN} --forwarder ${FORWARDER} --interface ${INTERFACE} 
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
        curl -OL https://github.com/tosin2013/ansiblesafe/releases/download/v${ANSIBLE_SAFE_VERSION}/ansiblesafe-v${ANSIBLE_SAFE_VERSION}-linux-amd64.tar.gz
        tar -zxvf ansiblesafe-v${ANSIBLE_SAFE_VERSION}-linux-amd64.tar.gz
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
    if [ -f ~/.bash_aliases ]; then
        echo "bash_aliases already exists"
        ./bash-aliases/setup-commands.sh || exit 1
    else
        ./bash-aliases/setup-commands.sh || exit 1
    fi
}

function confiure_lvm_storage(){
    echo "Configuring Storage"
    echo "************************"
    if [ ! -f /tmp/configure-lvm.sh ];
    then 
        curl -OL https://raw.githubusercontent.com/tosin2013/qubinode_navigator/main/dependancies/equinix-rocky/configure-lvm.sh
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
    source ~/.profile
    source ~/.bash_aliases
    kcli-utils setup
    kcli-utils configure-images
    kcli-utils check-kcli-plan
    curl -OL https://raw.githubusercontent.com/tosin2013/kcli-pipelines/hetzner/configure-kcli-profiles.sh
    chmod +x configure-kcli-profiles.sh
    ./configure-kcli-profiles.sh
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
    enable_ssh_password_authentication
    install_packages
    configure_python
    configure_ssh
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
