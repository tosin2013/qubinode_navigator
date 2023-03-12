#!/bin/bash 
#github-action genshdoc
set -xe
export ANSIBLE_SAFE_VERSION="0.0.4"
export INVENTORY="localhost"

# @description This function get_rhel_version function will determine the version of RHEL
function get_rhel_version() {
  if cat /etc/redhat-release  | grep "Red Hat Enterprise Linux release 9.[0-9]" > /dev/null 2>&1; then
    export BASE_OS="RHEL9"
    sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make  -y
  elif cat /etc/redhat-release  | grep "Red Hat Enterprise Linux release 8.[0-9]" > /dev/null 2>&1; then
      export BASE_OS="RHEL8"
  elif cat /etc/redhat-release  | grep "Rocky Linux release 8.[0-9]" > /dev/null 2>&1; then
    export BASE_OS="ROCKY8"
  elif cat /etc/redhat-release  | grep 7.[0-9] > /dev/null 2>&1; then
    export BASE_OS="RHEL7"
  elif cat /etc/redhat-release  | grep "CentOS Stream release 9" > /dev/null 2>&1; then
    export BASE_OS="CENTOS9"
    sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make  -y
  elif cat /etc/redhat-release  | grep "CentOS Stream release 8" > /dev/null 2>&1; then
    export BASE_OS="CENTOS8"
    sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make  -y
  elif cat /etc/redhat-release  | grep "Fedora" > /dev/null 2>&1; then
    export BASE_OS="FEDORA"
    sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make  -y
  else
    echo "Operating System not supported"
    echo "You may put a pull request to add support for your OS"
  fi
  echo ${BASE_OS}

}

# @description This function get_quibinode_navigator function will clone the quibinode_navigator repo
function get_quibinode_navigator() {
    if [ -d $1/quibinode_navigator ]; then
        echo "Qubinode Installer already exists"
    else
        git clone https://github.com/tosin2013/quibinode_navigator.git
    fi
}

function configure_navigator() {
    if [ -d $1/quibinode_navigator ]; then
        cd $1/quibinode_navigator
        if ! command -v ansible-navigator &> /dev/null; then
            make install-ansible-navigator
            make copy-navigator
            # Check if running as root
            if [ "$EUID" -eq 0 ]; then
               sed -i  's|/home/admin/quibinode_navigator/inventories/localhost|/root/quibinode_navigator/inventories/localhost|g'  ~/.ansible-navigator.yml
            else
                sed -i  's|/home/admin/quibinode_navigator/inventories/localhost|/home/'$USER'/quibinode_navigator/inventories/localhost|g'  ~/.ansible-navigator.yml
            fi
        fi
    else
        echo "Qubinode Installer does not exist"
    fi
}

function configure_vault() {
    if [ -d $1/quibinode_navigator ]; then
        cd $1/quibinode_navigator
        if ! command -v ansible-vault &> /dev/null; then
            sudo dnf install ansible-core -y 
        fi
        if ! command -v ansiblesafe &> /dev/null; then
            curl -OL https://github.com/tosin2013/ansiblesafe/releases/download/v${ANSIBLE_SAFE_VERSION}/ansiblesafe-v${ANSIBLE_SAFE_VERSION}-linux-amd64.tar.gz
            tar -zxvf ansiblesafe-v${ANSIBLE_SAFE_VERSION}-linux-amd64.tar.gz
            chmod +x ansiblesafe-linux-amd64 
            sudo mv ansiblesafe-linux-amd64 /usr/local/bin/ansiblesafe
        fi
        curl -OL https://gist.githubusercontent.com/tosin2013/022841d90216df8617244ab6d6aceaf8/raw/92400b9e459351d204feb67b985c08df6477d7fa/ansible_vault_setup.sh
        chmod +x ansible_vault_setup.sh
        ./ansible_vault_setup.sh
        if [ $(id -u) -ne 0 ]; then
            if [ ! -f /home/${USER}/quibinode_navigator/inventories/localhost/group_vars/control/vault.yml ];
            then
                ansiblesafe -f /home/${USER}/quibinode_navigator/inventories/localhost/group_vars/control/vault.yml
            fi
        else 
            if [ ! -f /root/quibinode_navigator/inventories/localhost/group_vars/control/vault.yml ];
            then
                ansiblesafe -f /root/quibinode_navigator/inventories/localhost/group_vars/control/vault.yml
            fi
        fi
        #ansible-navigator inventory --list -m stdout --vault-password-file $HOME/.vault_password
    else
        echo "Qubinode Installer does not exist"
    fi
}

function generate_inventory(){
    if [ -d $1/quibinode_navigator ]; then
        cd $1/quibinode_navigator
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

function copy-ssh-id(){
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

function configure-os(){
    if [ ${1} == "ROCKY8" ]; then
        sudo dnf install -y git make ansible-core
    elif [ ${1} == "FEDORA" ]; then
        sudo dnf install -y git make ansible-core
    elif [ ${1} == "UBUNTU" ]; then
        sudo apt install -y git make ansible-core
    elif [ ${1} == "CENTOS8" ]; then
        sudo dnf install -y git make ansible-core
    fi
}

get_rhel_version
if ! command -v git &> /dev/null; then
   echo "git could not be found"
   echo "Please install git and try again"
   exit 1
fi 

if [  $BASE_OS == "ROCKY8" ];
then 
    if [ $(id -u) -ne 0 ]; then
        echo "You must be root to run this script"
        exit 1
    fi
    configure-os $BASE_OS
    #groupadd lab-user
    get_quibinode_navigator "/root"
    configure_navigator "/root"
    configure_vault "/root"
    generate_inventory "/root"
    copy-ssh-id
elif [ $BASE_OS != "ROCKY8" ];
then 
    echo "Continuing with the script"
    if [ $(id -u) -ne 0 ]; then
        get_quibinode_navigator "$HOME"
        configure_navigator  "$HOME"
        configure_vault "$HOME"
        generate_inventory "$HOME"
        copy-ssh-id
    else 
        get_quibinode_navigator "/root"
        configure_navigator "/root"
        configure_vault "/root"
        generate_inventory "/root"
        copy-ssh-id
    fi
fi 