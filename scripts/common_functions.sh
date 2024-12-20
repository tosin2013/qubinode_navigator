#!/bin/bash

# Function: check_root
# Description: This function checks if the script is being run as the root user.
#              If the script is not run as root, it logs an error message and exits with a status code of 1.
#
# Parameters: None
#
# Returns: None
#
# Exit Codes:
#   1 - If the script is not run as root.
#
# Dependencies:
#   - log_message function for logging errors.
#
# Example Usage:
#   check_root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_message "Error: This script must be run as root"
        exit 1
    fi
}

# Function: log_message
# Description: This function logs a message to the console.
#
# Parameters:
#   - message: The message to log.
#
# Returns: None
#
# Example Usage:
#   log_message "Installing required packages..."
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}
