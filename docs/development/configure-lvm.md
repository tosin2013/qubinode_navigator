______________________________________________________________________

## layout: default title:  Configure Lvm parent: Developer Documentation nav_order: 1

# Configure LVM

The `configure_vg` function in the Qubinode Navigator script is responsible for configuring a logical volume manager (LVM) on a system. This documentation provides an overview of how the script works and what it does.

[Full Script](https://github.com/Qubinode/qubinode_navigator/blob/main/dependancies/equinix-rocky/configure-lvm.sh)

## Overview

The `configure_vg` function uses the `lsblk` command to get a list of all block devices on the system, excluding those that are already mounted. It then populates an associative array with device sizes and their counts. The function finds the largest size with the most devices of that size and uses these devices to create a new LVM volume group (VG) named `vg_qubi`.

## Steps

The script performs the following steps:

1. Get a list of all block devices on the system using `lsblk`.
1. Populate an associative array with device sizes and their counts.
1. Find the largest size with the most devices of that size.
1. Use these devices to create a new LVM volume group (VG) named `vg_qubi`.
1. Create a logical volume (LV) within the VG named `lv_qubi_images` and format it as an ext4 file system.
1. Mount the LV at `/var/lib/libvirt/images`.
1. Add an entry to the `/etc/fstab` file to mount the LV automatically on boot.

## Output

The script outputs a message indicating whether the LVM volume group `vg_qubi` was found or not. If it is not found, the script will configure it; otherwise, it will output a message saying that `vg_qubi` was already found.
