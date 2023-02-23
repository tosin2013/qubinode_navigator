# Qubinode Navigator



### How to build it

Git Clone Repo
```
git clone https://github.com/tosin2013/quibinode_navigator.git

cd quibinode_navigator/
```

Configure SSH 
```
IP_ADDRESS=$(hostname -I | awk '{print $1}')
ssh-keygen -f ~/.ssh/id_rsa -t rsa -N ''
ssh-copy-id $USER@${IP_ADDRESS}
```

Install Ansible Navigator
```bash
make install-ansible-navigator
```

If you use Red Hat Enterprise Linux with an active Subscription, you might have to lo log into the registry first:

```bash
make podman-login
```

Copy navigator 
```bash
make copy-navigator
```


Build the image:
**update the tag in the make file to update release**
```bash
make build-image
```

Configure Ansible Vault
```bash
curl -OL https://gist.githubusercontent.com/tosin2013/022841d90216df8617244ab6d6aceaf8/raw/92400b9e459351d204feb67b985c08df6477d7fa/ansible_vault_setup.sh
chmod +x ansible_vault_setup.sh
./ansible_vault_setup.sh
```

Install and configure ansible safe
```bash
dnf install ansible-core -y 
curl -OL https://github.com/tosin2013/ansiblesafe/releases/download/v0.0.4/ansiblesafe-v0.0.4-linux-amd64.tar.gz
tar -zxvf ansiblesafe-v0.0.4-linux-amd64.tar.gz
chmod +x ansiblesafe-linux-amd64 
sudo mv ansiblesafe-linux-amd64 /usr/local/bin/ansiblesafe
ansiblesafe -f /home/admin/quibinode_navigator/inventories/localhost/group_vars/control/vault.yml
```

List inventory 
```
 ansible-navigator inventory --list -m stdout --vault-password-file $HOME/.vault_password
```

Deploy KVM Host
```
ansible-navigator run ansible-navigator/setup_kvmhost.yml \
 --vault-password-file $HOME/.vault_password -m stdout 
```

Links: 
https://gitlab.com/cjung/ansible-ee-intro/-/blob/main/ansible-navigator/httpd.yml
https://redhat-cop.github.io/agnosticd/
