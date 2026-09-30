from collections.abc import AsyncGenerator

import pytest
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from tracewell_api import agent_runtime
from tracewell_api.agent_runtime import AgentConfigurationError
from tracewell_api.config import Settings


class FakeModel(BaseLlm):
    async def generate_content_async(
        self,
        llm_request: LlmRequest,
        stream: bool = False,
    ) -> AsyncGenerator[LlmResponse, None]:
        del llm_request, stream
        yield LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text="Grounded observability recommendations.")],
            )
        )


class FakeProvider:
    def __init__(self) -> None:
        self.flushed = False

    def force_flush(self, timeout_millis: int) -> bool:
        assert timeout_millis == 10_000
        self.flushed = True
        return True


def configured_settings() -> Settings:
    settings = Settings(_env_file=None)
    settings.soclaas_api_key = "test-key"
    return settings


def test_curated_evidence_matches_topics() -> None:
    matched = agent_runtime.lookup_observability_evidence("trace waterfall")
    fallback = agent_runtime.lookup_observability_evidence("unrelated")

    assert matched["evidence"][0]["area"] == "trace waterfall"
    assert len(fallback["evidence"]) == 2


@pytest.mark.asyncio
async def test_runs_adk_workflow_with_an_injected_model() -> None:
    provider = FakeProvider()

    result = await agent_runtime.run_research_workflow(
        "What should we observe?",
        configured_settings(),
        model_override=FakeModel(model="fake-model"),
        provider_override=provider,
    )

    assert result.answer == "Grounded observability recommendations."
    assert len(result.trace_id) == 32
    assert provider.flushed is True


@pytest.mark.asyncio
async def test_rejects_an_unconfigured_agent() -> None:
    settings = Settings(_env_file=None)
    settings.soclaas_api_key = ""

    with pytest.raises(AgentConfigurationError):
        await agent_runtime.run_research_workflow("hello", settings)


def test_configures_otlp_exporter_once(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[object] = []

    class Exporter:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

    class Processor:
        def __init__(self, exporter) -> None:
            self.exporter = exporter

    class Provider:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs
            self.processors = []
            created.append(self)

        def add_span_processor(self, processor) -> None:
            self.processors.append(processor)

    monkeypatch.setattr(agent_runtime, "_provider", None)
    monkeypatch.setattr(agent_runtime, "OTLPSpanExporter", Exporter)
    monkeypatch.setattr(agent_runtime, "BatchSpanProcessor", Processor)
    monkeypatch.setattr(agent_runtime, "TracerProvider", Provider)
    monkeypatch.setattr(agent_runtime.trace, "set_tracer_provider", lambda provider: None)

    settings = configured_settings()
    settings.ingest_token = "ingest-secret"
    first = agent_runtime._configure_telemetry(settings)
    second = agent_runtime._configure_telemetry(settings)

    assert first is second
    assert len(created) == 1
    exporter = first.processors[0].exporter
    assert exporter.kwargs["endpoint"] == settings.self_otlp_url
    assert exporter.kwargs["headers"] == {"Authorization": "Bearer ingest-secret"}
