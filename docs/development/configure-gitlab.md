---
layout: default
title: GitLab Deplpoyment
parent:  Developer Documentation
nav_order: 1
---

Variables
----------

The Qubinode Navigator uses several variables to configure the GitLab server.
These variables can be set using environment variables or by modifying the `defaults/main.yml` file.

* `GILAB_SERVICE_ACCOUNT`: The service account used for the GitLab server.
* `POSTGRES_PASSWORD`: The password for the PostgreSQL database.
* `gitlab_server_image_name`: The name of the Docker image used for the GitLab server.
* `specific_user`: The username used to access the GitLab server.

[Full Script](https://github.com/tosin2013/qubinode_navigator/blob/main/dependancies/gitlab/deployment-script.sh)

Functions
---------

The Qubinode Navigator uses several functions to manage the GitLab server.
These functions include:

* `create_gitlab`: Creates a new GitLab server using the specified container image and configuration.
* `restart_gitlab`: Restarts the GitLab server if it is not running.
* `start_gitlab`: Starts the Gitlab server if it is not running.

Troubleshooting
----------------

If you encounter any issues while using the Qubinode Navigator, please refer to the troubleshooting section below.

References
----------

* [Using Ansible to Setup GitLab using Podman Systemd Rootless Containers](https://github.com/tosin2013/ansible-podman-gitlab-server-role)
* [Ansible Documentation](https://docs.ansible.com/)
* [Podman Documentation](https://podman.io/)
