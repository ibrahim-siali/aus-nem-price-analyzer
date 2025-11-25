from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import pytest

from aus_nem_price_analyzer.analysis import compute_summary, detect_spikes, filter_data
from aus_nem_price_analyzer.data_loader import DataValidationError


def _make_df() -> pd.DataFrame:
    """Synthetic dataset with two regions for filter/spike tests."""
    base = datetime(2021, 1, 1)
    ts = pd.date_range(base, base + timedelta(hours=3), freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": ts,
            "region": ["VIC1", "VIC1", "NSW1", "NSW1"],
            "price": [50, 200, 100, 400],
            "demand": [1000, 1200, 900, 1500],
        }
    )


def test_filter_data_by_region_and_range() -> None:
    df = _make_df()
    filtered = filter_data(df, region="VIC1", start="2021-01-01 00:30", end="2021-01-01 02:00")
    assert len(filtered) == 1
    assert filtered.iloc[0]["price"] == 200


def test_compute_summary_includes_demand() -> None:
    df = _make_df()
    summary = compute_summary(df)
    assert summary["count"] == pytest.approx(4.0)
    assert summary["mean_price"] == pytest.approx(187.5)
    assert summary["mean_demand"] == pytest.approx(1150.0)
    assert summary["max_demand"] == pytest.approx(1500.0)


def test_compute_summary_empty_raises() -> None:
    empty = pd.DataFrame(columns=["timestamp", "region", "price"])
    with pytest.raises(DataValidationError):
        compute_summary(empty)


def test_detect_spikes_threshold_and_quantile() -> None:
    df = _make_df()
    events, stats = detect_spikes(df, threshold=300)
    assert len(events) == 1
    assert stats["cutoff"] == 300

    events_q, stats_q = detect_spikes(df, quantile=0.9)
    assert len(events_q) >= 1
    assert "max_spike" in stats_q
