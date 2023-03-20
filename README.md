# Qubinode Navigator


[![ansible-lint](https://github.com/tosin2013/quibinode_navigator/actions/workflows/ansible-lint.yml/badge.svg)](https://github.com/tosin2013/quibinode_navigator/actions/workflows/ansible-lint.yml)
[![Generate Documentation](https://github.com/tosin2013/quibinode_navigator/actions/workflows/generate-documentation.yml/badge.svg)](https://github.com/tosin2013/quibinode_navigator/actions/workflows/generate-documentation.yml)

### How to build it
```
curl -OL https://raw.githubusercontent.com/tosin2013/quibinode_navigator/main/setup.sh
chmod +x setup.sh
./setup.sh
```

### How to use it
```
cd quibinode_navigator/
pip3 install -r requirements.txt
python3 load-variables.py
```


List inventory 
```
ansible-navigator inventory --list -m stdout --vault-password-file $HOME/.vault_password
```

Deploy KVM Host
```bash 
$ ssh-agent bash
$ ssh-add ~/.ssh/id_rsa
$ cd $HOME/qubinode_navigator
$ ansible-navigator run ansible-navigator/setup_kvmhost.yml \
 --vault-password-file $HOME/.vault_password -m stdout 
```

Configure commands 
```bash 
./bash-aliases/setup-commands.sh
```

Configure KCLI for VMs
```bash
source ~/.bash_aliases
kcli-utils setup
kcli-utils configure-images
kcli-utils check-kcli-plan
```

Configure FreeIPA
```bash
source ~/.bash_aliases  
    
```

Links: 
* https://gitlab.com/cjung/ansible-ee-intro/-/blob/main/ansible-navigator/httpd.yml
* https://redhat-cop.github.io/agnosticd/
