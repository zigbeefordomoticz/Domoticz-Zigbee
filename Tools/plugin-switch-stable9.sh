#!/bin/bash

# Switches a Zigbee for Domoticz checkout from 'stable8' to 'stable9'.
#
# 'stable9' drops the legacy Domoticz widget model and requires the
# Domoticz Extended Framework (DomoticzEx, available since Domoticz
# 2025.1). This is a ONE-WAY move: once Domoticz (re)creates devices
# under the Extended Framework, 'stable8' can no longer manage them.
# There is no supported path back.
#
# Usage: plugin-switch-stable9.sh [domoticz_ip] [domoticz_port]
#   Defaults: 127.0.0.1 8080

set -e

DOMOTICZ_IP="${1:-127.0.0.1}"
DOMOTICZ_PORT="${2:-8080}"

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$(dirname "$SCRIPT_DIR")"  # Go to parent directory of Tools/

# Confirm the Domoticz version supports the Extended Framework, and
# require the user to have explicitly acknowledged the one-way notice
echo "Checking Domoticz version and stable9 migration acknowledgement..."
if ! python3 "$SCRIPT_DIR/check_stable9_migration.py" --ip "$DOMOTICZ_IP" --port "$DOMOTICZ_PORT" --no-simulate; then
    echo "Error: migration not confirmed. Cannot switch to stable9 branch."
    exit 1
fi

# Store current directory
CURRENT_DIR=$(pwd)

# Check if we are in a git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "Error: Not in a git repository"
    exit 1
fi

# Check for uncommitted changes
if ! git diff --quiet HEAD; then
    echo "Error: You have uncommitted changes. Please commit or stash them first."
    exit 1
fi

# Fetch latest changes
echo "Fetching latest changes..."
git fetch origin || {
    echo "Error: Failed to fetch from remote"
    exit 1
}

# Pull latest changes in current branch
echo "Pulling latest changes in current branch..."
git pull || {
    echo "Error: Failed to pull latest changes"
    exit 1
}

# Switch to stable9 branch
echo "Switching to stable9 branch..."
if git show-ref --verify --quiet refs/remotes/origin/stable9; then
    git checkout stable9 || {
        echo "Error: Failed to switch to stable9 branch"
        exit 1
    }

    # Pull latest changes in stable9
    git pull origin stable9 || {
        echo "Error: Failed to pull latest changes in stable9"
        exit 1
    }

    echo "Successfully switched to stable9 branch"
    echo "Reminder: this is a one-way move. Do not attempt to revert to stable8"
    echo "on this installation once Domoticz has (re)created your devices."
else
    echo "Error: stable9 branch does not exist in the remote repository"
    exit 1
fi

# Return to original directory
cd "$CURRENT_DIR"

echo "Branch switch completed successfully"
