#!/bin/bash

install_packages() {
    log_message "Updating system packages..."
    if ! dnf update -y; then
        log_message "Failed to update packages"
        exit 1
    fi

    log_message "Installing required packages..."
    local packages=(bzip2-devel libffi-devel wget vim podman ncurses-devel sqlite-devel firewalld make gcc git unzip sshpass lvm2 python3 python3-pip java-11-openjdk-devel perl-Digest-SHA)
    
    # Uninstall existing version of ansible-core
    if rpm -q ansible-core &>/dev/null; then
        log_message "Uninstalling existing version of ansible-core..."
        if ! dnf remove -y ansible-core; then
            log_message "Failed to uninstall existing version of ansible-core"
            exit 1
        fi
    fi

    for package in "${packages[@]}"; do
        install_package "$package"
    done

    log_message "Installing Ansible Core 2.13.1, Ansible Vault, and Navigator..."
    if ! python3 -m pip install ansible-core==2.13.10 ansible-navigator ansible-vault; then
        log_message "Failed to install Ansible Core or Navigator or Ansible Vault"
        exit 1
    fi

    # Add /usr/local/bin to PATH
    log_message "Adding /usr/local/bin to PATH..."
    echo 'export PATH=$PATH:/usr/local/bin' >> ~/.bashrc
    log_message "Please run 'source ~/.bashrc' or restart your shell to apply PATH changes."

    # Install "Development Tools"
    if ! dnf groupinstall -y "Development Tools"; then
        log_message "Failed to install Development Tools"
        exit 1
    fi

    # Install yq with version control
    YQ_VERSION="4.25.2"
    if ! command -v yq &>/dev/null; then
        log_message "Installing yq version ${YQ_VERSION}..."
        wget https://github.com/mikefarah/yq/releases/download/v${YQ_VERSION}/yq_linux_amd64 -O /usr/bin/yq
        chmod +x /usr/bin/yq
        log_message "yq installed successfully."
    else
        log_message "yq is already installed."
    fi
}

install_package() {
    local package="$1"
    if ! rpm -q "$package" &>/dev/null; then
        if ! dnf install -y "$package"; then
            log_message "Failed to install package: $package"
            exit 1
        fi
    fi
}

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}
