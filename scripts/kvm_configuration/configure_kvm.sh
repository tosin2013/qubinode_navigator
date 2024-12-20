#!/bin/bash

# Function: confiure_lvm_storage
# Description: This function configures LVM storage on the system.
#              It downloads a script to configure LVM if it does not already exist,
#              and then runs the script to set up LVM storage.
#
# Parameters: None
#
# Returns: None
#
# Exit Codes:
#   1 - If the LVM configuration script fails to execute.
#
# Dependencies:
#   - curl for downloading the LVM configuration script.
#   - chmod for setting the executable permission on the script.
#
# Example Usage:
#   confiure_lvm_storage
confiure_lvm_storage() {
    echo "Configuring Storage"
    echo "************************"
    if [ ! -f /tmp/configure-lvm.sh ]; then
        curl -OL https://raw.githubusercontent.com/tosin2013/qubinode_navigator/main/dependancies/equinix-rocky/configure-lvm.sh
        mv configure-lvm.sh /tmp/configure-lvm.sh
        sudo chmod +x /tmp/configure-lvm.sh
    fi
    /tmp/configure-lvm.sh || exit 1
}
