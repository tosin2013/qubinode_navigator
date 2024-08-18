---
layout: default
title:  Configure Rhel9 Equinix
parent: Github
nav_order: 4
---

The script can be triggered manually via GitHub Actions with the following inputs:

- `hostname`: The hostname of the server.
- `target_server`: The target server to configure.
- `forwarder`: DNS forwarder IP address.
- `domain`: Domain name.

##### Configuration Files

The script updates the `.env` file with the following environment variables:

- `CICD_PIPELINE`: Indicates the CI/CD pipeline is active.
- `SSH_PASSWORD`: SSH password for authentication.
- `INVENTORY`: The target server inventory.
- `ENV_USERNAME`: The environment username.
- `DOMAIN`: The domain name.
- `FORWARDER`: DNS forwarder IP address.
- `ACTIVE_BRIDGE`: Indicates whether an active bridge is used.
- `INTERFACE`: The network interface to use.

##### Expected Results

Upon successful execution, the RHEL 9 server will be configured with the specified settings, ready for further deployment or usage within the Qubinode project.

#### Best Practices for Modifying or Extending the Script

- **Coding Conventions**: Follow PEP 8 guidelines for Python code.
- **Style Guidelines**: Use clear and descriptive function and variable names.
- **Error Handling**: Implement robust error handling to manage potential issues during execution.
- **Documentation**: Ensure all new functions or modifications are well-documented.

#### References and Resources

- [Qubinode Project Documentation](https://qubinode.io/docs)
- [GitHub Actions Documentation](https://docs.github.com/actions)
- [Python PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/)

By adhering to these guidelines and leveraging the provided resources, users can effectively modify and extend the Qubinode Navigator script to meet their specific needs.