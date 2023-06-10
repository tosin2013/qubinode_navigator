# Qubinode Navigator
This repository contains a quickstart script setup.sh to set up and configure Qubinode Navigator. Qubinode Navigator helps to automate the deployment and management of virtual machines, containers, and other infrastructure resources.

[![ansible-lint](https://github.com/tosin2013/qubinode_navigator/actions/workflows/ansible-lint.yml/badge.svg)](https://github.com/tosin2013/qubinode_navigator/actions/workflows/ansible-lint.yml)
[![Generate Documentation](https://github.com/tosin2013/qubinode_navigator/actions/workflows/generate-documentation.yml/badge.svg)](https://github.com/tosin2013/qubinode_navigator/actions/workflows/generate-documentation.yml)

## Prerequisites
* Linux-based operating system (RHEL 9.2, CentOS, Rocky Linux, or Fedora)
* Git

## Quickstart 

### Running on RHEL, CentOS, or Fedora
```
curl https://raw.githubusercontent.com/tosin2013/qubinode_navigator/main/setup.sh | bash
```
### Running on Rocky Linux on RHPDS using tmux
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
remote_user_password: password
```
**Add the following to .bashrc as lab-user**
```
$ SSH_PASSOWRD=DontForgetToChangeMe
$ cat >notouch.env<<EOF
export SSH_USER=lab-user
export CICD_PIPELINE='true'
export ENV_USERNAME=lab-user
export DOMAIN=qubinodelab.io  # Change to your domain if you want to use your own domain
export FORWARDER='1.1.1.1'
export ACTIVE_BRIDGE='false'
export INTERFACE=bond0
export GIT_REPO=https://github.com/tosin2013/qubinode_navigator.git
export INVENTORY=equinix
export SSH_PASSWORD=${SSH_PASSOWRD}
EOF
```

**Run the following commands as lab-user**  
```
# sudo dnf install -y tmux curl
# git clone https://github.com/gpakosz/.tmux.git
# ln -s -f .tmux/.tmux.conf
# cp .tmux/.tmux.conf.local .
# curl -OL https://raw.githubusercontent.com/tosin2013/qubinode_navigator/main/rocky-linux-hypervisor.sh 
# chmod +x rocky-linux-hypervisor.sh 
# tmux new-session -d -s rocky-linux-hypervisor 'source notouch.env && sudo -E  ./rocky-linux-hypervisor.sh'
# tmux attach -t rocky-linux-hypervisor
```

*The install will fail on the first time to re-run un the following below*
```
source notouch.env && sudo -E  ./rocky-linux-hypervisor.sh
```

When the prompt below comes up follow the link and look for the corresponding rhel release.
![20230607131855](https://i.imgur.com/MaFsUau.png)
right click on the link and copy the link address
![20230607131930](https://i.imgur.com/83Gar1k.png)

Once deployment is complete you can run [kcli](https://kcli.readthedocs.io/en/latest/) commands or go to [kcli-pipelines](https://github.com/tosin2013/kcli-pipelines) repo to run vms. 
```
$ kcli --help
```

**Rocky Linux on RHPDS Post Steps**  
Login via RDP using the remote user and password you set in the config.yml file.  

![20230610101107](https://i.imgur.com/DjPE6NR.png)

`You can also use Remmina to login to the VM`

**ssh into vm and run the following**
```
$ sudo kcli download image rhel8
$ sudo kcli download image rhel9
```
## Running from Git Repository
![20230414005208](https://i.imgur.com/ekBytuN.png)

![20230414005443](https://i.imgur.com/eiV8NNM.png)

Follow these instructions to run the setup.sh script:

1. Open a terminal window.

2. Clone the qubinode_navigator repository:

```bash
git clone https://github.com/tosin2013/qubinode_navigator.git
```

3. Change directory to the qubinode_navigator folder:
```bash
cd qubinode_navigator
```
4. Make the setup.sh script executable:
```bash
chmod +x setup.sh
```
5. Run the setup.sh script:
```bash
./setup.sh
```

The script will now run and perform the necessary tasks, such as installing required packages, configuring the environment, and setting up the Qubinode Navigator.

## Features

The `setup.sh` script performs the following tasks:

* Detects the Linux distribution
* Installs required packages
* Configures SSH
* Configures firewalld
* Clones the Qubinode Navigator repository
* Configures Ansible Navigator
* Configures Ansible Vault using Ansiblesafe
* Tests the inventory
* Deploys KVM Host
* Configures bash aliases
* Sets up Kcli
  
## Options
The setup.sh script accepts the following command-line options:

* `-h, --help: Show help message`
* `--deploy-kvmhost: Deploy KVM host`
* `--configure-bash-aliases: Configure bash aliases`
* `--setup-kcli-base: Set up Kcli base`
* `--deploy-freeipa: Deploy FreeIPA`


For example, to deploy a KVM host, run:
**End to End Deployment**
```bash
./setup.sh
```

**Deploy KVM host**
```bash
./setup.sh --deploy-kvmhost # Deploy KVM host
```
**Deploy KCLI**
```bash
./setup.sh --setup-kcli-base # Set up Kcli base
```

**Help**
```bash
./setup.sh --help # Show help message
```
## View the Kcli pipelines 

## GitLab CI/CD
To Kick off a GitLab CI/CD pipeline, run the following command:
```bash
python3 trigger-gitlab-pipeline.py --project_id=1 --token=glpt-mytoken --ref=main --target_server=servername --ssh_host=server.example.com --ssh_password=PASSWORD
```

## Workloads 
**MicroShift Demos**
* https://github.com/tosin2013/kcli-plan-samples/tree/dev/microshift-demos
* https://github.com/redhat-et/microshift-demos

## Testing 
* https://github.com/jjaswanson4/device-edge-workshops/tree/main/exercises/rhde_aw_120
* https://github.com/FNNDSC/miniChRIS-podman

## Links: 
* https://gitlab.com/cjung/ansible-ee-intro/-/blob/main/ansible-navigator/httpd.yml
* https://redhat-cop.github.io/agnosticd/

## Contributing
Please submit bug reports, suggestions, and improvements as GitHub issues.

See [Developers Guide](docs/developers.md) for more information.