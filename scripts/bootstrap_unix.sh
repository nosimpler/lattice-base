#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:-myproj}"
PROJECT_NAME="${2:-My Project}"

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install "lattice-base @ git+https://github.com/your-user/lattice-base.git"

# Initialize a new lattice for this repo
lattice-base-init --repo . --id "$PROJECT_ID" --name "$PROJECT_NAME"

# Sanity check the lattice and reconcile test status
lattice-base-validate --repo .
lattice-base-test --complete

# Emit a Mermaid diagram of the lattice
lattice-base-mermaid --repo . > lattice.mmd
