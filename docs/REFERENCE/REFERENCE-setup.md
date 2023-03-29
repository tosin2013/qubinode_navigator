# Overview

This function get_quibinode_navigator function will clone the qubinode_navigator repo


# Settings

## setup.sh quickstart script for qubinode_navigator
* ./setup.sh 
*  The function get_rhel_version function will determine the version of RHEL


# Global Variables

* **ANSIBLE_SAFE_VERSION** (this): is the ansible safe version
* **INVENTORY** (this): is the inventory file name and path Example: inventories/localhost


# Functions
- [Overview](#overview)
- [Settings](#settings)
  - [setup.sh quickstart script for qubinode\_navigator](#setupsh-quickstart-script-for-qubinode_navigator)
- [Global Variables](#global-variables)
- [Functions](#functions)
  - [configure\_navigator()](#configure_navigator)
  - [configure\_vault()](#configure_vault)
  - [generate\_inventory()](#generate_inventory)
  - [configure\_ssh()](#configure_ssh)
  - [configure\_os()](#configure_os)


## configure_navigator()

This function configure_navigator function will configure the ansible-navigator

## configure_vault()

This function configure_vault function will configure the ansible-vault it will download ansible vault and ansiblesafe

## generate_inventory()

This function generate_inventory function will generate the inventory

## configure_ssh()

This function configure_ssh function will configure the ssh

## configure_os()

This configure_os function will get the base os and install the required packages


