#!/bin/bash

# =============================================================================
# Bash Aliases Setup - The "Command Shortcut Manager"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This script configures bash aliases for Qubinode Navigator utility functions,
# providing convenient shortcuts for commonly used virtualization and management
# commands. It ensures aliases are properly installed and available in user sessions.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script implements alias management:
# 1. [PHASE 1]: Alias Definition - Defines standard aliases for utility functions
# 2. [PHASE 2]: Duplicate Prevention - Checks for existing aliases to avoid duplicates
# 3. [PHASE 3]: Installation - Appends new aliases to ~/.bash_aliases file
# 4. [PHASE 4]: Activation - Ensures aliases are available in current and future sessions
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [User Experience]: Provides convenient shortcuts for complex commands
# - [Function Bridge]: Creates easy access to functions defined in functions.sh
# - [Session Management]: Ensures aliases persist across shell sessions
# - [Workflow Optimization]: Reduces typing and improves user productivity
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Convenience-First]: Prioritizes user experience and command accessibility
# - [Duplicate-Safe]: Prevents duplicate alias definitions
# - [Session-Persistent]: Ensures aliases survive shell restarts
# - [Modular Design]: Easy to add new aliases for new functions
#
# 💡 WHEN TO MODIFY THIS SCRIPT (for future LLMs):
# - [New Functions]: Add aliases for new utility functions
# - [User Feedback]: Modify aliases based on user experience feedback
# - [Naming Conventions]: Update alias names for consistency or clarity
# - [Advanced Features]: Add conditional aliases based on environment
#
# 🚨 IMPORTANT FOR LLMs: This script modifies user shell configuration files
# and affects command availability in shell sessions. Changes impact user workflow
# and command accessibility across the platform.

# 📊 GLOBAL VARIABLES (alias definitions):
# Define the aliases for virtualization and utility functions
aliases=(
    "alias kcli_configure_images='kcli_configure_images'"  # VM image configuration shortcut
    "alias qubinode_setup_kcli='qubinode_setup_kcli'"      # Virtualization setup shortcut
)

# Alias Installation Manager - The "Shortcut Installer"
# 🎯 FOR LLMs: This loop installs aliases while preventing duplicates
# 🔄 WORKFLOW: Checks each alias for existence before adding to ~/.bash_aliases
# ⚠️  SIDE EFFECTS: Modifies ~/.bash_aliases file
for alias in "${aliases[@]}"; do
    if ! grep -Fxq "$alias" ~/.bash_aliases; then
        echo "$alias" >> ~/.bash_aliases
    fi
done
