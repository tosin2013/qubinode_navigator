
Developers Guide
=============

## Getting Started


**Git Clone Repo**
```
git clone https://github.com/tosin2013/qubinode_navigator.git

cd $HOME/qubinode_navigator/
```

**Configure SSH**
```
IP_ADDRESS=$(hostname -I | awk '{print $1}')
ssh-keygen -f ~/.ssh/id_rsa -t rsa -N ''
ssh-copy-id $USER@${IP_ADDRESS}
```

**Install Ansible Navigator**
```bash
make install-ansible-navigator
```

**If you use Red Hat Enterprise Linux with an active Subscription, you might have to lo log into the registry first:**

```bash
make podman-login
```

**Create Ansible navigator config file**
```
# export INVENTORY=supermicro
# cat >~/.ansible-navigator.yml<<EOF
---
ansible-navigator:
  ansible:
    inventory:
      entries:
      - /home/admin/qubinode_navigator/inventories/${INVENTORY}
  execution-environment:
    container-engine: podman
    enabled: true
    environment-variables:
      pass:
      - USER
    image:  localhost/qubinode-installer:0.1.0
    pull:
      policy: missing
  logging:
    append: true
    file: /tmp/navigator/ansible-navigator.log
    level: debug
  playbook-artifact:
    enable: false
EOF
```

**Add hosts file**
```
# control_user=admin
# control_host=$(hostname -I | awk '{print $1}')
echo "[control]" > inventories/${INVENTORY}/hosts
echo "control ansible_host=${control_host} ansible_user=${control_user}" >> inventories/${INVENTORY}/hosts
```

**Create Requirement file for ansible builder** 
```
cat >ansible-builder/requirements.yml<<EOF
---
collections:
  - ansible.posix
  - containers.podman
  - community.general
  - community.libvirt
  - fedora.linux_system_roles
  - name: https://github.com/Qubinode/qubinode_kvmhost_setup_collection.git
    type: git
    version: main
roles: 
  - linux-system-roles.network
  - linux-system-roles.firewall
  - linux-system-roles.cockpit
EOF
```


**Build the image:**
```bash
make build-image
```

**Configure Ansible Vault**
```bash
curl -OL https://gist.githubusercontent.com/tosin2013/022841d90216df8617244ab6d6aceaf8/raw/92400b9e459351d204feb67b985c08df6477d7fa/ansible_vault_setup.sh
chmod +x ansible_vault_setup.sh
./ansible_vault_setup.sh
```

**Install and configure ansible safe**
```bash
curl -OL https://github.com/tosin2013/ansiblesafe/releases/download/v0.0.6/ansiblesafe-v0.0.6-linux-amd64.tar.gz
tar -zxvf ansiblesafe-v0.0.6-linux-amd64.tar.gz
chmod +x ansiblesafe-linux-amd64 
sudo mv ansiblesafe-linux-amd64 /usr/local/bin/ansiblesafe

# export INVENTORY=supermicro
# ansiblesafe -f /home/${USER}/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml
# ansiblesafe -f /root/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml
```


**Configure additional variables**
```
pip3 install -r requirements.txt
python3 load-variables.py
```

**List inventory**
```
ansible-navigator inventory --list -m stdout --vault-password-file $HOME/.vault_password
```

**Deploy KVM Host**
```
$ ssh-agent bash
$ ssh-add ~/.ssh/id_rsa
$ ansible-navigator run ansible-navigator/setup_kvmhost.yml \
 --vault-password-file $HOME/.vault_password -m stdout 
```

When developing a new collection, you can use the following command to build the collection and install it in the execution environment:
```
make build-image
```

When you are done developing, you can remove the images and bad builds with the following commands:
```
make remove-bad-builds
make remove-images
```