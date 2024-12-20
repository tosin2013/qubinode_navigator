#!/bin/bash

# Function to configure LVM storage
configure_lvm_storage() {
    log_message "Configuring LVM storage..."
    if [ ! -f /tmp/configure-lvm.sh ]; then
        curl -OL https://raw.githubusercontent.com/tosin2013/qubinode_navigator/main/dependancies/equinix-rocky/configure-lvm.sh
        mv configure-lvm.sh /tmp/configure-lvm.sh
        chmod +x /tmp/configure-lvm.sh
    fi
    /tmp/configure-lvm.sh || exit 1
}
