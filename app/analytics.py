from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def configured_data_dir() -> Path:
    """Resolve data at construction time so EV_DATA_DIR can be changed by callers."""
    return Path(os.environ.get("EV_DATA_DIR", str(DEFAULT_DATA_DIR))).expanduser().resolve()


BATTERY_COLUMNS = [
    "esd",
    "record_time",
    "soc",
    "pack_voltage",
    "charge_current",
    "max_cell_voltage",
    "min_cell_voltage",
    "max_temperature",
    "min_temperature",
    "available_energy",
    "available_capacity",
]

REQUIREMENT_COVERAGE = [
    {
        "id": "hadoop",
        "name": "Hadoop分布式环境",
        "status": "documented",
        "evidence": "课程背景要求；当前仓库未部署 Hadoop 集群，分析在本机 Pandas 中完成",
    },
    {
        "id": "hdfs",
        "name": "HDFS数据存储",
        "status": "documented",
        "evidence": "课程背景要求；当前仓库从 EV_DATA_DIR 读取本地 CSV，未接入 HDFS",
    },
    {
        "id": "mapreduce",
        "name": "MapReduce分布式计算",
        "status": "simulated",
        "evidence": "/api/mapreduce-jobs 用 Pandas 演示聚合口径，未运行分布式 MapReduce 作业",
    },
    {
        "id": "mysql",
        "name": "MySQL结果持久化",
        "status": "documented",
        "evidence": "课程背景要求；当前仓库通过 JSON/API 交付结果，未连接 MySQL",
    },
    {
        "id": "machine_learning",
        "name": "历史数据估算",
        "status": "implemented",
        "evidence": "4类估算卡片使用中位数、整体均值与近邻投票，不包含已训练的机器学习模型",
    },
    {
        "id": "flask",
        "name": "Flask可视化服务",
        "status": "implemented",
        "evidence": "app/web.py 提供首页、/api/dashboard、/api/requirements、/api/mapreduce-jobs",
    },
]


@dataclass(frozen=True)
class EVDataRepository:
    data_dir: Path = field(default_factory=configured_data_dir)

    def __post_init__(self) -> None:
        object.__setattr__(self, "data_dir", Path(self.data_dir).expanduser().resolve())

    def _csv_path(self, filename: str) -> Path:
        path = self.data_dir / filename
        if not path.is_file():
            raise FileNotFoundError(
                f"Missing {filename}. Put the required CSV files in data/ or set EV_DATA_DIR."
            )
        return path

    @lru_cache(maxsize=1)
    def sessions(self) -> pd.DataFrame:
        path = self._csv_path("nvv2t_md.csv")
        df = pd.read_csv(path)
        numeric_columns = [
            "kwhTotal",
            "charging_fees",
            "startTime",
            "endTime",
            "chargeTimeHrs",
            "facilityType",
            "managerVehicle",
        ]
        for column in numeric_columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        df["created"] = pd.to_datetime(df["created"], errors="coerce")
        df["ended"] = pd.to_datetime(df["ended"], errors="coerce")
        cleaned = df.dropna(subset=["kwhTotal", "chargeTimeHrs", "startTime", "platform"])
        cleaned = cleaned[(cleaned["kwhTotal"] > 0) & (cleaned["chargeTimeHrs"] > 0)]
        if cleaned.empty:
            raise ValueError("No valid charging sessions remain after cleaning.")
        return cleaned.copy()

    @lru_cache(maxsize=1)
    def battery(self) -> pd.DataFrame:
        path = self._csv_path("dsv13r2.csv")
        df = pd.read_csv(path)
        df.columns = BATTERY_COLUMNS
        for column in BATTERY_COLUMNS:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        cleaned = df.dropna(subset=["record_time", "soc"])
        if cleaned.empty:
            raise ValueError("No valid battery records remain after cleaning.")
        return cleaned.copy()


def _round(value: float, digits: int = 2) -> float:
    return round(float(value), digits)


def charging_frequency_by_hour(sessions: pd.DataFrame) -> list[dict[str, Any]]:
    grouped = (
        sessions.assign(startTime=pd.to_numeric(sessions["startTime"], errors="coerce"))
        .dropna(subset=["startTime"])
        .groupby("startTime", as_index=False)
        .agg(sessions=("sessionId", "count") if "sessionId" in sessions else ("startTime", "count"), kwh=("kwhTotal", "sum"))
        .sort_values("startTime")
    )
    return [
        {"hour": int(row.startTime), "sessions": int(row.sessions), "kwh": _round(row.kwh)}
        for row in grouped.itertuples(index=False)
    ]


def hourly_soc(battery: pd.DataFrame) -> list[dict[str, Any]]:
    times = battery["record_time"].astype("Int64").astype(str).str.zfill(14)
    df = battery.assign(hour=pd.to_numeric(times.str[8:10], errors="coerce"))
    grouped = df.dropna(subset=["hour", "soc"]).groupby("hour", as_index=False)["soc"].mean().sort_values("hour")
    return [{"hour": int(row.hour), "soc": _round(row.soc)} for row in grouped.itertuples(index=False)]


def time_distribution(sessions: pd.DataFrame) -> list[dict[str, Any]]:
    bins = [0, 0.5, 1, 2, 4, 8, float("inf")]
    labels = ["0-0.5h", "0.5-1h", "1-2h", "2-4h", "4-8h", "8h+"]
    df = sessions.assign(bucket=pd.cut(sessions["chargeTimeHrs"], bins=bins, labels=labels, include_lowest=True))
    counts = df["bucket"].value_counts().reindex(labels, fill_value=0)
    return [{"bucket": str(bucket), "sessions": int(count)} for bucket, count in counts.items()]


def average_speed_by_hour(sessions: pd.DataFrame) -> list[dict[str, Any]]:
    df = sessions.copy()
    df["speed"] = df["kwhTotal"] / df["chargeTimeHrs"].where(df["chargeTimeHrs"] > 0)
    grouped = df.dropna(subset=["speed"]).groupby("startTime", as_index=False)["speed"].mean().sort_values("startTime")
    return [{"hour": int(row.startTime), "kw_per_hour": _round(row.speed)} for row in grouped.itertuples(index=False)]


def _battery_hour_frame(battery: pd.DataFrame) -> pd.DataFrame:
    times = battery["record_time"].astype("Int64").astype(str).str.zfill(14)
    return battery.assign(hour=pd.to_numeric(times.str[8:10], errors="coerce")).dropna(subset=["hour"])


def voltage_current_by_hour(battery: pd.DataFrame) -> list[dict[str, Any]]:
    grouped = (
        _battery_hour_frame(battery)
        .groupby("hour", as_index=False)
        .agg(pack_voltage=("pack_voltage", "mean"), charge_current=("charge_current", "mean"))
        .sort_values("hour")
    )
    return [
        {"hour": int(row.hour), "pack_voltage": _round(row.pack_voltage), "charge_current": _round(row.charge_current)}
        for row in grouped.itertuples(index=False)
    ]


def cell_voltage_range(battery: pd.DataFrame) -> list[dict[str, Any]]:
    grouped = (
        _battery_hour_frame(battery)
        .groupby("hour", as_index=False)
        .agg(max_cell_voltage=("max_cell_voltage", "max"), min_cell_voltage=("min_cell_voltage", "min"))
        .sort_values("hour")
    )
    return [
        {
            "hour": int(row.hour),
            "max_cell_voltage": _round(row.max_cell_voltage, 3),
            "min_cell_voltage": _round(row.min_cell_voltage, 3),
            "spread": _round(row.max_cell_voltage - row.min_cell_voltage, 3),
        }
        for row in grouped.itertuples(index=False)
    ]


def temperature_by_hour(battery: pd.DataFrame) -> list[dict[str, Any]]:
    grouped = (
        _battery_hour_frame(battery)
        .groupby("hour", as_index=False)
        .agg(max_temperature=("max_temperature", "max"), min_temperature=("min_temperature", "min"))
        .sort_values("hour")
    )
    return [
        {"hour": int(row.hour), "max_temperature": _round(row.max_temperature), "min_temperature": _round(row.min_temperature)}
        for row in grouped.itertuples(index=False)
    ]


def energy_capacity_by_hour(battery: pd.DataFrame) -> list[dict[str, Any]]:
    grouped = (
        _battery_hour_frame(battery)
        .groupby("hour", as_index=False)
        .agg(available_energy=("available_energy", "mean"), available_capacity=("available_capacity", "mean"))
        .sort_values("hour")
    )
    return [
        {"hour": int(row.hour), "available_energy": _round(row.available_energy), "available_capacity": _round(row.available_capacity)}
        for row in grouped.itertuples(index=False)
    ]


def charge_current_by_hour(battery: pd.DataFrame) -> list[dict[str, Any]]:
    grouped = (
        _battery_hour_frame(battery)
        .groupby("hour", as_index=False)["charge_current"]
        .mean()
        .sort_values("hour")
    )
    return [{"hour": int(row.hour), "charge_current": _round(row.charge_current)} for row in grouped.itertuples(index=False)]


def voltage_change_rate(battery: pd.DataFrame) -> list[dict[str, Any]]:
    df = _battery_hour_frame(battery).sort_values("record_time").copy()
    df["voltage_delta"] = df["pack_voltage"].diff().abs()
    grouped = df.dropna(subset=["voltage_delta"]).groupby("hour", as_index=False)["voltage_delta"].mean().sort_values("hour")
    return [{"hour": int(row.hour), "avg_voltage_delta": _round(row.voltage_delta, 4)} for row in grouped.itertuples(index=False)]


def soc_variance(battery: pd.DataFrame) -> list[dict[str, Any]]:
    grouped = (
        _battery_hour_frame(battery)
        .groupby("hour", as_index=False)
        .agg(soc_mean=("soc", "mean"), soc_variance=("soc", "var"))
        .fillna({"soc_variance": 0})
        .sort_values("hour")
    )
    return [
        {"hour": int(row.hour), "soc_mean": _round(row.soc_mean), "soc_variance": _round(row.soc_variance, 4)}
        for row in grouped.itertuples(index=False)
    ]


def build_mapreduce_jobs(repo: EVDataRepository | None = None) -> dict[str, Any]:
    repo = repo or EVDataRepository()
    battery = repo.battery()
    return {
        "jobs": [
            {
                "id": "voltage_current_by_hour",
                "title": "电压与充电流",
                "map_key": "record_time小时",
                "reduce_value": "平均组电压、平均充电电流",
                "rows": voltage_current_by_hour(battery),
            },
            {
                "id": "cell_voltage_range",
                "title": "电池单体电压",
                "map_key": "record_time小时",
                "reduce_value": "最高/最低单体电压与压差",
                "rows": cell_voltage_range(battery),
            },
            {
                "id": "temperature_by_hour",
                "title": "时点高低温",
                "map_key": "record_time小时",
                "reduce_value": "最高温度、最低温度",
                "rows": temperature_by_hour(battery),
            },
            {
                "id": "energy_capacity_by_hour",
                "title": "时点能量与容量",
                "map_key": "record_time小时",
                "reduce_value": "平均可用能量、平均可用容量",
                "rows": energy_capacity_by_hour(battery),
            },
            {
                "id": "charge_current_by_hour",
                "title": "充电电流值",
                "map_key": "record_time小时",
                "reduce_value": "平均充电电流",
                "rows": charge_current_by_hour(battery),
            },
            {
                "id": "voltage_change_rate",
                "title": "组电压变化率",
                "map_key": "相邻采样点",
                "reduce_value": "每小时平均电压变化量",
                "rows": voltage_change_rate(battery),
            },
            {
                "id": "soc_variance",
                "title": "电池状态平均值与方差",
                "map_key": "record_time小时",
                "reduce_value": "SOC平均值与方差",
                "rows": soc_variance(battery),
            },
        ]
    }


def build_requirement_coverage() -> dict[str, Any]:
    implemented = sum(1 for item in REQUIREMENT_COVERAGE if item["status"] == "implemented")
    return {
        "summary": {
            "total": len(REQUIREMENT_COVERAGE),
            "implemented": implemented,
            "documented_or_simulated": len(REQUIREMENT_COVERAGE) - implemented,
        },
        "items": REQUIREMENT_COVERAGE,
    }


def performance_report(sessions: pd.DataFrame, battery: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {"name": "平均单次电量", "value": f"{_round(sessions['kwhTotal'].mean())} kWh", "level": "stable"},
        {"name": "平均充电时长", "value": f"{_round(sessions['chargeTimeHrs'].mean())} h", "level": "stable"},
        {"name": "平均电池 SOC", "value": f"{_round(battery['soc'].mean())}%", "level": "good"},
        {"name": "最高温度", "value": f"{_round(battery['max_temperature'].max())} C", "level": "watch"},
        {"name": "平台数量", "value": str(sessions["platform"].nunique()), "level": "good"},
    ]


def _nearest_rows(sessions: pd.DataFrame, sample: dict[str, float], limit: int = 40) -> pd.DataFrame:
    features = ["kwhTotal", "charging_fees", "chargeTimeHrs", "startTime", "facilityType"]
    df = sessions.dropna(subset=features).copy()
    if df.empty:
        return df
    score = 0
    for feature in features:
        spread = max(float(df[feature].std() or 1), 1)
        score += ((df[feature] - float(sample.get(feature, df[feature].median()))) / spread).abs()
    return df.assign(_score=score).sort_values("_score").head(limit)


def predict_platform(sessions: pd.DataFrame, sample: dict[str, float]) -> dict[str, Any]:
    nearest = _nearest_rows(sessions, sample)
    if nearest.empty:
        label = str(sessions["platform"].mode().iat[0])
        return {"label": label, "confidence": 0.5}
    counts = nearest["platform"].value_counts()
    label = str(counts.index[0])
    return {"label": label, "confidence": _round(counts.iloc[0] / counts.sum(), 3)}


def prediction_cards(sessions: pd.DataFrame) -> list[dict[str, Any]]:
    sample = {
        "kwhTotal": float(sessions["kwhTotal"].median()),
        "charging_fees": float(sessions["charging_fees"].median()),
        "chargeTimeHrs": float(sessions["chargeTimeHrs"].median()),
        "startTime": float(sessions["startTime"].mode().iat[0]),
        "facilityType": float(sessions["facilityType"].mode().iat[0]),
    }
    platform = predict_platform(sessions, sample)
    speed = sessions["kwhTotal"].sum() / sessions["chargeTimeHrs"].sum()
    return [
        {"id": "predict_energy", "title": "预测剩余电量", "value": f"{_round(sample['kwhTotal'])} kWh", "hint": "按历史中位充电量估算"},
        {"id": "predict_time", "title": "预测充电时间", "value": f"{_round(sample['kwhTotal'] / speed)} h", "hint": "用整体平均充电速率折算"},
        {"id": "predict_fee", "title": "预测充电费用", "value": f"{_round(sample['charging_fees'])} 元", "hint": "按历史费用中位数估算"},
        {"id": "predict_platform", "title": "预测充电平台", "value": platform["label"], "hint": f"近邻样本置信度 {platform['confidence']:.0%}"},
    ]


def build_dashboard_payload(repo: EVDataRepository | None = None) -> dict[str, Any]:
    repo = repo or EVDataRepository()
    sessions = repo.sessions()
    battery = repo.battery()
    total_hours = sessions["chargeTimeHrs"].sum()
    total_kwh = sessions["kwhTotal"].sum()
    sections = [
        {"id": "bi", "title": "BI商业智能数据可视化", "type": "overview"},
        {"id": "time_frequency", "title": "充电时间与次数频率分析", "type": "bar", "data": charging_frequency_by_hour(sessions)},
        {"id": "hourly_soc", "title": "每时电池平均SOC", "type": "line", "data": hourly_soc(battery)},
        {"id": "time_distribution", "title": "充电时间分布图分析", "type": "donut", "data": time_distribution(sessions)},
        {"id": "avg_speed", "title": "平均充电速率图分析", "type": "line", "data": average_speed_by_hour(sessions)},
        {"id": "performance_report", "title": "性能指标分类分析报告", "type": "report", "data": performance_report(sessions, battery)},
    ]
    sections.extend({"id": card["id"], "title": card["title"], "type": "prediction", "data": card} for card in prediction_cards(sessions))
    return {
        "summary": {
            "session_count": int(len(sessions)),
            "battery_points": int(len(battery)),
            "total_kwh": _round(total_kwh),
            "avg_charge_hours": _round(sessions["chargeTimeHrs"].mean()),
            "avg_speed": _round(total_kwh / total_hours),
            "platforms": int(sessions["platform"].nunique()),
        },
        "sections": sections,
    }
