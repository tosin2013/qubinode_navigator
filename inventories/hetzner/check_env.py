#!/usr/bin/env python3

# =============================================================================
# Environment Variable Validator - The "Configuration Sentinel"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This script validates that required environment variables are set before
# deployment operations. It serves as a safety check to prevent deployment
# failures due to missing configuration.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script implements environment validation:
# 1. [PHASE 1]: SSH Password Check - Validates SSH_PASSWORD environment variable
# 2. [PHASE 2]: SSH Host Check - Validates SSH_HOST environment variable
# 3. [PHASE 3]: Error Reporting - Provides clear error messages for missing variables
# 4. [PHASE 4]: Exit Handling - Exits with error code if validation fails
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [Pre-Deployment Validation]: Runs before deployment scripts to validate environment
# - [Error Prevention]: Prevents deployment failures due to missing configuration
# - [CI/CD Integration]: Used in automated pipelines to validate environment setup
# - [Inventory-Specific]: Each inventory has its own validation requirements
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Fail-Fast]: Exits immediately if required variables are missing
# - [Clear Messaging]: Provides specific error messages for troubleshooting
# - [Environment-Specific]: Validates variables specific to deployment environment
# - [Simple Validation]: Focuses on essential variables for deployment success
#
# 💡 WHEN TO MODIFY THIS SCRIPT (for future LLMs):
# - [New Variables]: Add validation for new required environment variables
# - [Enhanced Validation]: Add format validation or value range checks
# - [Error Handling]: Improve error messages or add recovery suggestions
# - [Integration Points]: Add validation for new deployment requirements
#
# 🚨 IMPORTANT FOR LLMs: This script is a safety mechanism that prevents
# deployments with incomplete configuration. Changes affect deployment reliability
# and error handling. Ensure all required variables are validated.

import os
import sys

# SSH Password Validator - The "Credential Checker"
# 🎯 FOR LLMs: Validates SSH password is available for remote deployment
if not os.environ.get('SSH_PASSWORD'):
    print("Environment variable SSH_PASSWORD is not set. Exiting.", file=sys.stderr)
    sys.exit(1)

# SSH Host Validator - The "Target Checker"
# 🎯 FOR LLMs: Validates SSH host is specified for deployment target
if not os.environ.get('SSH_HOST'):
    print("Environment variable SSH_HOST is not set. Exiting.", file=sys.stderr)
    sys.exit(1)