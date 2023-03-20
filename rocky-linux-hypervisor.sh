#!/bin/bash
set -xe 
KVM_VERSION=0.4.0
export INVENTORY="localhost"

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi


# @description This function generate_inventory function will generate the inventory
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


# Install necessary packages
sudo dnf install openssl-devel bzip2-devel libffi-devel wget  vim podman  ncurses-devel sqlite-devel firewalld -y
sudo dnf groupinstall "Development Tools" -y 
sudo dnf update -y

# Check if the group "lab-user" exists
if grep -q "^lab-user:" /etc/group; then
    echo "The group 'lab-user' already exists"
else
    # Create the group "lab-user"
    sudo groupadd lab-user
    echo "The group 'lab-user' has been created"
fi

if systemctl is-active --quiet firewalld; then
    echo "firewalld is already active"
else
    echo "starting firewalld"
    sudo systemctl start firewalld
    sudo systemctl enable firewalld
fi

if which python3 >/dev/null; then
    echo "Python is installed"
    source ~/.profile
else
    # Download Python 3.11 source code
    VERSION=3.11.2
    wget https://www.python.org/ftp/python/$VERSION/Python-$VERSION.tgz
    tar -xzf Python-$VERSION.tgz

    # Install Python 3.11
    cd Python-$VERSION
    ./configure --enable-loadable-sqlite-extensions --enable-optimizations
    sudo make altinstall

    # Verify Python 3.11 installation
    python3.11 --version
    pip3.11 --version


    sudo ln /usr/local/bin/python3.11 /usr/bin/python3
    sudo ln /usr/local/bin/python3.11 /usr/bin/python3.11
    sudo ln /usr/local/bin/pip3.11 /usr/bin/pip3

    sudo pip3 install setuptools-rust 
    sudo pip3 install --user ansible-core
    sudo pip3 install --upgrade --user ansible
    sudo pip3 install ansible-navigator
    sudo pip3 install firewall
    sudo pip3 install pyyaml
    sudo pip3 install ansible-vault
    echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.profile
    source ~/.profile
fi

if [ -d $HOME/quibinode_navigator ]; then
    echo "Qubinode Installer already exists"
else
    cd $HOME
    git clone https://github.com/tosin2013/quibinode_navigator.git
fi 
cd  $HOME/quibinode_navigator
sudo pip3  install  -r requirements.txt
python3 load-variables.py


if [ -f ~/.ssh/id_rsa ]; then
    echo "SSH key already exists"
else
    IP_ADDRESS=$(hostname -I | awk '{print $1}')
    ssh-keygen -f ~/.ssh/id_rsa -t rsa -N ''
    ssh-copy-id lab-user@${IP_ADDRESS}
fi

cat >~/.ansible-navigator.yml<<EOF
---
ansible-navigator:
  ansible:
    inventories:    
      - /root/quibinode_navigator/inventories/localhost
  logging:
    level: debug
    append: true
    file: /tmp/navigator/ansible-navigator.log
  playbook-artifact:
    enable: false
  execution-environment:
    container-engine: podman
    enabled: true
    pull-policy: missing
    image: quay.io/qubinode/qubinode-installer:${KVM_VERSION}
    environment-variables:
      pass:
        - USER
EOF

curl -OL https://gist.githubusercontent.com/tosin2013/022841d90216df8617244ab6d6aceaf8/raw/92400b9e459351d204feb67b985c08df6477d7fa/ansible_vault_setup.sh
chmod +x ansible_vault_setup.sh
./ansible_vault_setup.sh

curl -OL https://github.com/tosin2013/ansiblesafe/releases/download/v0.0.4/ansiblesafe-v0.0.4-linux-amd64.tar.gz
tar -zxvf ansiblesafe-v0.0.4-linux-amd64.tar.gz
chmod +x ansiblesafe-linux-amd64 
sudo mv ansiblesafe-linux-amd64 /usr/local/bin/ansiblesafe

ansiblesafe -f /root/quibinode_navigator/inventories/localhost/group_vars/control/vault.yml
generate_inventory /root

ansible-navigator inventory --list -m stdout --vault-password-file $HOME/.vault_password || exit 1
eval `ssh-agent`
ssh-add ~/.ssh/id_rsa
cd $HOME/quibinode_navigator
source ~/.profile
ansible-navigator run ansible-navigator/setup_kvmhost.yml \
 --vault-password-file $HOME/.vault_password -m stdout || exit 1

./bash-aliases/setup-commands.sh || exit 1

source ~/.bash_aliases
kcli-utils setup
kcli-utils configure-images
kcli-utils check-kcli-plan