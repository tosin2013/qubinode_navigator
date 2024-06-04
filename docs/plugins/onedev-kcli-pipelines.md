---
layout: default
title:  "OneDev - Git Server with CI/CD, Kanban, and Packages"
parent: Plugins
nav_order: 3
---

[https://onedev.io/](https://onedev.io/) is a Git server with full support for pull requests, code reviews, and continuous integration. It also provides a Kanban board, a wiki, and a package registry. It is a self-hosted alternative to GitHub, GitLab, and Bitbucket.

## Create OneDev Account on physical server
`The ip address is the external ip address of the server`
* Example URL: http://192.168.1.100:6610
* Create Administrator Account
  * `Login Name` 
  * `Password` 
  * `Full Name` 
  * `Email Address`
![20240320092532](https://i.imgur.com/AIZ1pG6.png)
**Add External IP address to URL**
![20240320092812](https://i.imgur.com/zMKVwrq.png)

# Add a agent for build pipelines 
*Switch to root*
```
sudo su -
cd /opt/qubinode_navigator/
```
*Run the agent*
```
./dependancies/onedev/configure-onedev-agent.sh
```
**After Script has ran you will see the agent as avaiable**
* Example Url: http://192.168.1.100:6610/~administration/agents
  * `Menu > Administration > Agents` 
![20240320095643](https://i.imgur.com/kAG9jX4.png)

**Add Job Executor**
* Type: `Remote Shell Executor`
* Name: `default-executor`
![20240320095851](https://i.imgur.com/BCMbk87.png)
![20240320100009](https://i.imgur.com/CfcrhHh.png)


# You can now run the following pipelines 

### OneDev - Deploying Generic VMs
- **Deploying Generic VMs**: Guide for deploying generic VMs using OneDev.
  - [OneDev - Deploying Generic VMs](plugins/onedev-generic-vm.html)

### OneDev - Agent Based Installer Pipelines
- **External Deployment**: Guide for deploying OpenShift using OneDev's agent-based installer pipelines for external environments.
  - [OneDev - Agent based Installer Pipelines - External Deployment](plugins/onedev-agent-based-external-deployment.html)
- **Internal Deployment**: Instructions for deploying OpenShift using OneDev's agent-based installer pipelines for internal environments.
  - [OneDev - Agent based Installer Pipelines - Internal Deployment](plugins/onedev-agent-based-internal-deployment.html)

### OneDev - kcli-openshift4-baremetal Pipelines
- **Externally**: Steps to deploy OpenShift 4 on baremetal using kcli pipelines for external environments.
  - [OneDev - kcli-openshift4-baremetal Pipelines Externally](plugins/onedev-kcli-openshift4-baremetal-external.html)
- **Internally**: Steps to deploy OpenShift 4 on baremetal using kcli pipelines for internal environments.
  - [OneDev - Agent based Installer Pipelines - Internal Deployment](plugins/onedev-kcli-openshift4-baremetal-internal.html)

### Deploy Step CA Server using Kcli Pipelines
Detailed guide on deploying a Step CA server using Kcli pipelines.
  - [Deploy Step CA Server using Kcli Pipelines](plugins/onedev-kcli-pipelines-step-ca-server.html)