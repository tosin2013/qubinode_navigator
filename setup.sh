#!/bin/bash 
#github-action genshdoc

# @setting-header setup.sh quickstart script for qubinode_navigator
# @setting ./setup.sh 
# Uncomment for debugging
export PS4='+(${BASH_SOURCE}:${LINENO}): ${FUNCNAME[0]:+${FUNCNAME[0]}(): }'
set -x
# @global ANSIBLE_SAFE_VERSION this is the ansible safe version
# @global INVENTORY this is the inventory file name and path Example: inventories/localhost
export ANSIBLE_SAFE_VERSION="0.0.6"
export GIT_REPO="https://github.com/tosin2013/qubinode_navigator.git"
if [ -z "$CICD_PIPELINE" ]; then
  export CICD_PIPELINE="false"
  export INVENTORY="localhost"
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

function install_packages() {
    # Check if packages are already installed
    echo "Installing packages"
    echo "*******************"
    for package in openssl-devel bzip2-devel libffi-devel wget vim podman ncurses-devel sqlite-devel firewalld make gcc git unzip sshpass lvm lvm2 python3 python3-pip; do
        if rpm -q "${package}" >/dev/null 2>&1; then
            echo "Package ${package} already installed"
        else
            echo "Installing package ${package}"
            sudo dnf install "${package}" -y
        fi
    done

    # Install necessary groups and updates
    if dnf group info "Development Tools" >/dev/null 2>&1; then
        echo "Package group Development Tools already installed"
    else
        echo "Installing package group Development Tools"
        sudo dnf groupinstall "Development Tools" -y
        sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
        sudo sh -c 'echo -e "[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" > /etc/yum.repos.d/vscode.repo'
        dnf check-update
        sudo dnf install code -y
    fi

    sudo dnf update -y

}

# @description This function get_qubinode_navigator function will clone the qubinode_navigator repo
function get_qubinode_navigator() {
    echo "Cloning qubinode_navigator"
    if [ -d $1/qubinode_navigator ]; then
        echo "Qubinode Installer already exists"
    else
        git clone ${GIT_REPO}
    fi
}

# @description This function configure_navigator function will configure the ansible-navigator
function configure_navigator() {
    echo "Configuring ansible navigator"
    echo "****************"
    if [ -d $1/qubinode_navigator ]; then
        cd $1/qubinode_navigator
        if ! command -v ansible-navigator &> /dev/null; then
            if [ ${BASE_OS}  == "RHEL8" ]; then {
                # Enable the Python 3.9 Module
                sudo dnf module install -y python39
                sudo dnf install -y python39 python39-devel python39-pip
                sudo dnf module enable -y python39

                # Make sure the Python 3.6 Module is disabled
                sudo dnf module disable -y python36

                # Set the default Python version to 3.9
                sudo alternatives --set python /usr/bin/python3.9
                sudo alternatives --set python3 /usr/bin/python3.9

                # Install needed Pip modules
                # - For Ansible-Navigator
                curl -sSL https://raw.githubusercontent.com/ansible/ansible-navigator/main/requirements.txt | sudo python3 -m pip install -r /dev/stdin
                sudo python3 -m pip install -r $HOME/qubinode_navigator/bash-aliases/bastion-requirements.txt
            }
            else
            {
                make install-ansible-navigator
            }
            
            make copy-navigator
            # Check if running as root
            if [ "$EUID" -eq 0 ]; then
               sed -i  's|/home/admin/qubinode_navigator/inventories/localhost|/root/qubinode_navigator/inventories/'${INVENTORY}'|g'  ~/.ansible-navigator.yml
            else
                sed -i  's|/home/admin/qubinode_navigator/inventories/localhost|/home/'$USER'/qubinode_navigator/inventories/'${INVENTORY}'|g'  ~/.ansible-navigator.yml
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
        
        if [ ! -f ~/qubinode_navigator/ansible_vault_setup.sh ];
        then 
            curl -OL https://gist.githubusercontent.com/tosin2013/022841d90216df8617244ab6d6aceaf8/raw/92400b9e459351d204feb67b985c08df6477d7fa/ansible_vault_setup.sh
            chmod +x ansible_vault_setup.sh
        fi
        rm -f ~/.vault_password
        sudo rm -rf /root/.vault_password 
       
        if [ $USE_HASHICORP_VAULT == "true" ];
        then
            echo "$SSH_PASSWORD" > ~/.vault_password
            sudo cp ~/.vault_password /root/.vault_password 
            bash  ./ansible_vault_setup.sh
            if [ $(id -u) -ne 0 ]; then
                if [ ! -f /home/${USER}/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml ];
                then
                    ansiblesafe -f /home/${USER}/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml -o 4
                    ansiblesafe -f /home/${USER}/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml -o 1
                fi
            else 
                if [ ! -f /root/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml ];
                then
                    ansiblesafe -f /root/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml -o 4
                    ansiblesafe -f /root/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml -o 1
                fi
            fi
        else
            read -t 360 -p "Press Enter to continue, or wait 5 minutes for the script to continue automatically" || true
            bash  ./ansible_vault_setup.sh
            if [ $(id -u) -ne 0 ]; then
                if [ ! -f /home/${USER}/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml ];
                then
                    ansiblesafe -f /home/${USER}/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml
                fi
            else 
                if [ ! -f /root/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml ];
                then
                    ansiblesafe -f /root/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml
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
            cp -r inventories/${INVENTORY}/group_vars/control/* inventories/${INVENTORY}/group_vars/control/
        fi
        sed -i 's|export CURRENT_INVENTORY="localhost"|export CURRENT_INVENTORY="'${INVENTORY}'"|g' bash-aliases/random-functions.sh
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
        if ! command -v ansible-navigator &> /dev/null; then
            sudo pip3 install ansible-navigator
            whereis ansible-navigator
            ANSIBLE_NAVIAGATOR=$(whereis ansible-navigator | awk '{print $2}')
        else 
            ANSIBLE_NAVIAGATOR="ansible-navigator "
        fi
        ${ANSIBLE_NAVIAGATOR} inventory --list -m stdout --vault-password-file $HOME/.vault_password
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
        if [ $CICD_PIPELINE == "true" ];
        then 
            if [ "$EUID" -eq 0 ]; then
                sshpass -p "$SSH_PASSWORD" ssh-copy-id -o StrictHostKeyChecking=no $control_user@${IP_ADDRESS}
            else
                sshpass -p "$SSH_PASSWORD" ssh-copy-id -o StrictHostKeyChecking=no $USER@${IP_ADDRESS}
                sudo ssh-keygen -f /root/.ssh/id_rsa -t rsa -N ''
            fi
        else 
            if [ "$EUID" -eq 0 ]; then
                read -p "Enter the target username to ssh into machine: " control_user
                ssh-copy-id $control_user@${IP_ADDRESS}
            else
                ssh-copy-id $USER@${IP_ADDRESS}
                sudo ssh-keygen -f /root/.ssh/id_rsa -t rsa -N ''
            fi
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
        sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make sshpass -y
    elif [ ${1} == "FEDORA" ]; then
        sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make  sshpass -y
    elif [ ${1} == "UBUNTU" ]; then
        sudo apt install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make  sshpass -y
    elif [ ${1} == "CENTOS8" ]; then
        sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make sshpass -y
    elif [ ${1} == "RHEL9" ]; then
        sudo dnf update -y 
        sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make sshpass -y
    elif [ ${1} == "CENTOS9" ]; then
        sudo dnf update -y 
        sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make sshpass -y
    fi
}

function test_inventory(){
    echo "Testing inventory"
    echo "****************"
    if [ -d $1/qubinode_navigator ]; then
        cd $1/qubinode_navigator
        if ! command -v ansible-navigator &> /dev/null; then
            ANSIBLE_NAVIAGATOR=$(whereis ansible-navigator | awk '{print $2}')
        else 
            ANSIBLE_NAVIAGATOR="ansible-navigator "
        fi
        ${ANSIBLE_NAVIAGATOR}  inventory --list -m stdout --vault-password-file $HOME/.vault_password || exit 1
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
    if ! command -v ansible-navigator &> /dev/null; then
        ANSIBLE_NAVIAGATOR=$(whereis ansible-navigator | awk '{print $2}')
    else 
        ANSIBLE_NAVIAGATOR="ansible-navigator"
    fi
    ${ANSIBLE_NAVIAGATOR} run ansible-navigator/setup_kvmhost.yml \
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
         ./bash-aliases/setup-commands.sh || exit 1
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
    #source $1/.profile
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
    configure_os  $BASE_OS
    install_packages
    configure_ssh
    configure_firewalld
    get_qubinode_navigator $MY_DIR
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