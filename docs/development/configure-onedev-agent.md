---
layout: default
title:  Configure Onedev Agent
parent: Developer Documentation
nav_order: 1
---

## Prerequisites

Before running the script, ensure that:

* You have Java 11 or higher installed.
* You have Git version 2.11.1 or higher installed.
  
[Full Script](https://github.com/Qubinode/qubinode_navigator/blob/main/dependancies/onedev/configure-onedev-agent.sh)

## Configuring the Agent

To configure the agent, follow these steps:

1. Run the Qubinode Navigator script and enter your OneDev username, password, and server IP address when prompted.
2. The script will download and extract the agent package from the specified URL.
3. It will then update the `serverUrl` in the `agent.properties` file with the provided IP address.

## Running the Agent

Once configured, you can run the agent by navigating to the extracted directory and running the `bin/agent.sh console` command.

Note: The script will log any output to a file named `agent.log`.

