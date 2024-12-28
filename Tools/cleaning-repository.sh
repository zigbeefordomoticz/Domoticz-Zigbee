#!/bin/bash

# This script performs a cleanup in the local repository to allow a git pull without issues.

# Ensure the script is run from the correct directory
if [ ! -d ".git" ]; then
    echo "This script must be run from the root of the git repository."
    exit 1
fi

# Warning message
echo "WARNING: This script will remove all local changes and reset the repository."
echo "If you have made any local updates, they will be removed."
read -p "Do you want to continue? (YES/no): " choice

if [ "$choice" != "YES" ]; then
    echo "Operation cancelled."
    exit 0
fi

echo ""
echo "Removing directories tracked by git, except Data, Conf, and OTAFirmware..."
# Remove directories tracked by git, except Data and Conf
for dir in $(git ls-tree -d --name-only HEAD); do
    if [ "$dir" != "Data" ] && [ "$dir" != "Conf" ] && [ "$dir" != "OTAFirmware" ]; then
        echo "Removing $dir..."
        rm -rf "$dir"
    fi
done

echo "Resetting the repository..."
git reset --hard

echo "Pulling the latest changes from the repository..."
git pull

echo ""
echo "Cleanup and update process completed."

echo ""
echo "Repository status:"
git status

echo ""
echo "Current branch:"
git branch --show-current

echo ""
echo "Latest commits:"
git log -n 5 --oneline