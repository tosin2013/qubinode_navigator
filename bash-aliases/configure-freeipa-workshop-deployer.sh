#!/bin/bash
#github-action genshdoc
# @ file Setup freeipa-workshop-deployer https://github.com/tosin2013/freeipa-workshop-deployer
# @ brief This script will setup the freeipa-workshop-deployer
set -x 

############################################
## @brief This function will deploy freeipa with dns
############################################
function deploy_freeipa(){
    if [ ! -d /opt/qubinode-installer/freeipa-workshop-deployer ]; then
        cd /opt/qubinode-installer/
        sudo git clone https://github.com/tosin2013/freeipa-workshop-deployer.git
    fi 

    if [ -d /opt/qubinode-installer/kcli-plan-samples ]; then
        echo "kcli-plan-samples folder  already exists"
    else 
        update_profiles_file
    fi 

    cd /opt/qubinode-installer/freeipa-workshop-deployer || return
    sudo cp  example.vars.sh vars.sh
    DOMAIN=$(yq eval '.domain' $ANSIBLE_ALL_VARIABLES)
    FORWARD_DOMAIN=$(yq eval '.domain' $ANSIBLE_ALL_VARIABLES)
    sudo sed -i "s/example.com/${DOMAIN}/g" vars.sh
    sudo sed -i "s/1.1.1.1/${FORWARD_DOMAIN}/g" vars.sh
    sudo sed -i 's|INFRA_PROVIDER="aws"|INFRA_PROVIDER="kcli"|g' vars.sh
    /opt/qubinode-installer/kcli-plan-samples/helper_scripts/get-ips-by-mac.sh freeipa vars.sh || exit 1
    cat vars.sh
    sleep 10
    ./total_deployer.sh
    set +x 
}

############################################
## @brief This function will destroy freeipa with dns
############################################
function destroy_freeipa(){
    cd /opt/qubinode-installer/freeipa-workshop-deployer || return
    ./1_kcli/destroy.sh
    set +x
}
