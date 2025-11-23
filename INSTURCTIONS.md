# Project: AUS NEM Price Analyzer

## 1. Overview

This project is a professional-grade Python tool for analysing Australian National Electricity Market (NEM) spot price and demand data.

Given one or more CSV files exported from AEMO (or similar sources), the tool will:
- Load and validate the time-series data (timestamps, region, price, demand).
- Provide basic analytics (summary statistics, price distributions, volatility indicators).
- Identify and report price spike events.
- Generate simple, publication-quality plots (price vs time, daily/weekly profiles).
- Optionally run a very simple battery arbitrage backtest (e.g. 1 MW / 1 MWh battery, quantile-based strategy).

The code is structured as a reusable Python package with a command-line interface (CLI), unit tests, and clear documentation. It is deliberately designed to be extended later into more advanced energy-trading or operations tools.

## 2. Tech Stack

- Language:
  - Python 3.12 (or latest stable Python 3.x available on the system).

- Core libraries:
  - `pandas` for data loading and time-series manipulation.
  - `numpy` for numerical operations.
  - `matplotlib` for plotting.
  - `click` for building the CLI.
  - `pyyaml` (optional) for configuration files.

- Testing:
  - `pytest` for automated tests.

- Tooling:
  - `venv` (or equivalent) for a dedicated virtual environment.
  - `pip` or `pip-tools` for dependency management.
  - `pre-commit` (optional stretch) for linting and formatting hooks.

## 3. File & Folder Structure

Target repository layout:

- `src/`
  - `aus_nem_price_analyzer/`
    - `__init__.py`
    - `cli.py`              # All CLI entry-points (using click)
    - `data_loader.py`      # CSV loading and validation
    - `models.py`           # Typed dataclasses / simple models (if needed)
    - `analysis.py`         # Summary metrics and spike detection
    - `plots.py`            # Plotting utilities (uses matplotlib)
    - `battery_strategy.py` # Simple battery arbitrage backtest logic
    - `config.py`           # Config structures and parsing (if using YAML)
- `tests/`
  - `test_data_loader.py`
  - `test_analysis.py`
  - `test_battery_strategy.py`
- `docs/`
  - `architecture.md`      # High-level design and module responsibilities
  - `examples.md`          # Example CLI commands and sample outputs
- `scripts/`
  - `bootstrap_venv.sh`    # Optional helper to create and activate venv
  - `run_examples.sh`      # Example commands for demoing the tool
- `.vscode/`
  - `settings.json`        # Optional VS Code config (linting, formatting, pytest)
- `README.md`
- `INSTRUCTIONS.md`
- `.gitignore`
- `pyproject.toml` or `requirements.txt`   # Dependencies
- `LICENSE` (optional, e.g. MIT)

Notes:
- The package name `aus_nem_price_analyzer` should be importable as `import aus_nem_price_analyzer`.
- The CLI should be invokable from the project root via `python -m aus_nem_price_analyzer.cli ...` during development.

## 4. Coding Standards

- Follow PEP 8 style guidelines.
- Use type hints for all public functions and methods.
- Use docstrings (`"""..."""`) for:
  - All public functions, methods, and classes.
  - Any non-trivial internal function whose purpose is not obvious.
- Prefer small, pure functions where possible.
- Keep modules focused:
  - `data_loader.py` only handles loading and validating raw data into clean DataFrames.
  - `analysis.py` only handles calculations on already-clean data.
  - `battery_strategy.py` only handles battery backtest logic.
- Error handling:
  - Fail fast and clearly when input data is invalid (bad columns, wrong dtypes).
  - Use custom exception types where appropriate (e.g. `DataValidationError`).

## 5. Requirements / Features

### 5.1 Core MVP Features

1. **Load NEM-style CSV file**
   - Input: Path to a CSV file with at least:
     - Timestamp column (e.g. `SETTLEMENTDATE`).
     - Regional reference price column (e.g. `RRP`).
     - Region identifier (e.g. `REGION` or `REGIONID`).
   - Behaviour:
     - Parse timestamps into timezone-aware `datetime` (or at least naive UTC).
     - Coerce numerical columns into `float`.
     - Validate presence of required columns; raise a clear error if missing.
     - Return a clean `pandas.DataFrame` with a standardised column set (e.g. `timestamp`, `region`, `price`, `demand` if present).

2. **Filter by region and date range**
   - Given a target region (e.g. `VIC1`) and an optional date range (`start`, `end`):
     - Filter the DataFrame accordingly.
   - Provide a simple API such as:
     - `filter_data(df, region="VIC1", start=None, end=None) -> DataFrame`.

3. **Basic price and demand summary**
   - Compute summary statistics for the filtered dataset, including:
     - Count of intervals.
     - Mean, median, min, max price.
     - Standard deviation and a simple volatility measure (e.g. coefficient of variation).
     - (If demand column available) mean and peak demand.
   - Return these metrics as a small dictionary or `pandas.Series`.

4. **Price spike detection**
   - Identify and return rows where price exceeds a specified threshold (e.g. > $300/MWh) or is within the top X% of the distribution (e.g. > 95th percentile).
   - Allow threshold to be specified as:
     - An absolute value (`--threshold 300`).
     - A quantile (`--quantile 0.95`).
   - Output:
     - A DataFrame of spike events (timestamp, price, region, and optionally demand).
     - Summary metrics (number of spikes, max spike, average spike level).

5. **Basic CLI commands**
   - Implement a top-level CLI group, for example:
     - `aus-nem analyze` → run summary analysis on a file.
     - `aus-nem spikes` → list spike events for a file.
   - Each command should:
     - Accept file path, region, date range, and threshold/quantile options.
     - Print human-readable summaries to stdout.
     - Optionally write CSV summaries to an output file if `--output` is provided.

6. **Simple plotting**
   - At minimum:
     - Line plot of price vs time for a given region and date range.
   - Optional enhancements:
     - Aggregated daily profile (average price by hour of day).
     - Aggregated weekly profile (average price by day of week).
   - Output:
     - Save plots as `.png` files to a specified folder (e.g. `./plots/`), with sensible filenames.

### 5.2 Nice-to-Have / Stretch Features

1. **Simple battery arbitrage backtest**
   - Assume a 1 MW / 1 MWh battery with:
     - Round-trip efficiency parameter (e.g. 0.9).
     - Max charge/discharge rate equal to 1 MW.
   - Strategy (baseline):
     - Define a low-price quantile (e.g. 25th percentile) and high-price quantile (e.g. 75th or 90th percentile).
     - Charge when price is in the low quantile range and battery is not full.
     - Discharge when price is in the high quantile range and battery is not empty.
   - Output:
     - Total profit over the period.
     - Number of charge/discharge cycles.
     - Simple utilisation metrics (capacity factor, hours at full charge, etc.).

2. **Multi-file support**
   - Allow passing multiple CSV files to the CLI (e.g. a full year split by month).
   - Concatenate them safely, with duplicate handling if needed.

3. **Config file support**
   - Optional YAML config for:
     - Default region.
     - Default date range.
     - Default thresholds/quantiles.
     - Default battery parameters.
   - Allow a flag like `--config config.yml` to override CLI defaults.

4. **Packaging niceties**
   - `pyproject.toml` with proper metadata (name, version, description).
   - An installable entry point so that, after `pip install -e .`, the CLI can be run as:
     - `aus-nem ...`

## 6. Implementation Order

Codex should implement features in the following sequence:

1. **Project scaffolding**
   - Create the `src/aus_nem_price_analyzer/` package with `__init__.py`.
   - Create empty modules: `cli.py`, `data_loader.py`, `analysis.py`, `plots.py`, `battery_strategy.py`, `config.py`.
   - Create initial `tests/` modules for each main component with placeholder tests.
   - Add `requirements.txt` or `pyproject.toml` listing core dependencies.

2. **Data loader**
   - Implement functions to:
     - Load a single CSV into a DataFrame.
     - Standardise column names (`timestamp`, `region`, `price`, `demand` if present).
     - Validate types and presence of required columns.
   - Write tests in `test_data_loader.py` using small synthetic CSV samples.

3. **Filtering & summary analysis**
   - Implement filtering utilities (region and date range).
   - Implement summary metrics in `analysis.py`.
   - Write tests in `test_analysis.py` for these functions.

4. **Price spike detection**
   - Implement quantile and threshold-based spike detection.
   - Update `analysis.py` and tests accordingly.

5. **CLI commands**
   - Implement CLI in `cli.py` using `click`:
     - A base group command.
     - Subcommands: `analyze`, `spikes`, and `plot` (for basic plots).
   - Ensure CLI commands call the functions in `data_loader.py`, `analysis.py`, and `plots.py`.

6. **Plotting utilities**
   - Implement plotting in `plots.py`:
     - Price vs time line plot.
   - Optionally, daily/weekly profiles.
   - No tests strictly required for plotting in MVP, but at least ensure functions run without error on simple test data.

7. **Battery arbitrage (stretch)**
   - Implement simple backtest strategy in `battery_strategy.py`.
   - Add a CLI subcommand, e.g. `aus-nem battery-backtest`.
   - Write corresponding tests in `test_battery_strategy.py` using synthetic price series.

8. **Docs and examples**
   - Fill out `docs/architecture.md` explaining module responsibilities and data flow.
   - Fill out `docs/examples.md` with example CLI commands and screenshots or textual description of outputs.

## 7. How AI (Codex) Must Work With This

When using Codex (or an equivalent AI code assistant) in the project root:

1. **Initial step – understanding**
   - Read the full `INSTRUCTIONS.md`.
   - Summarise the project in 5–10 bullet points.
   - Restate the implementation order and confirm understanding.

2. **Planning**
   - Propose a concrete, step-by-step plan that follows the Implementation Order:
     - For each step, list:
       - Files to create or modify.
       - Functions or classes to implement.
       - Tests to write or update.

3. **Implementation style**
   - Implement the project incrementally:
     - Complete one logical step (e.g. data loader + tests), then stop and summarise.
     - After each step, output:
       - What files were created/modified.
       - A summary of the functionality added.
       - Exact commands to run tests or demos (e.g. `pytest tests/test_data_loader.py`, `python -m aus_nem_price_analyzer.cli analyze ...`).
   - Restrict code changes to:
     - `src/aus_nem_price_analyzer/`
     - `tests/`
     - `docs/`
     - Project config files (`requirements.txt`, `pyproject.toml`, etc.)
   - Do **not** delete or radically restructure the project without explicit instructions.

4. **Quality expectations**
   - Ensure all tests pass before moving to the next implementation step.
   - Use type hints and docstrings for all new public functions.
   - Keep functions focused and small.
   - Avoid overcomplicating abstractions at this stage; prioritise clarity and reliability.

5. **Interaction loop**
   - After each major step:
     - Codex summarises changes and suggests the next step.
     - The human (user) reviews diffs, runs tests, and commits changes via Git.
     - Once happy, the human tells Codex to proceed.

6. **Non-goals for this phase**
   - Do not introduce external services, databases, or web UIs.
   - Do not attempt to fully automate data downloads from AEMO yet.
   - Do not add advanced optimisation or forecasting; keep the battery strategy intentionally simple.

This document fully specifies the requirements and structure for the initial version of the AUS NEM Price Analyzer project. Codex must follow these instructions as the source of truth during implementation.
