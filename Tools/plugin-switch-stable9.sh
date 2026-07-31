#!/bin/bash

# Switches a Zigbee for Domoticz checkout from 'stable8' to 'stable9'.
#
# 'stable9' drops the legacy Domoticz widget model and requires the
# Domoticz Extended Framework (DomoticzEx, available since Domoticz
# 2025.1). The switch itself is forward compatible and does not modify
# or recreate any existing device. The move is forward-only in terms of
# support: 'stable8' is closed for new development, so going back
# afterwards is not a supported path.
#
# Usage: plugin-switch-stable9.sh --i-understand [--ip IP] [--port PORT] [-h|--help]
#   Defaults: --ip 127.0.0.1 --port 8080
#
# Run with no arguments (or without --i-understand) to only display the
# migration notice and Domoticz version check, without touching git.
# The actual branch switch only happens when --i-understand is passed
# explicitly on the command line by a human who read the notice.

set -e

usage() {
    echo "Usage: $(basename "$0") --i-understand [--ip IP] [--port PORT]"
    echo
    echo "  --i-understand Required to actually perform the switch. Without it,"
    echo "                 only the migration notice and version check are shown."
    echo "  --ip IP        Domoticz server IP/host (default: 127.0.0.1)"
    echo "  --port PORT    Domoticz web server port (default: 8080)"
    echo "  -h, --help     Show this help and exit"
}

DOMOTICZ_IP="127.0.0.1"
DOMOTICZ_PORT="8080"
I_UNDERSTAND=false

while [ $# -gt 0 ]; do
    case "$1" in
        --i-understand)
            I_UNDERSTAND=true
            shift
            ;;
        --ip)
            DOMOTICZ_IP="$2"
            shift 2
            ;;
        --port)
            DOMOTICZ_PORT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1"
            usage
            exit 1
            ;;
    esac
done

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$(dirname "$SCRIPT_DIR")"  # Go to parent directory of Tools/

# Always show the notice and confirm the Domoticz version supports the
# Extended Framework. Without --i-understand this is display-only and
# the script stops here without touching git.
CHECK_ARGS=(--ip "$DOMOTICZ_IP" --port "$DOMOTICZ_PORT")
if [ "$I_UNDERSTAND" = true ]; then
    CHECK_ARGS+=(--i-understand)
fi

echo "Checking Domoticz version and stable9 migration notice..."
if ! python3 "$SCRIPT_DIR/check_stable9_migration.py" "${CHECK_ARGS[@]}"; then
    echo "Error: Domoticz version requirement not met. Cannot switch to stable9 branch."
    exit 1
fi

if [ "$I_UNDERSTAND" != true ]; then
    exit 0
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
    echo "Reminder: 'stable8' is closed for new development, so going back to it"
    echo "afterwards is not a supported path. Your devices were not modified by this switch."
else
    echo "Error: stable9 branch does not exist in the remote repository"
    exit 1
fi

# Return to original directory
cd "$CURRENT_DIR"

echo "Branch switch completed successfully"
