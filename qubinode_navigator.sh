#!/bin/bash
# Uncomment for debugging
export PS4='+(${BASH_SOURCE}:${LINENO}): ${FUNCNAME[0]:+${FUNCNAME[0]}(): }'
set -x

KVM_VERSION=0.8.0
export ANSIBLE_SAFE_VERSION="0.0.9"

export GIT_REPO="https://github.com/tosin2013/qubinode_navigator.git"
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root"
    exit 1
fi

# Load .env file if it exists
if [ -f /opt/qubinode_navigator/.env ]; then
    source /opt/qubinode_navigator/.env
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
: "${INVENTORY:="localhost"}"
: "${DEVELOPMENT_MODEL:="false"}"
: "${CONFIG_TEMPLATE:="localhost.yml.j2"}"
: "${VAULT_DEV_MODE:="false"}"

echo "CICD_PIPELINE is set to $CICD_PIPELINE"

if [ -z "$GUID" ]; then
  export GUID="$(uuidgen | cut -c 1-5)"
fi

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
    if [ -d "/opt/qubinode_navigator" ] && [ -f "/opt/qubinode_navigator/vault-integrated-setup.sh" ]; then
        qubinode_dir="/opt/qubinode_navigator"
    elif [ -f "./vault-integrated-setup.sh" ]; then
        qubinode_dir="$(pwd)"
    else
        qubinode_dir="/opt/qubinode_navigator"
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

# Function: check_for_lab_user
# Description: Checks if the lab-user exists and creates it if it doesn't.
#              This ensures compatibility regardless of the current system user.
# Parameters: None
# Returns: None
# Exit Codes: 1 - If user creation fails
check_for_lab_user() {
    if id "lab-user" &>/dev/null; then
        log_message "User lab-user exists"
    else
        log_message "Creating lab-user for system compatibility..."
        if ! curl -OL https://gist.githubusercontent.com/tosin2013/385054f345ff7129df6167631156fa2a/raw/b67866c8d0ec220c393ea83d2c7056f33c472e65/configure-sudo-user.sh; then
            log_message "Failed to download configure-sudo-user.sh"
            exit 1
        fi
        chmod +x configure-sudo-user.sh
        if ! ./configure-sudo-user.sh lab-user; then
            log_message "Failed to create lab-user"
            exit 1
        fi
        log_message "✅ lab-user created successfully"
    fi
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
    OS_VERSION=$(cat /etc/os-release | grep VERSION_ID | cut -d'"' -f2)

    # Check if we're on RHEL/Rocky 9 and need Python 3.11 for ansible-navigator v25.5.0+
    if [[ "$OS_VERSION" =~ ^9\. ]]; then
        echo "Detected RHEL/Rocky Linux 9. Installing Python 3.11 for ansible-navigator compatibility..."

        # Install Python 3.11 for ansible-navigator v25.5.0+ compatibility
        sudo dnf install -y python3.11 python3.11-devel python3.11-pip

        # Set Python 3.11 as the default python3
        sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
        sudo alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.11 1

        echo "Python 3.11 installed and set as default"
    elif [ "$PYTHON_VERSION" == "3.6.8" ]; then
        echo "Python version is 3.6.8. Upgrading to 3.9..."

        # Enable the Python 3.9 Module
        sudo dnf module install -y python39
        sudo dnf install -y python39 python39-devel python39-pip
        sudo dnf module enable -y python39

        # Make sure the Python 3.6 Module is disabled
        sudo dnf module disable -y python36

        # Set the default Python version to 3.9
        sudo alternatives --set python /usr/bin/python3.9
        sudo alternatives --set python3 /usr/bin/python3.9
    else
        echo "Python version ${PYTHON_VERSION}. Continuing..."
    fi

    if ! command -v ansible-navigator &> /dev/null
    then
        # - For Ansible-Navigator (use latest version for Python 3.11+ compatibility)
        curl -sSL https://raw.githubusercontent.com/ansible/ansible-navigator/main/requirements.txt | sudo python3 -m pip install -r /dev/stdin
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
    else
        cd "$HOME"
        sudo usermod -aG users $USER
        sudo chown -R root:users /opt
        sudo chmod -R g+w /opt
        git clone ${GIT_REPO}
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
        if [ -z "$SSH_PASSWORD" ]; then
            echo "SSH_PASSWORD enviornment variable is not set"
            exit 1
        fi   
        echo "$SSH_PASSWORD" > ~/.vault_password
        sudo cp ~/.vault_password /root/.vault_password 
        sudo cp ~/.vault_password /home/lab-user/.vault_password 
        bash  ./ansible_vault_setup.sh
    else 
        bash  ./ansible_vault_setup.sh
    fi 


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
    check_for_lab_user
    install_packages
    configure_ssh || exit $?
    confiure_lvm_storage
    configure_python
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
