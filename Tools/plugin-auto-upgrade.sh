#!/bin/bash

# export GIT_TRACE=1

exec 2>&1

echo "Starting Zigbee for Domoticz plugin Upgrade process."
echo "----------------------------------------------------"

# Function to set HOME environment variable if not set
set_home() {
    if [ -z ${HOME} ]; then
        export HOME=$(pwd)
    fi
}

# Function to print environment details
print_env_details() {
    env
    echo " "
    /usr/bin/id
    echo " "
    /usr/bin/whoami
    echo " "
}

# Function to set PIP options based on the distribution
set_pip_options() {
    PIP_OPTIONS="--no-input install -r requirements.txt --ignore-requires-python --upgrade"
    if command -v lsb_release &> /dev/null; then
        DISTRIB_ID=$(lsb_release -is)
        DISTRIB_RELEASE=$(lsb_release -rs)
        if [ "$DISTRIB_ID" = "Debian" ] && [ "$DISTRIB_RELEASE" = "12" ]; then
            PIP_OPTIONS="$PIP_OPTIONS --break-system-packages"
        fi
    fi
    echo "PIP Options: $PIP_OPTIONS"
}

# Function to check if pip is installed in the virtual environment
check_pip_in_venv() {
    if [ ! -f "$VENV_PATH/bin/$PYTHON_VERSION" ]; then
        echo "pip is not installed in the virtual environment. Installing pip..."
        install_pip
        $PYTHON_VERSION -m venv $VENV_PATH
    fi
}

# Function to install pip
install_pip() {
    if command -v lsb_release &> /dev/null && [ "$(lsb_release -is)" = "Debian" ] || [ "$(lsb_release -is)" = "Ubuntu" ]; then
        echo "We are expecting the user to properly install python3-pip package. if not yet done !!"
    else
        $PYTHON_VERSION -m ensurepip
        $PYTHON_VERSION -m pip install --upgrade pip virtualenv -t $VENV_PATH
    fi
}

# Function to activate virtual environment
activate_venv() {
    echo "Using virtual environment at: $VENV_PATH"
    source $VENV_PATH/bin/activate
}

# Function to check and activate virtual environment
check_and_activate_venv() {
    if [ -n "$PYTHONPATH" ]; then
        echo "PYTHONPATH is set to: $PYTHONPATH"
        VENV_PATH=$(echo $PYTHONPATH | cut -d':' -f1)
        if [ -d "$VENV_PATH/bin" ]; then
            check_pip_in_venv
        else
            echo "Virtual environment path $VENV_PATH does not exist"
            echo "pip is not installed in the virtual environment. Installing pip..."
            install_pip
            $PYTHON_VERSION -m venv $VENV_PATH
        fi
        VENV_ACTIVATED=true
        activate_venv
    else
        echo "PYTHONPATH is not set"
        VENV_ACTIVATED=false
    fi
}

# Function to install python3-pip on Debian if necessary
install_pip_on_debian() {
    if command -v lsb_release &> /dev/null; then
        DISTRIB_ID=$(lsb_release -is)
        DISTRIB_RELEASE=$(lsb_release -rs)
        if [ "$DISTRIB_ID" = "Debian" ] && [ "$DISTRIB_RELEASE" = "12" ]; then
            if ! command -v pip3 &> /dev/null; then
                echo "pip3 is not installed. Installing python3-pip..."
                sudo apt-get update
                sudo apt-get install -y python3-pip
            fi
        fi
    fi
}

# Function to update git configuration
update_git_config() {
    echo "(1) git config --global --add safe.directory"
    git config  --global --add safe.directory $(pwd)
}

# Function to update python modules
update_python_modules() {
    echo " "
    echo "(2) update $PYTHON_VERSION modules if needed"
    echo ""
    if [ "$VENV_ACTIVATED" = true ]; then
        $VENV_PATH/bin/python3 -m pip $PIP_OPTIONS -t $VENV_PATH
    else
        if [ "$(whoami)" == "root" ]; then
            $PYTHON_VERSION -m pip $PIP_OPTIONS
        else
            sudo $PYTHON_VERSION -m pip $PIP_OPTIONS
        fi
    fi
    ret="$?"
    if [ "$ret" != "0" ] ; then
        echo "ERROR while running command '$PYTHON_VERSION -m pip $PIP_OPTIONS'."
        echo "Is sudo available for this user without password ?"
        exit -2
    fi
}

# Function to print current version and latest git commit
print_version_info() {
    echo "Current version  : $(cat .hidden/VERSION)"
    echo "latest git commit: $(git log --pretty=oneline -1)"
    echo ""
}

# Main script execution
PYTHON_VERSION="python${1:-3}"
PIP_VERSION="python${1:-3}"

set_home
print_env_details
set_pip_options
#install_pip_on_debian
check_and_activate_venv
print_version_info
update_git_config
update_python_modules

echo " "
echo "Plugin Upgrade process completed without errors."
exit 0

# Documentation:
# This script automates the upgrade process for the Zigbee for Domoticz plugin.
# It performs the following steps:
# 1. Sets the HOME environment variable if not already set.
# 2. Prints environment details for debugging purposes.
# 3. Sets PIP options based on the distribution.
# 4. Checks if PYTHONPATH is set and activates the virtual environment if available.
# 5. Installs python3-pip on Debian if necessary.
# 6. Updates the git configuration to add the current directory as a safe directory.
# 7. Updates Python modules using pip.
# 8. Prints the current version and latest git commit of the plugin.
# 9. Completes the upgrade process and exits.
