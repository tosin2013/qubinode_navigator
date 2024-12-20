#!/bin/bash
#export PS4='+(${BASH_SOURCE}:${LINENO}): ${FUNCNAME[0]:+${FUNCNAME[0]}(): }'
#set -x
set -euo pipefail

# This script is located at /Users/takinosh/workspace/qubinode_navigator/rhel9-linux-hypervisor.sh
#
# Global variables:
# KVM_VERSION: Specifies the version of KVM to be used.
# GIT_REPO: URL of the Git repository for the Qubinode Navigator project.
# Global variables
readonly KVM_VERSION="0.8.0"
#readonly ANSIBLE_SAFE_VERSION="0.0.12"
readonly GIT_REPO="https://github.com/tosin2013/qubinode_navigator.git"

# This script sets default values for various environment variables used in the
# rhel9-linux-hypervisor.sh script. If these variables are not already set in the
# environment, the script will assign them the following default values:
#
# CICD_PIPELINE: Determines if the script is running in a CI/CD pipeline. Default is "false".
# USE_HASHICORP_VAULT: Indicates whether to use HashiCorp Vault. Default is "false".
# USE_HASHICORP_CLOUD: Indicates whether to use HashiCorp Cloud. Default is "false".
# VAULT_ADDRESS: The address of the HashiCorp Vault. Default is an empty string.
# VAULT_TOKEN: The token for accessing the HashiCorp Vault. Default is an empty string.
# USE_ROUTE53: Indicates whether to use AWS Route 53. Default is "false".
# ROUTE_53_DOMAIN: The domain name for AWS Route 53. Default is an empty string.
# CICD_ENVIORNMENT: Specifies the CI/CD environment. Default is "github".
# SECRET_PATH: The path to the secrets in the vault. Default is an empty string.
# INVENTORY: The inventory host for Ansible. Default is "localhost".
# DEVELOPMENT_MODEL: Indicates if the development model is enabled. Default is "false".
# Set default values for environment variables if they are not already set
: "${CICD_PIPELINE:="false"}"
: "${USE_HASHICORP_VAULT:="false"}"
: "${USE_HASHICORP_CLOUD:="false"}"
: "${VAULT_ADDRESS:=""}"
: "${VAULT_TOKEN:=""}"
: "${USE_ROUTE53:="false"}"
: "${ROUTE_53_DOMAIN:=""}"
: "${CICD_ENVIORNMENT:="github"}"
: "${SECRET_PATH:=""}"
: "${INVENTORY:="localhost"}"
: "${DEVELOPMENT_MODEL:="false"}"

# Function to log messages
# This script defines a function `log_message` that takes a single argument.
# The function prints a log message to the console with a timestamp in the format [YYYY-MM-DD HH:MM:SS].
# Usage: log_message "Your log message here"
log_message() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if the script is run as root
#
# This function verifies if the current user has root privileges.
# If the script is not executed by the root user, it logs a message
# indicating that root privileges are required and exits the script
# with a status code of 1.
#
# Usage:
#   check_root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_message "Please run as root"
        exit 1
    fi
}

# Function to handle HashiCorp Vault flag
# Function: handle_hashicorp_vault
# Description: Checks if HashiCorp Vault integration is enabled and verifies that necessary environment variables are set.
# Parameters: None
# Environment Variables:
#   USE_HASHICORP_VAULT - If set to "true", enables HashiCorp Vault integration.
#   VAULT_ADDRESS - The address of the HashiCorp Vault server.
#   VAULT_TOKEN - The token used to authenticate with the HashiCorp Vault server.
#   SECRET_PATH - The path to the secret in HashiCorp Vault.
# Outputs: Logs a message and exits with status 1 if required environment variables are not set.
handle_hashicorp_vault() {
    if [ "$USE_HASHICORP_VAULT" = "true" ]; then
        if [[ -z "$VAULT_ADDRESS" || -z "$VAULT_TOKEN" || -z "$SECRET_PATH" ]]; then
            log_message "VAULT environment variables are not set"
            exit 1
        fi
    fi
}


# This function checks if the required environment variables for HCP Cloud Vault are set.
# If any of the following environment variables are not set, the function will print an error message and exit with status 1:
# - HCP_CLIENT_ID: The client ID for HCP authentication.
# - HCP_CLIENT_SECRET: The client secret for HCP authentication.
# - HCP_ORG_ID: The organization ID for HCP.
# - HCP_PROJECT_ID: The project ID for HCP.
# - APP_NAME: The application name.
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


#
# Function: install_packages
# Description: This function installs a list of required packages and development tools on a RHEL 9 Linux hypervisor.
#              It first checks if each package is already installed using the rpm command. If a package is not installed,
#              it attempts to install it using dnf. If any package installation fails, the function logs an error message
#              and exits with a status of 1. After installing individual packages, it installs the "Development Tools" group.
#              Additionally, it checks if the 'yq' command-line YAML processor is installed. If not, it downloads and installs
#              'yq' from its GitHub releases. Finally, it updates all installed packages using dnf.
#
# Parameters: None
#
# Returns: None
#
# Exit Codes:
#   1 - If any package installation or update fails.
#
# Dependencies:
#   - log_message function for logging errors.
#   - dnf package manager for installing and updating packages.
#   - wget for downloading 'yq'.
#
# Example Usage:
#   install_packages
install_packages() {
    log_message "Installing required packages..."
    local packages=(bzip2-devel libffi-devel wget vim podman ncurses-devel sqlite-devel firewalld make gcc git unzip sshpass lvm2 python3 python3-pip java-11-openjdk-devel ansible-core perl-Digest-SHA)
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
    # Check if yq is installed
    if ! command -v yq &> /dev/null; then
        echo "yq is not installed. Installing..."
        # Download and install yq
        wget https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 -O /usr/bin/yq
        chmod +x /usr/bin/yq
        echo "yq installed successfully."
    else
        echo "yq is already installed."
    fi
    if ! dnf update -y; then
        log_message "Failed to update packages"
        exit 1
    fi
}


# Function: clone_repository
# Description: Clones the qubinode_navigator repository into the /opt/qubinode_navigator directory if it does not already exist.
# Parameters: None
# Environment Variables:
#   - GIT_REPO: The URL of the git repository to clone.
# Returns: None
# Exits:
#   - Exits with status 1 if the repository cloning fails.
# Usage: Call this function to ensure the qubinode_navigator repository is cloned to the specified directory.
clone_repository() {
    if [ ! -d "/opt/qubinode_navigator" ]; then
        log_message "Cloning qubinode_navigator repository..."
        if ! git clone "$GIT_REPO" "/opt/qubinode_navigator"; then
            log_message "Failed to clone repository"
            exit 1
        fi
    fi
}


# This function configures Ansible Navigator on a RHEL9 Linux hypervisor.
# It performs the following steps:
# 1. Checks if ansible-navigator is installed. If not, it installs ansible-navigator using pip3.
# 2. Adds the local bin directory to the PATH environment variable and sources the profile.
# 3. Changes the directory to /opt/qubinode_navigator.
# 4. Installs the required Python packages listed in requirements.txt using pip3.
# 5. Configures Ansible Navigator settings by creating a YAML configuration file at ~/.ansible-navigator.yml.
#    - Sets the inventory file path.
#    - Configures the execution environment to use Podman with a specific image.
#    - Sets the logging options, including the log file path and log level.
#    - Disables playbook artifact generation.
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


# This function configures Ansible Vault by performing the following steps:
# 1. Logs the start of the configuration process.
# 2. Checks if the 'ansiblesafe' command is available; if not, it downloads and installs it.
# 3. Downloads the 'ansible_vault_setup.sh' script if it does not exist in the specified directory.
# 4. Removes any existing vault password file.
# 5. If running in a CI/CD pipeline:
#    a. Ensures the SSH_PASSWORD environment variable is set.
#    b. Writes the SSH_PASSWORD to the vault password file and copies it to the lab-user's home directory.
#    c. Executes the 'ansible_vault_setup.sh' script.
#    d. Depending on the USE_HASHICORP_CLOUD environment variable:
#       - If false, copies 'config.yml' to 'vault.yml' and encrypts it using 'ansiblesafe'.
#       - If true, creates and encrypts 'vault.yml' using 'ansiblesafe', and optionally checks credentials.
# 6. If not running in a CI/CD pipeline:
#    a. Executes the 'ansible_vault_setup.sh' script.
#    b. Encrypts 'vault.yml' using 'ansiblesafe'.
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
            if [ -f /tmp/config.yml ]; then
                file1_yaml="/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml"
                file2_yaml="/tmp/config.yml"
                bash-aliases/check-creds.sh "$file1_yaml" "$file2_yaml"
            fi
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

# This function configures bash aliases by performing the following steps:
# 1. Prints a message indicating the start of the configuration process.
# 2. Checks if the current directory is "/opt/qubinode_navigator".
#    - If not, it changes the directory to "/opt/qubinode_navigator".
#    - If yes, it prints a message confirming the current directory.
# 3. Sources the function definitions from "bash-aliases/functions.sh".
# 4. Sources the alias definitions from "bash-aliases/aliases.sh".
# 5. Checks if the "~/.bash_aliases" file exists and sources it to apply changes.
# 6. Ensures that "~/.bash_aliases" is sourced from "~/.bashrc".
#    - If not already sourced, it appends the sourcing command to "~/.bashrc".
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


# This function configures the Qubinode Navigator by performing the following steps:
# 1. Logs the start of the configuration process.
# 2. Checks if the Qubinode Navigator directory exists in /opt:
#    - If it exists, it pulls the latest changes from the git repository.
#    - If it does not exist, it clones the repository into /opt/qubinode_navigator.
# 3. Changes the ownership and permissions of the /opt directory to allow the current user to write to it.
# 4. Installs the required Python packages from the requirements.txt file using pip3.
# 5. Logs the current DNS server being used.
# 6. Loads variables either interactively or from environment variables based on the CICD_PIPELINE flag:
#    - If CICD_PIPELINE is false, it waits for user input or continues after 5 minutes, then runs the load-variables.py script.
#    - If CICD_PIPELINE is true, it checks for required environment variables and runs the load-variables.py script with those variables.
# 7. Logs any errors encountered during the process and exits with a status of 1 if any step fails.
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


# This function generates an Ansible inventory file for the control node.
# It performs the following steps:
# 1. Logs a message indicating the start of inventory generation.
# 2. Checks if the inventory directory exists; if not, it creates the necessary directories.
# 3. Retrieves the control node's IP address and the current user.
# 4. Writes the control node's information to the inventory file.
# 5. If the DEVELOPMENT_MODEL environment variable is set to "true", it attempts to list the Ansible inventory using ansible-navigator.
#    If this step fails, it logs an error message and exits with a status of 1.
generate_inventory() {
    log_message "Generating inventory..."
    if [ ! -d "/opt/qubinode_navigator/inventories/$INVENTORY" ]; then
        mkdir -p "/opt/qubinode_navigator/inventories/$INVENTORY/group_vars/control"
    fi
    local control_host="$(hostname -I | awk '{print $1}')"
    local control_user="$USER"
    echo "[control]" > "/opt/qubinode_navigator/inventories/$INVENTORY/hosts"
    #echo "control ansible_host=$control_host ansible_user=$control_user" >> "/opt/qubinode_navigator/inventories/$INVENTORY/hosts"
    echo "control ansible_connection=local ansible_user=$control_user" >> "/opt/qubinode_navigator/inventories/$INVENTORY/hosts"
    if [ "${DEVELOPMENT_MODEL}" == "true" ]; then
        if ! ansible-navigator inventory --list -m stdout --vault-password-file ~/.vault_password; then
            log_message "Failed to list Ansible inventory"
            exit 1
        fi
    fi
}


# This function configures SSH by generating an SSH key pair if it does not already exist
# and copying the public key to the local machine's authorized keys.
# 
# Steps:
# 1. Logs the start of the SSH configuration process.
# 2. Checks if the SSH private key file (~/.ssh/id_rsa) exists.
# 3. If the private key file does not exist:
#    a. Generates a new RSA SSH key pair with an empty passphrase.
#    b. If key generation fails, logs an error message and exits with status 1.
#    c. Copies the public key to the local machine's authorized keys using ssh-copy-id.
#    d. If copying the key fails, logs an error message and exits with status 1.
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


# This function configures the firewalld service.
# It starts the firewalld service and enables it to start on boot.
# If either operation fails, it logs an error message and exits the script with a status of 1.
#
# Usage:
#   configure_firewalld
#
# Example:
#   configure_firewalld
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


# Function: deploy_kvmhost
# Description: This function deploys a KVM (Kernel-based Virtual Machine) host using Ansible Navigator.
#              It initializes the SSH agent, adds the SSH key, navigates to the specified directory,
#              and runs the Ansible playbook to set up the KVM host.
#              If the deployment fails, it logs an error message and exits with a status code of 1.
# 
# Steps:
# 1. Log the start of the KVM host deployment.
# 2. Initialize the SSH agent.
# 3. Add the SSH private key to the SSH agent.
# 4. Change the directory to /opt/qubinode_navigator.
# 5. Run the Ansible playbook (setup_kvmhost.yml) with the vault password file.
# 6. If the playbook execution fails, log an error message and exit with status code 1.
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


# This function sets up the Kcli base environment.
# It performs the following steps:
# 1. Checks if the current working directory is "/opt/qubinode_navigator".
#    - If not, it changes the directory to "/opt/qubinode_navigator".
#    - If already in the correct directory, it confirms this.
# 2. Configures Kcli by:
#    - Sourcing the user's .bash_aliases file.
#    - Running the qubinode_setup_kcli function.
#    - Running the kcli_configure_images function.
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


# This function configures OneDev by ensuring the current directory is /opt/qubinode_navigator.
# If the current directory is not /opt/qubinode_navigator, it changes to that directory.
# Then, it runs the configure-onedev.sh script located in ./dependancies/onedev/.
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


# This function configures Route53 DNS settings.
# It checks if the current working directory is /opt/qubinode_navigator.
# If not, it changes the directory to /opt/qubinode_navigator.
# Then, it prints the ZONE_NAME environment variable and runs the Route53 deployment script.
configure_route53() {
    if [ "$(pwd)" != "/opt/qubinode_navigator" ]; then
        echo "Current directory is not /opt/qubinode_navigator."
        echo "Changing to /opt/qubinode_navigator..."
        cd /opt/qubinode_navigator
    else
        echo "Current directory is /opt/qubinode_navigator."
    fi
    echo "Configuring Route53"
    echo "******************"
    echo "ZONE_NAME: $ZONE_NAME"
    ./dependancies/route53/deployment-script.sh
}


# This function configures Cockpit SSL.
# It first checks if the current working directory is /opt/qubinode_navigator.
# If not, it changes the directory to /opt/qubinode_navigator.
# Then, it checks if the SSL certificate file does not exist at the specified path.
# If the file does not exist, it runs the configure-cockpit-ssl.sh script to configure SSL for Cockpit.
configure_cockpit_ssl() {
    if [ "$(pwd)" != "/opt/qubinode_navigator" ]; then
        echo "Current directory is not /opt/qubinode_navigator."
        echo "Changing to /opt/qubinode_navigator..."
        cd /opt/qubinode_navigator
    else
        echo "Current directory is /opt/qubinode_navigator."
    fi
    echo "Configuring Cockpit SSL"
    echo "******************"
    if [ ! -f /etc/letsencrypt/live/sandbox1609.opentlc.com/fullchain.pem  ]; then
        ./dependancies/cockpit-ssl/configure-cockpit-ssl.sh
    fi
}


# This function configures GitLab by running a deployment script.
# It first checks if the current working directory is /opt/qubinode_navigator.
# If not, it changes the directory to /opt/qubinode_navigator.
# Then, it runs the GitLab deployment script located at ./dependancies/gitlab/deployment-script.sh.
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

# This function configures GitHub by running a deployment script.
# It first checks if the current working directory is /opt/qubinode_navigator.
# If not, it changes the directory to /opt/qubinode_navigator.
# Then, it runs the deployment script located at ./dependancies/github/deployment-script.sh.
# If the script fails, the function exits with the script's exit status.
configure_github() {
    if [ "$(pwd)" != "/opt/qubinode_navigator" ]; then
        echo "Current directory is not /opt/qubinode_navigator."
        echo "Changing to /opt/qubinode_navigator..."
        cd /opt/qubinode_navigator
    else
        echo "Current directory is /opt/qubinode_navigator."
    fi
    echo "Configuring GitHub"
    echo "******************"
    ./dependancies/github/deployment-script.sh || exit $?
}


# This function configures the Ollama workload on a RHEL9 Linux hypervisor.
# It performs the following steps:
# 1. Checks if Ollama is already running by sending a health check request to the local Ollama API.
# 2. If Ollama is running, it logs a message and skips the configuration.
# 3. If Ollama is not running, it logs a message indicating the start of the configuration process.
# 4. Downloads and installs Ollama using a script from the Ollama website.
# 5. Checks if the OLLAMA_API_BASE environment variable is already set in the ~/.bashrc file.
# 6. If the variable is set, it logs a message and skips adding it again.
# 7. If the variable is not set, it appends the export command to set OLLAMA_API_BASE in the ~/.bashrc file.
configure_ollama() {
    # Check if Ollama is already running
    if curl -s "http://127.0.0.1:11434/api/health" >/dev/null; then
        log_message "Ollama is already running. Skipping configuration."
    else
        log_message "Configuring Ollama Workload..."

        # Download and install Ollama
        curl -fsSL https://ollama.com/install.sh | sh

        # Check if the line exists in ~/.bashrc
        if grep -q "export OLLAMA_API_BASE=http://127.0.0.1:11434" ~/.bashrc; then
            log_message "OLLAMA_API_BASE is already set in ~/.bashrc. Skipping."
        else
            # Set the OLLAMA_API_BASE environment variable
            echo "export OLLAMA_API_BASE=http://127.0.0.1:11434" >> ~/.bashrc
        fi
    fi
}



# 
# This script sets up a RHEL 9 Linux hypervisor environment. The main function performs the following tasks:
# 
# 1. check_root: Ensures the script is run as root.
# 2. handle_hashicorp_vault: Manages HashiCorp Vault setup.
# 3. hcp_cloud_vault: Configures HashiCorp Cloud Vault if USE_HASHICORP_CLOUD is set to "true".
# 4. install_packages: Installs necessary packages.
# 5. configure_firewalld: Configures the firewall.
# 6. confiure_lvm_storage: Configures LVM storage.
# 7. clone_repository: Clones the required repository.
# 8. configure_ansible_navigator: Sets up Ansible Navigator.
# 9. configure_ansible_vault: Configures Ansible Vault.
# 10. generate_inventory: Generates the inventory file.
# 11. configure_navigator: Configures the navigator.
# 12. configure_ssh: Sets up SSH configuration.
# 13. deploy_kvmhost: Deploys the KVM host.
# 14. configure_bash_aliases: Configures bash aliases.
# 15. setup_kcli_base: Sets up kcli base.
# 16. configure_route53: Configures Route 53.
# 17. configure_cockpit_ssl: Configures Cockpit with SSL.
# 18. configure_onedev: Configures OneDev if CICD_ENVIORNMENT is set to "onedev".
# 19. configure_gitlab: Configures GitLab if CICD_ENVIORNMENT is set to "gitlab".
# 20. configure_github: Configures GitHub if CICD_ENVIORNMENT is set to "github".
# 21. log_message: Logs an error message and exits if CICD_ENVIORNMENT is not set.
# 22. configure_ollama: Configures Ollama if OLLAMA_WORKLOAD is set to "true".
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
    configure_cockpit_ssl
    if [ "$CICD_ENVIORNMENT" == "onedev" ]; then
        configure_onedev
    elif [ "$CICD_ENVIORNMENT" == "gitlab" ]; then
        configure_gitlab
    elif [ "$CICD_ENVIORNMENT" == "github" ]; then
        configure_github
    else
        log_message "Error: CICD_ENVIORNMENT is not set"
        exit 1
    fi
    if [ "$OLLAMA_WORKLOAD" == "true" ]; then
        configure_ollama
    fi
}

main "$@"