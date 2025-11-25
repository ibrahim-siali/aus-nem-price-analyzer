# CLI Examples

Activate your environment first:
```bash
source .venv/bin/activate
```

## Analyze summary
```bash
aus-nem analyze data.csv --region VIC1 --start 2021-01-01 --end 2021-01-31
```

## Spike detection
```bash
aus-nem spikes data1.csv data2.csv --region NSW1 --quantile 0.95
# or with absolute threshold
aus-nem spikes data.csv --threshold 300
```

## Plotting
```bash
aus-nem plot data.csv --region SA1 --kind timeseries --output-dir plots
aus-nem plot data.csv --kind daily --output-dir plots
```

## Battery backtest
```bash
aus-nem battery-backtest data.csv --region VIC1 --low-quantile 0.2 --high-quantile 0.8
```
