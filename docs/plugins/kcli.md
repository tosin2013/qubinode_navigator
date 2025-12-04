______________________________________________________________________

## layout: default title:  "Kcli pipelines" parent: Plugins nav_order: 3

This tool is meant to provide a unified user experience when interacting with the following virtualization providers:

- `Libvirt/Vsphere/Kubevirt/Aws/Azure/Gcp/Ibmcloud/oVirt/Openstack/Packet/Proxmox`

Beyond handling virtual machines, Kubernetes clusters can also be managed for the following types:

- `Kubeadm/Openshift/OKD/Hypershift/Microshift/K3s`

Read more about kcli [here](https://kcli.readthedocs.io/en/latest/)

## Workflow Documents

- [Create KCLI profiles for multiple environments](https://github.com/tosin2013/kcli-pipelines/blob/main/docs/configure-kcli-profiles.md)
- [Deploy VM Workflow](https://github.com/tosin2013/kcli-pipelines/blob/main/docs/deploy-vm.md)

## How to deploy Vms

- [Deploy the freeipa-server-container on vm](https://github.com/tosin2013/kcli-pipelines/blob/main/docs/deploy-dns.md)
- [Deploy the mirror-registry on vm](https://github.com/tosin2013/kcli-pipelines/blob/main/docs/mirror-registry.md)
- [Deploy the microshift-demos on vm](https://github.com/tosin2013/kcli-pipelines/blob/main/docs/microshift-demos.md)
- [Deploy the device-edge-workshops on vm](https://github.com/tosin2013/kcli-pipelines/blob/main/docs/device-edge-workshops.md)
- [Deploy the openshift-jumpbox on vm](https://github.com/tosin2013/kcli-pipelines/blob/main/docs/openshift-jumpbox.md)
- [Deploy the Red Hat Ansible Automation Platform on vm](https://github.com/tosin2013/kcli-pipelines/blob/main/docs/ansible-aap.md)
- [Deploy the ubuntu on vm](https://github.com/tosin2013/kcli-pipelines/blob/main/docs/ubuntu.md)
- [Deploy the fedora on vm](https://github.com/tosin2013/kcli-pipelines/blob/main/docs/fedora.md)
- [Deploy the rhel9 on vm](https://github.com/tosin2013/kcli-pipelines/blob/main/docs/rhel.md)
- [Deploy the OpenShift 4 Disconnected Helper](https://github.com/tosin2013/kcli-pipelines/blob/main/docs/ocp4-disconnected-helper.md)

## How to deploy Vms using Gitlab pipelines

Edit and run the trigger pipeline to trigger a build.

![20230527093215](https://i.imgur.com/I9ERA5a.png)

```bash
$ vim trigger-pipeline.sh

TOKEN="GITLAB-TOKEN"
SSH_PASSWORD="MACHINE_PASSWORD"
TARGET_SERVER=equinix
SSH_HOST="192.168.1.25"
SSH_USER="lab-user"
ACTION=create #delete
```

Run the pipeline

```
$ ./trigger-pipeline.sh
```
