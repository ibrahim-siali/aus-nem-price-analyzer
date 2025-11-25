from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from .data_loader import DataValidationError


def _ensure_output_path(output_path: str | Path) -> Path:
    """Create parent directories as needed and return a Path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def plot_price_timeseries(df: pd.DataFrame, output_path: str | Path) -> Path:
    """
    Plot price over time and save to the provided path.

    Returns the output path so callers can print/verify location.
    """
    if df.empty:
        raise DataValidationError("Cannot plot empty data.")
    sorted_df = df.sort_values("timestamp")
    fig, ax = plt.subplots(figsize=(10, 4))
    # Simple line plot of price vs time for the requested slice.
    ax.plot(sorted_df["timestamp"], sorted_df["price"], label="Price")
    ax.set_title("Price over time")
    ax.set_xlabel("Timestamp")  # x-axis shows time
    ax.set_ylabel("Price ($/MWh)")  # y-axis shows price
    ax.grid(True, alpha=0.3)
    ax.legend()

    output = _ensure_output_path(output_path)
    fig.autofmt_xdate()  # rotate date labels for readability
    fig.tight_layout()  # reduce whitespace
    fig.savefig(output, dpi=150)  # write PNG to disk
    plt.close(fig)
    return output


def plot_daily_profile(df: pd.DataFrame, output_path: str | Path) -> Path:
    """
    Plot average price by hour of day.

    Requires a datetime-like timestamp column to extract hour.
    """
    if df.empty:
        raise DataValidationError("Cannot plot empty data.")
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        raise DataValidationError("Timestamp column must be datetime-like.")

    # Work on a copy to avoid mutating caller data.
    data = df.copy()
    data["hour"] = data["timestamp"].dt.hour  # extract hour-of-day
    grouped = data.groupby("hour")["price"].mean()  # average price per hour

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(grouped.index, grouped.values, width=0.8)
    ax.set_title("Average price by hour of day")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Price ($/MWh)")
    ax.grid(True, axis="y", alpha=0.3)

    output = _ensure_output_path(output_path)
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    return output
