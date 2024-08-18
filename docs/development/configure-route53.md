---
layout: default
title: Configure Route53
parent: Developer Documentation
nav_order: 1
---
### Script Components

The script consists of several key components, including:

* **Requirements file generation**: The script generates a requirements file (`/tmp/requirements.yml`) that specifies the necessary Ansible collections and roles for deployment.
* **Ansible configuration**: The script sets up Ansible configuration files (`/opt/qubinode_navigator/inventories/${INVENTORY}/group_vars/control/vault.yml`) with environment variables such as AWS access key, secret key, and IP address.
* **Playbook creation**: The script creates a playbook file (`/tmp/playbook.yml`) that defines the OpenShift DNS entries to be created or updated.
* **Ansible execution**: The script executes the playbook using Ansible, with options for verbose mode and action (create or delete).

[Full Script](https://github.com/tosin2013/qubinode_navigator/blob/main/dependancies/route53/deployment-script.sh)

### Environment Variables

The script relies on several environment variables to function correctly. These include:

* `ZONE_NAME`: The zone name for the OpenShift DNS entries.
* `AWS_ACCESS_KEY`: The AWS access key for Route53 access.
* `AWS_SECRET_KEY`: The AWS secret key for Route53 access.
* `IP_ADDRESS`: The IP address you want to use.
* `GUID`: A unique identifier for the deployment.
* `ACTION`: The action to perform (create or delete).
* `VERBOSE_LEVEL`: The level of verbosity for Ansible execution.

### Script Structure

The script is structured around several key functions, including:

* `generate_requirements_file()`: Generates the requirements file based on the environment variables.
* `configure_ansible()`: Sets up Ansible configuration files with the necessary environment variables.
* `create_playbook()`: Creates the playbook file based on the OpenShift DNS entries to be created or updated.
* `execute_playbook()`: Executes the playbook using Ansible, with options for verbose mode and action.

### External Dependencies

The script relies on several external dependencies, including:

* `boto3` and `botocore` libraries for AWS access key and secret key management.
* `Ansible` for playbook execution.

### Input and Output Formats

The script accepts input in the form of environment variables, such as `ZONE_NAME`, `GUID`, and `ACTION`. The output format is a set of OpenShift DNS entries created or updated based on the playbook execution.

### Best Practices

When modifying or extending the script, it's recommended to follow best practices for coding conventions and style guidelines. This includes:

* Using consistent indentation and spacing.
* Following PEP 8 guidelines for Python code.
* Documenting changes and updates clearly.

### References

For further information on the script's implementation, refer to the following resources:

* Ansible documentation: <https://docs.ansible.com/>
* ansible-role-update-ip-route53: <https://github.com/tosin2013/ansible-role-update-ip-route53>
* AWS SDK for Python (Boto3) documentation: <https://boto3.amazonaws.com/v1/documentation/api/latest/index.html>
* Qubinode project documentation: <https://qubinode.readthedocs.io/>
