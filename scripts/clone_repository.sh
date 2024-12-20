#!/bin/bash

# Function to clone the repository
clone_repository() {
    if [ ! -d "/opt/qubinode_navigator" ]; then
        log_message "Cloning qubinode_navigator repository..."
        if ! git clone "$GIT_REPO" "/opt/qubinode_navigator"; then
            log_message "Failed to clone repository"
            exit 1
        fi
    fi
}
