# AUS NEM Price Analyzer

Analyze Australian National Electricity Market (NEM) spot price data: load CSVs, compute summaries, detect spikes, generate plots, and run a simple battery arbitrage backtest.

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .             # or: python -m pip install -r requirements.txt
```

Run tests:
```bash
pytest
```

## CLI Usage
Run from repo root (single or multiple CSVs):
```bash
# Summary stats
aus-nem analyze data.csv --region VIC1 --start 2021-01-01 --end 2021-01-31

# Spike detection (quantile or absolute threshold)
aus-nem spikes data1.csv data2.csv --region NSW1 --quantile 0.95
aus-nem spikes data.csv --threshold 300

# Plots
aus-nem plot data.csv --kind timeseries --output-dir plots
aus-nem plot data.csv --kind daily

# Battery backtest
aus-nem battery-backtest data.csv --region SA1 --low-quantile 0.2 --high-quantile 0.8
```

## Config (optional)
Provide a YAML file to set defaults and column aliases:
```yaml
timezone: "Australia/Melbourne"
columns:
  timestamp: "SETTLEMENTDATE"
  region: "REGIONID"
  price: "RRP"
defaults:
  region: "VIC1"
  start: "2021-01-01"
  quantile: 0.95
  low_quantile: 0.2
  high_quantile: 0.8
  round_trip_efficiency: 0.9
```
Pass it via `--config config.yml` on any command. Column overrides must match the CSV headers.

## Project Layout
- `src/aus_nem_price_analyzer/`: package modules (`data_loader.py`, `analysis.py`, `plots.py`, `battery_strategy.py`, `config.py`, `cli.py`)
- `tests/`: pytest suite with synthetic data
- `docs/`: architecture notes and CLI examples
- `scripts/`: helper scripts (e.g., venv bootstrap)

## Licensing and commercial use
Apache License 2.0 (see `LICENSE`).

For commercial licensing or bespoke features, contact: real.ibby.2003@gmail.com
