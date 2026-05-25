import importlib

from fastapi.testclient import TestClient


def test_health_and_device_listing(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("SMART_LAB_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("SMART_LAB_ENABLE_WORKER_RUNTIME", "false")

    config_module = importlib.import_module("smart_lab.shared.config")
    config_module.get_settings.cache_clear()
    main_module = importlib.import_module("smart_lab.api.main")

    with TestClient(main_module.create_app()) as client:
        health = client.get("/api/v1/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        devices = client.get("/api/v1/devices")
        assert devices.status_code == 200
        assert {device["device_id"] for device in devices.json()} >= {"temp_sensor_1", "pump_1"}
