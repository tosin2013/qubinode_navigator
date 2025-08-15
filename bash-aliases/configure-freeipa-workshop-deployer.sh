#!/bin/bash

# =============================================================================
# FreeIPA Workshop Deployer - The "Identity Management Specialist"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This script deploys and configures FreeIPA identity management server with DNS
# services using the freeipa-workshop-deployer project. It provides centralized
# authentication, authorization, and DNS services for enterprise environments.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script implements FreeIPA deployment:
# 1. [PHASE 1]: Repository Management - Clones or updates freeipa-workshop-deployer
# 2. [PHASE 2]: Configuration Generation - Creates environment-specific configuration
# 3. [PHASE 3]: Variable Substitution - Updates configuration with domain and DNS settings
# 4. [PHASE 4]: Platform Configuration - Configures for kcli virtualization platform
# 5. [PHASE 5]: Service Deployment - Deploys FreeIPA server with DNS integration
# 6. [PHASE 6]: DNS Management - Configures dynamic DNS for workshop services
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [Identity Management]: Provides centralized authentication for infrastructure
# - [DNS Services]: Offers DNS resolution for workshop and lab environments
# - [Workshop Integration]: Supports educational and training deployments
# - [Virtualization Integration]: Works with kcli and KVM virtualization
# - [Domain Management]: Manages domain names and DNS records
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Workshop-Focused]: Designed for educational and training environments
# - [DNS Integration]: Provides both identity management and DNS services
# - [Platform-Agnostic]: Supports multiple infrastructure providers (kcli, AWS)
# - [Dynamic Configuration]: Adapts to different domain and network configurations
# - [Cleanup-Capable]: Includes destruction and cleanup capabilities
#
# 💡 WHEN TO MODIFY THIS SCRIPT (for future LLMs):
# - [FreeIPA Updates]: Update for new FreeIPA versions or features
# - [Platform Support]: Add support for new virtualization platforms
# - [DNS Enhancements]: Add support for new DNS providers or configurations
# - [Workshop Features]: Add new workshop services or integrations
# - [Security Updates]: Implement new security configurations or hardening
#
# 🚨 IMPORTANT FOR LLMs: This script deploys identity management infrastructure
# that affects authentication and DNS for the entire environment. It requires
# network configuration and may impact existing DNS settings.

#github-action genshdoc
# @ file Setup freeipa-workshop-deployer https://github.com/tosin2013/freeipa-workshop-deployer
# @ brief This script will setup the freeipa-workshop-deployer

# FreeIPA Deployment Manager - The "Identity Infrastructure Deployer"
function deploy_freeipa(){
# 🎯 FOR LLMs: This function deploys FreeIPA identity management server with
# DNS services, configured for workshop and educational environments.
# 🔄 WORKFLOW:
# 1. Sets up environment variables and dependencies
# 2. Clones or updates freeipa-workshop-deployer repository
# 3. Configures deployment variables for current environment
# 4. Adapts configuration for kcli virtualization platform
# 5. Executes total deployment process
# 📊 INPUTS/OUTPUTS:
# - INPUT: Environment variables and system configuration
# - OUTPUT: Deployed FreeIPA server with DNS services
# ⚠️  SIDE EFFECTS: Creates virtual machines, modifies DNS configuration, requires network access
    set_variables
    dependency_check
    if [ ! -d /opt/freeipa-workshop-deployer ]; then
        cd /opt/
        sudo git clone https://github.com/tosin2013/freeipa-workshop-deployer.git
    else 
        cd /opt/freeipa-workshop-deployer
        sudo git pull
    fi 

    if [ -d /opt/qubinode_navigator/kcli-plan-samples ]; then
        echo "kcli-plan-samples folder  already exists"
    else 
        update_profiles_file
    fi 

    cd /opt/freeipa-workshop-deployer || return
    sudo cp  example.vars.sh vars.sh
    cat $ANSIBLE_ALL_VARIABLES
    DOMAIN=$(yq eval '.domain' $ANSIBLE_ALL_VARIABLES)
    FORWARD_DOMAIN=$(yq eval '.dns_forwarder' $ANSIBLE_ALL_VARIABLES)
    sudo sed -i "s/example.com/${DOMAIN}/g" vars.sh
    sudo sed -i "s/1.1.1.1/${FORWARD_DOMAIN}/g" vars.sh
    sudo sed -i 's|INFRA_PROVIDER="aws"|INFRA_PROVIDER="kcli"|g' vars.sh
    sudo sed -i 's|export INVENTORY=localhost|export INVENTORY="'${CURRENT_INVENTORY}'"|g' vars.sh
    get_rhel_version
    if [ "$BASE_OS" == "ROCKY8" ]; then
      sudo sed -i 's|KCLI_NETWORK="qubinet"|KCLI_NETWORK="default"|g' vars.sh
    fi
    cat vars.sh
    ./total_deployer.sh
}

# FreeIPA Destruction Manager - The "Infrastructure Cleanup Specialist"
function destroy_freeipa(){
# 🎯 FOR LLMs: This function safely destroys FreeIPA infrastructure and cleans up
# DNS records to return the environment to its original state.
# 🔄 WORKFLOW:
# 1. Destroys FreeIPA virtual machines using kcli
# 2. Retrieves IP address information for DNS cleanup
# 3. Removes dynamic DNS records for workshop services
# 4. Returns to home directory for cleanup completion
# 📊 INPUTS/OUTPUTS:
# - INPUT: Existing FreeIPA deployment and DNS records
# - OUTPUT: Cleaned environment with removed infrastructure and DNS records
# ⚠️  SIDE EFFECTS: Destroys virtual machines, removes DNS records, requires network access
    cd /opt/freeipa-workshop-deployer || return
    ./1_kcli/destroy.sh
    cd /opt/freeipa-workshop-deployer/2_ansible_config/
    IP_ADDRESS=$(sudo kcli info vm device-edge-workshops | grep ip: | awk '{print $2}')
    echo "IP Address: ${IP_ADDRESS}"
    sudo python3 dynamic_dns.py --remove controller
    sudo python3 dynamic_dns.py --remove 'cockpit'
    sudo python3 dynamic_dns.py --remove 'gitea'
    sudo python3 dynamic_dns.py --remove 'edge-manager'
    cd ~
}
