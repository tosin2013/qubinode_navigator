______________________________________________________________________

## layout: default title:  "Deploying on baremetal server" parent: Deployment Documentation nav_order: 2

## Running from Git Repository

Follow these instructions to run the setup.sh script:

1. Open a terminal window.

1. Clone the qubinode_navigator repository:

```bash
git clone https://github.com/Qubinode/qubinode_navigator.git
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

- Detects the Linux distribution
- Installs required packages
- Configures SSH
- Configures firewalld
- Clones the Qubinode Navigator repository
- Configures Ansible Navigator
- Configures Ansible Vault using Ansiblesafe
- Tests the inventory
- Deploys KVM Host
- Configures bash aliases
- Sets up Kcli

## Options

The setup.sh script accepts the following command-line options:

- `-h, --help: Show help message`
- `--deploy-kvmhost: Deploy KVM host`
- `--configure-bash-aliases: Configure bash aliases`
- `--setup-kcli-base: Set up Kcli base`
- `--deploy-freeipa: Deploy FreeIPA`

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
