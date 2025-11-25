#!/usr/bin/env bash
set -euo pipefail

# Run common CLI commands using a provided CSV path.
DATA_PATH="${1:-data.csv}"

if [[ ! -f "${DATA_PATH}" ]]; then
  echo "Data file not found at ${DATA_PATH}"
  echo "Usage: $0 /path/to/data.csv"
  exit 1
fi

echo "Analyzing ${DATA_PATH}..."
python -m aus_nem_price_analyzer.cli analyze "${DATA_PATH}" --region VIC1

echo "Detecting spikes..."
python -m aus_nem_price_analyzer.cli spikes "${DATA_PATH}" --quantile 0.95

echo "Plotting..."
python -m aus_nem_price_analyzer.cli plot "${DATA_PATH}" --kind timeseries --output-dir plots
