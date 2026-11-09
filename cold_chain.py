"""Core data processing for the pharmaceutical cold-chain dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

import pandas as pd

REQUIRED_COLUMNS = {"timestamp", "device_id", "location", "temperature"}


def load_readings(source: str | Path | BinaryIO) -> pd.DataFrame:
    """Load and validate readings from a CSV source."""
    readings = pd.read_csv(source)
    missing = REQUIRED_COLUMNS - set(readings.columns)
    if missing:
        missing_columns = ", ".join(sorted(missing))
        raise ValueError(f"CSV 缺少必需字段：{missing_columns}")

    readings = readings.copy()
    readings["timestamp"] = pd.to_datetime(readings["timestamp"], errors="coerce")
    readings["temperature"] = pd.to_numeric(readings["temperature"], errors="coerce")
    readings = readings.dropna(subset=["timestamp", "temperature", "device_id", "location"])
    if readings.empty:
        raise ValueError("CSV 中没有可用的温度记录")

    return readings.sort_values("timestamp").reset_index(drop=True)


def classify_readings(
    readings: pd.DataFrame,
    lower_limit: float = 2.0,
    upper_limit: float = 8.0,
) -> pd.DataFrame:
    """Add alarm status and deviation columns to validated readings."""
    if lower_limit >= upper_limit:
        raise ValueError("下限必须小于上限")

    result = readings.copy()
    result["status"] = "正常"
    result.loc[result["temperature"] < lower_limit, "status"] = "低温"
    result.loc[result["temperature"] > upper_limit, "status"] = "超温"
    result["deviation"] = result["temperature"].clip(lower=lower_limit, upper=upper_limit)
    result["deviation"] = result["temperature"] - result["deviation"]
    return result


def summarize_readings(readings: pd.DataFrame) -> dict[str, int | float]:
    """Return dashboard KPIs for classified readings."""
    total = len(readings)
    alarms = int((readings["status"] != "正常").sum())
    return {
        "total": total,
        "devices": int(readings["device_id"].nunique()),
        "alarms": alarms,
        "alarm_rate": round(alarms / total * 100, 1) if total else 0.0,
        "average": round(float(readings["temperature"].mean()), 1),
    }
