"""Generate synthetic test records; original course datasets are not required."""
import pandas as pd
import pytest

from app.analytics import BATTERY_COLUMNS


@pytest.fixture(autouse=True)
def synthetic_data_dir(tmp_path, monkeypatch):
    sessions = pd.DataFrame({
        "sessionId": [1, 2, 3, 4, 5],
        "kwhTotal": [5, 7, 20, 21, None],
        "charging_fees": [0, .1, 5, 5.3, 0],
        "startTime": [8, 8, 20, 20, 10],
        "endTime": [9, 9, 22, 23, 10],
        "chargeTimeHrs": [.5, .6, 4, 4.2, 0],
        "facilityType": [1, 1, 3, 3, 1],
        "managerVehicle": [0, 0, 1, 1, 0],
        "platform": ["ios", "ios", "android", "android", "ios"],
        "weekday": [1, 1, 2, 2, 3],
        "created": ["2025-01-01"] * 5,
        "ended": ["2025-01-01"] * 5,
    })
    sessions.to_csv(tmp_path / "nvv2t_md.csv", index=False)
    battery = pd.DataFrame([
        [1, 20250101080000, 20, 300, 10, 4.1, 3.9, 30, 20, 10, 20],
        [1, 20250101083000, 30, 305, 12, 4.2, 3.9, 32, 21, 12, 22],
        [1, 20250101090000, 40, 310, 15, 4.3, 4.0, 34, 22, 14, 24],
        [1, 20250101093000, 50, 315, 18, 4.4, 4.0, 36, 23, 16, 26],
    ], columns=BATTERY_COLUMNS)
    battery.to_csv(tmp_path / "dsv13r2.csv", index=False)
    monkeypatch.setenv("EV_DATA_DIR", str(tmp_path))
    return tmp_path
