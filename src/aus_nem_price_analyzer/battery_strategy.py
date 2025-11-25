from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .data_loader import DataValidationError


@dataclass(frozen=True)
class BatteryResult:
    """Summary of a backtest run."""

    total_profit: float
    charge_events: int
    discharge_events: int
    cycles: int
    energy_from_grid_mwh: float
    energy_to_grid_mwh: float
    low_threshold: float
    high_threshold: float
    interval_hours: float


def _estimate_interval_hours(df: pd.DataFrame) -> float:
    """Infer interval length (hours) using median delta between timestamps."""
    deltas = df["timestamp"].sort_values().diff().dt.total_seconds().dropna()
    if deltas.empty:
        return 1.0
    median_seconds = deltas.median()
    return float(median_seconds / 3600) if median_seconds else 1.0


def battery_backtest(
    df: pd.DataFrame,
    *,
    low_quantile: float = 0.25,
    high_quantile: float = 0.75,
    round_trip_efficiency: float = 0.9,
    capacity_mwh: float = 1.0,
    power_mw: float = 1.0,
) -> BatteryResult:
    """
    Run a simple quantile-driven charge/discharge simulation.

    Beginner-friendly logic:
    - Charge when price <= low_quantile threshold and capacity remains.
    - Discharge when price >= high_quantile threshold and energy exists.
    - Round-trip efficiency is applied on discharge only (charging is assumed lossless)
      to approximate overall round-trip behaviour.
    """
    if df.empty:
        raise DataValidationError("Cannot run battery backtest on empty data.")
    if not 0 < round_trip_efficiency <= 1:
        raise DataValidationError("round_trip_efficiency must be in (0, 1].")
    if not 0 <= low_quantile < high_quantile <= 1:
        raise DataValidationError("Quantiles must satisfy 0 <= low < high <= 1.")

    sorted_df = df.sort_values("timestamp").reset_index(drop=True)
    prices = sorted_df["price"]
    # Quantile bands determine when to charge vs discharge.
    low_thr = float(prices.quantile(low_quantile))
    high_thr = float(prices.quantile(high_quantile))
    # Assume constant spacing; fall back to hourly if missing.
    interval_hours = _estimate_interval_hours(sorted_df)

    soc = 0.0
    cost = 0.0  # money spent charging
    revenue = 0.0  # money earned discharging
    charge_events = 0
    discharge_events = 0
    energy_from_grid = 0.0
    energy_to_grid = 0.0

    for price in prices:
        # Charge when price is in the low bucket and capacity remains.
        if price <= low_thr and soc < capacity_mwh:
            # Maximum energy you can add this interval based on power limit and remaining space.
            max_energy_in = power_mw * interval_hours
            allowed_in = min(max_energy_in, capacity_mwh - soc)
            if allowed_in > 0:
                # Increase state of charge by allowed energy (no loss on charge).
                soc += allowed_in
                # Pay grid price for energy pulled in.
                cost += price * allowed_in
                energy_from_grid += allowed_in
                charge_events += 1

        # Discharge when price is in the high bucket and energy is available.
        if price >= high_thr and soc > 0:
            # You cannot discharge more than current SOC or power limit.
            max_energy_out = power_mw * interval_hours
            allowed_out = min(max_energy_out, soc)
            if allowed_out > 0:
                # Apply round-trip efficiency on discharge to approximate losses.
                delivered = allowed_out * round_trip_efficiency
                soc -= allowed_out
                # Earn revenue at market price for delivered energy.
                revenue += price * delivered
                energy_to_grid += delivered
                discharge_events += 1

    cycles = min(charge_events, discharge_events)
    profit = revenue - cost
    return BatteryResult(
        total_profit=profit,
        charge_events=charge_events,
        discharge_events=discharge_events,
        cycles=cycles,
        energy_from_grid_mwh=energy_from_grid,
        energy_to_grid_mwh=energy_to_grid,
        low_threshold=low_thr,
        high_threshold=high_thr,
        interval_hours=interval_hours,
    )
