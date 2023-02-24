import fire
import getpass
import os
import yaml
import netifaces
import psutil
import re
import time 

def update_inventory(username=None):
    if os.geteuid() == 0:
        if not username:
            username = input("Enter username: ")
    else:
        username = getpass.getuser()

    while True:
        domain_name = input("Enter the domain name for your system: ")
        regex = r"^(?:(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,}$"
        if re.match(regex, domain_name):
            break
        print("Invalid domain name format. Please try again.")

    dnf_forwarder = input("Enter the DNS forwarder for your system: ")

    inventory_path = 'inventories/localhost/group_vars/all.yml'
    with open(inventory_path, 'r') as f:
        inventory = yaml.safe_load(f)

    inventory['admin_user'] = username
    inventory['domain'] = domain_name
    inventory['dns_forwarder'] = dnf_forwarder

    with open(inventory_path, 'w') as f:
        yaml.dump(inventory, f, default_flow_style=False)


def get_interface_ips():
    if os.geteuid() == 0:
        print("Error: Cannot set configure_bridge to True when running as root.")
        configure_bridge = False
        print("configure_bridge is set to", configure_bridge)
        time.sleep(3) 
    else:
        configure_bridge = True  # set configure_bridge to True or False based on your requirements
        print("configure_bridge is set to", configure_bridge)
        time.sleep(3) 

    # Get a list of network interfaces
    interfaces = netifaces.interfaces()

    # Filter out loopback interfaces and any that don't have an IPv4 address
    interfaces = [i for i in interfaces if i != 'lo' and netifaces.AF_INET in netifaces.ifaddresses(i)]

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

    inventory_path = 'inventories/localhost/group_vars/control/kvm_host.yml'
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
    elif len(disks) == 1:
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


def select_disk():
    # Get available disks
    disks = get_disk()
    print(disks)

    # Update YAML file with selected disk
    inventory_path = 'inventories/localhost/group_vars/control/kvm_host.yml'
    with open(inventory_path, 'r') as f:
        inventory = yaml.safe_load(f)
    
    if '/dev/' not in disks:
        print('No disk selected.')
        inventory['create_libvirt_storage'] = False
        with open(inventory_path, 'w') as f:
            yaml.dump(inventory, f, default_flow_style=False)
        exit(1)
    else:
        disks = disks.replace('/dev/', '')
        inventory['create_libvirt_storage'] = True
        inventory['kvm_host_libvirt_extra_disk'] = disks
        with open(inventory_path, "w") as f:
            yaml.dump(inventory, f)
            
        print(f"Selected disk: {disks}")
        print(f"Updated {inventory_path}")


if __name__ == '__main__':
    fire.Fire(update_inventory)
    get_interface_ips()
    select_disk()