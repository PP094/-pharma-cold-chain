import pandas as pd
import pytest

from cold_chain import classify_readings, load_readings, summarize_readings


def test_load_and_classify_sample_data():
    readings = load_readings("data/sample_temperature.csv")
    classified = classify_readings(readings)

    assert len(classified) == 12
    assert set(classified["status"]) == {"正常", "低温", "超温"}
    assert summarize_readings(classified) == {
        "total": 12,
        "devices": 4,
        "alarms": 2,
        "alarm_rate": 16.7,
        "average": 5.3,
    }


def test_load_readings_rejects_missing_columns(tmp_path):
    source = tmp_path / "invalid.csv"
    pd.DataFrame({"timestamp": ["2026-01-01"], "temperature": [4]}).to_csv(source, index=False)

    with pytest.raises(ValueError, match="CSV 缺少必需字段"):
        load_readings(source)


def test_classify_rejects_invalid_limits():
    readings = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-01-01"]),
            "device_id": ["D-1"],
            "location": ["冷库"],
            "temperature": [4.0],
        }
    )

    with pytest.raises(ValueError, match="下限必须小于上限"):
        classify_readings(readings, 8, 2)
