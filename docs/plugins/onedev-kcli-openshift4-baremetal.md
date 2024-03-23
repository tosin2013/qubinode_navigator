---
layout: default
title:  "OneDev - kcli-openshift4-baremetal Pipelines"
parent: Plugins
nav_order: 3
---

This repository provides a plan which deploys a vm where:

* openshift-baremetal-install is downloaded with the specific version and tag specified (and renamed openshift-install)
* stop the nodes to deploy through redfish
* launch the install against a set of baremetal nodes. Virtual ctlplanes and workers can also be deployed


# Prerequisites
* [OneDev - Kcli Pipelines](../plugins/onedev-kcli-pipelines.md)  - is configured and running. 
  
Git Repo: [https://github.com/karmab/kcli-openshift4-baremetal](https://github.com/karmab/kcli-openshift4-baremetal)

*Click on `import`*
![20240320093529](https://i.imgur.com/1b3zrpr.png)
*Click on `From URL`*
![20240320093616](https://i.imgur.com/pwPpEx0.png)
*Click on `Import` using kcli pipelines repo*
![20240320093704](https://i.imgur.com/EZTDdm5.png)
*click on the `tosin2013/kcli-pipelines.git` to view repos*
![20240320093809](https://i.imgur.com/MgdGkEN.png)

![20240320093959](https://i.imgur.com/pVvwaTR.png)

# Start Job 
**Click .onedev-buildspec.yml**
 ![20240320100513](https://i.imgur.com/NtvjpQv.png)

*Click on `Deploy VM` - Deploy FreeIPA VM first this will allow you to deploy the other vms*
![20240320100623](https://i.imgur.com/kigo2L3.png)

**Current List of Deployable VMs after FreeIPA Deployment**
![20240320101445](https://i.imgur.com/IXsGQg3.png)