# Architecture Overview

## Modules
- `data_loader.py`: Reads one or more CSVs, maps common column names to `timestamp`, `region`, `price`, `demand`, coerces dtypes, optionally drops duplicate `(timestamp, region)` rows, and raises `DataValidationError` on missing/invalid data.
- `analysis.py`: Filtering by region/date (tz-aware) and computing summary stats plus spike detection.
- `plots.py`: Matplotlib helpers for price time series and hourly profiles.
- `battery_strategy.py`: Simple quantile-driven charge/discharge simulation with configurable round-trip efficiency, returning `BatteryResult`.
- `config.py`: Optional YAML loader for column overrides, timezone defaults, and per-command defaults.
- `cli.py`: Click-based entrypoints (`analyze`, `spikes`, `plot`, `battery-backtest`) that orchestrate the above modules and apply config defaults.

## Data Flow
1. `cli.py` parses arguments and loads config (if provided).
2. `data_loader.load_csv` ingests CSVs and standardises column names and dtypes.
3. `analysis.filter_data` trims by region and date; other analysis functions compute summaries or spikes.
4. `plots` or `battery_strategy` run on the filtered DataFrame.

## Error Handling
- Input validation failures raise `DataValidationError`; the CLI converts these to friendly messages.
- Missing files raise `FileNotFoundError` up-front. Timezone handling defaults to UTC but can be overridden in config.
