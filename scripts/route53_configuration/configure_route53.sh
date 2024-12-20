#!/bin/bash

# Function: configure_route53
# Description: Configures Route53 DNS settings.
# It checks if the current working directory is /opt/qubinode_navigator.
# If not, it changes the directory to /opt/qubinode_navigator.
# Then, it prints the ZONE_NAME environment variable and runs the Route53 deployment script.
configure_route53() {
    if [ "$(pwd)" != "/opt/qubinode_navigator" ]; then
        echo "Current directory is not /opt/qubinode_navigator."
        echo "Changing to /opt/qubinode_navigator..."
        cd /opt/qubinode_navigator
    else
        echo "Current directory is /opt/qubinode_navigator."
    fi
    echo "Configuring Route53"
    echo "******************"
    echo "ZONE_NAME: $ZONE_NAME"
    ./dependancies/route53/deployment-script.sh
}
