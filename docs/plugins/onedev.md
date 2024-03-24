---
layout: default
title:  "OneDev - Git Server with CI/CD, Kanban, and Packages"
parent: Plugins
nav_order: 3
---

[https://onedev.io/](https://onedev.io/) is a Git server with full support for pull requests, code reviews, and continuous integration. It also provides a Kanban board, a wiki, and a package registry. It is a self-hosted alternative to GitHub, GitLab, and Bitbucket.

## Create OneDev Account on phyical server
`The ip address is the external ip address of the server`
* Example URL: http://192.168.1.100:6610
* Create Administrator Account
  * `Login Name` 
  * `Password` 
  * `Full Name` 
  * `Email Address`
![20240320092532](https://i.imgur.com/AIZ1pG6.png)
**Add IP address to URL**
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

* See [OneDev - Kcli Pipelines](../plugins/onedev-kcli-pipelines.html)
* For OpenShift Deployments see [OneDev - kcli-openshift4-baremetal Pipelines](../plugins/onedev-kcli-openshift4-baremetal.html)