#!/bin/bash
# Install necessary packages
sudo dnf install openssl-devel bzip2-devel libffi-devel wget  vim podman  ncurses-devel sqlite-devel zabbix40-4.0.39-1.el8.x86_64 -y
sudo dnf groupinstall "Development Tools" -y 
sudo dnf update -y

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


ln /usr/local/bin/python3.11 /usr/bin/python3
ln /usr/local/bin/python3.11 /usr/bin/python3.11
ln /usr/local/bin/pip3.11 /usr/bin/pip3

sudo pip3 install setuptools-rust 
sudo pip3 install --user ansible-core
sudo pip3 install --upgrade --user ansible
echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.profile
source ~/.profile



sudo pip3 install ansible-navigator
echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.profile
source ~/.profile
#/usr/bin/python3 -m pip install _sqlite3

git clone https://github.com/tosin2013/quibinode_navigator.git
cd quibinode_navigator
sudo pip3  install  -r requirements.txt
python3 load-variables.py


IP_ADDRESS=$(hostname -I | awk '{print $1}')
ssh-keygen -f ~/.ssh/id_rsa -t rsa -N ''
ssh-copy-id admin@${IP_ADDRESS}