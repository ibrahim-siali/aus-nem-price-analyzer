from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, MutableMapping, Sequence

import pandas as pd


class DataValidationError(ValueError):
    """Raised when input data fails validation or coercion."""


DEFAULT_ALIASES: Mapping[str, tuple[str, ...]] = {
    "timestamp": ("timestamp", "datetime", "settlementdate", "trading_interval"),
    "region": ("region", "regionid"),
    "price": ("price", "rrp"),
    "demand": ("demand", "totaldemand", "total_demand", "demandmw"),
}


@dataclass(frozen=True)
class LoadOptions:
    """
    Options controlling CSV loading and standardisation.

    Beginners: use `column_overrides` when your CSV headers differ from the defaults,
    and set `timezone` to match your data (e.g., "Australia/Melbourne").
    """

    column_overrides: Mapping[str, str] | None = None
    timezone: str | None = "UTC"


def _resolve_column(columns: Iterable[str], target: str, overrides: Mapping[str, str] | None) -> str | None:
    """
    Find a column matching the target role using overrides and aliases.

    Preference order:
    1) Explicit override in options.
    2) Known aliases in DEFAULT_ALIASES (case-insensitive).
    3) Otherwise return None.
    """
    normalized = {c.lower(): c for c in columns}

    if overrides and target in overrides:
        override = overrides[target]
        if override in columns:
            return override
        raise DataValidationError(f"Override for '{target}' not found in CSV: {override}")

    aliases = DEFAULT_ALIASES.get(target, ())
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    return None


def _coerce_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure required columns are non-null and properly typed.

    Raises DataValidationError when core fields contain NaT/NaN after coercion.
    """
    if df["timestamp"].isna().any():
        raise DataValidationError("Timestamp column contains invalid or missing values.")
    if df["price"].isna().any():
        raise DataValidationError("Price column contains invalid or missing values.")
    if df["region"].isna().any():
        raise DataValidationError("Region column contains invalid or missing values.")
    return df


def load_csv(file_path: str | Path, options: LoadOptions | None = None) -> pd.DataFrame:
    """
    Load a CSV file and standardise columns to timestamp, region, price, demand (optional).

    Args:
        file_path: Path to the CSV file.
        options: Optional loading options controlling overrides and timezone handling.

    Returns:
        Cleaned pandas DataFrame with standardised columns.

    Raises:
        FileNotFoundError: If the file does not exist.
        DataValidationError: When required columns are missing or invalid.

    Steps:
      1) Read CSV and resolve canonical column names (using overrides/aliases).
      2) Coerce timestamps and localize/convert to configured timezone.
      3) Coerce numeric fields; fail fast on missing/invalid required data.
      4) Sort by timestamp and return only the standard columns.
    """
    opts = options or LoadOptions()
    path = Path(file_path)
    # Check the file exists before loading to give a clear error.
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    # Raw ingest with pandas defaults; typing/cleaning happens below.
    df = pd.read_csv(path)
    if df.empty:
        raise DataValidationError("CSV file is empty.")

    resolved: MutableMapping[str, str] = {}
    # Walk through required roles and find matching columns.
    for key in ("timestamp", "region", "price"):
        column = _resolve_column(df.columns, key, opts.column_overrides)
        if not column:
            raise DataValidationError(f"Missing required column for '{key}'.")
        resolved[key] = column

    demand_col = _resolve_column(df.columns, "demand", opts.column_overrides)
    if demand_col:
        resolved["demand"] = demand_col

    # Normalize to canonical column names for downstream functions.
    rename_map = {value: key for key, value in resolved.items()}
    df = df.rename(columns=rename_map)

    # Timestamp handling
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    if opts.timezone:
        # Localize when the source is naive; otherwise convert to the configured zone.
        if df["timestamp"].dt.tz is None:
            df["timestamp"] = df["timestamp"].dt.tz_localize(
                opts.timezone, nonexistent="NaT", ambiguous="NaT"
            )
        else:
            df["timestamp"] = df["timestamp"].dt.tz_convert(opts.timezone)

    # Numeric coercion
    # Convert numeric columns so math later does not fail.
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    if "demand" in df.columns:
        df["demand"] = pd.to_numeric(df["demand"], errors="coerce")

    # Validate required fields and keep ordering predictable for downstream users.
    df = _coerce_required_columns(df)
    # Sort chronologically and only keep the standard columns.
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df[["timestamp", "region", "price", *(["demand"] if "demand" in df.columns else [])]]


def load_csvs(
    file_paths: Sequence[str | Path],
    options: LoadOptions | None = None,
    *,
    drop_duplicates: bool = True,
) -> pd.DataFrame:
    """
    Load and concatenate multiple CSV files, dropping duplicate rows by timestamp/region if requested.

    Args:
        file_paths: Iterable of CSV paths.
        options: Optional loading options.
        drop_duplicates: When True, drop duplicate (timestamp, region) rows keeping the first.

    Returns:
        Combined DataFrame sorted by timestamp.
    """
    if not file_paths:
        raise DataValidationError("No CSV files provided.")
    # Load each file independently so validation is per-file.
    frames = [load_csv(path, options=options) for path in file_paths]
    # Combine all frames into a single DataFrame.
    combined = pd.concat(frames, ignore_index=True)
    if drop_duplicates:
        # Duplicates defined by identical timestamp/region pairs.
        subset = ["timestamp", "region"]
        combined = combined.drop_duplicates(subset=subset, keep="first")
    # Keep the merged frame ordered in time.
    combined = combined.sort_values("timestamp").reset_index(drop=True)
    return combined
