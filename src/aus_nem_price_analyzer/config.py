from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml


def load_config(path: str | Path | None) -> Mapping[str, Any]:
    """
    Load a YAML config file; return an empty dict when not provided.

    Expected shape:
      timezone: "UTC"
      columns: { timestamp: "...", region: "...", price: "...", demand: "..." }
      defaults: { region: "VIC1", start: "...", quantile: 0.95, ... }
    """
    if path is None:
        return {}
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        # safe_load prevents execution of arbitrary YAML tags.
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("Config file must contain a top-level mapping.")
    return data
