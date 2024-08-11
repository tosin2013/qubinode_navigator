#!/bin/bash
export PS4='+(${BASH_SOURCE}:${LINENO}): ${FUNCNAME[0]:+${FUNCNAME[0]}(): }'
set -x
set -euo pipefail

# Global variables
readonly KVM_VERSION="0.8.0"
#readonly ANSIBLE_SAFE_VERSION="0.0.12"
readonly GIT_REPO="https://github.com/tosin2013/qubinode_navigator.git"

# Set default values for environment variables if they are not already set
: "${CICD_PIPELINE:="false"}"
: "${USE_HASHICORP_VAULT:="false"}"
: "${USE_HASHICORP_CLOUD:="false"}"
: "${VAULT_ADDRESS:=""}"
: "${VAULT_TOKEN:=""}"
: "${USE_ROUTE53:="false"}"
: "${ROUTE_53_DOMAIN:=""}"
: "${CICD_ENVIORNMENT:="gitlab"}"
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

# Function to handle HashiCorp Cloud Vault flag
hcp_cloud_vault() {
  # Check if the required environment variables are set
    if [[ -z "${HCP_CLIENT_ID}" ]]; then
        echo "Error: HCP_CLIENT_ID is not set."
        exit 1
    fi
    if [[ -z "${HCP_CLIENT_SECRET}" ]]; then
        echo "Error: HCP_CLIENT_SECRET is not set."
        exit 1
    fi
    if [[ -z "${HCP_ORG_ID}" ]]; then
        echo "Error: HCP_ORG_ID is not set."
        exit 1
    fi
    if [[ -z "${HCP_PROJECT_ID}" ]]; then
        echo "Error: HCP_PROJECT_ID is not set."
        exit 1
    fi
    if [[ -z "${APP_NAME}" ]]; then
        echo "Error: APP_NAME is not set."
        exit 1
    fi
}

# Function to install packages
install_packages() {
    log_message "Installing required packages..."
    local packages=(openssl-devel bzip2-devel libffi-devel wget vim podman ncurses-devel sqlite-devel firewalld make gcc git unzip sshpass lvm2 python3 python3-pip java-11-openjdk-devel ansible-core)
    for package in "${packages[@]}"; do
        if ! rpm -q "$package" &>/dev/null; then
            if ! dnf install -y "$package"; then
                log_message "Failed to install package: $package"
                exit 1
            fi
        fi
    done
    if ! dnf groupinstall -y "Development Tools"; then
        log_message "Failed to install Development Tools"
        exit 1
    fi
    if ! dnf update -y; then
        log_message "Failed to update packages"
        exit 1
    fi
}

# Function to clone the repository
clone_repository() {
    if [ ! -d "/opt/qubinode_navigator" ]; then
        log_message "Cloning qubinode_navigator repository..."
        if ! git clone "$GIT_REPO" "/opt/qubinode_navigator"; then
            log_message "Failed to clone repository"
            exit 1
        fi
    fi
}

# Function to configure Ansible Navigator
configure_ansible_navigator() {
    if ! command -v ansible-navigator &>/dev/null; then
        log_message "Installing ansible-navigator..."
        if ! pip3 install ansible-navigator --user; then
            log_message "Failed to install ansible-navigator"
            exit 1
        fi
        echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.profile
        source ~/.profile
    fi
    log_message "Configuring ansible-navigator..."
    cd "/opt/qubinode_navigator"
    if ! pip3 install -r requirements.txt; then
        log_message "Failed to install Ansible Navigator requirements"
        exit 1
    fi

    log_message "Configuring Ansible Navigator settings"
    cat >~/.ansible-navigator.yml <<EOF
---
ansible-navigator:
  ansible:
    inventory:
      entries:
      - /opt/qubinode_navigator/inventories/${INVENTORY}
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
        local ansiblesafe_url="https://github.com/tosin2013/ansiblesafe/releases/download/v0.0.12/ansiblesafe-v0.0.14-linux-amd64.tar.gz"
        if ! curl -OL "$ansiblesafe_url"; then
            log_message "Failed to download ansiblesafe"
            exit 1
        fi
        if ! tar -zxvf "ansiblesafe-v0.0.14-linux-amd64.tar.gz"; then
            log_message "Failed to extract ansiblesafe"
            exit 1
        fi
        chmod +x ansiblesafe-linux-amd64
        mv ansiblesafe-linux-amd64 /usr/local/bin/ansiblesafe
    fi
    if [ ! -f "/opt/qubinode_navigator/ansible_vault_setup.sh" ]; then
        if ! curl -OL https://gist.githubusercontent.com/tosin2013/022841d90216df8617244ab6d6aceaf8/raw/92400b9e459351d204feb67b985c08df6477d7fa/ansible_vault_setup.sh; then
            log_message "Failed to download ansible_vault_setup.sh"
            exit 1
        fi
        chmod +x ansible_vault_setup.sh
    fi
    rm -f ~/.vault_password
    if [ "$CICD_PIPELINE" == "true" ]; then 
        if [ -z "$SSH_PASSWORD" ]; then
            log_message "SSH_PASSWORD environment variable is not set"
            exit 1
        fi   
        echo "$SSH_PASSWORD" > ~/.vault_password
        sudo cp ~/.vault_password /home/lab-user/.vault_password 
        if ! bash ./ansible_vault_setup.sh; then
            log_message "Failed to execute ansible_vault_setup.sh"
            exit 1
        fi
        if [ -f /tmp/config.yml ] && [  "$USE_HASHICORP_CLOUD"  == "false" ]; then
            log_message "Copying config.yml to vault.yml"
            if [ -f /opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml ];
            then 
              rm -rf /opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml
            fi 
            
            cp -avi /tmp/config.yml "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml"
            ls -l "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" || exit $?
            if ! /usr/local/bin/ansiblesafe -f "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" -o 1; then
                log_message "Failed to encrypt vault.yml"
                exit 1
            fi
        elif [ "$USE_HASHICORP_CLOUD" == "true" ]; then
            log_message "Copying config.yml to vault.yml"
            if [ -f /opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml ];
            then 
              rm -rf /opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml
            fi 
            
            /usr/local/bin/ansiblesafe -o 5  --file="/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" || exit $?
            ls -l "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" || exit $?
            if ! /usr/local/bin/ansiblesafe -f "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" -o 1; then
                log_message "Failed to encrypt vault.yml"
                exit 1
            fi
        else
            log_message "Error:/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml  not created"
            exit 1
        fi
    else 
        if ! bash ./ansible_vault_setup.sh; then
            log_message "Failed to execute ansible_vault_setup.sh"
            exit 1
        fi
        if ! /usr/local/bin/ansiblesafe -f "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml"; then
            log_message "Failed to encrypt vault.yml"
            exit 1
        fi
    fi
}

function configure_bash_aliases() {
    echo "Configuring bash aliases"
    echo "************************"
    if [ "$(pwd)" != "/opt/qubinode_navigator" ]; then
        echo "Current directory is not /opt/qubinode_navigator."
        echo "Changing to /opt/qubinode_navigator..."
        cd /opt/qubinode_navigator
    else
        echo "Current directory is /opt/qubinode_navigator."
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
        curl -OL https://raw.githubusercontent.com/tosin2013/qubinode_navigator/main/dependancies/equinix-rocky/configure-lvm.sh
        mv configure-lvm.sh /tmp/configure-lvm.sh
        sudo chmod +x /tmp/configure-lvm.sh
    fi 
    /tmp/configure-lvm.sh || exit 1
}


# Function to configure Qubinode Navigator
configure_navigator() {
    log_message "Configuring Qubinode Navigator..."
    echo "******************************"
    if [ -d "/opt/qubinode_navigator" ]; then
        log_message "Qubinode Navigator already exists"
        git -C "/opt/qubinode_navigator" pull
    else
        cd "$HOME"
        sudo usermod -aG users "$USER"
        sudo chown -R root:users /opt
        sudo chmod -R g+w /opt
        if ! git clone "${GIT_REPO}"; then
            log_message "Failed to clone repository"
            exit 1
        fi
        ln -s /opt/qubinode_navigator /opt/qubinode_navigator
    fi
    cd "/opt/qubinode_navigator"
    if ! sudo pip3 install -r requirements.txt; then
        log_message "Failed to install Qubinode Navigator requirements"
        exit 1
    fi
    log_message "Current DNS Server: $(cat /etc/resolv.conf | grep nameserver | awk '{print $2}' | head -1)"
    log_message "Load variables"
    echo "**************"
    if [ "$CICD_PIPELINE" == "false" ]; then
        read -t 360 -p "Press Enter to continue, or wait 5 minutes for the script to continue automatically" || true
        if ! python3 load-variables.py; then
            log_message "Failed to load variables"
            exit 1
        fi
    else 
        if [[ -z "$ENV_USERNAME" || -z "$DOMAIN" || -z "$FORWARDER" || -z "$INTERFACE" ]]; then
            log_message "Error: One or more environment variables are not set"
            exit 1
        fi
        if ! python3 load-variables.py --username "${ENV_USERNAME}" --domain "${DOMAIN}" --forwarder "${FORWARDER}" --interface "${INTERFACE}"; then
            log_message "Failed to load variables with environment parameters"
            exit 1
        fi
    fi
}

# Function to generate inventory
generate_inventory() {
    log_message "Generating inventory..."
    if [ ! -d "/opt/qubinode_navigator/inventories/$INVENTORY" ]; then
        mkdir -p "/opt/qubinode_navigator/inventories/$INVENTORY/group_vars/control"
    fi
    local control_host="$(hostname -I | awk '{print $1}')"
    local control_user="$USER"
    echo "[control]" > "/opt/qubinode_navigator/inventories/$INVENTORY/hosts"
    echo "control ansible_host=$control_host ansible_user=$control_user" >> "/opt/qubinode_navigator/inventories/$INVENTORY/hosts"
    if ! ansible-navigator inventory --list -m stdout --vault-password-file ~/.vault_password; then
        log_message "Failed to list Ansible inventory"
        exit 1
    fi
}

# Function to configure SSH
configure_ssh() {
    log_message "Configuring SSH..."
    if [ ! -f ~/.ssh/id_rsa ]; then
        if ! ssh-keygen -t rsa -N '' -f ~/.ssh/id_rsa; then
            log_message "Failed to generate SSH key"
            exit 1
        fi
        if ! ssh-copy-id "$USER@$(hostname -I | awk '{print $1}')"; then
            log_message "Failed to copy SSH key"
            exit 1
        fi
    fi
}

# Function to configure firewalld
configure_firewalld() {
    log_message "Configuring firewalld..."
    if ! systemctl start firewalld; then
        log_message "Failed to start firewalld"
        exit 1
    fi
    if ! systemctl enable firewalld; then
        log_message "Failed to enable firewalld"
        exit 1
    fi
}

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

# Function to set up KCLI base
setup_kcli_base() {
    if [ "$(pwd)" != "/opt/qubinode_navigator" ]; then
        echo "Current directory is not /opt/qubinode_navigator."
        echo "Changing to /opt/qubinode_navigator..."
        cd /opt/qubinode_navigator
    else
        echo "Current directory is /opt/qubinode_navigator."
    fi
    echo "Configuring Kcli"
    echo "****************"
    source ~/.bash_aliases
    qubinode_setup_kcli
    kcli_configure_images
}

# Function to configure OneDev
configure_onedev() {
    if [ "$(pwd)" != "/opt/qubinode_navigator" ]; then
        echo "Current directory is not /opt/qubinode_navigator."
        echo "Changing to /opt/qubinode_navigator..."
        cd /opt/qubinode_navigator
    else
        echo "Current directory is /opt/qubinode_navigator."
    fi
    echo "Configuring OneDev"
    echo "******************"
    ./dependancies/onedev/configure-onedev.sh
}
# Function to configure Route53
configure_route53() {
    if [ "$(pwd)" != "/opt/qubinode_navigator" ]; then
        echo "Current directory is not /opt/qubinode_navigator."
        echo "Changing to /opt/qubinode_navigator..."
        cd /opt/qubinode_navigator
    else
        echo "Current directory is /opt/qubinode_navigator."
    fi
    echo "Configuring OneDev"
    echo "******************"
    ./dependancies/route53/deployment-script.sh
}
# Function to configure GitLab
configure_gitlab() {
    if [ "$(pwd)" != "/opt/qubinode_navigator" ]; then
        echo "Current directory is not /opt/qubinode_navigator."
        echo "Changing to /opt/qubinode_navigator..."
        cd /opt/qubinode_navigator
    else
        echo "Current directory is /opt/qubinode_navigator."
    fi
    echo "Configuring GitLab"
    echo "******************"
    ./dependancies/gitlab/deployment-script.sh
}

# Main function
main() {
    check_root
    handle_hashicorp_vault
    if [ "$USE_HASHICORP_CLOUD" == "true" ]; then
        hcp_cloud_vault
    fi
    install_packages
    configure_firewalld
    confiure_lvm_storage
    clone_repository
    configure_ansible_navigator
    configure_ansible_vault
    generate_inventory
    configure_navigator
    configure_ssh
    deploy_kvmhost
    configure_bash_aliases
    setup_kcli_base
    configure_route53
    if [ "$CICD_ENVIORNMENT" == "onedev" ]; then
        configure_onedev
    elif [ "$CICD_ENVIORNMENT" == "gitlab" ]; then
        configure_gitlab
    else
        log_message "Error: CICD_ENVIORNMENT is not set"
        exit 1
    fi
}

main "$@"
