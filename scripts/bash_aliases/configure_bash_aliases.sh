#!/bin/bash

# Function: configure_bash_aliases
# Description: Configures bash aliases by performing the following steps:
# 1. Prints a message indicating the start of the configuration process.
# 2. Checks if the current directory is "/opt/qubinode_navigator".
#    - If not, it changes the directory to "/opt/qubinode_navigator".
#    - If yes, it prints a message confirming the current directory.
# 3. Sources the function definitions from "bash-aliases/functions.sh".
# 4. Sources the alias definitions from "bash-aliases/aliases.sh".
# 5. Checks if the "~/.bash_aliases" file exists and sources it to apply changes.
# 6. Ensures that "~/.bash_aliases" is sourced from "~/.bashrc".
#    - If not already sourced, it appends the sourcing command to "~/.bashrc".
function configure_bash_aliases() {
    echo "Configuring bash aliases"
    echo "************************"
    if [ "$(pwd)" != "/opt/qubinode_navigator" ]; then
        echo "Current directory is not /opt/qubinode_navigator."
        echo "Changing to /opt/qubinode_navigator..."
        cd /opt/qubinode_navigator
    else
        echo "Current directory is /opt/qubinode_navigator."
    fi
    # Source the function definitions
    source bash-aliases/functions.sh

    # Source the alias definitions
    source bash-aliases/aliases.sh

    # Source .bash_aliases to apply changes
    if [ -f ~/.bash_aliases ]; then
        . ~/.bash_aliases
    fi

    # Ensure .bash_aliases is sourced from .bashrc
    if ! grep -qF "source ~/.bash_aliases" ~/.bashrc; then
        echo "source ~/.bash_aliases" >> ~/.bashrc
    fi
}
