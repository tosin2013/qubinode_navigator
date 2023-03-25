#!/bin/bash 
#github-action genshdoc

# @setting-header setup.sh quickstart script for quibinode_navigator
# @setting ./setup.sh 

set -xe
# @global ANSIBLE_SAFE_VERSION this is the ansible safe version
# @global INVENTORY this is the inventory file name and path Example: inventories/localhost
export ANSIBLE_SAFE_VERSION="0.0.4"
export INVENTORY="localhost"

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

# @description This function get_quibinode_navigator function will clone the quibinode_navigator repo
function get_quibinode_navigator() {
    echo "Cloning quibinode_navigator"
    if [ -d $1/quibinode_navigator ]; then
        echo "Qubinode Installer already exists"
    else
        git clone https://github.com/tosin2013/quibinode_navigator.git
    fi
}

# @description This function configure_navigator function will configure the ansible-navigator
function configure_navigator() {
    echo "Configuring ansible navigator"
    echo "****************"
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

# @description This function configure_vault function will configure the ansible-vault it will download ansible vault and ansiblesafe
function configure_vault() {
    echo "Configuring vault using ansible safe"
    echo "****************"
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
        echo "Configure Ansible Vault password file"
        echo "****************"
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

# @description This function generate_inventory function will generate the inventory
function generate_inventory(){
    echo "Generating inventory"
    echo "****************"
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

# @description This function configure_ssh function will configure the ssh
function copy-ssh-id(){
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

# @description This configure-os function will get the base os and install the required packages
function configure-os(){
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

get_rhel_version


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
        configure-os $BASE_OS
        get_quibinode_navigator "$HOME"
        configure_navigator  "$HOME"
        configure_vault "$HOME"
        generate_inventory "$HOME"
        copy-ssh-id
    else 
        configure-os $BASE_OS
        get_quibinode_navigator "/root"
        configure_navigator "/root"
        configure_vault "/root"
        generate_inventory "/root"
        copy-ssh-id
    fi
fi 


ansible-navigator inventory --list -m stdout --vault-password-file $HOME/.vault_password || exit 1
eval `ssh-agent`
ssh-add ~/.ssh/id_rsa
cd  $HOME/quibinode_navigator
sudo pip3  install  -r requirements.txt
echo "Loading variables for Ansible Navigator"
echo "****************"
python3 load-variables.py
echo "Running setup_kvmhost.yml to configure the host with KVM"
echo "****************"
ansible-navigator run ansible-navigator/setup_kvmhost.yml \
 --vault-password-file $HOME/.vault_password -m stdout || exit 1

echo "Configuring bash aliases for command commands"
./bash-aliases/setup-commands.sh || exit 1

source ~/.bash_aliases
kcli-utils setup
kcli-utils configure-images
kcli-utils check-kcli-plan