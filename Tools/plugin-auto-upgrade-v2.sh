#!/bin/bash
# Plugin upgrade script for Zigbee for Domoticz
# Works on Debian/Ubuntu and Fedora/RedHat

set -euo pipefail
exec 2>&1

echo "Starting Zigbee for Domoticz plugin upgrade process."
echo "----------------------------------------------------"

# Initialize globals
VENV_PATH=""
VENV_ACTIVATED=false
PYTHON_VERSION="python${1:-3}"
PIP_OPTIONS="--no-input install -r requirements.txt --ignore-requires-python --upgrade"

# ------------------------
# Utility functions
# ------------------------

set_home() {
    if [ -z "${HOME:-}" ]; then
        export HOME="$(pwd)"
    fi
}

print_env_details() {
    echo "Environment details:"
    env
    echo "User ID: $(id)"
    echo "Current user: $(whoami)"
}

detect_package_manager() {
    if command -v apt-get >/dev/null 2>&1; then
        PKG_MANAGER="apt"
    elif command -v dnf >/dev/null 2>&1; then
        PKG_MANAGER="dnf"
    elif command -v yum >/dev/null 2>&1; then
        PKG_MANAGER="yum"
    else
        echo "No supported package manager found (apt, dnf, yum). Install Python manually."
        exit 1
    fi
    echo "Detected package manager: $PKG_MANAGER"
}

install_packages() {
    # Install python3, venv, pip
    echo "Ensuring Python3, venv and pip are installed..."
    if [ "$(whoami)" = "root" ]; then
        case "$PKG_MANAGER" in
            apt)
                apt-get update
                apt-get install -y python3 python3-venv python3-pip
                ;;
            dnf)
                dnf install -y python3 python3-pip
                ;;
            yum)
                yum install -y python3 python3-pip
                ;;
        esac
    else
        case "$PKG_MANAGER" in
            apt)
                sudo apt-get update
                sudo apt-get install -y python3 python3-venv python3-pip
                ;;
            dnf)
                sudo dnf install -y python3 python3-pip
                ;;
            yum)
                sudo yum install -y python3 python3-pip
                ;;
        esac
    fi
}

install_pip() {
    echo "Ensuring pip is installed..."
    "$PYTHON_VERSION" -m ensurepip --upgrade || true
    "$PYTHON_VERSION" -m pip install --upgrade pip virtualenv
}

activate_venv() {
    if [ -d "$VENV_PATH" ] && [ -f "$VENV_PATH/bin/activate" ]; then
        echo "Activating virtual environment at: $VENV_PATH"
        # shellcheck disable=SC1090
        source "$VENV_PATH/bin/activate"
        VENV_ACTIVATED=true
    else
        echo "Virtual environment not found at $VENV_PATH"
        VENV_ACTIVATED=false
    fi
}

check_and_activate_venv() {
    echo "Checking virtual environment..."

    # 1) Prefer VIRTUAL_ENV if set
    if [ -n "${VIRTUAL_ENV:-}" ]; then
        VENV_PATH="$VIRTUAL_ENV"

        if [ ! -f "$VENV_PATH/bin/activate" ]; then
            echo "VIRTUAL_ENV is set but no bin/activate found."
            echo "Creating virtual environment at $VENV_PATH..."
            "$PYTHON_VERSION" -m venv "$VENV_PATH"
        fi

        activate_venv
        return
    fi

    # 2) Fallback: check PYTHONPATH entries for venv
    if [ -n "${PYTHONPATH:-}" ]; then
        for path in $(echo "$PYTHONPATH" | tr ':' ' '); do
            if [ -f "$path/bin/activate" ]; then
                VENV_PATH="$path"
                activate_venv
                return
            fi
        done
    fi

    echo "No virtual environment found. Using system Python."
}

check_and_upgrade_pip() {
    echo "Checking pip version..."
    if [ "$VENV_ACTIVATED" = true ]; then
        PIP_INVOKER="$VENV_PATH/bin/python3 -m pip"
    else
        PIP_INVOKER="$PYTHON_VERSION -m pip"
        [ "$(whoami)" != "root" ] && PIP_INVOKER="sudo $PIP_INVOKER"
    fi

    if ! $PIP_INVOKER --version >/dev/null 2>&1; then
        echo "pip not found. Installing..."
        install_pip
    fi

    OUTDATED=$($PIP_INVOKER list --outdated --format=columns 2>/dev/null || true)
    if echo "$OUTDATED" | awk 'NR>2 {print $1}' | grep -xq "pip"; then
        echo "pip is outdated. Upgrading..."
        $PIP_INVOKER install --upgrade pip
    else
        echo "pip is up-to-date."
    fi
}

update_python_modules() {
    echo "Updating Python modules from requirements.txt..."
    if [ "$VENV_ACTIVATED" = true ]; then
        "$VENV_PATH/bin/python3" -m pip $PIP_OPTIONS
    else
        if [ "$(whoami)" = "root" ]; then
            "$PYTHON_VERSION" -m pip $PIP_OPTIONS
        else
            sudo "$PYTHON_VERSION" -m pip $PIP_OPTIONS
        fi
    fi
}

is_docker() {
    [ -f /.dockerenv ] || [ -f /.dockerinit ]
}

update_git_config() {
    echo "Updating git configuration..."
    dir=$(pwd)
    if ! git config --get-all --global safe.directory | grep -qx "$dir"; then
        git config --global --add safe.directory "$dir"
        echo "Added safe.directory: $dir"
    fi

    [ "$(is_docker)" ] && git config --global pull.rebase false
    git pull || echo "Warning: git pull failed, continuing..."
}

print_version_info() {
    if [ -f .hidden/VERSION ]; then
        echo "Current version  : $(cat .hidden/VERSION)"
    else
        echo "Current version  : Unknown"
    fi
    echo "Latest git commit: $(git log --pretty=oneline -1 || echo 'N/A')"
}

check_stable9_migration_notice() {
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    NOTICE_SCRIPT="$SCRIPT_DIR/check_stable9_migration.py"

    if [ -f "$NOTICE_SCRIPT" ]; then
        # Display-only, no flags, no stdin expected: remind the user that
        # 'stable8' no longer receives feature updates and that switching to
        # 'stable9' requires explicitly running
        # Tools/plugin-switch-stable9.sh --i-understand on the command line.
        python3 "$NOTICE_SCRIPT"
        rc=$?
        echo "check_stable9_migration.py exited with code $rc"
    else
        echo "Warning: $NOTICE_SCRIPT not found. Skipping stable9 migration notice."
    fi
}

# ------------------------
# Main script execution
# ------------------------
echo "[upgrade-v2] Using Python: $PYTHON_VERSION"
set_home
print_env_details
detect_package_manager
install_packages
check_and_activate_venv
check_and_upgrade_pip
update_python_modules
update_git_config
print_version_info
check_stable9_migration_notice

echo ""
echo "Plugin upgrade process completed successfully."
exit 0