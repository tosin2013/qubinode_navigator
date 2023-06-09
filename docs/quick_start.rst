=============
Quick Start
=============

Getting Started
===============

The first step is to get RHEL 9 based operating system installed on your hardware

Suppoted Operating  Systems
========================

`Fedora 38 <https://getfedora.org/>`_
---------
Make sure the following packages are installed on your system before startng the install::

    sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make  -y

`CentOS 9 Streams <https://www.centos.org/>`_
---------

Make sure the following packages are installed on your system before startng the install::

    sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user  gcc python3-devel podman ansible-core make  -y


`Rocky 8.8 <https://rockylinux.org//>`_
---------

Make sure the following packages are installed on your system before startng the install::
    sudo dnf upgrade -y 
    sudo dnf install git vim unzip wget bind-utils tar util-linux-user  gcc podman ansible-core make  -y

If you are using RHEL you can follow the steps below to get started.:

    Get Subscriptions
    -----------------
    -  Get your `No-cost developer subscription <https://developers.redhat.com/articles/faqs-no-cost-red-hat-enterprise-linux>`_ for RHEL.
    -  Get a Red Hat OpenShift Container Platform (OCP) `60-day evalution subscription <https://www.redhat.com/en/technologies/cloud-computing/openshift/try-it?intcmp=701f2000000RQykAAG&extIdCarryOver=true&sc_cid=701f2000001OH74AAG>`_.

`Red Hat Enterprise Linux 9 <https://developers.redhat.com/products/rhel/hello-world>`_
---------

Make sure the following packages are installed on your system before startng the install on RHEL 9::

    curl -OL https://gist.githubusercontent.com/tosin2013/695835751174d725ac196582f3822137/raw/de9534504434d07f0d85db6f352e72c32d397890/configure-rhel9.x.sh
    chmod +x configure-rhel9.x.sh
    ./configure-rhel9.x.sh

`Other RHEL Based Distros`_
---------
Make sure the following packages are installed on your system before startng the install::

    sudo dnf install git vim unzip wget bind-utils python3-pip tar util-linux-user podman ansible-core make -y
