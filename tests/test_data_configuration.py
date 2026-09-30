from pathlib import Path

import pandas as pd
import pytest

from app.analytics import EVDataRepository, time_distribution
from app.web import create_app


def test_environment_is_resolved_when_repository_is_constructed(monkeypatch, tmp_path):
    monkeypatch.setenv("EV_DATA_DIR", str(tmp_path / "another-directory"))
    assert EVDataRepository().data_dir == (tmp_path / "another-directory").resolve()


def test_missing_data_returns_actionable_error_without_leaking_path(monkeypatch, tmp_path):
    monkeypatch.setenv("EV_DATA_DIR", str(tmp_path / "private-directory"))
    response = create_app().test_client().get("/api/dashboard")
    assert response.status_code == 503
    assert "EV_DATA_DIR" in response.get_json()["error"]
    assert str(tmp_path) not in response.get_data(as_text=True)


def test_explicit_directory_is_supported(synthetic_data_dir):
    assert len(EVDataRepository(data_dir=str(synthetic_data_dir)).sessions()) == 4


def test_invalid_dataset_returns_422(synthetic_data_dir):
    path = synthetic_data_dir / "nvv2t_md.csv"
    frame = pd.read_csv(path)
    frame["chargeTimeHrs"] = 0
    frame.to_csv(path, index=False)
    assert create_app().test_client().get("/api/dashboard").status_code == 422


def test_duration_above_24_hours_is_counted():
    result = time_distribution(pd.DataFrame({"chargeTimeHrs": [30.0]}))
    assert sum(item["sessions"] for item in result) == 1
    assert result[-1] == {"bucket": "8h+", "sessions": 1}
