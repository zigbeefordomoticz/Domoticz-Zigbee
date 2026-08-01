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

# Function to check and install python3-venv if missing
ensure_python3_venv() {
    echo "Checking python3 env presence..."
    if [ "$(whoami)" = "root" ]; then
        apt-get update
        apt-get install -y python3-venv python3-pip
    else
        sudo apt-get update
        sudo apt-get install -y python3-venv python3-pip
    fi
}

# Function to install pip
install_pip() {
    $PYTHON_VERSION -m ensurepip
    $PYTHON_VERSION -m pip install --upgrade pip virtualenv -t $VENV_PATH
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

    git pull 
    ret="$?"
    if [ "$ret" != "0" ] ; then
        echo "ERROR while running command 'git pull, we continue."
        echo "Git Status: $(git status)"
    fi
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

# Function to check if pip needs upgrade and perform upgrade if necessary
check_and_upgrade_pip() {
    echo " "
    echo "(2a) check if pip needs upgrade"
    echo ""

    # Choose pip invoker depending on venv or system
    if [ "$VENV_ACTIVATED" = true ]; then
        PIP_INVOKER="$VENV_PATH/bin/python3 -m pip"
    else
        if [ "$(whoami)" == "root" ]; then
            PIP_INVOKER="$PYTHON_VERSION -m pip"
        else
            PIP_INVOKER="sudo $PYTHON_VERSION -m pip"
        fi
    fi

    # Ensure pip is available (try ensurepip if missing)
    if ! $PIP_INVOKER --version >/dev/null 2>&1; then
        echo "pip not found for invoker: $PIP_INVOKER. Attempting to install pip..."
        if [ "$VENV_ACTIVATED" = true ]; then
            $VENV_PATH/bin/python3 -m ensurepip --upgrade >/dev/null 2>&1 || true
            $VENV_PATH/bin/python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
        else
            $PYTHON_VERSION -m ensurepip --upgrade >/dev/null 2>&1 || true
            if [ "$(whoami)" == "root" ]; then
                $PYTHON_VERSION -m pip install --upgrade pip >/dev/null 2>&1 || true
            else
                sudo $PYTHON_VERSION -m pip install --upgrade pip >/dev/null 2>&1 || true
            fi
        fi
    fi

    # Check if pip is listed as outdated by pip itself
    OUTDATED_LIST=$($PIP_INVOKER list --outdated --format=columns 2>/dev/null || true)
    if echo "$OUTDATED_LIST" | awk 'NR>2 {print $1}' | grep -xq "pip"; then
        echo "pip is outdated. Upgrading pip now..."
        if [ "$VENV_ACTIVATED" = true ]; then
            $VENV_PATH/bin/python3 -m pip install --upgrade pip
        else
            if [ "$(whoami)" == "root" ]; then
                $PYTHON_VERSION -m pip install --upgrade pip
            else
                sudo $PYTHON_VERSION -m pip install --upgrade pip
            fi
        fi
        rc="$?"
        if [ "$rc" != "0" ]; then
            echo "Warning: pip upgrade returned non-zero exit code $rc"
        else
            echo "pip upgraded successfully."
        fi
    else
        echo "pip is up-to-date."
    fi
}

# Function to print current version and latest git commit
print_version_info() {
    if [ -f .hidden/VERSION ]; then
    echo "Current version  : $(cat .hidden/VERSION)"
    else
        echo "Current version  : Unknown (no .hidden/VERSION found)"
    fi
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

check_stable9_migration_notice() {
    # inside Tools/plugin-auto-upgrade.sh

    # Resolve the Tools directory relative to this script
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    NOTICE_SCRIPT="$SCRIPT_DIR/check_stable9_migration.py"

    if [ ! -f "$NOTICE_SCRIPT" ]; then
        echo "Warning: $NOTICE_SCRIPT not found. Skipping stable9 migration notice."
        return
    fi

    if ! command -v python3 >/dev/null 2>&1; then
      echo "python3 not found in PATH. Skipping stable9 migration notice."
      return
    fi

    # Display-only, no flags, no stdin expected: remind the user that
    # 'stable8' no longer receives feature updates and that switching to
    # 'stable9' requires explicitly running
    # Tools/plugin-switch-stable9.sh --i-understand on the command line.
    python3 "$NOTICE_SCRIPT"

    rc=$?
    echo "check_stable9_migration.py exited with code $rc"
}


# Main script execution
PYTHON_VERSION="python${1:-3}"
PIP_VERSION="python${1:-3}"

check_stable9_migration_notice
set_home
print_env_details
set_pip_options
ensure_python3_venv
check_and_activate_venv
print_version_info
update_git_config
uninstall_modules_from_constraints
check_and_upgrade_pip
update_python_modules

echo " "
echo "Plugin Upgrade process completed without errors."
exit 0

