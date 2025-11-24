---
layout: default
title:   "Deploying on Red Hat Product Demo System"
parent: Deployment Documentation
nav_order: 2
---

Deploy to [Red Hat Product Demo System](https://connect.redhat.com/en/training/product-demo-system) using the following steps.

> **Documentation status**
> - Validation: `IN PROGRESS` – Steps have been used in prior demo environments but may lag behind current platform changes.
> - Last reviewed: 2025-11-21
> - Community: If you run this successfully or need fixes, please contribute improvements via [Contributing to docs](../how-to/contribute.md).

**SSH into Equinix Metal baremetal**

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
export KVM_VERSION="0.8.0"
export CICD_ENVIORNMENT="gitlab" # or onedev change this vault for default cicd enviornment to deploy VMS
export DOMAIN=qubinodelab.io  # Change to your domain if you want to use your own domain
export USE_HASHICORP_VAULT='false'
export USE_HASHICORP_CLOUD='false'
export FORWARDER='1.1.1.1'
export ACTIVE_BRIDGE='false'
export INTERFACE=bond0
export USE_ROUTE53=true
export GIT_REPO=https://github.com/Qubinode/qubinode_navigator.git
export INVENTORY=rhel9-equinix
export SSH_PASSWORD=${SSH_PASSWORD}
EOF
$ vi notouch.env
```

**Recommned option: Setting Up Variables in HashiCorp Cloud Platform (HCP) Vault Secrets**
[Setting Up Variables in HashiCorp Cloud Platform (HCP) Vault Secrets](https://github.com/tosin2013/ansiblesafe/blob/main/docs/hashicorp_cloud_secret_setup.md)
```bash
$ SSH_PASSWORD=DontForgetToChangeMe # Use the password of the lab-user
$ DOMAIN=sandbox000.opentlc.com 
$ EMAIL=user@example.com # used for letsencrypt
$ GUID=your-guid
$ cat >notouch.env<<EOF
export SSH_USER=lab-user
export CICD_PIPELINE='true'
export ENV_USERNAME=lab-user
export KVM_VERSION="0.8.0"
export CICD_ENVIORNMENT="gitlab" # or onedev change this vault for default cicd enviornment to deploy VMS
export DOMAIN=${DOMAIN} # Change to your domain if you want to use your own domain
export FORWARDER='$(awk '/^nameserver/ {print $2}' /etc/resolv.conf | head -1)'
export ACTIVE_BRIDGE='false'
export INTERFACE=bond0
export EMAIL=${EMAIL}
export GUID=$GUID
export USE_ROUTE53=true
export ZONE_NAME=${DOMAIN}
export USE_HASHICORP_VAULT='true'
export USE_HASHICORP_CLOUD='true'
export GIT_REPO=https://github.com/Qubinode/qubinode_navigator.git
export INVENTORY=rhel9-equinix
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

**Run the following commands as lab-user**  
```bash
sudo dnf install -y tmux curl git vim 
curl -OL https://raw.githubusercontent.com/Qubinode/qubinode_navigator/main/rhel9-linux-hypervisor.sh 
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

After the Red Hat Product Demo System deployment is complete, you can use **Apache Airflow** and the AI Assistant to orchestrate and monitor end-to-end workflows instead of relying on OneDev-based pipelines.

### Orchestrate with Apache Airflow

- [Airflow Integration Overview](../AIRFLOW-INTEGRATION.md)
- [Airflow Integration Guide](../airflow-integration-guide.md)
- [DAG Deployment Workflows](../airflow-dag-deployment-workflows.md)
- [Airflow Community Ecosystem](../airflow-community-ecosystem.md)

These guides show how to:

- Deploy and manage DAGs for Qubinode Navigator
- Integrate with the AI Assistant for chat-driven workflow execution
- Build RAG-enabled workflows and continuous learning loops