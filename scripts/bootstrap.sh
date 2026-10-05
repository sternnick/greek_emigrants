#!/usr/bin/env bash
set -euo pipefail

# Enable repo-local git hooks
git config core.hooksPath .githooks
echo "core.hooksPath set to .githooks"

# Install Python deps
pip install -r requirements.txt

echo "Bootstrap complete."
