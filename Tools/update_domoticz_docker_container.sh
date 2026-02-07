#!/usr/bin/env bash
# File: manage_domoticz.sh
#
# Script to manage Domoticz Zigbee4Domoticz Docker container
#
# Features:
# - Works on Fedora and Debian
# - Supports both `docker compose` and `docker-compose`
# - Rebuild image, stopping container if running (with confirmation)
# - Optional force mode to skip confirmation
# - Dry-run mode to preview actions without executing
# - Auto-check for plugin updates inside container (default)
# - Default container, image, compose file, and plugin directory with override options
#
# Usage:
#   ./manage_domoticz.sh [options]
#
# Options:
#   --rebuild             Rebuild the Docker image
#   --force               Force stop container without confirmation (use with --rebuild)
#   --dry-run             Show what would be done without executing
#   --no-auto-update      Disable automatic plugin updates (default is enabled)
#   --plugin-dir PATH     Override the plugin directory inside the container (default: /opt/domoticz/plugins/Domoticz-Zigbee)
#   --container NAME      Override container name (default: domoticz)
#   --image NAME          Override image name (default: domoticz-custom:latest)
#   --compose FILE        Override docker-compose file (default: docker-compose.yml)
#
# Examples:
#   ./manage_domoticz.sh                     # Start container, auto-update plugin by default
#   ./manage_domoticz.sh --rebuild          # Force rebuild, auto-update first
#   ./manage_domoticz.sh --dry-run          # Dry-run of auto-update + start
#   ./manage_domoticz.sh --no-auto-update   # Start container without plugin check
#   ./manage_domoticz.sh --plugin-dir /opt/domoticz/custom-plugins --auto-update
#   ./manage_domoticz.sh --force --rebuild  # Rebuild container, skipping confirmation
#

set -euo pipefail

# Default values
CONTAINER_NAME="domoticz"
IMAGE_NAME="domoticz-custom:latest"
DOCKER_COMPOSE_FILE="docker-compose.yml"
REBUILD=false
FORCE=false
DRY_RUN=false
START=false
STOP=false
PLUGIN_AUTO_UPDATE=false
PLUGIN_DIR="/opt/domoticz/plugins/Domoticz-Zigbee"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --rebuild)
            REBUILD=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --no-auto-update)
            PLUGIN_AUTO_UPDATE=false
            shift
            ;;
        --plugin-dir)
            PLUGIN_DIR="$2"
            shift 2
            ;;
        --container)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        --image)
            IMAGE_NAME="$2"
            shift 2
            ;;
        --start)
            START=true
            shift
            ;;
        --stop)
            STOP=true
            shift;;
        --compose)
            DOCKER_COMPOSE_FILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: $0 [--rebuild] [--force] [--dry-run] [--no-auto-update] [--plugin-dir PATH] [--container NAME] [--image NAME] [--compose FILE]"
            exit 1
            ;;
    esac
done

# Determine which docker compose command is available
if command -v docker &>/dev/null; then
    if docker compose version &>/dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker compose"
    elif command -v docker-compose &>/dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
    else
        echo "Error: Neither 'docker compose' nor 'docker-compose' found."
        exit 1
    fi
else
    echo "Error: Docker is not installed."
    exit 1
fi

echo "Using: $DOCKER_COMPOSE_CMD"
echo "Container: $CONTAINER_NAME, Image: $IMAGE_NAME, Compose file: $DOCKER_COMPOSE_FILE"
echo "Plugin directory: $PLUGIN_DIR"
echo "Dry-run mode: $DRY_RUN"
echo "Plugin auto-update: $PLUGIN_AUTO_UPDATE"


# Check if container is running
is_running() {
    docker ps --filter "name=^${CONTAINER_NAME}$" --format '{{.Names}}' | grep -w "${CONTAINER_NAME}" >/dev/null 2>&1
}

# Stop container if running
stop_container() {
    if is_running; then
        if ! $FORCE && ! $DRY_RUN; then
            read -p "Container ${CONTAINER_NAME} is running. Do you want to stop it? [y/N] " CONFIRM
            if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
                echo "Aborting operation."
                exit 0
            fi
        fi
        if $DRY_RUN; then
            echo "[DRY-RUN] Would stop container ${CONTAINER_NAME}"
        else
            echo "Stopping container ${CONTAINER_NAME}..."
            $DOCKER_COMPOSE_CMD -f "$DOCKER_COMPOSE_FILE" down
        fi
    else
        echo "Container ${CONTAINER_NAME} is not running."
    fi
}

# Rebuild Docker image (does not stop/start container)
rebuild_image() {
    if $DRY_RUN; then
        echo "[DRY-RUN] Would rebuild image ${IMAGE_NAME} using $DOCKER_COMPOSE_FILE"
    else
        echo "Rebuilding image ${IMAGE_NAME}..."
        $DOCKER_COMPOSE_CMD -f "$DOCKER_COMPOSE_FILE" build --no-cache  --progress=plain
    fi
}

# Start container
start_container() {
    if $DRY_RUN; then
        echo "[DRY-RUN] Would start container ${CONTAINER_NAME}"
    else
        if ! is_running; then
            echo "Starting container ${CONTAINER_NAME}..."
            $DOCKER_COMPOSE_CMD -f "$DOCKER_COMPOSE_FILE" up -d
        fi
    fi
}

# Run plugin auto-upgrade inside container
plugin_auto_update() {
    if ! $PLUGIN_AUTO_UPDATE; then
        echo "Plugin auto-update disabled."
        return 1
    fi

    CONTAINER_WAS_RUNNING=false
    if ! is_running; then
        echo "Starting temporary container to run plugin auto-upgrade..."
        if $DRY_RUN; then
            echo "[DRY-RUN] Would start container ${CONTAINER_NAME} for plugin auto-upgrade"
        else
            $DOCKER_COMPOSE_CMD -f "$DOCKER_COMPOSE_FILE" up -d
        fi
    else
        CONTAINER_WAS_RUNNING=true
    fi

    echo "Running plugin-auto-upgrade inside container..."
    if $DRY_RUN; then
        echo "[DRY-RUN] Would execute ${PLUGIN_DIR}/Tools/plugin-auto-upgrade.sh inside container"
    else
        $DOCKER_COMPOSE_CMD -f "$DOCKER_COMPOSE_FILE" exec -T "$CONTAINER_NAME" \
            bash -c "cd ${PLUGIN_DIR} && Tools/plugin-auto-upgrade.sh"
    fi

    # Stop the temporary container if we started it
    if ! $CONTAINER_WAS_RUNNING && ! $DRY_RUN; then
        echo "Stopping temporary container..."
        $DOCKER_COMPOSE_CMD -f "$DOCKER_COMPOSE_FILE" down
    fi
}

# Main execution
WAS_RUNNING=false
if is_running; then
    WAS_RUNNING=true
fi

# Ensure container is running if plugin auto-update is enabled
if $PLUGIN_AUTO_UPDATE; then
    if ! is_running; then
        echo "Container not running, starting temporarily for plugin auto-update..."
        $DRY_RUN && echo "[DRY-RUN] Would start container ${CONTAINER_NAME}" || $DOCKER_COMPOSE_CMD -f "$DOCKER_COMPOSE_FILE" up -d
        TEMP_CONTAINER_STARTED=true
    else
        TEMP_CONTAINER_STARTED=false
    fi

    # Test if plugin directory exists inside container
    if ! $DRY_RUN && ! $($DOCKER_COMPOSE_CMD -f "$DOCKER_COMPOSE_FILE" exec -T "$CONTAINER_NAME" test -d "$PLUGIN_DIR"); then
        echo "Error: Plugin directory $PLUGIN_DIR does not exist inside container"; exit 1
    fi

    # Test if plugin upgrade script exists
    if ! $DRY_RUN && ! $($DOCKER_COMPOSE_CMD -f "$DOCKER_COMPOSE_FILE" exec -T "$CONTAINER_NAME" test -x "$PLUGIN_DIR/Tools/plugin-auto-upgrade.sh"); then
        echo "Error: plugin-auto-upgrade.sh not found or not executable in $PLUGIN_DIR/Tools"; exit 1
    fi

    # Run plugin upgrade
    plugin_auto_update

    # Stop container if it was started temporarily
    if [[ "$TEMP_CONTAINER_STARTED" == true ]] && ! $DRY_RUN; then
        echo "Stopping temporary container..."
        $DOCKER_COMPOSE_CMD -f "$DOCKER_COMPOSE_FILE" down
    fi
fi

# If rebuild is requested, stop container if running
if $REBUILD; then
    rebuild_image
fi

if $WAS_RUNNING; then
    start_container
fi

if $START; then
    start_container
fi
if $STOP; then
    stop_container
fi
if is_running; then
    echo "Done. Container '${CONTAINER_NAME}' is running."
else
    echo "Done. Container '${CONTAINER_NAME}' is not running."
fi
