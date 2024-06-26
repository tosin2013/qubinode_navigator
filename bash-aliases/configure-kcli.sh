
#!/bin/bash
#github-action genshdoc


############################################
## @brief This function will configure the images for kcli
##  * @param {string} $1 - The path to the vault file
############################################
function kcli_configure_images(){
    echo "Configuring images"
    dependency_check
    echo "Downloading Fedora"
    sudo kcli download image fedora39
    #echo "Downloading Centos Streams"
    sudo kcli download image centos9stream
    sudo kcli download image centos8stream
    sudo kcli download image ubuntu2204
    kcli list available-images

  #if [[ $LINUX_VERSION == "rhel"  &&  "A${INSTALL_RHEL_IMAGES}" != "Atrue" ]]; then
  #  echo "Downloading Red Hat Enterprise Linux 8"
  #  sudo kcli download image rhel8
  #  echo "Downloading Red Hat Enterprise Linux 9"
  #  echo "For AAP Deployments use: Red Hat Enterprise Linux 9.1 KVM Guest Image"
  #  sudo kcli download image rhel9
  #fi

}

############################################
## @brief This function will install and configure the default settings for kcli
############################################
function qubinode_setup_kcli() {
    get_rhel_version
    if [[ ! -f /usr/bin/kcli ]];
    then 
        sudo dnf -y install libvirt libvirt-daemon-driver-qemu qemu-kvm
        sudo systemctl enable --now libvirtd
        sudo usermod -aG qemu,libvirt $USER
        if [[ $BASE_OS == "CENTOS9" ]]; then
          sudo dnf copr enable karmab/kcli  epel-9-x86_64
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

function install_dependencies {
  cd /opt/kcli-plan-samples
  sudo pip3 install -r profile_generator/requirements.txt
}

function check_kcli_plan {
  if [ -d /opt/kcli-plan-samples ]; then
    echo "kcli plan already exists"
    cd /opt/kcli-plan-samples 
    sudo git pull 
  else
    cd /opt/ || return
    sudo git clone https://github.com/tosin2013/kcli-plan-samples.git
    cd /opt/kcli-plan-samples || return
    sudo git checkout dev
    install_dependencies
  fi
}

function update_profiles_file {
  if [ -d /opt/kcli-plan-samples ]; then
    cd /opt/kcli-plan-samples || return
    if [ ! -f /opt/kcli-plan-samples/.vault_password ]; then
      sudo curl -OL https://gist.githubusercontent.com/tosin2013/022841d90216df8617244ab6d6aceaf8/raw/92400b9e459351d204feb67b985c08df6477d7fa/ansible_vault_setup.sh
      sudo chmod +x ansible_vault_setup.sh
      sudo ./ansible_vault_setup.sh
    fi
    dependency_check
    set_variables
     /usr/local/bin/ansiblesafe -f "${ANSIBLE_VAULT_FILE}" -o 2
    PASSWORD=$(yq eval '.admin_user_password' "${ANSIBLE_VAULT_FILE}")
    RHSM_ORG=$(yq eval '.rhsm_org' "${ANSIBLE_VAULT_FILE}")
    RHSM_ACTIVATION_KEY=$(yq eval '.rhsm_activationkey' "${ANSIBLE_VAULT_FILE}")
    sudo python3 profile_generator/profile_generator.py update_yaml rhel9 rhel9/template.yaml --image rhel-baseos-9.1-x86_64-kvm.qcow2 --user $USER --user-password ${PASSWORD} --rhnorg ${RHSM_ORG} --rhnactivationkey ${RHSM_ACTIVATION_KEY}
    sudo python3 profile_generator/profile_generator.py update_yaml fedora37 fedora37/template.yaml --image Fedora-Cloud-Base-37-1.7.x86_64.qcow2  --disk-size 30 --numcpus 4 --memory 8192 --user  $USER  --user-password ${PASSWORD}
     /usr/local/bin/ansiblesafe -f "${ANSIBLE_VAULT_FILE}" -o 1

    sudo mkdir -p "${KCLI_CONFIG_DIR}"
    sudo cp "${PROFILES_FILE}" "${KCLI_CONFIG_FILE}"
    if [ "${SECURE_DEPLOYMENT}" == "true" ];
    then 
      sudo  /usr/local/bin/ansiblesafe -f "${KCLI_CONFIG_FILE}" -o 1
    fi 
  fi
}
