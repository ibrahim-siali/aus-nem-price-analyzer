#!/usr/bin/env bash
set -euo pipefail

# Create and activate a virtual environment, then install dependencies in editable mode.
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
