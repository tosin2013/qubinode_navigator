
#!/bin/bash

if [ -f random-functions.sh ]; then
    source random-functions.sh
else
    echo "random-functions.sh does not exist"
    exit 1
fi

############################################
## @brief This function will configure the images for kcli
##  * @param {string} $1 - The path to the vault file
############################################
function kcli_configure_images(){
    echo "Configuring images"
    echo "Downloading Fedora"
    sudo kcli download image fedora37
    echo "Downloading Centos Streams"
    sudo kcli download image centos9jumpbox -u https://cloud.centos.org/centos/9-stream/x86_64/images/CentOS-Stream-GenericCloud-9-20221206.0.x86_64.qcow2
    sudo kcli download image  ztpfwjumpbox  -u https://cloud.centos.org/centos/9-stream/x86_64/images/CentOS-Stream-GenericCloud-9-20221206.0.x86_64.qcow2
    sudo kcli download image centos8jumpbox -u https://cloud.centos.org/centos/8-stream/x86_64/images/CentOS-Stream-GenericCloud-8-20220913.0.x86_64.qcow2
    sudo kcli download image centos8streams -u https://cloud.centos.org/centos/8-stream/x86_64/images/CentOS-Stream-GenericCloud-8-20220913.0.x86_64.qcow2
    # sudo kcli download image ubuntu -u https://cloud-images.ubuntu.com/releases/jammy/release/ubuntu-22.04-server-cloudimg-amd64.img
    RUN_ON_RHPDS=$(yq -r  -o=json ~/quibinode_navigator/inventories/localhost/group_vars/all.yml | jq -r '.run_on_rhpds')
    if [[ $(get_distro) == "rhel"  || "A${RUN_ON_RHPDS}" == "Afalse"  ]]; then
      echo "Downloading Red Hat Enterprise Linux 8"
      sudo kcli download image rhel8
      echo "Downloading Red Hat Enterprise Linux 9"
      echo "For AAP Deployments use: Red Hat Enterprise Linux 9.1 KVM Guest Image"
      sudo kcli download image rhel9
    fi

}

############################################
## @brief This function will install and configure the default settings for kcli
############################################
function qubinode_setup_kcli() {
    if [[ ! -f /usr/bin/kcli ]];
    then 
        sudo dnf -y install libvirt libvirt-daemon-driver-qemu qemu-kvm
        sudo systemctl enable --now libvirtd
        sudo usermod -aG qemu,libvirt $USER
        if [[ $RHEL_VERSION == "CENTOS9" ]]; then
          sudo dnf copr enable karmab/kcli  epel-9-x86_64
        fi
        curl https://raw.githubusercontent.com/karmab/kcli/master/install.sh | bash
        echo "eval '$(register-python-argcomplete kcli)'" >> ~/.bashrc
        if [[ $RHEL_VERSION == "CENTOS9" ]]; then
          sudo kcli create host kvm -H 127.0.0.1 local
        fi
        #update_default_settings
        #kcli_configure_images
    else 
      echo "kcli is installed"
      kcli --help
    fi 
}
