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
    # Check if lsb_release command exists
    if command -v lsb_release &> /dev/null; then
        # Get distribution ID and release number
        DISTRIB_ID=$(lsb_release -is 2>/dev/null)
        DISTRIB_RELEASE=$(lsb_release -rs 2>/dev/null)

        # Check if the distribution ID and release number were retrieved successfully
        if [ -n "$DISTRIB_ID" ] && [ -n "$DISTRIB_RELEASE" ]; then
            if [ "$DISTRIB_ID" = "Debian" ] && [ "$DISTRIB_RELEASE" = "12" ]; then
                if ! command -v pip3 &> /dev/null; then
                    echo "pip3 is not installed. Installing python3-pip..."
                    sudo apt-get update
                    sudo apt-get install -y python3-pip
                else
                    echo "pip3 is already installed."
                fi
            else
                echo "This script is intended for Debian 12 only."
            fi
        else
            echo "Failed to retrieve distribution information."
        fi
    else
        echo "lsb_release command not found. This script requires lsb_release to determine the distribution."
    fi
}

# Function to update git configuration
update_git_config() {
    echo "(1) git config --global --add safe.directory"
    # Define the directory you want to add
    directory_to_add=$(pwd)

    # Get the list of currently configured safe directories
    configured_directories=$(git config --get-all --global safe.directory)

    # Check if the directory is already configured
    if [[ "$configured_directories" != *"$directory_to_add"* ]]; then
      # Add the directory if it is not already configured
      git config --global --add safe.directory "$directory_to_add"
      echo "Directory added: $directory_to_add"
    else
      echo "Directory already configured: $directory_to_add"
    fi

    echo " "
    echo "(2) updating Zigbee for Domoticz plugin"
    echo ""
    git pull 
    #git pull --recurse-submodules  && git submodule update --recursive
    ret="$?"
    if [ "$ret" != "0" ] ; then
        echo "ERROR while running command 'git pull --recurse-submodules'."
        echo "Git Status: $(git status)"
        exit -1
    fi
}

check_and_remove_duplicates() {
    # Get the directory of the current script
    SCRIPT_DIR=$(dirname "$(realpath "$0")")

    # Print the directory (for debugging purposes)
    echo "Script directory: $SCRIPT_DIR"
    python3 $SCRIPT_DIR/check_and_remove_duplicates.py $VENV_PATH --remove-duplicates
}

check_and_remove_duplicates() {
    # Get the directory of the current script
    SCRIPT_DIR=$(dirname "$(realpath "$0")")

    # Print the directory (for debugging purposes)
    echo "Script directory: $SCRIPT_DIR"

    # Check if the Python script exists
    if [ ! -f "$SCRIPT_DIR/check_and_remove_duplicates.py" ]; then
        echo "Error: Python script not found at $SCRIPT_DIR/check_and_remove_duplicates.py"
        return 1
    fi

    # Launch the Python script
    python3 "$SCRIPT_DIR/check_and_remove_duplicates.py" "$VENV_PATH" --remove-duplicates

    # Check if the Python script executed successfully
    if [ $? -ne 0 ]; then
        echo "Error: Python script execution failed"
        return 1
    fi

    echo "Duplicates removed successfully"
}


# Function to update python modules
update_python_modules() {
    echo " "
    echo "(3) update $PYTHON_VERSION modules if needed"
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
check_and_remove_duplicates
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
