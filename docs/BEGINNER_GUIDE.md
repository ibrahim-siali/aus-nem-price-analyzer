# Beginner Guide: AUS NEM Price Analyzer

This guide assumes you are new to the code and to command-line Python projects. It explains the problem we solve, how the repository is structured, how to set up your environment, and how to run the code end to end.

## What Problem Are We Solving?
The Australian National Electricity Market (NEM) publishes spot prices for electricity. Analysts often get this data as CSV files (one file per month or year). Common needs:
- Clean and standardize columns (timestamps, region codes, prices, demand).
- Filter by region or date range.
- Compute quick summaries (min/mean/max, volatility).
- Find extreme price spikes.
- Visualize prices and daily patterns.
- Try a simple battery arbitrage strategy to see if buying low and selling high could make money.

This repository provides a reusable Python package and a CLI to do all of the above with minimal setup.

## Quick Setup (No Prior Experience Required)
1) Install Python 3.11+ (check with `python --version`).
2) Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3) Install the project in editable mode (so code changes are picked up automatically):
   ```bash
   python -m pip install --upgrade pip
   python -m pip install -e .
   ```
   If you prefer requirements.txt:
   ```bash
   python -m pip install -r requirements.txt
   ```
4) Run tests to verify your setup:
   ```bash
   pytest
   ```

## Typical CSV Input Shape
You need at least three columns (names can vary; see config below):
- Timestamp (e.g., `SETTLEMENTDATE`, `datetime`)
- Region (e.g., `REGIONID`, values like VIC1, NSW1)
- Price (e.g., `RRP`)
Optional: Demand (e.g., `TOTALDEMAND`)

If your columns differ, you can map them in a config file (see “Using a Config”).

## Project Layout (What Lives Where)
- `src/aus_nem_price_analyzer/data_loader.py`: Reads one or more CSVs, maps columns to standard names, coerces types, and handles timezones.
- `src/aus_nem_price_analyzer/analysis.py`: Filtering by region/date, summary stats, and spike detection.
- `src/aus_nem_price_analyzer/plots.py`: Plotting price time series and daily profiles (hourly averages).
- `src/aus_nem_price_analyzer/battery_strategy.py`: Simple quantile-based charge/discharge simulation for a 1 MWh/1 MW battery.
- `src/aus_nem_price_analyzer/config.py`: Loads YAML config for column aliases, timezone, and default CLI options.
- `src/aus_nem_price_analyzer/cli.py`: CLI entrypoints (`analyze`, `spikes`, `plot`, `battery-backtest`).
- `tests/`: Pytest suite exercising loaders, analysis, and backtest logic.
- `docs/`: Reference docs and this guide.
- `scripts/`: Helper shell scripts (e.g., `bootstrap_venv.sh`).

## How the Code Solves the Problem
1) **Loading and Cleaning** (`data_loader.py`):
   - Reads CSV(s) with pandas.
   - Renames columns to standard names using overrides/aliases.
   - Converts timestamps to timezone-aware datetimes (default UTC; configurable).
   - Converts price/demand to numeric; fails fast if required data is missing.
   - Merges multiple files and optionally drops duplicate timestamp/region rows.
2) **Filtering and Stats** (`analysis.py`):
   - Filters by region (case-insensitive) and inclusive date range.
   - Computes min/mean/median/max/std and coefficient of variation; includes demand stats if present.
   - Detects spikes by absolute threshold or by quantile (e.g., top 5% of prices).
3) **Plotting** (`plots.py`):
   - Time series plot: price vs. timestamp.
   - Daily profile: average price for each hour of the day.
   - Saves PNGs to a chosen directory.
4) **Battery Backtest** (`battery_strategy.py`):
   - Picks low/high price cutoffs from chosen quantiles.
   - Charges when price is low (until capacity or power limit reached).
   - Discharges when price is high (honoring power limit and round-trip efficiency).
   - Reports profit, cycle counts, and energy in/out.
5) **CLI Orchestration** (`cli.py`):
   - Handles arguments, loads config, calls loader/filter, then runs analysis/plots/backtest.
   - Works with one or many CSV files in one command.

## Using the CLI (Step by Step)
After `pip install -e .`, you get the `aus-nem` command:

- Summary stats:
  ```bash
  aus-nem analyze mydata.csv --region VIC1 --start 2021-01-01 --end 2021-01-31
  ```
- Spike detection:
  ```bash
  aus-nem spikes jan.csv feb.csv --region NSW1 --quantile 0.95
  # or absolute threshold
  aus-nem spikes mydata.csv --threshold 300
  ```
- Plots:
  ```bash
  aus-nem plot mydata.csv --kind timeseries --output-dir plots
  aus-nem plot mydata.csv --kind daily --output-dir plots
  ```
- Battery backtest:
  ```bash
  aus-nem battery-backtest mydata.csv --region SA1 --low-quantile 0.2 --high-quantile 0.8
  ```

## Using a Config (Column Aliases and Defaults)
Create a YAML file (see `config.example.yml`) to avoid repeating flags:
```yaml
timezone: "Australia/Melbourne"
columns:
  timestamp: "SETTLEMENTDATE"
  region: "REGIONID"
  price: "RRP"
  demand: "TOTALDEMAND"
defaults:
  region: "VIC1"
  start: "2021-01-01"
  quantile: 0.95
  low_quantile: 0.2
  high_quantile: 0.8
  round_trip_efficiency: 0.9
```
Then run:
```bash
aus-nem analyze mydata.csv --config config.example.yml
```

## Running Tests (To Verify Everything Works)
From the repo root with your venv active:
```bash
pytest
```
This runs data loader tests (column mapping, deduping), analysis tests (filtering, spikes), and battery tests (profitability, validation).

## Where to Customize
- **Column names/timezone**: edit your YAML config under `columns` and `timezone`.
- **Spike logic**: adjust `threshold` or `quantile` flags.
- **Battery behavior**: change `low_quantile`, `high_quantile`, `round_trip_efficiency`, `capacity_mwh`, `power_mw`.
- **Plots**: extend `plots.py` with new chart types (e.g., weekly profiles) and add a `--kind` option in `cli.py`.
- **Data quality checks**: add stricter validation in `data_loader.py` (e.g., allowed regions, min/max price bounds).

## Troubleshooting Tips
- Import errors in tests: ensure `pip install -e .` and that `.venv` is activated; the tests also add `src/` to `sys.path` via `tests/conftest.py`.
- Timezone errors: set `timezone` in config to match your data; mixed tz-naive and tz-aware inputs are handled by aligning to the DataFrame’s timezone.
- Empty outputs: check your filters (`--region`, `--start`, `--end`) and that your CSV columns match the expected names or config overrides.
- Duplicate rows across files: defaults drop duplicate `(timestamp, region)` pairs; pass `--keep-duplicates` if you want raw data.

## Next Steps for Beginners
- Start with a tiny CSV (2–3 rows) to confirm the CLI works.
- Open `tests/` to see small, readable examples of the expected data shapes.
- Try `scripts/run_examples.sh /path/to/your.csv` for a quick demo.
- Read the inline comments in `src/` files; they explain each operation in plain language.
