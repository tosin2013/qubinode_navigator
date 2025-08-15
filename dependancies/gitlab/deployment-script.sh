#!/bin/bash

# =============================================================================
# GitLab Server Deployment - The "DevOps Platform Architect"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This script deploys a complete GitLab CE server with GitLab Runner in containerized
# environments using Ansible automation. It provides self-hosted Git repository management,
# CI/CD pipelines, and DevOps platform capabilities.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script implements GitLab platform deployment:
# 1. [PHASE 1]: Dependency Installation - Installs required Ansible collections
# 2. [PHASE 2]: Role Deployment - Clones and installs GitLab server Ansible role
# 3. [PHASE 3]: Configuration Generation - Creates dynamic configuration with secrets
# 4. [PHASE 4]: GitLab Deployment - Deploys GitLab CE server with SSL certificates
# 5. [PHASE 5]: Runner Installation - Installs and configures GitLab Runner
# 6. [PHASE 6]: Service Integration - Configures systemd services and firewall
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [DevOps Platform]: Provides Git repository hosting and CI/CD capabilities
# - [Container-First]: Uses containerized GitLab deployment per ADR-0001
# - [Vault Integration]: Uses AnsibleSafe for secure credential management
# - [SSL Integration]: Implements Let's Encrypt certificates for secure access
# - [CI/CD Integration]: Supports automated deployment pipelines
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Container-Native]: Uses Podman containers for GitLab server deployment
# - [Security-First]: Implements SSL certificates and secure credential management
# - [Self-Hosted]: Provides on-premises GitLab platform without external dependencies
# - [Automation-Ready]: Includes GitLab Runner for CI/CD pipeline execution
# - [Scalable Architecture]: Supports multiple projects and users
#
# 💡 WHEN TO MODIFY THIS SCRIPT (for future LLMs):
# - [GitLab Updates]: Update GitLab CE container image versions
# - [Security Enhancements]: Add additional security configurations or authentication
# - [Integration Features]: Add integration with external services or tools
# - [Performance Tuning]: Optimize container resources or database configuration
# - [Backup Solutions]: Add backup and disaster recovery capabilities
#
# 🚨 IMPORTANT FOR LLMs: This script deploys a complete GitLab platform with
# persistent data storage. It requires significant system resources and network
# configuration. Changes affect DevOps workflows and CI/CD pipeline functionality.

# Ansible Collection Manager - The "Dependency Installer"
# 🎯 FOR LLMs: Ensures required Ansible collections are available for GitLab deployment
if [ ! -f /tmp/requirements.yml ]; then
  cat >/tmp/requirements.yml<<EOF
---
collections:
- containers.podman  # Container management collection
- community.crypto   # SSL certificate management
- ansible.posix      # POSIX system management
EOF
fi

# Install collections with force update and verbose output
sudo ansible-galaxy install -r /tmp/requirements.yml --force -vv
ansible-galaxy install -r /tmp/requirements.yml --force -vv

# GitLab Role Manager - The "Platform Installer"
# 🎯 FOR LLMs: Clones and installs the GitLab server Ansible role for containerized deployment
if [ ! -d /opt/podman-gitlab-server-role ];
then
  cd /opt
  git clone https://github.com/tosin2013/ansible-podman-gitlab-server-role.git
  cd /opt/ansible-podman-gitlab-server-role
  cp -r podman-gitlab-server-role /etc/ansible/roles/
fi

# 📊 GLOBAL VARIABLES (GitLab configuration):
GILAB_SERVICE_ACCOUNT=gitlab  # Service account for GitLab processes
POSTGRES_PASSWORD=$(cat /dev/urandom | tr -dc 'A-Za-z0-9%+=-_' | fold -w 11 | head -n 1)  # Random PostgreSQL password
cat > /etc/ansible/roles/podman-gitlab-server-role/defaults/main.yml <<EOF
---
# Username Variables
gitlab_service_account: ${GILAB_SERVICE_ACCOUNT}
postgres_service_account: ${GILAB_SERVICE_ACCOUNT}
gitlab_service_account_uid: 1001
specific_user: lab-user

# Container Image Variables
gitlab_server_image_name: docker.io/gitlab/gitlab-ce:latest

# Container Name Variables
gitlab_server_name: gitlab_server

# GitLab Hostname
gitlab_server_hostname: gitlab

# Domain
domain: '.${GUID}.${DOMAIN}'
your_email: '${EMAIL}'
gitlab_postgres_password:  '${POSTGRES_PASSWORD}'

# Podman Ports
gitlab_container_ssl_port: '8443:8443/tcp'
gitlab_gui_ssl_port: '8443'
gitlab_container_ssh_port: '2222:22/tcp'

# FirewallD Ports
gitlab_firewall_ssl_port: '8443/tcp'
gitlab_firewall_ssh_port: '2222/tcp'

# GitLab Container Specific Variables
gitlab_server_restart_policy: always

# Use Let's Encrypt
letsencrypt_enabled: true
EOF

/usr/local/bin/ansiblesafe -f "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" -o 2
ansible-playbook /opt/ansible-podman-gitlab-server-role/playbooks/gitlab-mgmt.yml \
  --extra-vars  "@/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" \
  -t "initial_setup,create_gitlab" --skip-tags "custom_cert" || exit 1
/usr/local/bin/ansiblesafe -f "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" -o 1

if [ ! -f /usr/local/bin/gitlab-runner ];
then
  sudo curl -L --output /usr/bin/gitlab-runner https://gitlab-runner-downloads.s3.amazonaws.com/latest/binaries/gitlab-runner-linux-amd64
  sudo chmod +x /usr/bin/gitlab-runner
  sudo useradd --comment 'GitLab Runner' --create-home gitlab-runner --shell /bin/bash
  sudo /usr/bin/gitlab-runner install --user=gitlab-runner --working-directory=/home/gitlab-runner
  # cat /home/lab-user/.gitlab-runner/config.toml
  # sudo cp /home/lab-user/.gitlab-runner/config.toml /etc/gitlab-runner/config.toml
  # sudo systemctl start gitlab-runner.service
  # sudo systemctl enable gitlab-runner.service
  # sudo systemctl status gitlab-runner.service
fi