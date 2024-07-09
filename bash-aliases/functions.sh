#!/bin/bash

function kcli_configure_images() {
    echo "Configuring images"
    dependency_check
    echo "Downloading Fedora"
    sudo kcli download image fedora39
    sudo kcli download image centos9stream
    sudo kcli download image centos8stream
    sudo kcli download image ubuntu2204
    kcli list available-images
}

function qubinode_setup_kcli() {
    get_rhel_version
    if [[ ! -f /usr/bin/kcli ]]; then
        sudo dnf -y install libvirt libvirt-daemon-driver-qemu qemu-kvm
        sudo systemctl enable --now libvirtd
        sudo usermod -aG qemu,libvirt $USER
        if [[ $BASE_OS == "CENTOS9" ]]; then
            sudo dnf copr enable karmab/kcli epel-9-x86_64
        fi
        curl https://raw.githubusercontent.com/karmab/kcli/master/install.sh | bash
        echo "eval '$(register-python-argcomplete kcli)'" >> ~/.bashrc
        if [[ $BASE_OS == "CENTOS9" ]]; then
            sudo kcli create host kvm -H 127.0.0.1 local
        elif [[ $BASE_OS == "RHEL9" ]]; then
            sudo kcli create host kvm -H 127.0.0.1 local
        fi
    else
        echo "kcli is installed"
        kcli --help
    fi
}

