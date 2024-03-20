#!/bin/bash
#set -x

if [ ! -d /opt/onedev-agent/agent/ ]; then
    read -p "Enter OneDev username: " ONEDEV_USER
    read -s -p "Enter OneDev password: " ONEDEV_PASS
    read -p "Enter OneDev server IP address: " IPADDRESS
    echo
fi

# Set your OneDev server URL here
oneDevServerUrl="http://${IPADDRESS}:6610"

# Download URL for the agent package - replace this with the actual URL
DOWNLOAD_URL="http://${IPADDRESS}:6610/~downloads/agent.tar.gz"

# Directory to extract the agent
extractDir="/opt/onede-agent"



# Encode the username and password for Basic Auth
CREDENTIALS=$(printf "%s:%s" "$ONEDEV_USER" "$ONEDEV_PASS" | base64)

# Check for Java 11 or higher
if ! java -version 2>&1 | grep -q 'version "1[1-9]'; then
    echo "Java 11 or higher is not installed."
    sudo alternatives --config java
fi


# Check for Git 2.11.1 or higher
if ! git --version | grep -q 'git version 2\.[1-9][1-9]\.'; then
    echo "Git version 2.11.1 or higher is not installed."
    exit 1
fi


if [ ! -d /opt/onedev-agent/agent/ ]; then
    # Download and extract the agent package
    echo "Downloading and extracting the agent package..."
    mkdir -p "$extractDir"
    cd "$extractDir"
    # Download the agent file
    curl -OL "$DOWNLOAD_URL" \
        --header "Authorization: Basic $CREDENTIALS" \
        --header 'Cookie: JSESSIONID=node01h4wpzkk0f56b42hsv8so0p8c2.node0' || exit $?
    tar -xzf "$extractDir/agent.tar.gz" -C "$extractDir"  || exit $?
    ls -lath "$extractDir" || exit $?
    rm "$extractDir/agent.tar.gz" || exit $?
    # Update serverUrl in agent.properties
    echo "Configuring agent..."
    sed -i "s#^serverUrl=.*#serverUrl=$oneDevServerUrl#g" "$extractDir/conf/agent.properties"
fi

if [ ! -f "$extractDir/agent/conf/agent.properties" ]; then
    echo "agent.properties not found in $extractDir/conf"
    exit 1
fi  


# Run the agent
echo "Starting the agent..."
cd "$extractDir/agent"
nohup bin/agent.sh console > agent.log 2>&1 &


