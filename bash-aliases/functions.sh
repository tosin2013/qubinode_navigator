#!/bin/bash

# This function will check for the existence of the yq binary
function dependency_check() {
    if ! yq -v  &> /dev/null
    then
        VERSION=v4.34.1
        BINARY=yq_linux_amd64
        sudo wget https://github.com/mikefarah/yq/releases/download/${VERSION}/${BINARY} -O /usr/bin/yq &&\
        sudo chmod +x /usr/bin/yq
    fi
    get_rhel_version
    if [ "$BASE_OS" == "ROCKY8" ]; then
      source ~/.profile
    fi
}
# The function get_rhel_version function will determine the version of RHEL
function get_rhel_version() {
  if cat /etc/redhat-release  | grep "Red Hat Enterprise Linux release 9.[0-9]" > /dev/null 2>&1; then
    export BASE_OS="RHEL9"
  elif cat /etc/redhat-release  | grep "Red Hat Enterprise Linux release 8.[0-9]" > /dev/null 2>&1; then
      export BASE_OS="RHEL8"
  elif cat /etc/redhat-release  | grep "Rocky Linux release 8.[0-9]" > /dev/null 2>&1; then
    export BASE_OS="ROCKY8"
  elif cat /etc/redhat-release  | grep 7.[0-9] > /dev/null 2>&1; then
    export BASE_OS="RHEL7"
  elif cat /etc/redhat-release  | grep "CentOS Stream release 9" > /dev/null 2>&1; then
    export BASE_OS="CENTOS9"
  elif cat /etc/redhat-release  | grep "CentOS Stream release 8" > /dev/null 2>&1; then
    export BASE_OS="CENTOS8"
  elif cat /etc/redhat-release  | grep "Fedora" > /dev/null 2>&1; then
    export BASE_OS="FEDORA"
  else
    echo "Operating System not supported"
    echo "You may put a pull request to add support for your OS"
  fi
  echo ${BASE_OS}

}

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

