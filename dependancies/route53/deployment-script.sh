#!/bin/bash 

if [ ! -f /tmp/requirements.yml ]; then
  cat >/tmp/requirements.yml<<EOF
---
collections:
- amazon.aws
- community.general
- ansible.posix
roles: 
- name: ansible_role_update_ip_route53
  src: https://github.com/tosin2013/ansible-role-update-ip-route53.git
  version: master
EOF
fi
/usr/local/bin/ansiblesafe -f "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml" -o 2
AWS_ACCESS_KEY=$(yq eval '.aws_access_key' "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml")
AWS_SECRET_KEY=$(yq eval '.aws_secret_key' "/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml")
IP_ADDRESS=$(hostname -I | awk '{print $1}')
VERBOSE_LEVEL="-v"
ACTION="create"
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