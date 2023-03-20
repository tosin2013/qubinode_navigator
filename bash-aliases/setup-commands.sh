#!/bin/bash 
#github-action genshdoc
# @file Setup the bash aliases for the qubinode installer
# @brief This script will setup the bash aliases for the qubinode installer

if ! command -v alf &> /dev/null; then
    curl -Ls get.dannyb.co/alf/setup | bash
fi 


if [ ! -d /opt/quibinode_navigator ];
then
    cd /opt/
    sudo git clone https://github.com/tosin2013/quibinode_navigator.git quibinode_navigator
    cd /opt/quibinode_navigator
    sudo git pull 
    alf generate
    alf save
else
    cd /opt/quibinode_navigator
    sudo git pull 
    alf generate
    alf save
fi

# Define the array of lines to add
lines=(
    'source /opt/quibinode_navigator/bash-aliases/random-functions.sh'
    'source /opt/quibinode_navigator/bash-aliases/configure-kcli.sh'
    'source  /opt/quibinode_navigator/bash-aliases/configure-freeipa-workshop-deployer.sh'
)

# Iterate through the array and check if each line exists in the file
should_add=0
for line in "${lines[@]}"; do
    if ! grep -Fxq "$line" ~/.bash_aliases; then
        should_add=1
        break
    fi
done

# If any line does not exist, append all the lines to the file
if [[ $should_add -eq 1 ]]; then
    printf '%s\n' "${lines[@]}" | tee -a ~/.bash_aliases > /dev/null
fi


if [ -f ~/.bash_aliases ]; then
. ~/.bash_aliases
fi