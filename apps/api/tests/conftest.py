from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from tracewell_api.main import app
from tracewell_api.repository import get_repository


class FakeRepository:
    def __init__(self) -> None:
        self.spans = []
        self.runs = [
            {
                "trace_id": "01" * 16,
                "root_name": "research workflow",
                "status": "ok",
                "started_at": "2026-09-30T00:00:00+00:00",
                "duration_ms": 1250,
                "total_tokens": 42,
                "cost_usd": None,
                "prompt_hash": None,
                "model": "qwen3.5:9b",
                "git_sha": None,
                "eval_run_id": None,
                "verdict": None,
            }
        ]

    async def upsert_spans(self, spans):
        self.spans.extend(spans)
        return len(spans)

    async def list_runs(self, limit: int = 50):
        return self.runs[:limit]

    async def get_trace(self, trace_id: str):
        if trace_id != self.runs[0]["trace_id"]:
            return None
        return {"run": self.runs[0], "spans": []}


@pytest.fixture
def repository() -> FakeRepository:
    return FakeRepository()


@pytest.fixture
def client(repository: FakeRepository) -> Iterator[TestClient]:
    app.dependency_overrides[get_repository] = lambda: repository
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
