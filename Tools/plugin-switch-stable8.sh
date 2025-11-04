#!/bin/bash

# Exit on error
set -e

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$(dirname "$SCRIPT_DIR")"  # Go to parent directory of Tools/

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

# Switch to stable8 branch
echo "Switching to stable8 branch..."
if git show-ref --verify --quiet refs/remotes/origin/stable8; then
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
    echo "Error: stable8 branch does not exist in the remote repository"
    exit 1
fi

# Return to original directory
cd "$CURRENT_DIR"

echo "Branch switch completed successfully"