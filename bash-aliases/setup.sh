#!/bin/bash 
if [ ! -d /opt/qubinode-installer ]; then
    echo "Qubinode Installer does not exist"
    exit 1
fi

cd /opt/qubinode-installer

sudo cp -R $HOME/quibinode_navigator/bash-aliases/ .


if [ -d /opt/qubinode-installer/bash-aliases/ ];
then
        source /opt/qubinode-installer/bash-aliases/random-functions.sh
        source /opt/qubinode-installer/bash-aliases/configure-kcli.sh
fi


if [ -f ~/.bash_aliases ]; then
. ~/.bash_aliases
fi