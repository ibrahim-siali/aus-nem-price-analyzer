from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from aus_nem_price_analyzer.data_loader import DataValidationError, LoadOptions, load_csv
from aus_nem_price_analyzer.data_loader import load_csvs


def test_load_csv_standardizes_columns(tmp_path: Path) -> None:
    csv = tmp_path / "sample.csv"
    csv.write_text(
        "SETTLEMENTDATE,REGIONID,RRP,TOTALDEMAND\n"
        "2021-01-01 00:00,VIC1,50,1000\n"
        "2021-01-01 00:30,VIC1,75,1100\n",
        encoding="utf-8",
    )

    df = load_csv(csv)

    assert list(df.columns) == ["timestamp", "region", "price", "demand"]
    assert isinstance(df["timestamp"].dtype, pd.DatetimeTZDtype)
    assert df["price"].iloc[0] == 50
    assert df["region"].iloc[0] == "VIC1"


def test_load_csv_respects_overrides(tmp_path: Path) -> None:
    csv = tmp_path / "override.csv"
    csv.write_text("time,zone,price_value\n2021-01-01 00:00,VIC1,100\n", encoding="utf-8")

    options = LoadOptions(column_overrides={"timestamp": "time", "region": "zone", "price": "price_value"})
    df = load_csv(csv, options=options)

    assert df.loc[0, "price"] == 100
    assert df.loc[0, "region"] == "VIC1"


def test_load_csv_missing_column_raises(tmp_path: Path) -> None:
    csv = tmp_path / "bad.csv"
    csv.write_text("timestamp,region\n2021-01-01 00:00,VIC1\n", encoding="utf-8")

    with pytest.raises(DataValidationError):
        load_csv(csv)


def test_load_csv_invalid_timestamp_raises(tmp_path: Path) -> None:
    csv = tmp_path / "bad_ts.csv"
    csv.write_text("timestamp,region,price\ninvalid,VIC1,50\n", encoding="utf-8")

    with pytest.raises(DataValidationError):
        load_csv(csv)


def test_load_csvs_concat_and_deduplicate(tmp_path: Path) -> None:
    """Ensure multiple files combine and drop duplicate timestamp/region rows."""
    csv1 = tmp_path / "part1.csv"
    csv2 = tmp_path / "part2.csv"
    csv1.write_text(
        "SETTLEMENTDATE,REGIONID,RRP\n2021-01-01 00:00,VIC1,50\n2021-01-01 00:30,VIC1,60\n",
        encoding="utf-8",
    )
    csv2.write_text(
        "SETTLEMENTDATE,REGIONID,RRP\n2021-01-01 00:30,VIC1,70\n2021-01-01 01:00,VIC1,80\n",
        encoding="utf-8",
    )

    df = load_csvs([csv1, csv2], drop_duplicates=True)
    assert len(df) == 3
    assert df["price"].iloc[-1] == 80
