import fire
import argparse
import getpass
import os
import yaml
import netifaces
import psutil
import re
import time 
import subprocess
import sys

inventory_env = os.environ.get('INVENTORY')
if not inventory_env:
    print("INVENTORY environment variable not found.")
    sys.exit(1)

def update_inventory(username=None, domain_name=None, dnf_forwarder=None):
    if username is None:
        if os.geteuid() == 0:
            username = input("Enter username: ")
        else:
            username = getpass.getuser()

    if domain_name is None:
        while True:
            domain_name = input("Enter the domain name for your system: ")
            regex = r"^(?:(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,}$"
            if re.match(regex, domain_name):
                break
            print("Invalid domain name format. Please try again.")

    if dnf_forwarder is None:
        dnf_forwarder = input("Enter the DNS forwarder for your system: ")

    inventory_path = 'inventories/'+str(inventory_env)+'/group_vars/all.yml'
    with open(inventory_path, 'r') as f:
        inventory = yaml.safe_load(f)

    inventory['admin_user'] = username
    inventory['domain'] = domain_name
    inventory['dns_forwarder'] = dnf_forwarder

    with open(inventory_path, 'w') as f:
        yaml.dump(inventory, f, default_flow_style=False)


def get_interface_ips(configure_bridge=None, interface=None):
    if configure_bridge is None:
        if os.geteuid() == 0:
            print("Error: Cannot set configure_bridge to True when running as root.")
            configure_bridge = False
            print("configure_bridge is set to", configure_bridge)
        else:
            configure_bridge = True  # set configure_bridge to True or False based on your requirements
            print("configure_bridge is set to", configure_bridge)

    # Get a list of network interfaces
    interfaces = netifaces.interfaces()

    # Filter out loopback interfaces and any that don't have an IPv4 address
    interfaces = [i for i in interfaces if i != 'lo' and netifaces.AF_INET in netifaces.ifaddresses(i)]

    if interface is None:
        # If there's only one interface, use that
        if len(interfaces) == 1:
            interface = interfaces[0]
        # If there's more than one, prompt the user to choose one
        elif len(interfaces) > 1:
            print("Multiple network interfaces found:")
            for i, interface in enumerate(interfaces):
                print(f"{i+1}. {interface}")
            choice = int(input("Choose an interface to use: "))
            interface = interfaces[choice-1]
        # If there are no interfaces, raise an exception
        else:
            raise Exception("No network interfaces found")

    # Get the IPv4 address, netmask, and MAC address for the chosen interface
    addrs = netifaces.ifaddresses(interface)
    ip = addrs[netifaces.AF_INET][0]['addr']
    netmask = addrs[netifaces.AF_INET][0]['netmask']
    macaddr = addrs[netifaces.AF_LINK][0]['addr']

    # Calculate the network address and prefix length from the netmask
    netaddr = '.'.join(str(int(x) & int(y)) for x, y in zip(ip.split('.'), netmask.split('.')))
    prefix_len = sum(bin(int(x)).count('1') for x in netmask.split('.'))

    inventory_path = 'inventories/'+str(inventory_env)+'/group_vars/control/kvm_host.yml'
    with open(inventory_path, 'r') as f:
        inventory = yaml.safe_load(f)

    inventory['configure_bridge'] = configure_bridge
    inventory['kvm_host_gw'] = netifaces.gateways()['default'][netifaces.AF_INET][0]
    inventory['kvm_host_interface'] = interface
    inventory['kvm_host_ip'] = ip
    inventory['kvm_host_macaddr'] = macaddr
    inventory['kvm_host_mask_prefix'] = prefix_len
    inventory['kvm_host_netmask'] = netmask

    with open(inventory_path, 'w') as f:
        yaml.dump(inventory, f, default_flow_style=False)

    print({
        "kvm_host_gw": netifaces.gateways()['default'][netifaces.AF_INET][0],
        "kvm_host_interface": interface,
        "kvm_host_ip": ip,
        "kvm_host_macaddr": macaddr,
        "kvm_host_mask_prefix": prefix_len,
        "kvm_host_netmask": netmask,
    })

def get_disk():
    disks = []
    for root, dirs, files in os.walk('/dev/'):
        for file in files:
            if file.startswith('nvme') or file.startswith('sd') or file.startswith('vd'):
                disks.append(os.path.join(root, file))
    if not disks:
        print('No suitable disks found.')
        return None
    elif len(disks) == 3:
        return disks[0]
    else:
        print('Found multiple suitable disks:')
        for i, disk in enumerate(disks):
            print(f'{i + 1}: {disk}')
        print('0: Exit')
        choice = input('Select a disk to use (1, 2, ...): ')
        while not choice.isdigit() or int(choice) < 0 or int(choice) > len(disks):
            choice = input('Invalid choice. Select a disk to use (1, 2, ...): ')
        if int(choice) == 0:
            return None
        return disks[int(choice) - 1]


def select_disk(disks=None):
    # Get available disks
    if disks is None:
        disks = get_disk()
    print(disks)
    # Check if disk is already mounted
    mounted = False
    if disks:
        for disk in disks:
            if os.path.ismount(f'/mnt/{disk}'):
                print(f"Disk {disk} is already mounted.")
                disks = [disk]
                mounted = True
                break

    # Skip disk selection if only one disk is available and already mounted
    if mounted and len(disks) == 1:
        print(f"Using disk: {disks[0]}")
        use_root_disk = True
    else:
        use_root_disk = False

    # Update YAML file with selected disk
    inventory_path = 'inventories/'+str(inventory_env)+'/group_vars/control/kvm_host.yml'
    with open(inventory_path, 'r') as f:
        inventory = yaml.safe_load(f)
    
    if use_root_disk is True:
        print('No disk selected.')
        inventory['create_libvirt_storage'] = False
        inventory['create_lvm'] = False
        with open(inventory_path, 'w') as f:
            yaml.dump(inventory, f, default_flow_style=False)
        exit(1)
    else:
        disks = disks.replace('/dev/', '')
        inventory['create_libvirt_storage'] = True
        inventory['create_lvm'] = True
        inventory['kvm_host_libvirt_extra_disk'] = disks
        with open(inventory_path, "w") as f:
            yaml.dump(inventory, f)
            
        print(f"Selected disk: {disks}")
        print(f"Updated {inventory_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', help='Username for the system')
    parser.add_argument('--domain', help='Domain name for the system')
    parser.add_argument('--forwarder', help='DNS forwarder for the system')
    parser.add_argument('--bridge', type=bool, help='Configure bridge for the system')
    parser.add_argument('--interface', help='Network interface to use')
    parser.add_argument('--disk', help='Disk to use')
    args = parser.parse_args()

    update_inventory(args.username, args.domain, args.forwarder)
    get_interface_ips(args.bridge, args.interface)
    select_disk(args.disk)