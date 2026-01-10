
#!/bin/bash

# Function to cleanup a Python virtual environment completely
cleanup_venv_full() {
    local VENV_ROOT="$1"

    if [[ -z "$VENV_ROOT" || ! -d "$VENV_ROOT" ]]; then
        echo "Error: Directory '$VENV_ROOT' does not exist."
        return 1
    fi

    echo "Starting full cleanup in $VENV_ROOT..."

    # Keep these core folders/files
    local KEEP=("bin" "lib" "include" "pyvenv.cfg" "lib64")

    # Loop through everything in the root
    for item in "$VENV_ROOT"/*; do
        local base_item=$(basename "$item")
        if [[ ! " ${KEEP[*]} " =~ " ${base_item} " ]]; then
            echo "Removing: $item"
            rm -rf "$item"
        fi
    done

    # Clean __pycache__ and .pyc files in lib folder
    find "$VENV_ROOT/lib" -type d -name "__pycache__" -exec echo "Removing directory: {}" \; -exec rm -rf {} +
    find "$VENV_ROOT/lib" -type f -name "*.pyc" -exec echo "Removing file: {}" \; -exec rm -f {} +

    echo "Full cleanup completed."
}


check_venv() {
    # Initialize defaults
    VENV=false
    VENV_VERSION=""
    VENV_ROOT=""
    echo "[check_venv] Starting check for PYTHONPATH='$PYTHONPATH'"

    # Return if PYTHONPATH is empty
    if [ -z "$PYTHONPATH" ]; then
        echo "[check_venv] PYTHONPATH is empty or not set."
        return
    fi

    # Split PYTHONPATH by colon
    IFS=':' read -ra PATH_ENTRIES <<< "$PYTHONPATH"

    for path in "${PATH_ENTRIES[@]}"; do
        # Skip empty entries
        [ -z "$path" ] && continue

        # Normalize path (remove trailing slash)
        path="${path%/}"
        echo "[check_venv] Checking path: '$path'"

        # Check if it's a site-packages folder (V2)
        if [[ "$path" =~ /lib/python3\.[0-9]+/ ]]; then
            VENV=true
            VENV_VERSION="V2"
            # Venv root is three levels up from site-packages
            VENV_ROOT="$(dirname "$(dirname "$(dirname "$path")")")"
            echo "[check_venv] Detected site-packages folder (V2) at '$path'"
            echo "[check_venv] Setting venv root to '$VENV_ROOT'"
            break

        # Then check if it's a venv root (V1)
        elif [ -f "$path/bin/activate" ]; then
            VENV=true
            VENV_VERSION="V1"
            VENV_ROOT="$path"
            echo "[check_venv] Detected virtualenv root (V1) at '$path'"
            break
        else
            echo "[check_venv] Path '$path' does not match V1 or V2 patterns."
        fi
    done

    if [ "$VENV" = false ]; then
        echo "[check_venv] No valid venv detected in PYTHONPATH."
    fi

    # Export for external use
    export VENV
    export VENV_VERSION
    export VENV_ROOT
}

# --- MAIN SCRIPT ---

check_venv

echo "VENV=$VENV"
echo "VENV_VERSION=$VENV_VERSION"
echo "VENV_ROOT=$VENV_ROOT"

# Call the appropriate upgrade script if a venv was detected
if [ "$VENV" = true ]; then
    case "$VENV_VERSION" in
        V1)
            echo "[main] Running Tools/plugin-auto-upgrade-v1.sh with PYTHONPATH='$VENV_ROOT'"
            PYTHONPATH="$VENV_ROOT" bash Tools/plugin-auto-upgrade-v1.sh
            ;;
        V2)
            echo "[main] Running Tools/plugin-auto-upgrade-v2.sh with PYTHONPATH='$VENV_ROOT'"
            cleanup_venv_full "$VENV_ROOT"
            PYTHONPATH="$VENV_ROOT" bash Tools/plugin-auto-upgrade-v2.sh
            ;;
        *)
            echo "[main] Unknown VENV_VERSION='$VENV_VERSION', default to V1."
            bash Tools/plugin-auto-upgrade-v1.sh
            ;;
    esac
else
    echo "[main] No venv detected, default to V1."
    bash Tools/plugin-auto-upgrade-v1.sh

fi
