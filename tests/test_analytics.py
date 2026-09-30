from pathlib import Path

import pandas as pd

from app.analytics import (
    EVDataRepository,
    build_dashboard_payload,
    charging_frequency_by_hour,
    hourly_soc,
    predict_platform,
)


def test_repository_loads_course_csv_files():
    repo = EVDataRepository()

    sessions = repo.sessions()
    battery = repo.battery()

    assert len(sessions) == 4
    assert len(battery) == 4
    assert {"kwhTotal", "chargeTimeHrs", "platform", "weekday"}.issubset(sessions.columns)
    assert {"record_time", "soc", "pack_voltage"}.issubset(battery.columns)


def test_charging_frequency_by_hour_counts_start_time_values():
    sessions = pd.DataFrame({"startTime": [8, 8, 9, 23], "kwhTotal": [5.0, 7.0, 2.0, 1.0]})

    result = charging_frequency_by_hour(sessions)

    hour_8 = next(item for item in result if item["hour"] == 8)
    assert hour_8["sessions"] == 2
    assert hour_8["kwh"] == 12.0


def test_hourly_soc_uses_record_time_hour():
    battery = pd.DataFrame(
        {
            "record_time": ["20190726111742", "20190726111850", "20190726121742"],
            "soc": [10.0, 14.0, 20.0],
        }
    )

    result = hourly_soc(battery)

    assert result == [{"hour": 11, "soc": 12.0}, {"hour": 12, "soc": 20.0}]


def test_predict_platform_returns_existing_platform_label():
    sessions = pd.DataFrame(
        {
            "kwhTotal": [1.0, 20.0, 2.0, 21.0],
            "charging_fees": [0.0, 5.0, 0.1, 5.3],
            "chargeTimeHrs": [0.5, 4.0, 0.6, 4.2],
            "startTime": [8, 20, 8, 20],
            "facilityType": [1, 3, 1, 3],
            "platform": ["ios", "android", "ios", "android"],
        }
    )

    prediction = predict_platform(
        sessions,
        {"kwhTotal": 19, "charging_fees": 4.8, "chargeTimeHrs": 4.1, "startTime": 20, "facilityType": 3},
    )

    assert prediction["label"] == "android"
    assert 0 <= prediction["confidence"] <= 1


def test_build_dashboard_payload_contains_required_course_sections():
    payload = build_dashboard_payload(EVDataRepository())
    section_ids = {section["id"] for section in payload["sections"]}

    assert payload["summary"]["session_count"] == 4
    assert {
        "bi",
        "time_frequency",
        "hourly_soc",
        "time_distribution",
        "avg_speed",
        "performance_report",
        "predict_energy",
        "predict_time",
        "predict_fee",
        "predict_platform",
    }.issubset(section_ids)
