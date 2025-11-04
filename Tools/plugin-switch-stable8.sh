#!/bin/bash

# Exit on error
set -e

# Default to dry-run mode
DRY_RUN=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --I-want-to-update)
            DRY_RUN=false
            shift
            ;;
        *)
            echo "Usage: $0 [--dry-run] [--I-want-to-update]"
            echo "  --dry-run         : Simulate the switch without making changes (default)"
            echo "  --I-want-to-update: Actually perform the branch switch"
            exit 1
            ;;
    esac
done

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$(dirname "$SCRIPT_DIR")"  # Go to parent directory of Tools/

if $DRY_RUN; then
    echo "DRY RUN MODE - No changes will be made"
fi

# First check Python version requirements using check_python_and_branch.py
echo "Checking Python version requirements..."
if ! python3 "$SCRIPT_DIR/check_python_and_branch.py" --min-version 3.11; then
    echo "Error: Python version requirements not met. Cannot switch to stable8 branch."
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
if ! $DRY_RUN; then
    git fetch origin || {
        echo "Error: Failed to fetch from remote"
        exit 1
    }
else
    echo "DRY RUN: Would fetch from remote"
fi

# Pull latest changes in current branch
echo "Pulling latest changes in current branch..."
if ! $DRY_RUN; then
    git pull || {
        echo "Error: Failed to pull latest changes"
        exit 1
    }
else
    echo "DRY RUN: Would pull latest changes"
fi

# Switch to stable8 branch
echo "Switching to stable8 branch..."
if git show-ref --verify --quiet refs/remotes/origin/stable8; then
    if ! $DRY_RUN; then
        git checkout stable8 || {
            echo "Error: Failed to switch to stable8 branch"
            exit 1
        }
        
        # Pull latest changes in stable8
        git pull origin stable8 || {
            echo "Error: Failed to pull latest changes in stable8"
            exit 1
        }
        
        echo "Successfully switched to stable8 branch"
    else
        echo "DRY RUN: Would switch to stable8 branch"
        echo "DRY RUN: Would pull latest changes in stable8"
    fi
else
    echo "Error: stable8 branch does not exist in the remote repository"
    exit 1
fi

# Return to original directory
cd "$CURRENT_DIR"

if $DRY_RUN; then
    echo "DRY RUN: Branch switch simulation completed successfully"
    echo "To perform the actual switch, run with: --I-want-to-update"
else
    echo "Branch switch completed successfully"
fi