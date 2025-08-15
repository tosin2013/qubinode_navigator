#!/bin/bash

# =============================================================================
# LVM Storage Configuration - The "Storage Architecture Specialist"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This script automatically configures LVM (Logical Volume Manager) storage for
# virtualization environments, specifically optimized for Equinix Rocky Linux
# deployments. It creates storage pools for libvirt virtual machine images.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script implements intelligent storage configuration:
# 1. [PHASE 1]: Device Discovery - Scans for available unmounted block devices
# 2. [PHASE 2]: Size Analysis - Groups devices by size and identifies optimal candidates
# 3. [PHASE 3]: Device Selection - Selects largest available devices for storage pool
# 4. [PHASE 4]: LVM Creation - Creates physical volumes, volume groups, and logical volumes
# 5. [PHASE 5]: Filesystem Setup - Formats and mounts storage for libvirt images
# 6. [PHASE 6]: Persistence Configuration - Updates /etc/fstab for automatic mounting
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [Storage Foundation]: Provides storage infrastructure for virtualization
# - [Libvirt Integration]: Creates storage pools for KVM virtual machines
# - [Cloud Optimization]: Optimized for Equinix bare metal server storage
# - [Automated Setup]: Eliminates manual storage configuration steps
# - [Virtualization Support]: Enables VM image storage and management
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [Intelligent Selection]: Automatically selects optimal storage devices
# - [Safety-First]: Only uses unmounted devices to prevent data loss
# - [Size Optimization]: Groups devices by size for optimal storage utilization
# - [Libvirt Integration]: Creates storage specifically for virtualization workloads
# - [Persistent Configuration]: Ensures storage survives system reboots
#
# 💡 WHEN TO MODIFY THIS SCRIPT (for future LLMs):
# - [Storage Requirements]: Modify for different storage size or performance requirements
# - [Filesystem Changes]: Update filesystem type or mount options
# - [Device Selection]: Enhance device selection logic for new hardware types
# - [Cloud Platforms]: Adapt for different cloud provider storage configurations
# - [Performance Tuning]: Add performance optimizations for specific workloads
#
# 🚨 IMPORTANT FOR LLMs: This script modifies disk partitions and creates filesystems.
# It requires root privileges and can affect system storage configuration. Changes
# should be tested carefully to prevent data loss or system instability.

set -xe

# Volume Group Configuration Manager - The "Storage Pool Creator"
function configure_vg(){
# 🎯 FOR LLMs: This function intelligently selects and configures storage devices
# for LVM volume groups, optimizing for virtualization workloads.
# 🔄 WORKFLOW:
# 1. Scans all block devices and identifies unmounted candidates
# 2. Groups devices by size to find optimal storage configuration
# 3. Selects largest available devices for maximum storage capacity
# 4. Creates LVM physical volumes, volume groups, and logical volumes
# 5. Formats with ext4 filesystem and mounts for libvirt images
# 6. Updates /etc/fstab for persistent mounting
# 📊 INPUTS/OUTPUTS:
# - INPUT: Available block devices and system storage configuration
# - OUTPUT: Configured LVM storage pool mounted at /var/lib/libvirt/images
# ⚠️  SIDE EFFECTS: Creates filesystems, modifies /etc/fstab, requires root privileges
    # Get list of all block devices excluding those excluded by lsblk and their sizes
    readarray -t device_info <<< "$(lsblk -l -d -e 11 -n -o NAME,SIZE)"

    declare -A device_sizes

    # Populate an associative array with device sizes and their counts
    for info in "${device_info[@]}"; do
        device=$(echo "$info" | awk '{print $1}')
        size=$(echo "$info" | awk '{print $2}')
        mount=$(lsblk -no MOUNTPOINT "/dev/$device")

        if [[ -z "$mount" ]]; then # Check if the device is not mounted
            if [[ -v device_sizes[$size] ]]; then
                device_sizes[$size]="${device_sizes[$size]} /dev/$device"
            else
                device_sizes[$size]="/dev/$device"
            fi
        fi
    done

    # Find the largest size with the most devices of that size
    largest_size=""
    for size in "${!device_sizes[@]}"; do
        if [[ -z "$largest_size" || "${#device_sizes[$size]}" -gt "${#device_sizes[$largest_size]}" ]]; then
            largest_size=$size
        fi
    done

    # Get the devices with the largest common size
    not_mounted="${device_sizes[$largest_size]}"

    if [[ -z "$not_mounted" ]]; then
        echo "No suitable unmounted devices found."
        exit 1
    fi

    echo "Using devices: $not_mounted"

    sudo /usr/sbin/pvcreate $not_mounted
    sudo /usr/sbin/vgcreate vg_qubi $not_mounted
    sudo /usr/sbin/lvcreate -l 100%FREE -n vg_qubi-lv_qubi_images vg_qubi 
    sudo mkfs.ext4 /dev/vg_qubi/vg_qubi-lv_qubi_images
    sudo mkdir -p /var/lib/libvirt/images
    sudo mount /dev/vg_qubi/vg_qubi-lv_qubi_images /var/lib/libvirt/images
    echo "/dev/vg_qubi/vg_qubi-lv_qubi_images /var/lib/libvirt/images ext4 defaults 0 0" | sudo tee -a /etc/fstab
}

if ! sudo /usr/sbin/vgdisplay | grep -q vg_qubi; then
  echo "vg_qubi not found"
  configure_vg
else
    echo "vg_qubi found"
fi
