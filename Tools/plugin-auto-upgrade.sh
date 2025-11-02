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
    if [ -d "$VENV_PATH" ] && [ -f "$VENV_PATH/bin/activate" ]; then
        echo "Using virtual environment at: $VENV_PATH"
        source "$VENV_PATH/bin/activate"
    else
        echo "Virtual environment not found at $VENV_PATH"
    fi
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
    # Configure the pull strategy to avoid the hint message
    if is_docker; then
        git config --global pull.rebase false  # You can choose true or false based on your preference
    fi

    # Before performing a git pull, ensure the running python3 is new enough.
    # Only allow automatic git pull when Python is 3.11 or newer.
    check_python_min_version 3 11
    check_ret="$?"
    if [ "$check_ret" = "1" ]; then
        echo "Python version is older than 3.11. Skipping git pull update for safety."
        echo "Please upgrade your Python interpreter to 3.11+ before attempting plugin upgrade."
        return 0
    elif [ "$check_ret" = "2" ]; then
        echo "Could not determine Python version (or $PYTHON_VERSION not found). Skipping git pull."
        return 0
    fi

    git pull
    ret="$?"
    if [ "$ret" != "0" ] ; then
        echo "ERROR while running command 'git pull', we continue."
        echo "Git Status: $(git status)"
    fi

    git checkout stable8
    ret="$?"
    if [ "$ret" != "0" ] ; then
        echo "ERROR while running command 'git checkout stable8', we continue."
        echo "Git Status: $(git status)"
    fi

}


# Check that $PYTHON_VERSION exists and has at least MIN_MAJOR.MIN_MINOR
# Returns:
# 0 -> version is >= required
# 1 -> version is lower than required
# 2 -> python command not found or unable to determine version
check_python_min_version() {
    MIN_MAJOR="$1"
    MIN_MINOR="$2"

    if ! command -v "$PYTHON_VERSION" &> /dev/null; then
        echo "$PYTHON_VERSION not found in PATH"
        return 2
    fi

    # Get major.minor from the python interpreter
    PY_VER=$($PYTHON_VERSION -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)
    if [ -z "$PY_VER" ]; then
        echo "Unable to determine version for $PYTHON_VERSION"
        return 2
    fi

    MAJOR=${PY_VER%%.*}
    MINOR=${PY_VER##*.}
    # sanitize
    MAJOR=${MAJOR//[^0-9]/}
    MINOR=${MINOR//[^0-9]/}

    COMBINED=$((MAJOR * 100 + MINOR))
    REQUIRED=$((MIN_MAJOR * 100 + MIN_MINOR))

    echo "Found $PYTHON_VERSION version: $MAJOR.$MINOR and required is $MIN_MAJOR.$MIN_MINOR"
    if [ "$COMBINED" -lt "$REQUIRED" ]; then
        return 1
    fi
    return 0
}

uninstall_modules_from_constraints() {
    echo " "
    echo "(2b) uninstalling modules listed in constraints.txt"
    echo ""

    if [ ! -f constraints.txt ]; then
        echo "No constraints.txt file found. Skipping uninstallation."
        return
    fi

    MODULES_TO_REMOVE=$(grep -oE '^[a-zA-Z0-9_.-]+' constraints.txt | tr '\n' ' ')
    if [ -z "$MODULES_TO_REMOVE" ]; then
        echo "No modules found to uninstall in constraints.txt."
        return
    fi

    if [ "$VENV_ACTIVATED" = true ]; then
        $VENV_PATH/bin/python3 -m pip uninstall -y $MODULES_TO_REMOVE
    else
        if [ "$(whoami)" == "root" ]; then
            $PYTHON_VERSION -m pip uninstall -y $MODULES_TO_REMOVE
        else
            sudo $PYTHON_VERSION -m pip uninstall -y $MODULES_TO_REMOVE
        fi
    fi
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

is_docker() {
    if [ -f /.dockerenv ] || [ -f /.dockerinit ]; then
        echo "Running inside Docker"
        return 0  # Running inside Docker
    else
    echo "Not running inside Docker"
        return 1  # Not running inside Docker
    fi
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
uninstall_modules_from_constraints
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
