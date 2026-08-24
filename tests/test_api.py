from fastapi.testclient import TestClient

from app.main import app


def test_health_reports_unready_dependencies_without_stack_trace():
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["lm_studio"] in {"ready", "offline"}
    assert payload["qdrant"] in {"ready", "offline"}
    assert "configured" in payload


def test_local_ingest_is_restricted_to_data_raw_csv():
    with TestClient(app) as client:
        response = client.post("/api/ingest-local", json={"filename": "..\\.env", "limit": 1, "year": 2024})
    assert response.status_code == 400
    assert "data/raw" in response.json()["detail"]


def test_metrics_endpoint_is_available():
    with TestClient(app) as client:
        response = client.get("/metrics")
    assert response.status_code == 200
    assert "opensupport_http_requests_total" in response.text


def test_stage_preview_exposes_v1_control_trace():
    with TestClient(app) as client:
        response = client.get("/api/stage/v1_0/preview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["stage"] == "v1_0"
    assert payload["status"] in {"preflight_passed", "locked"}
    assert [event["name"] for event in payload["trace"]] == ["agent_preflight", "tool_allowlist", "human_approval_gate"]
