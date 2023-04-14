# Qubinode Navigator
This repository contains a quickstart script setup.sh to set up and configure Qubinode Navigator. Qubinode Navigator helps to automate the deployment and management of virtual machines, containers, and other infrastructure resources.

[![ansible-lint](https://github.com/tosin2013/qubinode_navigator/actions/workflows/ansible-lint.yml/badge.svg)](https://github.com/tosin2013/qubinode_navigator/actions/workflows/ansible-lint.yml)
[![Generate Documentation](https://github.com/tosin2013/qubinode_navigator/actions/workflows/generate-documentation.yml/badge.svg)](https://github.com/tosin2013/qubinode_navigator/actions/workflows/generate-documentation.yml)

## Prerequisites
* Linux-based operating system (RHEL, CentOS, Rocky Linux, or Fedora)
* Git

## Quickstart 

### Running on RHEL, CentOS, or Fedora
```
curl https://raw.githubusercontent.com/tosin2013/qubinode_navigator/main/setup.sh | bash
```
### Runing on Rocky Linux on RHPDS
```
sudo su - 
curl https://raw.githubusercontent.com/tosin2013/qubinode_navigator/main/rocky-linux-hypervisor.sh | bash
```
### Runing on Rocky Linux on RHPDS using tmux Recommened 
```
sudo su - 
dnf install -y tmux curl
tmux new-session -d -s rocky-linux-hypervisor 'curl https://raw.githubusercontent.com/tosin2013/qubinode_navigator/main/rocky-linux-hypervisor.sh | bash'
tmux attach -t rocky-linux-hypervisor
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

**Deploy KVM host**
```bash
./setup.sh --deploy-freeipa # Deploy FreeIPA DNS
```

**Help**
```bash
./setup.sh --help # Show help message
```

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

See [Developers Guide](docs/developers.rst) for more information.