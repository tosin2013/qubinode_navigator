---
layout: default
title:   "Deploying on Hetzner"
parent: Deployment Documentation
nav_order: 2
---

Deploy to [Hetzner](https://www.hetzner.com/) using the following steps.
**Tested on**
* Rocky Linux 9

**Activate Rocky linux**
![alt text](<Screenshot from 2024-03-20 15-09-38-new.png>)

**SSH into Hetzner baremetal server**

## Create lab-user 
```bash
curl -OL https://gist.githubusercontent.com/tosin2013/385054f345ff7129df6167631156fa2a/raw/b67866c8d0ec220c393ea83d2c7056f33c472e65/configure-sudo-user.sh
chmod +x configure-sudo-user.sh
./configure-sudo-user.sh lab-user
```

## SSH into the lab-user
```bash
sudo su - lab-user
```


**Configure SSH**
```
IP_ADDRESS=$(hostname -I | awk '{print $1}')
ssh-keygen -f ~/.ssh/id_rsa -t rsa -N ''
ssh-copy-id lab-user@${IP_ADDRESS}
```

**create /tmp/config.yml as lab-user**   
`you can uae ansiblesafe to generate the content of this file` - [link](https://github.com/tosin2013/ansiblesafe)   
[Ansible Vault Secrets Documentation](https://dev.to/tosin2013/ansible-vault-secrets-documentation-3g1a)

```bash
$ vi /tmp/config.yml
rhsm_username: rheluser
rhsm_password: rhelpassword
rhsm_org: orgid
rhsm_activationkey: activationkey
admin_user_password: password # Change to the lab-user password
offline_token: offlinetoken
openshift_pull_secret: pullsecret
automation_hub_offline_token: automationhubtoken
freeipa_server_admin_password: password # Change to the lab-user password
xrdp_remote_user: remoteuser
xrdp_remote_user_password: password
aws_access_key: accesskey # optional used for aws credentials and route53
aws_secret_key: secretkey # optional used for aws credentials and route53
```

**Add the following to .bashrc as lab-user when using /tmp/config.yml file**
```bash
$ SSH_PASSWORD=DontForgetToChangeMe # Use the password of the lab-user
$ cat >notouch.env<<EOF
export SSH_USER=lab-user
export CICD_PIPELINE='true'
export ENV_USERNAME=lab-user
export CICD_ENVIORNMENT="gitlab" # or onedev change this vault for default cicd enviornment to deploy VMS
export DOMAIN=qubinodelab.io  # Change to your domain if you want to use your own domain
export USE_HASHICORP_CLOUD='false' 
export FORWARDER='1.1.1.1'
export ACTIVE_BRIDGE='false'
export INTERFACE=bond0
export USE_ROUTE53=true
export GIT_REPO=https://github.com/tosin2013/qubinode_navigator.git
export INVENTORY=hetzner
export SSH_PASSWORD=${SSH_PASSWORD}
EOF
$ vi notouch.env
```

**Recommned Option: Setting Up Variables in HashiCorp Cloud Platform (HCP) Vault Secrets**
[Setting Up Variables in HashiCorp Cloud Platform (HCP) Vault Secrets](https://github.com/tosin2013/ansiblesafe/blob/main/docs/hashicorp_cloud_secret_setup.md)
```bash
$ SSH_PASSWORD=DontForgetToChangeMe # Use the password of the lab-user
$ cat >notouch.env<<EOF
export SSH_USER=lab-user
export CICD_PIPELINE='true'
export ENV_USERNAME=lab-user
export CICD_ENVIORNMENT="gitlab" # or onedev change this vault for default cicd enviornment to deploy VMS
export DOMAIN=qubinodelab.io  # Change to your domain if you want to use your own domain
export ZONE_NAME=${DOMAIN}
export EMAIL=user@example.com
export USE_HASHICORP_CLOUD='true'
export FORWARDER='1.1.1.1'
export ACTIVE_BRIDGE='false'
export INTERFACE=bond0
export USE_ROUTE53=true
export GIT_REPO=https://github.com/tosin2013/qubinode_navigator.git
export INVENTORY=hetzner
export SSH_PASSWORD=${SSH_PASSWORD}
export HCP_CLIENT_ID="your-client-id"
export HCP_CLIENT_SECRET="your-client-secret"
export HCP_ORG_ID="your-org-id"
export HCP_PROJECT_ID="your-project-id"
export APP_NAME="appname"
export OLLAMA_WORKLOAD="false"
EOF
$ vi notouch.env
```

## Run the following commands as lab-user
```bash
sudo dnf install -y tmux curl git vim 
git clone https://github.com/gpakosz/.tmux.git
ln -s -f .tmux/.tmux.conf
cp .tmux/.tmux.conf.local .
curl -OL https://raw.githubusercontent.com/tosin2013/qubinode_navigator/main/rocky-linux-hetzner.sh
chmod +x rocky-linux-hetzner.sh
tmux new-session -s rocky-linux-hetzner
source notouch.env && sudo -E  ./rocky-linux-hetzner.sh
```


**ssh into vm and run the following**
```
$ sudo kcli download image rhel8
$ sudo kcli download image rhel9
```

When the prompt below comes up follow the link and look for the corresponding rhel release.
![20230607131855](https://i.imgur.com/MaFsUau.png)
right click on the link and copy the link address
![20230607131930](https://i.imgur.com/83Gar1k.png)


## To Access the Baremetal Node 
**Option 1: Access the VM via the console**

Login to the VM using ssh or cockpit console. The endpoint will be `https://SERVER_ADDRESS:9090` and the username and password are the same as the lab-user password you set in the config.yml file.
![20240531101946](https://i.imgur.com/YuPbVpO.png)

**Option 2: Access the Server GUI**
```
IP_ADDRESS=192.168.1.100
xfreerdp /v:${IP_ADDRESS}:3389 /u:remoteuser
```
You may also use Remmina or any other RDP client to access the server.

![alt text](image.png)
![alt text](<Screenshot from 2024-03-20 18-06-28.png>)

See [OneDev - Git Server with CI/CD, Kanban, and Packages](../plugins/onedev-kcli-pipelines.html) 