#!/bin/bash 
#github-action genshdoc

# @setting-header setup.sh quickstart script for qubinode_navigator
# @setting ./setup.sh 

#set -xe
# @global ANSIBLE_SAFE_VERSION this is the ansible safe version
# @global INVENTORY this is the inventory file name and path Example: inventories/localhost
export ANSIBLE_SAFE_VERSION="0.0.5"
export INVENTORY="localhost"
if [ -z "$CICD_PIPELINE" ]; then
  export CICD_PIPELINE="false"
fi

if [ -z "$USE_HASHICORP_VAULT" ]; then
  export USE_HASHICORP_VAULT="false"
else
    if [[ -z "$VAULT_ADDRESS" && -z "$VAULT_ADDRESS" && -z ${SECRET_PATH} ]]; then
      echo "VAULT enviornment variables are not passed  is not set"
      exit 1
    fi
fi

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

# @description This function get_quibinode_navigator function will clone the qubinode_navigator repo
function get_quibinode_navigator() {
    echo "Cloning qubinode_navigator"
    if [ -d $1/qubinode_navigator ]; then
        echo "Qubinode Installer already exists"
    else
        git clone https://github.com/tosin2013/qubinode_navigator.git
    fi
}

# @description This function configure_navigator function will configure the ansible-navigator
function configure_navigator() {
    echo "Configuring ansible navigator"
    echo "****************"
    if [ -d $1/qubinode_navigator ]; then
        cd $1/qubinode_navigator
        if ! command -v ansible-navigator &> /dev/null; then
            make install-ansible-navigator
            make copy-navigator
            # Check if running as root
            if [ "$EUID" -eq 0 ]; then
               sed -i  's|/home/admin/qubinode_navigator/inventories/localhost|/root/qubinode_navigator/inventories/localhost|g'  ~/.ansible-navigator.yml
            else
                sed -i  's|/home/admin/qubinode_navigator/inventories/localhost|/home/'$USER'/qubinode_navigator/inventories/localhost|g'  ~/.ansible-navigator.yml
            fi
        fi
    else
        echo "Qubinode Installer does not exist"
    fi
    cd $1/qubinode_navigator
    sudo pip3 install -r requirements.txt
    echo "Load variables"
    echo "**************"
    if [ $CICD_PIPELINE == "false" ];
    then
        python3 load-variables.py
    else 
        if [[ -z "$ENV_USERNAME" && -z "$DOMAIN" && -z "$FORWARDER" && -z "$ACTIVE_BRIDGE" && -z "$INTERFACE" && -z "$DISK" ]]; then
            echo "Error: One or more environment variables are not set"
            exit 1
        fi
        python3 load-variables.py --username ${ENV_USERNAME} --domain ${DOMAIN} --forwarder ${FORWARDER} --bridge ${ACTIVE_BRIDGE} --interface ${INTERFACE} --disk ${DISK}
    fi
}

# @description This function configure_vault function will configure the ansible-vault it will download ansible vault and ansiblesafe
function configure_vault() {
    echo "Configuring vault using ansible safe"
    echo "****************"
    if [ -d $1/qubinode_navigator ]; then
        cd $1/qubinode_navigator
        if ! command -v ansible-vault &> /dev/null; then
            sudo dnf install ansible-core -y 
        fi
        if ! command -v ansiblesafe &> /dev/null; then
            curl -OL https://github.com/tosin2013/ansiblesafe/releases/download/v${ANSIBLE_SAFE_VERSION}/ansiblesafe-v${ANSIBLE_SAFE_VERSION}-linux-amd64.tar.gz
            tar -zxvf ansiblesafe-v${ANSIBLE_SAFE_VERSION}-linux-amd64.tar.gz
            chmod +x ansiblesafe-linux-amd64 
            sudo mv ansiblesafe-linux-amd64 /usr/local/bin/ansiblesafe
        fi
        echo "Configure Ansible Vault password file"
        echo "****************"
        read -t 360 -p "Press Enter to continue, or wait 5 minutes for the script to continue automatically" || true
        if [ ! -f ~/qubinode_navigator/ansible_vault_setup.sh ];
        then 
            curl -OL https://gist.githubusercontent.com/tosin2013/022841d90216df8617244ab6d6aceaf8/raw/92400b9e459351d204feb67b985c08df6477d7fa/ansible_vault_setup.sh
            chmod +x ansible_vault_setup.sh
        fi
        rm -f ~/.vault_password
        bash  ./ansible_vault_setup.sh
        if [ $USE_HASHICORP_VAULT == "true" ];
        then
             if [ $(id -u) -ne 0 ]; then
                if [ ! -f /home/${USER}/qubinode_navigator/inventories/localhost/group_vars/control/vault.yml ];
                then
                    ansiblesafe -f /home/${USER}/qubinode_navigator/inventories/localhost/group_vars/control/vault.yml -o 4
                    ansiblesafe -f /home/${USER}/qubinode_navigator/inventories/localhost/group_vars/control/vault.yml -o 1
                fi
            else 
                if [ ! -f /root/qubinode_navigator/inventories/localhost/group_vars/control/vault.yml ];
                then
                    ansiblesafe -f /root/qubinode_navigator/inventories/localhost/group_vars/control/vault.yml -o 4
                    ansiblesafe -f /root/qubinode_navigator/inventories/localhost/group_vars/control/vault.yml -o 1
                fi
            fi
        else
            if [ $(id -u) -ne 0 ]; then
                if [ ! -f /home/${USER}/qubinode_navigator/inventories/localhost/group_vars/control/vault.yml ];
                then
                    ansiblesafe -f /home/${USER}/qubinode_navigator/inventories/localhost/group_vars/control/vault.yml
                fi
            else 
                if [ ! -f /root/qubinode_navigator/inventories/localhost/group_vars/control/vault.yml ];
                then
                    ansiblesafe -f /root/qubinode_navigator/inventories/localhost/group_vars/control/vault.yml
                fi
            fi
        fi 
        #ansible-navigator inventory --list -m stdout --vault-password-file $HOME/.vault_password
    else
        echo "Qubinode Installer does not exist"
    fi
}

# @description This function generate_inventory function will generate the inventory
function generate_inventory(){
    echo "Generating inventory"
    echo "****************"
    if [ -d $1/qubinode_navigator ]; then
        cd $1/qubinode_navigator
        if [ ! -d inventories/${INVENTORY} ]; then
            mkdir -p inventories/${INVENTORY}
            mkdir -p inventories/${INVENTORY}/group_vars/control
            cp -r inventories/localhost/group_vars/control/* inventories/${INVENTORY}/group_vars/control/
        fi
        # set the values
        control_host="$(hostname -I | awk '{print $1}')"
        # Check if running as root
        if [ "$EUID" -eq 0 ]; then
            read -p "Enter the target username to ssh into machine: " control_user
        else
            control_user="$USER"
        fi
        
        echo "[control]" > inventories/${INVENTORY}/hosts
        echo "control ansible_host=${control_host} ansible_user=${control_user}" >> inventories/${INVENTORY}/hosts
        ansible-navigator inventory --list -m stdout --vault-password-file $HOME/.vault_password
    else
        echo "Qubinode Installer does not exist"
    fi
}

# @description This function configure_ssh function will configure the ssh
function configure_ssh(){
    echo "Configuring SSH"
    echo "****************"
    if [ -f ~/.ssh/id_rsa ]; then
        echo "SSH key already exists"
    else
        IP_ADDRESS=$(hostname -I | awk '{print $1}')
        ssh-keygen -f ~/.ssh/id_rsa -t rsa -N ''
        # Check if running as root
        if [ "$EUID" -eq 0 ]; then
            read -p "Enter the target username to ssh into machine: " control_user
            ssh-copy-id $control_user@${IP_ADDRESS}
        else
            ssh-copy-id $USER@${IP_ADDRESS}
        fi
    fi
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

# @description This configure_os function will get the base os and install the required packages
function configure_os(){
    if [ ${1} == "ROCKY8" ]; then
        sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make  -y
    elif [ ${1} == "FEDORA" ]; then
        sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make  -y
    elif [ ${1} == "UBUNTU" ]; then
        sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make  -y
    elif [ ${1} == "CENTOS8" ]; then
        sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make  -y
    elif [ ${1} == "RHEL9" ]; then
        sudo dnf update -y 
        sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make  -y
    elif [ ${1} == "CENTOS9" ]; then
        sudo dnf update -y 
        sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make  -y
    fi
}

function test_inventory(){
    echo "Testing inventory"
    echo "****************"
    if [ -d $1/qubinode_navigator ]; then
        cd $1/qubinode_navigator
        ansible-navigator inventory --list -m stdout --vault-password-file $HOME/.vault_password || exit 1
    else
        echo "Qubinode Installer does not exist"
    fi
}



function deploy_kvmhost() {
    echo "Deploying KVM Host"
    echo "******************"
    eval $(ssh-agent)
    ssh-add ~/.ssh/id_rsa
    cd "$HOME"/qubinode_navigator
    source ~/.profile
    ansible-navigator run ansible-navigator/setup_kvmhost.yml \
        --vault-password-file "$HOME"/.vault_password -m stdout || exit 1
}

function configure_bash_aliases() {
    echo "Configuring bash aliases"
    echo "************************"
    if [ "$(pwd)" != "$1/qubinode_navigator" ]; then
        echo "Current directory is not $1/qubinode_navigator."
        echo "Changing to $1/qubinode_navigator..."
        cd $1/qubinode_navigator
    else
        echo "Current directory is $1/qubinode_navigator."
    fi
    if [ -f $1/.bash_aliases ]; then
        echo "bash_aliases already exists"
    else
        ./bash-aliases/setup-commands.sh || exit 1
    fi
}


function setup_kcli_base() {
    if [ "$(pwd)" != "$1/qubinode_navigator" ]; then
        echo "Current directory is not $1/qubinode_navigator."
        echo "Changing to $1/qubinode_navigator..."
        cd $1/qubinode_navigator
    else
        echo "Current directory is $1/qubinode_navigator."
    fi
    echo "Configuring Kcli"
    echo "****************"
    source $1/.bash_aliases
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

get_rhel_version


if [  $BASE_OS == "ROCKY8" ];
then 
  echo "Please run the rocky-linux-hypervisor.sh script"
  exit 1
fi

if [ "$EUID" -eq 0 ]; then
  MY_DIR="/root"
else
  MY_DIR="$HOME"
fi

if [ $# -eq 0 ]; then
    configure_ssh
    configure_os  $BASE_OS
    configure_firewalld
    get_quibinode_navigator $MY_DIR
    configure_navigator $MY_DIR
    configure_vault $MY_DIR
    generate_inventory $MY_DIR
    test_inventory $MY_DIR
    deploy_kvmhost
    configure_bash_aliases $MY_DIR
    setup_kcli_base  $MY_DIR
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
            configure_bash_aliases  $MY_DIR
            shift
            ;;
        --setup-kcli-base)
            setup_kcli_base  $MY_DIR
            shift
            ;;
        --deploy-freeipa)
            freeipa-utils deploy
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done