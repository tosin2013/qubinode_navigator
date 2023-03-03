#!/bin/bash 
if [ ! -d /opt/qubinode-installer ]; then
    echo "Qubinode Installer does not exist"
    exit 1
fi

cd /opt/qubinode-installer

sudo cp -R $HOME/quibinode_navigator/bash-aliases/ .
