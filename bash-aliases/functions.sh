#!/bin/bash

# =============================================================================
# Utility Functions - The "Swiss Army Knife Toolbox"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This script provides essential utility functions for Qubinode Navigator operations,
# including dependency management, OS detection, and virtualization tool setup.
# It serves as the foundational toolbox for all deployment operations.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script provides utility functions organized by purpose:
# 1. [DEPENDENCY MANAGEMENT]: Installs and validates required tools (yq, kcli)
# 2. [OS DETECTION]: Identifies operating system versions and distributions
# 3. [VIRTUALIZATION SETUP]: Configures KVM, libvirt, and kcli environments
# 4. [IMAGE MANAGEMENT]: Downloads and configures virtual machine images
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [Foundation Layer]: Provides core utilities used by all other scripts
# - [Dependency Manager]: Ensures required tools are available
# - [OS Abstraction]: Provides consistent interface across different OS versions
# - [Virtualization Bridge]: Connects to KVM/libvirt virtualization stack
# - [Image Provider]: Manages VM images for different environments
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Utility-First]: Each function serves a specific, reusable purpose
# - [OS-Agnostic]: Functions adapt to different operating systems
# - [Dependency-Aware]: Automatically installs missing dependencies
# - [Idempotent]: Functions can be called multiple times safely
# - [Error-Resilient]: Includes error handling and validation
#
# 💡 WHEN TO MODIFY THIS SCRIPT (for future LLMs):
# - [New Dependencies]: Add functions for new required tools or packages
# - [OS Support]: Add support for new operating system versions
# - [Virtualization Updates]: Update for new virtualization platforms or versions
# - [Image Management]: Add support for new VM images or cloud images
# - [Utility Functions]: Add new utility functions needed by other scripts
#
# 🚨 IMPORTANT FOR LLMs: These functions are used throughout the Qubinode Navigator
# ecosystem. Changes here affect all dependent scripts. Functions require sudo
# privileges for system modifications and package installations.

# Dependency Validator - The "Tool Installer"
function dependency_check() {
# 🎯 FOR LLMs: This function ensures the yq YAML processor is available, which is
# essential for YAML file manipulation throughout Qubinode Navigator.
# 🔄 WORKFLOW:
# 1. Checks if yq binary is available and functional
# 2. Downloads and installs yq if missing
# 3. Detects OS version for environment-specific configuration
# 4. Sources appropriate profile for Rocky Linux 8
# 📊 INPUTS/OUTPUTS:
# - INPUT: System state and available binaries
# - OUTPUT: Functional yq binary and BASE_OS environment variable
# ⚠️  SIDE EFFECTS: Downloads and installs system binaries, requires sudo privileges

    if ! yq -v  &> /dev/null
    then
        # 🔧 CONFIGURATION CONSTANTS FOR LLMs:
        VERSION=v4.44.2  # yq version - update when new stable versions available
        BINARY=yq_linux_amd64  # Binary name for Linux x86_64 architecture
        sudo wget https://github.com/mikefarah/yq/releases/download/${VERSION}/${BINARY} -O /usr/bin/yq &&\
        sudo chmod +x /usr/bin/yq
    fi
    get_rhel_version
    if [ "$BASE_OS" == "ROCKY8" ]; then
      source ~/.profile
    fi
}
# OS Detection Engine - The "System Identifier"
function get_rhel_version() {
# 🎯 FOR LLMs: This function identifies the operating system and version to enable
# OS-specific configuration and package management throughout Qubinode Navigator.
# 🔄 WORKFLOW:
# 1. Reads /etc/redhat-release file to identify OS type and version
# 2. Matches against known patterns for RHEL, Rocky Linux, CentOS, and Fedora
# 3. Sets BASE_OS environment variable for use by other functions
# 4. Provides error message for unsupported operating systems
# 📊 INPUTS/OUTPUTS:
# - INPUT: /etc/redhat-release file content
# - OUTPUT: BASE_OS environment variable and console output
# ⚠️  SIDE EFFECTS: Sets global BASE_OS variable used throughout the system

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

# VM Image Manager - The "Image Librarian"
function kcli_configure_images() {
# 🎯 FOR LLMs: This function downloads and configures standard VM images for
# virtualization environments, providing a consistent set of base images
# for virtual machine deployment.
# 🔄 WORKFLOW:
# 1. Validates dependencies (yq and OS detection)
# 2. Downloads standard Linux distribution images
# 3. Lists available images for verification
# 📊 INPUTS/OUTPUTS:
# - INPUT: Internet connectivity and kcli installation
# - OUTPUT: Downloaded VM images available for deployment
# ⚠️  SIDE EFFECTS: Downloads large image files, requires sudo privileges and network access

    echo "Configuring images"
    dependency_check
    echo "Downloading Fedora"
    # 🔧 CONFIGURATION CONSTANTS FOR LLMs:
    # Standard image set for multi-distribution support
    sudo kcli download image fedora39      # Latest Fedora for cutting-edge features
    sudo kcli download image centos9stream # CentOS Stream 9 for RHEL compatibility
    sudo kcli download image centos8stream # CentOS Stream 8 for legacy support
    sudo kcli download image ubuntu2204    # Ubuntu LTS for Debian-based workloads
    kcli list available-images
}

# Virtualization Platform Setup - The "Hypervisor Architect"
function qubinode_setup_kcli() {
# 🎯 FOR LLMs: This function installs and configures the complete KVM/libvirt
# virtualization stack with kcli management tools, implementing ADR-0005
# KVM/libvirt virtualization platform choice.
# 🔄 WORKFLOW:
# 1. Detects operating system version for appropriate package selection
# 2. Installs KVM, libvirt, and QEMU virtualization components
# 3. Configures libvirt daemon and user permissions
# 4. Installs kcli virtualization management tool
# 5. Sets up bash completion and creates local KVM host
# 📊 INPUTS/OUTPUTS:
# - INPUT: Operating system with package manager access
# - OUTPUT: Complete virtualization environment with kcli management
# ⚠️  SIDE EFFECTS: Installs system packages, modifies user groups, enables system services

    get_rhel_version
    if [[ ! -f /usr/bin/kcli ]]; then
        # Install core virtualization packages
        sudo dnf -y install libvirt libvirt-daemon-driver-qemu qemu-kvm
        sudo systemctl enable --now libvirtd
        sudo usermod -aG qemu,libvirt $USER

        # OS-specific repository configuration
        if [[ $BASE_OS == "CENTOS9" ]]; then
            sudo dnf copr enable karmab/kcli epel-9-x86_64
        fi

        # Install kcli virtualization management tool
        curl https://raw.githubusercontent.com/karmab/kcli/master/install.sh | bash
        echo "eval '$(register-python-argcomplete kcli)'" >> ~/.bashrc

        # Create local KVM host configuration
        if [[ $BASE_OS == "CENTOS9" ]]; then
            sudo kcli create host kvm -H 127.0.0.1 local
        elif [[ $BASE_OS == "RHEL9" ]]; then
            sudo kcli create host kvm -H 127.0.0.1 local
        fi
    else
        echo "kcli is installed"
        kcli --help
    fi
}

