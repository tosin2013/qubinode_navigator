#!/bin/bash
#github-action genshdoc

# @description This function will check for the existence of the yq binary
function dependency_check() {
    if ! yq -v  &> /dev/null
    then
        VERSION=v4.30.6
        BINARY=yq_linux_amd64
        sudo wget https://github.com/mikefarah/yq/releases/download/${VERSION}/${BINARY} -O /usr/bin/yq &&\
        sudo chmod +x /usr/bin/yq
    fi
    get_rhel_version
    if [ "$BASE_OS" == "ROCKY8" ]; then
      source ~/.profile
    fi
}

# @description This function will set the variables for the installer
# ANSIBLE_SAFE_VERSION - The version of the ansiblesafe binary
# ANSIBLE_VAULT_FILE - The location of the vault file
# KCLI_CONFIG_DIR - The location of the kcli config directory
# KCLI_CONFIG_FILE - The location of the kcli config file
# PROFILES_FILE - The name of the kcli profiles file
# SECURE_DEPLOYMENT - The value of the secure deployment variable
# INSTALL_RHEL_IMAGES - Set the vault to true if you want to install the RHEL images
function set_variables() {
    export ANSIBLE_SAFE_VERSION="0.0.4"
    export ANSIBLE_VAULT_FILE="$HOME/qubinode_navigator/inventories/localhost/group_vars/control/vault.yml"
    export ANSIBLE_ALL_VARIABLES="$HOME/qubinode_navigator/inventories/localhost/group_vars/all.yml"
    KCLI_CONFIG_DIR="${HOME}/.kcli"
    KCLI_CONFIG_FILE="${KCLI_CONFIG_DIR}/profiles.yml"
    PROFILES_FILE="kcli-profiles.yml"
    SECURE_DEPLOYMENT="false"
    INSTALL_RHEL_IMAGES="false"
}

# @setting  The function get_rhel_version function will determine the version of RHEL
function get_rhel_version() {
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