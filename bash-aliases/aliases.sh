#!/bin/bash

# Define the aliases
aliases=(
    "alias kcli_configure_images='kcli_configure_images'"
    "alias qubinode_setup_kcli='qubinode_setup_kcli'"
)

# Append aliases to .bash_aliases
for alias in "${aliases[@]}"; do
    if ! grep -Fxq "$alias" ~/.bash_aliases; then
        echo "$alias" >> ~/.bash_aliases
    fi
done
