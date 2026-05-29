#!/bin/sh
# Run the test suite before allowing a commit.
REPO_ROOT="$(git rev-parse --show-toplevel)"
echo "Running tests before commit..."
python3 -m unittest discover -s "$REPO_ROOT/tests" -v 2>&1
if [ $? -ne 0 ]; then
    echo ""
    echo "Pre-commit check FAILED: tests did not pass. Commit aborted."
    exit 1
fi
echo "All tests passed. Proceeding with commit."
exit 0
