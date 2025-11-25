from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping, Optional

import click
import pandas as pd

from .analysis import compute_summary, detect_spikes, filter_data
from .battery_strategy import battery_backtest
from .config import load_config
from .data_loader import DataValidationError, LoadOptions, load_csvs
from .plots import plot_daily_profile, plot_price_timeseries


def _parse_datetime(value: Optional[str], tz: Optional[str]) -> Optional[pd.Timestamp]:
    """Parse a datetime string and localize/convert to the target timezone."""
    if value is None:
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise click.BadParameter(f"Invalid datetime: {value}")
    if tz:
        parsed = parsed.tz_localize(tz) if parsed.tzinfo is None else parsed.tz_convert(tz)
    return parsed


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli() -> None:
    """CLI for AUS NEM Price Analyzer."""


def _defaults(cfg: Mapping[str, object], key: str) -> Optional[object]:
    """
    Fetch a default value from a loaded config mapping.

    Beginners: put common defaults under `defaults:` in YAML to avoid repeating flags.
    """
    defaults = cfg.get("defaults") if isinstance(cfg.get("defaults"), dict) else {}
    return defaults.get(key)


def _load_and_filter(
    file_paths: Iterable[Path],
    region: Optional[str],
    start: Optional[str],
    end: Optional[str],
    cfg: Mapping[str, object],
    drop_duplicates: bool,
) -> pd.DataFrame:
    """
    Load one or more CSVs, apply configuration, and filter by region/date.

    The result is the cleaned, filtered DataFrame used by all subcommands.
    """
    tz = cfg.get("timezone", "UTC")
    # Allow CLI flags to override config defaults when provided.
    region = region or _defaults(cfg, "region")
    start = start or _defaults(cfg, "start")
    end = end or _defaults(cfg, "end")

    options = LoadOptions(
        column_overrides=cfg.get("columns") if isinstance(cfg.get("columns"), dict) else None,
        timezone=tz,
    )
    # Combine files, clean them, and apply dedupe if requested.
    df = load_csvs(list(file_paths), options=options, drop_duplicates=drop_duplicates)
    return filter_data(df, region=region, start=_parse_datetime(start, tz), end=_parse_datetime(end, tz))


@cli.command()
@click.argument("file_paths", nargs=-1, type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True)
@click.option("--region", help="Filter by region code (e.g. VIC1).")
@click.option("--start", help="Inclusive start datetime (e.g. 2021-01-01).")
@click.option("--end", help="Inclusive end datetime (e.g. 2021-12-31).")
@click.option("--config", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="Optional YAML config.")
@click.option("--keep-duplicates", is_flag=True, help="Keep duplicate timestamp/region rows across files.")
def analyze(
    file_paths: tuple[Path, ...],
    region: Optional[str],
    start: Optional[str],
    end: Optional[str],
    config: Optional[Path],
    keep_duplicates: bool,
) -> None:
    """Compute summary statistics for one or more CSV files."""
    try:
        cfg = load_config(config)
        df = _load_and_filter(file_paths, region, start, end, cfg, drop_duplicates=not keep_duplicates)
        summary = compute_summary(df)
    except (FileNotFoundError, DataValidationError) as err:
        raise click.ClickException(str(err)) from err

    click.echo("Summary statistics:")
    for key, value in summary.items():
        click.echo(f"- {key}: {value}")


@cli.command()
@click.argument("file_paths", nargs=-1, type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True)
@click.option("--region", help="Filter by region code (e.g. NSW1).")
@click.option("--start", help="Inclusive start datetime.")
@click.option("--end", help="Inclusive end datetime.")
@click.option("--threshold", type=float, help="Absolute price threshold for spikes.")
@click.option("--quantile", type=float, default=0.95, show_default=True, help="Quantile for spike detection.")
@click.option("--config", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="Optional YAML config.")
@click.option("--keep-duplicates", is_flag=True, help="Keep duplicate timestamp/region rows across files.")
def spikes(
    file_paths: tuple[Path, ...],
    region: Optional[str],
    start: Optional[str],
    end: Optional[str],
    threshold: Optional[float],
    quantile: Optional[float],
    config: Optional[Path],
    keep_duplicates: bool,
) -> None:
    """List spike events for one or more CSV files."""
    try:
        cfg = load_config(config)
        # Prefer explicit CLI inputs; otherwise fallback to config defaults.
        threshold = threshold if threshold is not None else _defaults(cfg, "threshold")
        quantile = quantile if quantile is not None else _defaults(cfg, "quantile")
        if threshold is not None:
            threshold = float(threshold)
        if quantile is not None:
            quantile = float(quantile)
        df = _load_and_filter(file_paths, region, start, end, cfg, drop_duplicates=not keep_duplicates)
        events, stats = detect_spikes(df, threshold=threshold, quantile=quantile)
    except (FileNotFoundError, DataValidationError) as err:
        raise click.ClickException(str(err)) from err

    click.echo(f"Cutoff: {stats['cutoff']}")
    click.echo(f"Spike count: {stats['spike_count']}")
    if "max_spike" in stats:
        click.echo(f"Max spike: {stats['max_spike']}")
        click.echo(f"Mean spike: {stats['mean_spike']}")

    if events.empty:
        click.echo("No spikes detected.")
        return

    click.echo("\nSpike events (first 5):")
    preview = events.head(5)[["timestamp", "region", "price"]]
    click.echo(preview.to_string(index=False))


@cli.command()
@click.argument("file_paths", nargs=-1, type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True)
@click.option("--region", help="Filter by region code.")
@click.option("--start", help="Inclusive start datetime.")
@click.option("--end", help="Inclusive end datetime.")
@click.option("--kind", type=click.Choice(["timeseries", "daily"], case_sensitive=False), default="timeseries", show_default=True)
@click.option("--output-dir", type=click.Path(file_okay=False, path_type=Path), default=Path("plots"), show_default=True)
@click.option("--config", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="Optional YAML config.")
@click.option("--keep-duplicates", is_flag=True, help="Keep duplicate timestamp/region rows across files.")
def plot(
    file_paths: tuple[Path, ...],
    region: Optional[str],
    start: Optional[str],
    end: Optional[str],
    kind: str,
    output_dir: Path,
    config: Optional[Path],
    keep_duplicates: bool,
) -> None:
    """Generate plots for the dataset."""
    try:
        cfg = load_config(config)
        default_kind = _defaults(cfg, "plot_kind")
        if default_kind and kind == "timeseries":
            kind = default_kind
        if isinstance(cfg.get("output_dir"), (str, Path)):
            output_dir = Path(cfg["output_dir"])
        df = _load_and_filter(file_paths, region, start, end, cfg, drop_duplicates=not keep_duplicates)
    except (FileNotFoundError, DataValidationError) as err:
        raise click.ClickException(str(err)) from err

    output_dir.mkdir(parents=True, exist_ok=True)
    selected_kind = str(kind).lower()
    output_path = output_dir / ("price_timeseries.png" if selected_kind == "timeseries" else "daily_profile.png")

    if selected_kind == "timeseries":
        saved = plot_price_timeseries(df, output_path)
    else:
        saved = plot_daily_profile(df, output_path)

    click.echo(f"Plot saved to: {saved}")


@cli.command(name="battery-backtest")
@click.argument("file_paths", nargs=-1, type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True)
@click.option("--region", help="Filter by region code.")
@click.option("--start", help="Inclusive start datetime.")
@click.option("--end", help="Inclusive end datetime.")
@click.option("--low-quantile", type=float, default=0.25, show_default=True)
@click.option("--high-quantile", type=float, default=0.75, show_default=True)
@click.option("--round-trip-efficiency", type=float, default=0.9, show_default=True)
@click.option("--capacity-mwh", type=float, default=1.0, show_default=True)
@click.option("--power-mw", type=float, default=1.0, show_default=True)
@click.option("--config", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="Optional YAML config.")
@click.option("--keep-duplicates", is_flag=True, help="Keep duplicate timestamp/region rows across files.")
def battery_backtest_cmd(
    file_paths: tuple[Path, ...],
    region: Optional[str],
    start: Optional[str],
    end: Optional[str],
    low_quantile: float,
    high_quantile: float,
    round_trip_efficiency: float,
    capacity_mwh: float,
    power_mw: float,
    config: Optional[Path],
    keep_duplicates: bool,
) -> None:
    """Run the simple battery arbitrage backtest."""
    try:
        cfg = load_config(config)
        low_quantile = low_quantile if low_quantile is not None else _defaults(cfg, "low_quantile")
        high_quantile = high_quantile if high_quantile is not None else _defaults(cfg, "high_quantile")
        rte_cfg = _defaults(cfg, "round_trip_efficiency")
        if rte_cfg is not None and round_trip_efficiency == 0.9:
            round_trip_efficiency = float(rte_cfg)

        df = _load_and_filter(file_paths, region, start, end, cfg, drop_duplicates=not keep_duplicates)
        result = battery_backtest(
            df,
            low_quantile=low_quantile,
            high_quantile=high_quantile,
            round_trip_efficiency=round_trip_efficiency,
            capacity_mwh=capacity_mwh,
            power_mw=power_mw,
        )
    except (FileNotFoundError, DataValidationError) as err:
        raise click.ClickException(str(err)) from err

    click.echo("Battery backtest results:")
    click.echo(f"- Profit: {result.total_profit:.2f}")
    click.echo(f"- Cycles: {result.cycles}")
    click.echo(f"- Charge events: {result.charge_events}")
    click.echo(f"- Discharge events: {result.discharge_events}")
    click.echo(f"- Energy from grid (MWh): {result.energy_from_grid_mwh:.3f}")
    click.echo(f"- Energy to grid (MWh): {result.energy_to_grid_mwh:.3f}")
    click.echo(f"- Low threshold: {result.low_threshold:.2f}")
    click.echo(f"- High threshold: {result.high_threshold:.2f}")
    click.echo(f"- Interval hours: {result.interval_hours:.3f}")


if __name__ == "__main__":
    cli()
