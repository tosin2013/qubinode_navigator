#!/bin/bash 

if [ ! -f /tmp/requirements.yml ]; then
  cat >/tmp/requirements.yml<<EOF
---
collections:
- containers.podman
- community.crypto
- ansible.posix
EOF
fi

if [ ! -d /opt/ansible/roles/podman-gitlab-server-role ];
then
  git clone https://github.com/tosin2013/ansible-podman-gitlab-server-role.git
  cd /opt/ansible-podman-gitlab-server-role
  cp -r podman-gitlab-server-role /etc/ansible/roles/
  cp /opt/ansible-podman-gitlab-server-role/playbooks/gitlab-mgmt.yml $HOME 
fi
GILAB_SERVICE_ACCOUNT=gitlab
cat > /etc/ansible/roles/podman-gitlab-server-role/defaults/main.yml <<EOF
---
# Username Variables
gitlab_service_account: ${GILAB_SERVICE_ACCOUNT}
gitlab_service_account_uid: 1001

# Container Image Variables
gitlab_server_image_name: gitlab/gitlab-ce:latest

# Container Name Variables
gitlab_server_name: gitlab_server

# GitLab Hostname
gitlab_server_hostname: gitlab

# Domain
domain: '${DOMAIN}'

# Podman Ports
gitlab_container_ssl_port: '8443:8443/tcp'
gitlab_gui_ssl_port: '8443'
gitlab_container_ssh_port: '2222:22/tcp'

# FirewallD Ports
gitlab_firewall_ssl_port: '8443/tcp'
gitlab_firewall_ssh_port: '2222/tcp'

# GitLab Container Specific Variables
gitlab_server_restart_policy: always
EOF

ansible-playbook gitlab-mgmt.yml
