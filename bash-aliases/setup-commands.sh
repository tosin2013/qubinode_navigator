#!/bin/bash 
#github-action genshdoc
# @file Setup the bash aliases for the qubinode installer
# @brief This script will setup the bash aliases for the qubinode installer

if [ ! -d /opt/qubinode-installer ]; then
    echo "Qubinode Installer does not exist"
    exit 1
fi

if ! command -v alf &> /dev/null; then
    curl -OL https://github.com/DannyBen/alf/archive/refs/tags/v0.5.0.tar.gz
fi 

cd /opt/qubinode-installer

sudo cp -R $HOME/quibinode_navigator/bash-aliases/ .
cd /opt/qubinode-installer/bash-aliases
ls -lath .

alf generate
alf save

# Define the array of lines to add
lines=(
    'source /opt/qubinode-installer/bash-aliases/random-functions.sh'
    'source /opt/qubinode-installer/bash-aliases/configure-kcli.sh'
    'source  /opt/qubinode-installer/bash-aliases/configure-freeipa-workshop-deployer.sh'
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