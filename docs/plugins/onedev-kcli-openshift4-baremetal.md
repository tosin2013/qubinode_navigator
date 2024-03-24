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
* [OneDev - Kcli Pipelines](../plugins/onedev-kcli-pipelines.html)  - is configured and running.  

**ssh into vm and run the following**
```
$ sudo kcli download image rhel8
$ sudo kcli download image rhel9
```
  
Reference Git Repo: [https://github.com/karmab/kcli-openshift4-baremetal](https://github.com/karmab/kcli-openshift4-baremetal)

## Configure pipelines
Git Repo: [https://github.com/tosin2013/kcli-pipelines.git](https://github.com/tosin2013/kcli-pipelines.git)

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
![20240323193344](https://i.imgur.com/mi3udC6.png)

*Click on `kcli-openshift4-baremetal` - Deploy OpenShift on KVM*
![20240323193525](https://i.imgur.com/ZmyBOo6.png)
![20240323193635](https://i.imgur.com/qOR2ZO9.png)

**Wait for deployment to complete it should take 45 minutes to 1 hour**
![20240323194135](https://i.imgur.com/dsLFUqO.png)

![20240323213443](https://i.imgur.com/NnqvNFx.png)


*Click on `Deploy VM` - Deploy FreeIPA VM first this will allow you to access the vms*
![20240320100623](https://i.imgur.com/kigo2L3.png)

**Configure DNS**
```
$ /opt/kcli-pipelines/configure-dns.sh
```

**SSH into the bastion node to get the kubeconfig**
```
ssh admin@baremetalhost.com
```

**ssh into jump host**
```
sudo kcli list vms
sudo kcli ssh lab-installer
[centos@lab-installer ~]$ sudo su -
[root@lab-installer ~]# ls
bin                  machineconfigs  openshift_pull.json  version.txt
cluster_ready.txt    manifests       original-ks.cfg
install-config.yaml  ocp             scripts
[root@lab-installer ~]# cat ocp/.openshift_install.log
```


