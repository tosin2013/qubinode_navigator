#!/bin/bash
#github-action genshdoc
# @ file Setup freeipa-workshop-deployer https://github.com/tosin2013/freeipa-workshop-deployer
# @ brief This script will setup the freeipa-workshop-deployer

############################################
## @brief This function will deploy freeipa with dns
############################################
function deploy_freeipa(){
    set_variables
    if [ ! -d /opt/quibinode_navigator/freeipa-workshop-deployer ]; then
        cd /opt/quibinode_navigator/
        sudo git clone https://github.com/tosin2013/freeipa-workshop-deployer.git
    fi 

    if [ -d /opt/quibinode_navigator/kcli-plan-samples ]; then
        echo "kcli-plan-samples folder  already exists"
    else 
        update_profiles_file
    fi 

    cd /opt/quibinode_navigator/freeipa-workshop-deployer || return
    sudo cp  example.vars.sh vars.sh
    cat $ANSIBLE_ALL_VARIABLES
    DOMAIN=$(yq eval '.domain' $ANSIBLE_ALL_VARIABLES)
    FORWARD_DOMAIN=$(yq eval '.dns_forwarder' $ANSIBLE_ALL_VARIABLES)
    sudo sed -i "s/example.com/${DOMAIN}/g" vars.sh
    sudo sed -i "s/1.1.1.1/${FORWARD_DOMAIN}/g" vars.sh
    sudo sed -i 's|INFRA_PROVIDER="aws"|INFRA_PROVIDER="kcli"|g' vars.sh
    cat vars.sh
    ./total_deployer.sh
}

############################################
## @brief This function will destroy freeipa with dns
############################################
function destroy_freeipa(){
    cd /opt/quibinode_navigator/freeipa-workshop-deployer || return
    ./1_kcli/destroy.sh
}
