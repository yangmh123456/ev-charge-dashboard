from app.web import create_app


def test_create_app_uses_secure_defaults():
    app = create_app()

    assert app.debug is False
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["MAX_CONTENT_LENGTH"] == 1_000_000


def test_security_headers_are_sent():
    client = create_app().test_client()

    response = client.get("/")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]


def test_api_dashboard_returns_summary_and_sections():
    client = create_app().test_client()

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["session_count"] == 4
    assert len(payload["sections"]) >= 10


def test_index_serves_dashboard_shell():
    client = create_app().test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert "新能源充电桩大数据分析平台" in response.get_data(as_text=True)


def test_api_requirements_maps_course_requirements():
    client = create_app().test_client()

    response = client.get("/api/requirements")

    assert response.status_code == 200
    payload = response.get_json()
    ids = {item["id"] for item in payload["items"]}
    assert {"hadoop", "hdfs", "mapreduce", "flask", "machine_learning", "mysql"}.issubset(ids)
    assert all(item["status"] in {"implemented", "documented", "simulated"} for item in payload["items"])


def test_api_mapreduce_jobs_returns_course_job_outputs():
    client = create_app().test_client()

    response = client.get("/api/mapreduce-jobs")

    assert response.status_code == 200
    payload = response.get_json()
    job_ids = {job["id"] for job in payload["jobs"]}
    assert {
        "voltage_current_by_hour",
        "cell_voltage_range",
        "temperature_by_hour",
        "energy_capacity_by_hour",
        "charge_current_by_hour",
        "voltage_change_rate",
        "soc_variance",
    }.issubset(job_ids)
