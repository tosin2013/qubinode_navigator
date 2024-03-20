---
layout: default
title:   "Deploying on Hetzner"
parent: Deployment Documentation
nav_order: 2
---

Deploy to [Hetzner](https://www.hetzner.com/) using the following steps.

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

## Before running pipeline create /tmp/config.yml as lab-user
```bash
$ vi /tmp/config.yml
rhsm_username: rheluser
rhsm_password: rhelpassword
rhsm_org: orgid
rhsm_activationkey: activationkey
admin_user_password: password # Change to the lab-user password
offline_token: offlinetoken 
openshift_pull_secret: pullsecret
freeipa_server_admin_password: password # Change to the lab-user password
xrdp_remote_user: remoteuser
xrdp_remote_user_password: password
```

## Add the following to .bashrc as lab-user
```bash
$ SSH_PASSOWRD='DontForgetToChangeMe'
$ cat >notouch.env<<EOF
export SSH_USER=lab-user
export CICD_PIPELINE='true'
export ENV_USERNAME=lab-user
export DOMAIN=qubinodelab.io  # Change to your domain if you want to use your own domain
export FORWARDER='1.1.1.1'
export ACTIVE_BRIDGE='false'
export INTERFACE=enp4s0
export GIT_REPO=https://github.com/tosin2013/qubinode_navigator.git
export INVENTORY=hetzner
export TARGET_SERVER=${INVENTORY}
export SSH_PASSWORD=${SSH_PASSOWRD}
EOF
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

## Access the Server GUI
```
IP_ADDRESS=192.168.1.100
xfreerdp /v:${IP_ADDRESS}:3389 /u:remoteuser
```
You may also use Remmina or any other RDP client to access the server.

![alt text](image.png)

See [OneDev - Git Server with CI/CD, Kanban, and Packages](../plugins/onedev.html) 