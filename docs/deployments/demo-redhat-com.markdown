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
[Ansible Vault Secrets Documentation](https://dev.to/tosin2013/ansible-vault-secrets-documentation-3g1a)

```
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
**Add the following to .bashrc as lab-user**
```
$ SSH_PASSWORD=DontForgetToChangeMe # Use the password of the lab-user
$ cat >notouch.env<<EOF
export SSH_USER=lab-user
export CICD_PIPELINE='true'
export ENV_USERNAME=lab-user
export CICD_ENVIORNMENT="gitlab" # or onedev change this vault for default cicd enviornment to deploy VMS
export DOMAIN=qubinodelab.io  # Change to your domain if you want to use your own domain
export FORWARDER='1.1.1.1'
export ACTIVE_BRIDGE='false'
export INTERFACE=bond0
export GIT_REPO=https://github.com/tosin2013/qubinode_navigator.git
export INVENTORY=rhel9-equinix
export SSH_PASSWORD=${SSH_PASSWORD}
EOF
```

**Run the following commands as lab-user**  
```
sudo dnf install -y tmux curl git
curl -OL https://raw.githubusercontent.com/tosin2013/qubinode_navigator/main/rhel9-linux-hypervisor.sh 
chmod +x rhel9-linux-hypervisor.sh
tmux new-session -s rhel9-linux-hypervisor 
source notouch.env && sudo -E  ./rhel9-linux-hypervisor.sh
```

*The install will fail on the first time to re-run un the following below*
```
source notouch.env && sudo -E  ./rhel9-linux-hypervisor.sh
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

## To Access the Baremetal Node 
**Option 1: Access the VM via the console**  
Login to the VM using ssh or cockpit console. The endpoint will be `https://SERVER_ADDRESS:9090` and the username and password are the same as the lab-user password you set in the config.yml file.
![20240531095517](https://i.imgur.com/Z9WimBp.png)

**Option 2: RDP into Server on  Red Hat Product Demo System**  
Login via RDP using the remote user and password you set in the config.yml file.  

![20230610101107](https://i.imgur.com/DjPE6NR.png)

`You can also use Remmina to login to the VM`

## Post Steps 
* Configure Onedev for CI/CD - [OneDev - Git Server with CI/CD, Kanban, and Packages](../plugins/onedev-kcli-pipelines.html)

### OneDev - Deploying Generic VMs
- **Deploying Generic VMs**: Guide for deploying generic VMs using OneDev.
  - [OneDev - Deploying Generic VMs](../plugins/onedev-generic-vm.html)

### OneDev - Agent Based Installer Pipelines
- **External Deployment**: Guide for deploying OpenShift using OneDev's agent-based installer pipelines for external environments.
  - [OneDev - Agent based Installer Pipelines - External Deployment](../plugins/onedev-agent-based-external-deployment.html)
- **Internal Deployment**: Instructions for deploying OpenShift using OneDev's agent-based installer pipelines for internal environments.
  - [OneDev - Agent based Installer Pipelines - Internal Deployment](../plugins/onedev-agent-based-internal-deployment.html)

### OneDev - kcli-openshift4-baremetal Pipelines
- **Externally**: Steps to deploy OpenShift 4 on baremetal using kcli pipelines for external environments.
  - [OneDev - kcli-openshift4-baremetal Pipelines Externally](../plugins/onedev-kcli-openshift4-baremetal-external.html)
- **Internally**: Steps to deploy OpenShift 4 on baremetal using kcli pipelines for internal environments.
  - [OneDev - Agent based Installer Pipelines - Internal Deployment](../plugins/onedev-kcli-openshift4-baremetal-internal.html)

### Deploy Step CA Server using Kcli Pipelines
Detailed guide on deploying a Step CA server using Kcli pipelines.
  - [Deploy Step CA Server using Kcli Pipelines](../plugins/onedev-kcli-pipelines-step-ca-server.html)