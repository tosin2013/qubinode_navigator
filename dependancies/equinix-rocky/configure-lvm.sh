#!/bin/bash
set -xe

function configure_vg(){
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
