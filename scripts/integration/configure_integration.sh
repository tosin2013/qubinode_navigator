#!/bin/bash

# Function: configure_onedev
# Description: Configures OneDev by ensuring the current directory is /opt/qubinode_navigator.
# If the current directory is not /opt/qubinode_navigator, it changes to that directory.
# Then, it runs the configure-onedev.sh script located in ./dependancies/onedev/.
configure_onedev() {
    if [ "$(pwd)" != "/opt/qubinode_navigator" ]; then
        echo "Current directory is not /opt/qubinode_navigator."
        echo "Changing to /opt/qubinode_navigator..."
        cd /opt/qubinode_navigator
    else
        echo "Current directory is /opt/qubinode_navigator."
    fi
    echo "Configuring OneDev"
    echo "******************"
    ./dependancies/onedev/configure-onedev.sh
}

# Function: configure_gitlab
# Description: Configures GitLab by running a deployment script.
# It first checks if the current working directory is /opt/qubinode_navigator.
# If not, it changes the directory to /opt/qubinode_navigator.
# Then, it runs the GitLab deployment script located at ./dependancies/gitlab/deployment-script.sh.
configure_gitlab() {
    if [ "$(pwd)" != "/opt/qubinode_navigator" ]; then
        echo "Current directory is not /opt/qubinode_navigator."
        echo "Changing to /opt/qubinode_navigator..."
        cd /opt/qubinode_navigator
    else
        echo "Current directory is /opt/qubinode_navigator."
    fi
    echo "Configuring GitLab"
    echo "******************"
    ./dependancies/gitlab/deployment-script.sh
}

# Function: configure_github
# Description: Configures GitHub by running a deployment script.
# It first checks if the current working directory is /opt/qubinode_navigator.
# If not, it changes the directory to /opt/qubinode_navigator.
# Then, it runs the deployment script located at ./dependancies/github/deployment-script.sh.
# If the script fails, the function exits with the script's exit status.
configure_github() {
    if [ "$(pwd)" != "/opt/qubinode_navigator" ]; then
        echo "Current directory is not /opt/qubinode_navigator."
        echo "Changing to /opt/qubinode_navigator..."
        cd /opt/qubinode_navigator
    else
        echo "Current directory is /opt/qubinode_navigator."
    fi
    echo "Configuring GitHub"
    echo "******************"
    ./dependancies/github/deployment-script.sh || exit $?
}
