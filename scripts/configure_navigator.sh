#!/bin/bash

# This function configures the Qubinode Navigator by performing the following steps:
# 1. Logs the start of the configuration process.
# 2. Checks if the Qubinode Navigator directory exists in /opt:
#    - If it exists, it pulls the latest changes from the git repository.
#    - If it does not exist, it clones the repository into /opt/qubinode_navigator.
# 3. Changes the ownership and permissions of the /opt directory to allow the current user to write to it.
# 4. Installs the required Python packages from the requirements.txt file using pip3.
# 5. Logs the current DNS server being used.
# 6. Loads variables either interactively or from environment variables based on the CICD_PIPELINE flag:
#    - If CICD_PIPELINE is false, it waits for user input or continues after 5 minutes, then runs the load-variables.py script.
#    - If CICD_PIPELINE is true, it checks for required environment variables and runs the load-variables.py script with those variables.
# 7. Logs any errors encountered during the process and exits with a status of 1 if any step fails.
configure_navigator() {
    log_message "Configuring Qubinode Navigator..."
    echo "******************************"
    if [ -d "/opt/qubinode_navigator" ]; then
        log_message "Qubinode Navigator already exists"
        git -C "/opt/qubinode_navigator" pull
    else
        cd "$HOME"
        sudo usermod -aG users "$USER"
        sudo chown -R root:users /opt
        sudo chmod -R g+w /opt
        if ! git clone "${GIT_REPO}"; then
            log_message "Failed to clone repository"
            exit 1
        fi
        ln -s /opt/qubinode_navigator /opt/qubinode_navigator
    fi
    cd "/opt/qubinode_navigator"
    if ! sudo pip3 install -r requirements.txt; then
        log_message "Failed to install Qubinode Navigator requirements"
        exit 1
    fi
    log_message "Current DNS Server: $(cat /etc/resolv.conf | grep nameserver | awk '{print $2}' | head -1)"
    log_message "Load variables"
    echo "**************"
    if [ "$CICD_PIPELINE" == "false" ]; then
        read -t 360 -p "Press Enter to continue, or wait 5 minutes for the script to continue automatically" || true
        if ! python3 load-variables.py; then
            log_message "Failed to load variables"
            exit 1
        fi
    else
        if [[ -z "$ENV_USERNAME" || -z "$DOMAIN" || -z "$FORWARDER" || -z "$INTERFACE" ]]; then
            log_message "Error: One or more environment variables are not set"
            exit 1
        fi
        if ! python3 load-variables.py --username "${ENV_USERNAME}" --domain "${DOMAIN}" --forwarder "${FORWARDER}" --interface "${INTERFACE}"; then
            log_message "Failed to load variables with environment parameters"
            exit 1
        fi
    fi
}
