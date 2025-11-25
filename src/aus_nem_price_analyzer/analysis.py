from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

import pandas as pd

from .data_loader import DataValidationError


def _coerce_timestamp(value: Any, tz) -> pd.Timestamp | None:
    """
    Parse a datetime-like value and align it to the provided timezone.

    This keeps comparisons safe even for beginners mixing naive and tz-aware inputs.
    """
    if value is None:
        return None
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        raise DataValidationError(f"Invalid datetime value: {value}")
    if tz:
        ts = ts.tz_localize(tz) if ts.tzinfo is None else ts.tz_convert(tz)
    elif ts.tzinfo is not None:
        ts = ts.tz_localize(None)
    return ts


def filter_data(
    df: pd.DataFrame,
    *,
    region: str | None = None,
    start: datetime | str | None = None,
    end: datetime | str | None = None,
) -> pd.DataFrame:
    """
    Filter by region and optional date range (inclusive start, inclusive end).

    All comparisons use the timezone present on the DataFrame so beginners do not
    have to reason about tz-aware vs tz-naive mismatches.
    """
    filtered = df
    if region:
        # Match region case-insensitively so users do not worry about casing.
        filtered = filtered[filtered["region"].str.upper() == region.upper()]
    tz = filtered["timestamp"].dt.tz
    # Align string inputs to the same timezone as the dataset before comparing.
    start_ts = _coerce_timestamp(start, tz)
    end_ts = _coerce_timestamp(end, tz)
    if start_ts is not None:
        # Inclusive lower bound on timestamp.
        filtered = filtered[filtered["timestamp"] >= start_ts]
    if end_ts is not None:
        # Inclusive upper bound on timestamp.
        filtered = filtered[filtered["timestamp"] <= end_ts]
    return filtered.reset_index(drop=True)


def compute_summary(df: pd.DataFrame) -> Mapping[str, float]:
    """
    Return core summary statistics for price (and demand if present).

    Uses population std dev (ddof=0) and adds coefficient of variation when mean != 0.
    If demand exists, mean and max demand are included as well.
    """
    if df.empty:
        raise DataValidationError("Cannot compute summary on empty dataset.")

    # Work with the price series directly for convenience.
    price = df["price"]
    summary: dict[str, float] = {
        # Cast to float so JSON serialization is safe.
        "count": float(len(price)),
        "mean_price": float(price.mean()),
        "median_price": float(price.median()),
        "min_price": float(price.min()),
        "max_price": float(price.max()),
        "std_price": float(price.std(ddof=0)),
    }
    if summary["mean_price"]:
        # Coefficient of variation = std / mean.
        summary["coeff_var"] = summary["std_price"] / summary["mean_price"]
    if "demand" in df.columns:
        demand = df["demand"].dropna()
        if not demand.empty:
            # Demand stats only when column exists and has data.
            summary["mean_demand"] = float(demand.mean())
            summary["max_demand"] = float(demand.max())
    return summary


def detect_spikes(
    df: pd.DataFrame, *, threshold: float | None = None, quantile: float | None = 0.95
) -> tuple[pd.DataFrame, Mapping[str, float]]:
    """
    Detect price spikes by absolute threshold or quantile.

    Returns:
        events_df: rows meeting/exceeding the cutoff.
        stats: cutoff and basic event summary (counts and max/mean when present).
    """
    if df.empty:
        raise DataValidationError("Cannot detect spikes on empty dataset.")
    if threshold is None and quantile is None:
        raise DataValidationError("Provide either threshold or quantile.")

    price = df["price"]
    cutoff = threshold
    if cutoff is None:
        if quantile is None or not 0 <= quantile <= 1:
            raise DataValidationError("Quantile must be between 0 and 1.")
        # Compute the price cutoff from the chosen quantile.
        cutoff = float(price.quantile(quantile))

    # Keep rows meeting or exceeding the cutoff, preserving original fields.
    events = df[df["price"] >= cutoff].copy()
    stats: dict[str, float] = {
        "cutoff": float(cutoff),  # the threshold actually used
        "spike_count": float(len(events)),  # how many rows met/exceeded it
    }
    if not events.empty:
        stats["max_spike"] = float(events["price"].max())
        stats["mean_spike"] = float(events["price"].mean())
    return events.reset_index(drop=True), stats
