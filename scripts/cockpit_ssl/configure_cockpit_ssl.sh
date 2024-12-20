#!/bin/bash

# Function: configure_cockpit_ssl
# Description: Configures Cockpit SSL.
# It first checks if the current working directory is /opt/qubinode_navigator.
# If not, it changes the directory to /opt/qubinode_navigator.
# Then, it checks if the SSL certificate file does not exist at the specified path.
# If the file does not exist, it runs the configure-cockpit-ssl.sh script to configure SSL for Cockpit.
configure_cockpit_ssl() {
    if [ "$(pwd)" != "/opt/qubinode_navigator" ]; then
        echo "Current directory is not /opt/qubinode_navigator."
        echo "Changing to /opt/qubinode_navigator..."
        cd /opt/qubinode_navigator
    else
        echo "Current directory is /opt/qubinode_navigator."
    fi
    echo "Configuring Cockpit SSL"
    echo "******************"
    if [ ! -f /etc/letsencrypt/live/sandbox1609.opentlc.com/fullchain.pem  ]; then
        ./dependancies/cockpit-ssl/configure-cockpit-ssl.sh
    fi
}
