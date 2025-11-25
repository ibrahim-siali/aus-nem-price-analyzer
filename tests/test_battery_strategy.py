from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import pytest

from aus_nem_price_analyzer.battery_strategy import battery_backtest
from aus_nem_price_analyzer.data_loader import DataValidationError


def _make_price_series() -> pd.DataFrame:
    """Toy price series to exercise charge/discharge behaviour."""
    base = datetime(2021, 1, 1, tzinfo=None)
    timestamps = pd.date_range(base, base + timedelta(hours=3), freq="h", tz="UTC")
    prices = [20, 100, 200, 50]
    return pd.DataFrame({"timestamp": timestamps, "region": ["VIC1"] * 4, "price": prices})


def test_battery_backtest_produces_profit() -> None:
    df = _make_price_series()
    result = battery_backtest(df, low_quantile=0.25, high_quantile=0.75, round_trip_efficiency=0.9)
    assert result.total_profit > 0
    assert result.charge_events >= 1
    assert result.discharge_events >= 1
    assert result.cycles >= 1


def test_battery_backtest_empty_raises() -> None:
    empty = pd.DataFrame(columns=["timestamp", "region", "price"])
    with pytest.raises(DataValidationError):
        battery_backtest(empty)
