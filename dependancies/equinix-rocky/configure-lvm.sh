 #!/bin/bash
set -xe

function configure_vg(){
    # Get list of block devices
    devices=$(lsblk -l -d -e 11 -n -o NAME)

    # Initialize a variable to store the not mounted devices
    not_mounted=""

    # Iterate through devices and check if they are mounted
    for device in $devices; do
    mount=$(df -P | grep "/dev/$device" | awk '{print $1}')
    if [[ -z "$mount" ]]; then
        if [[ -z "$not_mounted" ]]; then
        not_mounted="/dev/$device"
        else
        not_mounted="$not_mounted /dev/$device"
        fi
    fi
    done

    # Print the list of not mounted devices
    echo "Not mounted devices: $not_mounted"
    lsblk -dno SIZE $not_mounted | awk '{total += $1} END {print "Total size: " total " GB"}'
    lsblk -dno SIZE $not_mounted | awk '{total += $1} END {print "Total size: " total" GB"}'
    TOTAL_SIZE=$(lsblk -dno SIZE $not_mounted | awk '{total += $1} END { print total"GB"}')

    sudo /usr/sbin/pvcreate $not_mounted
    sudo /usr/sbin/vgcreate vg_qubi $not_mounted
    sudo /usr/sbin/lvcreate -L${TOTAL_SIZE} -n vg_qubi-lv_qubi_images vg_qubi 
    sudo mkfs.ext4 /dev/vg_qubi/vg_qubi-lv_qubi_images
    sudo mkdir -p /var/lib/libvirt/images
    sudo mount  /dev/vg_qubi/vg_qubi-lv_qubi_images /var/lib/libvirt/images
    echo "/dev/vg_qubi/vg_qubi-lv_qubi_images   /var/lib/libvirt/images  ext4   defaults    0   0" | sudo tee -a /etc/fstab

    #echo "/dev/vg_qubi/vg_qubi-lv_qubi_images   /var/lib/libvirt/images  ext4   defaults    0   0" >>  /etc/fstab
}

if ! sudo /usr/sbin/vgdisplay | grep -q vg_qubi; then
  echo "vg_qubi not found"
  configure_vg
else
    echo "vg_qubi found"
fi
  