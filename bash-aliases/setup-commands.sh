#!/bin/bash 
#github-action genshdoc
# @file Setup the bash aliases for the qubinode installer
# @brief This script will setup the bash aliases for the qubinode installer
export PS4='+(${BASH_SOURCE}:${LINENO}): ${FUNCNAME[0]:+${FUNCNAME[0]}(): }'
set -x

if ! command -v alf &> /dev/null; then
    curl -Ls get.dannyb.co/alf/setup | bash
fi 

if [ -f /usr/local/bin/alf ]; then
    echo "alf is not installed"
    exit 1
fi

if [ ! -d /opt/qubinode_navigator/bash-aliases/ ];
then
    cd /opt/
    sudo git clone https://github.com/tosin2013/qubinode_navigator.git qubinode_navigator
    cd $HOME/qubinode_navigator
    sudo cp bash-aliases/random-functions.sh /opt/qubinode_navigator/bash-aliases/random-functions.sh
    cd /opt/qubinode_navigator/bash-aliases/
    /usr/local/bin/alf generate
    /usr/local/bin/alf save
else
    cd $HOME/qubinode_navigator
    sudo cp bash-aliases/random-functions.sh /opt/qubinode_navigator/bash-aliases/random-functions.sh
    cd /opt/qubinode_navigator/bash-aliases/
    sudo git pull 
    /usr/local/bin/alf generate
    /usr/local/bin/alf save
    cat  ~/.bash_aliases || exit 1
fi

# Define the array of lines to add
lines=(
    'source /opt/qubinode_navigator/bash-aliases/random-functions.sh'
    'source /opt/qubinode_navigator/bash-aliases/configure-kcli.sh'
    'source /opt/qubinode_navigator/bash-aliases/configure-freeipa-workshop-deployer.sh'
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

ALIASES_LINE='[[ -f ~/.bash_aliases ]] && . ~/.bash_aliases'

if ! grep -qF "$ALIASES_LINE" ~/.bashrc; then
  echo "$ALIASES_LINE" >> ~/.bashrc
fi