#!/bin/bash

# Function: configure_firewalld
# Description: Configures the firewalld service.
# It starts the firewalld service and enables it to start on boot.
# If either operation fails, it logs an error message and exits the script with a status of 1.
#
# Usage:
#   configure_firewalld
#
# Example:
#   configure_firewalld
configure_firewalld() {
    log_message "Configuring firewalld..."
    if ! systemctl start firewalld; then
        log_message "Failed to start firewalld"
        exit 1
    fi
    if ! systemctl enable firewalld; then
        log_message "Failed to enable firewalld"
        exit 1
    fi
}
