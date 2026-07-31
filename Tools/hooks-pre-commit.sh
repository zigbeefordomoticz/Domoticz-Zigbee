#!/bin/sh
# Place this file in .git/hooks/pre-commit (and chmod +x) to run tests before every commit.
# Symlink: ln -s ../../Tools/hooks-pre-commit.sh .git/hooks/pre-commit

REPO_ROOT="$(git rev-parse --show-toplevel)"

echo "Running tests before commit..."

pytest "$REPO_ROOT/tests/" -v --tb=short 2>&1

if [ $? -ne 0 ]; then
    echo ""
    echo "Pre-commit check FAILED: tests did not pass. Commit aborted."
    exit 1
fi

echo "All tests passed. Proceeding with commit."
exit 0
