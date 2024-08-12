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

sudo ansible-galaxy install -r /tmp/requirements.yml --force -vv
ansible-galaxy install -r /tmp/requirements.yml --force -vv

if [ ! -d /opt/podman-gitlab-server-role ];
then
  cd /opt
  git clone https://github.com/tosin2013/ansible-podman-gitlab-server-role.git
  cd /opt/ansible-podman-gitlab-server-role
  cp -r podman-gitlab-server-role /etc/ansible/roles/
fi
GILAB_SERVICE_ACCOUNT=gitlab
cat > /etc/ansible/roles/podman-gitlab-server-role/defaults/main.yml <<EOF
---
# Username Variables
gitlab_service_account: ${GILAB_SERVICE_ACCOUNT}
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

# Podman Ports
gitlab_container_ssl_port: '8443:8443/tcp'
gitlab_gui_ssl_port: '8443'
gitlab_container_ssh_port: '2222:22/tcp'

# FirewallD Ports
gitlab_firewall_ssl_port: '8443/tcp'
gitlab_firewall_ssh_port: '2222/tcp'

# GitLab Container Specific Variables
gitlab_server_restart_policy: always

# Let's Encrypt Enabled
letsencrypt_enabled: true
EOF

/usr/local/bin/ansiblesafe -f "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" -o 2
ansible-playbook /opt/ansible-podman-gitlab-server-role/playbooks/gitlab-mgmt.yml --extra-vars  "@/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" || exit 1
/usr/local/bin/ansiblesafe -f "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" -o 1

if [ ! -f /usr/local/bin/gitlab-runner ];
then
  sudo curl -L --output /usr/local/bin/gitlab-runner https://gitlab-runner-downloads.s3.amazonaws.com/latest/binaries/gitlab-runner-linux-amd64
  sudo chmod +x /usr/local/bin/gitlab-runner
  sudo useradd --comment 'GitLab Runner' --create-home gitlab-runner --shell /bin/bash
  sudo /usr/local/bin/gitlab-runner install --user=gitlab-runner --working-directory=/home/gitlab-runner
  sudo /usr/local/bin/gitlab-runner start
fi