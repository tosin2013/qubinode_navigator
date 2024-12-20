#!/bin/bash

# Function: configure_lvm_storage
# Description: This function configures LVM storage on the system by downloading and executing a remote script.
# Parameters: None
# Returns: None
# Exit Codes:
#   1 - If LVM configuration fails.
configure_lvm_storage() {
    echo "Configuring Storage"
    echo "************************"
    if [ ! -f /tmp/configure-lvm.sh ]; then
        curl -OL https://raw.githubusercontent.com/tosin2013/qubinode_navigator/main/dependancies/equinix-rocky/configure-lvm.sh
        mv configure-lvm.sh /tmp/configure-lvm.sh
        sudo chmod +x /tmp/configure-lvm.sh
    fi
    /tmp/configure-lvm.sh || exit 1
}
