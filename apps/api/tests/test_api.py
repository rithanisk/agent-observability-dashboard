import json

from fastapi.testclient import TestClient
from google.protobuf.json_format import MessageToDict

from tracewell_api import main

from .conftest import FakeRepository
from .fixtures import sample_request


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_ingests_json(client: TestClient, repository: FakeRepository) -> None:
    payload = MessageToDict(sample_request())
    span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    span["traceId"] = "01" * 16
    span["spanId"] = "02" * 8
    response = client.post(
        "/v1/traces",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json() == {}
    assert len(repository.spans) == 1


def test_ingests_protobuf(client: TestClient, repository: FakeRepository) -> None:
    response = client.post(
        "/v1/traces",
        content=sample_request().SerializeToString(),
        headers={"Content-Type": "application/x-protobuf"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-protobuf")
    assert len(repository.spans) == 1


def test_rejects_bad_payload(client: TestClient) -> None:
    response = client.post(
        "/v1/traces",
        content="not-json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400


def test_rejects_wrong_media_type(client: TestClient) -> None:
    response = client.post(
        "/v1/traces",
        content="{}",
        headers={"Content-Type": "text/plain"},
    )

    assert response.status_code == 415


def test_ingestion_token(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "ingest_token", "secret")
    unauthorized = client.post(
        "/v1/traces",
        content=sample_request().SerializeToString(),
        headers={"Content-Type": "application/x-protobuf"},
    )
    authorized = client.post(
        "/v1/traces",
        content=sample_request().SerializeToString(),
        headers={"Content-Type": "application/x-protobuf", "Authorization": "Bearer secret"},
    )

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200
    monkeypatch.setattr(main.settings, "ingest_token", "")


def test_lists_runs(client: TestClient) -> None:
    response = client.get("/api/runs?limit=1")

    assert response.status_code == 200
    assert response.json()["data"][0]["model"] == "qwen3.5:9b"


def test_gets_trace_and_returns_404(client: TestClient) -> None:
    found = client.get(f"/api/runs/{'01' * 16}")
    missing = client.get(f"/api/runs/{'ff' * 16}")

    assert found.status_code == 200
    assert found.json()["run"]["root_name"] == "research workflow"
    assert missing.status_code == 404
