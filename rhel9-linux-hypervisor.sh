#!/bin/bash
source notouch.env
export PS4='+(${BASH_SOURCE}:${LINENO}): ${FUNCNAME[0]:+${FUNCNAME[0]}(): }'
set -x
set -euo pipefail

# Source modularized functions
source scripts/common_functions.sh || { echo "Failed to source common_functions.sh"; exit 1; }
source scripts/package_installation/install_packages.sh || { echo "Failed to source install_packages.sh"; exit 1; }
source scripts/kvm_configuration/configure_kvm.sh || { echo "Failed to source configure_kvm.sh"; exit 1; }
source scripts/ansible_navigator/configure_ansible_navigator.sh || { echo "Failed to source configure_ansible_navigator.sh"; exit 1; }
source scripts/hashicorp_vault/configure_hashicorp_vault.sh || { echo "Failed to source configure_hashicorp_vault.sh"; exit 1; }
source scripts/ssh_configuration/configure_ssh.sh || { echo "Failed to source configure_ssh.sh"; exit 1; }
source scripts/firewall_configuration/configure_firewalld.sh || { echo "Failed to source configure_firewalld.sh"; exit 1; }
source scripts/inventory_generation/generate_inventory.sh || { echo "Failed to source generate_inventory.sh"; exit 1; }
source scripts/bash_aliases/configure_bash_aliases.sh || { echo "Failed to source configure_bash_aliases.sh"; exit 1; }
source scripts/route53_configuration/configure_route53.sh || { echo "Failed to source configure_route53.sh"; exit 1; }
source scripts/configure_navigator.sh || { echo "Failed to source configure_navigator.sh"; exit 1; }
source scripts/cockpit_ssl/configure_cockpit_ssl.sh || { echo "Failed to source configure_cockpit_ssl.sh"; exit 1; }
source scripts/integration/configure_integration.sh || { echo "Failed to source configure_integration.sh"; exit 1; }
source scripts/lvm_configuration/configure_lvm_storage.sh || { echo "Failed to source configure_lvm_storage.sh"; exit 1; }
source scripts/deploy_kvmhost.sh || { echo "Failed to source deploy_kvmhost.sh"; exit 1; }
source scripts/clone_repository.sh || { echo "Failed to source clone_repository.sh"; exit 1; }



# Main function to orchestrate the setup
main() {
    check_root
    handle_hashicorp_vault
    if [ "$USE_HASHICORP_CLOUD" == "true" ]; then
        hcp_cloud_vault
    fi
    install_packages
    configure_firewalld
    configure_lvm_storage
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
    if [ "$CICD_ENVIRONMENT" == "onedev" ]; then
        configure_onedev
    elif [ "$CICD_ENVIRONMENT" == "gitlab" ]; then
        configure_gitlab
    elif [ "$CICD_ENVIRONMENT" == "github" ]; then
        configure_github
    else
        log_message "Error: CICD_ENVIRONMENT is not set"
        exit 1
    fi
    if [ "$OLLAMA_WORKLOAD" == "true" ]; then
        configure_ollama
    fi
}

main "$@"
