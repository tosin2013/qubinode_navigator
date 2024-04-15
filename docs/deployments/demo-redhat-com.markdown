---
layout: default
title:   "Deploying on Red Hat Product Demo System"
parent: Deployment Documentation
nav_order: 2
---

Deploy to [Red Hat Product Demo System](https://connect.redhat.com/en/training/product-demo-system) using the following steps.

**SSH into Equinix Metal baremetal**

**create /tmp/config.yml as lab-user**  
`you can uae ansiblesafe to generate the content of this file` - [link](https://github.com/tosin2013/ansiblesafe) 
```
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
**Add the following to .bashrc as lab-user**
```
$ SSH_PASSWORD=DontForgetToChangeMe # Use the password of the lab-user
$ cat >notouch.env<<EOF
export SSH_USER=lab-user
export CICD_PIPELINE='true'
export ENV_USERNAME=lab-user
export DOMAIN=qubinodelab.io  # Change to your domain if you want to use your own domain
export FORWARDER='1.1.1.1'
export ACTIVE_BRIDGE='false'
export INTERFACE=bond0
export GIT_REPO=https://github.com/tosin2013/qubinode_navigator.git
export INVENTORY=rhel8-equinix
export SSH_PASSWORD=${SSH_PASSWORD}
EOF
```

**Run the following commands as lab-user**  
```
# sudo dnf install -y tmux curl
# git clone https://github.com/gpakosz/.tmux.git
# ln -s -f .tmux/.tmux.conf
# cp .tmux/.tmux.conf.local .
# curl -OL https://raw.githubusercontent.com/tosin2013/qubinode_navigator/main/rhel8-linux-hypervisor.sh 
# chmod +x rhel8-linux-hypervisor.sh
# tmux new-session -d -s rhel8-linux-hypervisor 'source notouch.env && sudo -E  ./rhel8-linux-hypervisor.sh'
# tmux attach -t rhel8-linux-hypervisor
```

*The install will fail on the first time to re-run un the following below*
```
source notouch.env && sudo -E  ./rhel8-linux-hypervisor.sh
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

Once deployment is complete you can run [kcli](https://kcli.readthedocs.io/en/latest/) commands or go to [kcli-pipelines](https://github.com/tosin2013/kcli-pipelines) repo to run vms. 
```
$ kcli --help
```

**RDP into Server on  Red Hat Product Demo System**  
Login via RDP using the remote user and password you set in the config.yml file.  

![20230610101107](https://i.imgur.com/DjPE6NR.png)

`You can also use Remmina to login to the VM`

See [OneDev - Git Server with CI/CD, Kanban, and Packages](../plugins/onedev.html) 

## Post Steps 
* Configure Onedev for CI/CD - [OneDev - Git Server with CI/CD, Kanban, and Packages](../plugins/onedev.html)
* Deploy FreeIPA and other VMs - [FreeIPA - Identity Management](../plugins/onedev-kcli-pipelines.html) 
* Deploy OpenShift on KVM - [OpenShift - KVM](../plugins/onedev-kcli-openshift4-baremetal.html)
