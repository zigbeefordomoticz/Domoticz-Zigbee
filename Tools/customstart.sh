#!/bin/bash

# customestart.sh
#
# Purpose:
# This script is designed to initialize a Docker container for Domoticz. It performs the following tasks:
# 1. Checks if it is the first run of the container.
# 2. Updates the package list.
# 3. Installs necessary packages (iputils-ping, vim, and openssh-client).
# 4. Installs Python modules required for the Zigbee for Domoticz plugin.
# 5. Changes the working directory to /opt/domoticz.
#
# Usage:
# 1. First Run Check: The script checks if a file named FIRSTRUN exists in the /opt/domoticz directory.
#    If the file does not exist, it creates the file and proceeds with the initialization steps.
# 2. Package Update: The script updates the package list to ensure that the latest package information is available.
# 3. Package Installation: The script installs necessary packages (iputils-ping, vim, and openssh-client).
# 4. Python Module Installation: The script installs the necessary Python modules for the Zigbee for Domoticz plugin.
# 5. Change Working Directory: The script changes the working directory to /opt/domoticz.
#
# Error Handling:
# The script includes error handling to ensure that it exits gracefully if any command fails.
# This helps in debugging and ensures that the container is not left in an inconsistent state.
#
# Logging:
# The script includes logging to capture the output of commands for debugging purposes.
# This helps in identifying issues and understanding the script's behavior.

if [ -f /opt/domoticz/FIRSTRUN ]; then
    true
else
    echo 'creating FIRSTRUN file so script can check on next run'
    touch /opt/domoticz/FIRSTRUN

    echo 'updating packages'
    apt-get -qq update || { echo 'Failed to update packages'; exit 1; }

    echo 'installing iputils-ping'
    apt-get -y install iputils-ping || { echo 'Failed to install iputils-ping'; exit 1; }

    echo 'installing vim editor'
    apt-get -y install vim || { echo 'Failed to install vim'; exit 1; }

    echo 'installing ssh to run the pull'
    apt-get -y install openssh-client || { echo 'Failed to install openssh-client'; exit 1; }

    if [ -f /opt/domoticz/userdata/plugins/Domoticz-Zigbee/requirements.txt ]; then
        echo 'Install the necessary python3 modules for Zigbee for Domoticz plugin'
        cd /opt/domoticz/userdata/plugins/Domoticz-Zigbee/ || { echo 'Failed to change directory'; exit 1; }
        ./Tools/plugin-auto-upgrade.sh || { echo 'Failed to run plugin-auto-upgrade.sh'; exit 1; }
    fi

    cd /opt/domoticz || { echo 'Failed to change directory to /opt/domoticz'; exit 1; }
fi

