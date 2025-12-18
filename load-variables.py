#!/usr/bin/env python3

# =============================================================================
# Load Variables - The "Configuration Detective"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This is the original configuration management script that handles interactive
# configuration collection, system auto-detection, and YAML inventory updates.
# It serves as the foundation for the enhanced configuration system.
#
# ✨ ENHANCED: Now checks environment variables FIRST before prompting
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script implements traditional configuration management:
# 1. [PHASE 1]: Environment Check - First checks ENV vars (QUBINODE_ADMIN_USER, QUBINODE_DOMAIN, FORWARDER)
# 2. [PHASE 2]: Interactive Input - Prompts only if env vars not set
# 3. [PHASE 3]: Network Detection - Auto-detects network interfaces and IP configuration
# 4. [PHASE 4]: Storage Detection - Identifies available disks and storage configuration
# 5. [PHASE 5]: Inventory Updates - Updates YAML inventory files with collected data
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [Legacy Configuration]: Original configuration method before template system
# - [Environment-First]: Prioritizes .env file values over interactive prompts
# - [Backward Compatibility]: Still used as fallback when enhanced system unavailable
# - [Interactive Mode]: Provides user-friendly prompts for manual configuration
# - [System Detection]: Core auto-detection logic used by enhanced system
# - [YAML Management]: Direct YAML file manipulation for inventory updates
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Environment Variables First]: Checks QUBINODE_* and other env vars before prompting
# - [Interactive Fallback]: Only prompts if environment variables not set
# - [System Auto-Detection]: Automatically discovers network and storage configuration
# - [Direct YAML Updates]: Modifies inventory YAML files in-place
# - [Validation Logic]: Includes input validation for domains and network configuration
# - [Backward Compatibility]: Maintains compatibility with existing deployment scripts
#
# 💡 WHEN TO MODIFY THIS SCRIPT (for future LLMs):
# - [New System Detection]: Add support for new hardware or network configurations
# - [Validation Updates]: Enhance input validation for new requirements
# - [YAML Structure Changes]: Update for new inventory file structures
# - [Interactive Improvements]: Enhance user experience and error handling
# - [Integration Points]: Maintain compatibility with enhanced_load_variables.py
#
# 🚨 IMPORTANT FOR LLMs: This script directly modifies inventory YAML files and
# collects sensitive user input. It's used as a fallback when the enhanced template
# system is unavailable. Changes must maintain backward compatibility.

import argparse
import getpass
import os
import pwd
import re
import subprocess
import sys
import yaml
import netifaces
import psutil

# Constants for user validation
MIN_USER_UID = 1000  # Minimum UID for regular users
MAX_USER_UID = 65534  # Maximum UID for regular users (excludes nobody/nogroup)

# 📊 GLOBAL VARIABLES (shared with other scripts):
inventory_env = os.environ.get("INVENTORY")  # Environment inventory name
if not inventory_env:
    print("INVENTORY environment variable not found.")
    sys.exit(1)


# Inventory Update Manager - The "Configuration Collector"
def update_inventory(username=None, domain_name=None, dnf_forwarder=None):
    """
    🎯 FOR LLMs: This function collects user credentials and system information
    through environment variables first, then interactive prompts as fallback.
    It updates the inventory YAML files with the collected configuration data.

    🔄 WORKFLOW:
    1. Checks QUBINODE_ADMIN_USER env var, then prompts if not set
    2. Validates and checks QUBINODE_DOMAIN env var, then prompts if not set
    3. Checks FORWARDER env var, then prompts if not set
    4. Updates inventory YAML files with collected data

    📊 INPUTS/OUTPUTS:
    - INPUT: username, domain_name, dnf_forwarder (optional parameters override env vars)
    - OUTPUT: Updated inventory YAML files in inventories/{env}/group_vars/

    ⚠️  SIDE EFFECTS: Modifies YAML files, only prompts if parameters and env vars not provided
    """
    # Priority 1: Function parameters (from CLI args)
    # Priority 2: Environment variables
    # Priority 3: Interactive prompts

    if username is None:
        # Check environment variables first (priority order)
        username = (
            os.environ.get("QUBINODE_ADMIN_USER")
            or os.environ.get("ENV_USERNAME")
            or (os.environ.get("SUDO_USER") if os.environ.get("SUDO_USER") != "root" else None)
            or (os.environ.get("SSH_USER") if os.environ.get("SSH_USER") != "root" else None)
            or (os.environ.get("USER") if os.environ.get("USER") != "root" else None)
        )

        if username is None:
            # Fall back to interactive prompt
            if os.geteuid() == 0:
                username = input("Enter username: ")
            else:
                username = getpass.getuser()

    # Validate that the user exists on the system
    try:
        pwd.getpwnam(username)
    except KeyError:
        print(f"ERROR: User '{username}' does not exist on this system", file=sys.stderr)
        print("Available non-root users:", file=sys.stderr)
        # Use getent passwd for consistency with bash script and better performance
        try:
            result = subprocess.run(
                ["getent", "passwd"],
                capture_output=True,
                text=True,
                check=False
            )
            for line in result.stdout.splitlines():
                parts = line.split(":")
                if len(parts) >= 3:
                    try:
                        uid = int(parts[2])
                        if MIN_USER_UID <= uid < MAX_USER_UID:
                            print(f"  - {parts[0]}", file=sys.stderr)
                    except ValueError:
                        continue
        except Exception:
            # Fallback to pwd module if getent fails
            for user in pwd.getpwall():
                if MIN_USER_UID <= user.pw_uid < MAX_USER_UID:
                    print(f"  - {user.pw_name}", file=sys.stderr)
        print("\nTo fix this issue:", file=sys.stderr)
        print(f"  1. Set QUBINODE_ADMIN_USER in .env to an existing user", file=sys.stderr)
        print(f"  2. Or create the user: sudo useradd -m {username}", file=sys.stderr)
        print(f"  3. Or run the script as the target user (it will be auto-detected)", file=sys.stderr)
        sys.exit(1)

    if domain_name is None:
        # Check environment variables first
        domain_name = os.environ.get("QUBINODE_DOMAIN")

        if domain_name is None:
            # Fall back to interactive prompt with validation
            while True:
                domain_name = input("Enter the domain name for your system: ")
                regex = r"^(?:(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,}$"
                if re.match(regex, domain_name):
                    break
                print("Invalid domain name format. Please try again.")

    if dnf_forwarder is None:
        # Check environment variables first
        dnf_forwarder = os.environ.get("FORWARDER")

        if dnf_forwarder is None:
            # Fall back to interactive prompt
            dnf_forwarder = input("Enter the DNS forwarder for your system: ")

    inventory_path = "inventories/" + str(inventory_env) + "/group_vars/all.yml"
    with open(inventory_path, "r") as f:
        inventory = yaml.safe_load(f)

    inventory["admin_user"] = username
    inventory["domain"] = domain_name
    inventory["dns_forwarder"] = dnf_forwarder

    with open(inventory_path, "w") as f:
        yaml.dump(inventory, f, default_flow_style=False)


def get_interface_ips(configure_bridge=None, interface=None):
    """
    Detect and configure network interfaces with environment variable support.

    Enhanced: Now checks INTERFACE and ACTIVE_BRIDGE environment variables first
    """
    if configure_bridge is None:
        # Check environment variables first
        bridge_env = os.environ.get("ACTIVE_BRIDGE")
        if bridge_env is not None:
            configure_bridge = bridge_env.lower() in ("true", "1", "yes")
        else:
            # Fall back to original logic
            if os.geteuid() == 0:
                print("Error: Cannot set configure_bridge to True when running as root.")
                configure_bridge = False
                print("configure_bridge is set to", configure_bridge)
            else:
                configure_bridge = True
                print("configure_bridge is set to", configure_bridge)

    # Get a list of network interfaces
    interfaces = netifaces.interfaces()

    # Filter out loopback interfaces and any that don't have an IPv4 address
    interfaces = [i for i in interfaces if i != "lo" and netifaces.AF_INET in netifaces.ifaddresses(i)]

    if interface is None:
        # Check environment variables first
        interface = os.environ.get("INTERFACE")

        if interface is None:
            # Fall back to auto-detection
            if len(interfaces) == 1:
                interface = interfaces[0]
            elif len(interfaces) > 1:
                print("Multiple network interfaces found:")
                for i, iface in enumerate(interfaces):
                    print(f"{i+1}. {iface}")
                choice = int(input("Choose an interface to use: "))
                interface = interfaces[choice - 1]
            else:
                raise Exception("No network interfaces found")

    # Get the IPv4 address, netmask, and MAC address for the chosen interface
    addrs = netifaces.ifaddresses(interface)
    ip = addrs[netifaces.AF_INET][0]["addr"]
    netmask = addrs[netifaces.AF_INET][0]["netmask"]
    macaddr = addrs[netifaces.AF_LINK][0]["addr"]

    # Calculate the network address and prefix length from the netmask
    ".".join(str(int(x) & int(y)) for x, y in zip(ip.split("."), netmask.split(".")))
    prefix_len = sum(bin(int(x)).count("1") for x in netmask.split("."))

    # Prepare the configuration for the inventory
    config = {
        "kvm_host_gw": get_default_gateway(),
        "kvm_host_interface": interface,
        "kvm_host_ip": ip,
        "kvm_host_macaddr": macaddr,
        "kvm_host_mask_prefix": prefix_len,
        "kvm_host_netmask": netmask,
    }

    print(config)

    # Update YAML file
    inventory_path = "inventories/" + str(inventory_env) + "/group_vars/control/kvm_host.yml"
    with open(inventory_path, "r") as f:
        inventory = yaml.safe_load(f)

    for key, value in config.items():
        inventory[key] = value

    with open(inventory_path, "w") as f:
        yaml.dump(inventory, f)


def get_default_gateway():
    """Get the default gateway IP address"""
    try:
        gws = netifaces.gateways()
        return gws["default"][netifaces.AF_INET][0]
    except Exception:
        return "0.0.0.0"


def select_disk(disk=None):
    """
    Select a disk for KVM storage with environment variable support.

    Enhanced: Now checks KVM_HOST_LIBVIRT_EXTRA_DISK environment variable first,
    and allows "skip" to disable disk selection
    """
    if disk is None:
        # Check environment variables first
        disk = os.environ.get("KVM_HOST_LIBVIRT_EXTRA_DISK")

        if disk is None:
            # Fall back to interactive selection
            disks = []
            mounted = False

            # Get a list of all disks
            for partition in psutil.disk_partitions():
                disk_name = partition.device.split("/")[-1]
                # Skip loop devices, ram disks, and the root partition
                if not disk_name.startswith("loop") and not disk_name.startswith("ram") and disk_name != "sda":
                    disks.append(partition.device)

            disks = list(set(disks))

            # If there's only one disk, use that
            if len(disks) == 1:
                disk = disks[0]
            # If there's more than one, prompt the user to choose one
            elif len(disks) > 1:
                print("Found multiple suitable disks:")
                for i, disk_option in enumerate(disks, 1):
                    print(f"{i}: {disk_option}")
                print("0: Exit")
                choice = input("Select a disk to use (1, 2, ...): ")

                if choice == "0":
                    print("Exiting disk selection.")
                    return
                elif choice == "skip":
                    print("Skipping disk selection.")
                    return
                else:
                    try:
                        disk = disks[int(choice) - 1]
                    except (ValueError, IndexError):
                        print("Invalid selection.")
                        return
            else:
                print("No suitable disks found.")
                return

    # Handle "skip" option
    if disk and disk.lower() == "skip":
        print("Skipping disk selection.")
        use_root_disk = True
    else:
        use_root_disk = False

        # Check if disk is already mounted
        mounted = False
        if disk:
            for partition in psutil.disk_partitions():
                if partition.device == disk:
                    if os.path.ismount(partition.mountpoint):
                        print(f"Disk {disk} is already mounted.")
                        mounted = True
                        break

        # Skip disk selection if only one disk is available and already mounted
        if mounted and disk:
            print(f"Using disk: {disk}")
            use_root_disk = True

    # Update YAML file with selected disk
    inventory_path = "inventories/" + str(inventory_env) + "/group_vars/control/kvm_host.yml"
    with open(inventory_path, "r") as f:
        inventory = yaml.safe_load(f)

    if use_root_disk is True or disk is None:
        print("No disk selected.")
        inventory["create_libvirt_storage"] = False
        inventory["create_lvm"] = False
        with open(inventory_path, "w") as f:
            yaml.dump(inventory, f, default_flow_style=False)
    else:
        disk_name = disk.replace("/dev/", "")
        inventory["create_libvirt_storage"] = True
        inventory["create_lvm"] = True
        inventory["kvm_host_libvirt_extra_disk"] = disk_name
        with open(inventory_path, "w") as f:
            yaml.dump(inventory, f)

        print(f"Selected disk: {disk_name}")
        print(f"Updated {inventory_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", help="Username for the system")
    parser.add_argument("--domain", help="Domain name for the system")
    parser.add_argument("--forwarder", help="DNS forwarder for the system")
    parser.add_argument("--bridge", type=bool, help="Configure bridge for the system")
    parser.add_argument("--interface", help="Network interface to use")
    parser.add_argument("--disk", help='Disk to use, or "skip" to skip disk selection')
    args = parser.parse_args()

    update_inventory(args.username, args.domain, args.forwarder)
    get_interface_ips(args.bridge, args.interface)
    select_disk(args.disk)
