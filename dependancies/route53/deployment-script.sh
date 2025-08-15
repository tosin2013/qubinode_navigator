#!/bin/bash

# =============================================================================
# Route53 DNS Management - The "Cloud DNS Orchestrator"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This script manages AWS Route53 DNS records for Qubinode Navigator infrastructure,
# automatically creating and updating DNS entries for deployed services. It provides
# dynamic DNS management for cloud and hybrid deployments.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script implements Route53 DNS management:
# 1. [PHASE 1]: Dependency Installation - Installs AWS collections and DNS management role
# 2. [PHASE 2]: Credential Retrieval - Securely retrieves AWS credentials from vault
# 3. [PHASE 3]: IP Detection - Automatically detects server IP addresses
# 4. [PHASE 4]: Environment Validation - Validates required environment variables
# 5. [PHASE 5]: Playbook Generation - Creates dynamic Ansible playbook for DNS updates
# 6. [PHASE 6]: DNS Execution - Executes DNS record creation/updates via Route53
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [DNS Management]: Provides automated DNS record management for infrastructure
# - [Cloud Integration]: Integrates with AWS Route53 for DNS services
# - [Vault Security]: Uses AnsibleSafe for secure AWS credential management
# - [Dynamic Configuration]: Automatically detects and configures IP addresses
# - [Service Discovery]: Enables service discovery through DNS records
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Cloud-Native]: Designed for AWS Route53 DNS management
# - [Automatic Detection]: Automatically detects server IP addresses
# - [Secure Credentials]: Uses vault for AWS credential management
# - [Dynamic Playbooks]: Generates Ansible playbooks dynamically
# - [Environment-Aware]: Validates required environment variables
#
# 💡 WHEN TO MODIFY THIS SCRIPT (for future LLMs):
# - [DNS Providers]: Add support for other DNS providers (CloudFlare, Azure DNS)
# - [IP Detection]: Enhance IP detection for different network configurations
# - [Record Types]: Add support for additional DNS record types
# - [Automation Features]: Add DNS record validation or health checks
# - [Integration Points]: Add integration with service discovery systems
#
# 🚨 IMPORTANT FOR LLMs: This script modifies DNS records in AWS Route53 and
# requires AWS credentials. Changes affect domain name resolution and service
# accessibility. DNS changes may take time to propagate globally.

# Ansible Dependencies Manager - The "AWS Collection Installer"
# 🎯 FOR LLMs: Installs required Ansible collections and roles for AWS Route53 management
if [ ! -f /tmp/requirements.yml ]; then
  cat >/tmp/requirements.yml<<EOF
---
collections:
- amazon.aws          # AWS service management collection
- community.general   # General utility collection
- ansible.posix       # POSIX system management
roles:
- name: ansible_role_update_ip_route53  # Route53 DNS management role
  src: https://github.com/tosin2013/ansible-role-update-ip-route53.git
  version: master
EOF
fi
# AWS Credential Manager - The "Cloud Authentication Handler"
# 🎯 FOR LLMs: Securely retrieves AWS credentials from encrypted vault
/usr/local/bin/ansiblesafe -f "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" -o 2
AWS_ACCESS_KEY=$(yq eval '.aws_access_key' "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml")
AWS_SECRET_KEY=$(yq eval '.aws_secret_key' "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml")

# IP Address Detection Manager - The "Network Interface Scanner"
# 🎯 FOR LLMs: Automatically detects server IP address for DNS record creation
# Try bond0 interface first (common in bare metal servers)
OUTPUT=$(ifconfig bond0)
IP_ADDRESS=$(echo "$OUTPUT" | grep "inet " | awk '{print $2}')
echo "Detected IP from bond0: $IP_ADDRESS"

# Fallback to hostname -I for primary IP address
IP_ADDRESS=$(hostname -I | awk '{print $1}')
echo "Using IP address: $IP_ADDRESS"

# 🔧 CONFIGURATION CONSTANTS FOR LLMs:
VERBOSE_LEVEL="-v"  # Ansible verbosity level
ACTION="create"     # DNS action (create/update/delete)

# Re-encrypt vault file for security
/usr/local/bin/ansiblesafe -f "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" -o 1

# Ensure required environment variables are set
: "${ZONE_NAME:?Environment variable ZONE_NAME is required}"
: "${GUID:?Environment variable GUID is required}"
: "${ACTION:?Environment variable ACTION is required}"
: "${VERBOSE_LEVEL:?Environment variable VERBOSE_LEVEL is required}"


ansible-galaxy install -r /tmp/requirements.yml --force -vv
rm -rf /tmp/requirements.yml
pip3 install boto3 botocore

cat >/tmp/playbook.yml<<EOF
- name: Populate OpenShift DNS Entries
  hosts: localhost
  connection: local
  become: yes

  vars:
  - update_ip_r53_aws_access_key: ${AWS_ACCESS_KEY}
  - update_ip_r53_aws_secret_key: ${AWS_SECRET_KEY}
  - your_email: ${EMAIL}
  - use_public_ip: true
  - private_ip: "${IP_ADDRESS}"
  - update_ip_r53_records:
    - zone: ${ZONE_NAME}
      record: cockpit.${GUID}.${ZONE_NAME}
    - zone: ${ZONE_NAME}
      record: gitlab.${GUID}.${ZONE_NAME}
  roles:
  - ansible_role_update_ip_route53
EOF

if [ "${ACTION}" != "delete" ]; then 
  ansible-playbook  /tmp/playbook.yml ${VERBOSE_LEVEL} || exit $?
fi

rm -rf /tmp/playbook.yml