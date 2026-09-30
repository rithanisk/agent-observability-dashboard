import asyncio
from dataclasses import dataclass
from threading import Lock
from typing import Any
from uuid import uuid4

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode

from tracewell_api.config import Settings

_telemetry_lock = Lock()
_provider: TracerProvider | None = None


class AgentConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AgentRunResult:
    trace_id: str
    answer: str
    model: str


def lookup_observability_evidence(topic: str) -> dict[str, object]:
    """Look up curated product evidence for one observability topic.

    Args:
        topic: The capability or problem to investigate.

    Returns:
        Relevant evidence and a source label for the research agent.
    """
    topic_lower = topic.lower()
    evidence = [
        {
            "area": "trace waterfall",
            "finding": (
                "Nested timing reveals slow model calls, tool bottlenecks, and broken handoffs."
            ),
            "source": "OpenTelemetry GenAI agent span conventions",
        },
        {
            "area": "regression evaluation",
            "finding": (
                "Versioned test cases make prompt and model changes measurable before release."
            ),
            "source": "Tracewell product requirements",
        },
        {
            "area": "online checks",
            "finding": (
                "Repeated tool calls and runaway token use can be flagged before a run completes."
            ),
            "source": "Tracewell product requirements",
        },
        {
            "area": "interoperability",
            "finding": "OTLP ingestion avoids locking instrumentation to one agent framework.",
            "source": "OpenTelemetry protocol",
        },
    ]
    matches = [
        item for item in evidence if any(word in item["area"] for word in topic_lower.split())
    ]
    return {"query": topic, "evidence": matches or evidence[:2]}


async def run_research_workflow(
    prompt: str,
    settings: Settings,
    *,
    model_override: Any | None = None,
    provider_override: Any | None = None,
) -> AgentRunResult:
    if not settings.soclaas_api_key:
        raise AgentConfigurationError("SOCLAAS_API_KEY is not configured")

    provider = provider_override or _configure_telemetry(settings)

    # Import ADK only after the global tracer provider is installed. ADK obtains
    # its tracer during import and then emits native GenAI semantic-convention spans.
    from google.adk.agents import LlmAgent, SequentialAgent
    from google.adk.agents.run_config import RunConfig
    from google.adk.models.lite_llm import LiteLlm
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.telemetry import ContentCapturingMode, TelemetryConfig
    from google.genai import types

    model = model_override or LiteLlm(
        model=f"openai/{settings.soclaas_model}",
        api_base=settings.soclaas_base_url,
        api_key=settings.soclaas_api_key,
    )
    research_agent = LlmAgent(
        name="research_agent",
        description="Finds evidence about AI agent observability.",
        model=model,
        instruction=(
            "You are the research stage of a product-analysis workflow. "
            "Use lookup_observability_evidence at least once to ground your answer. "
            "Return concise evidence that directly addresses the user's request."
        ),
        tools=[lookup_observability_evidence],
        output_key="research_notes",
    )
    synthesis_agent = LlmAgent(
        name="synthesis_agent",
        description="Turns research evidence into an actionable answer.",
        model=model,
        instruction=(
            "You are the synthesis stage. Answer the user's original request using only the "
            "research notes below. Be direct, concrete, and under 180 words.\n\n"
            "Research notes:\n{research_notes}"
        ),
    )
    workflow = SequentialAgent(
        name="research_and_synthesis",
        description="Researches a question and synthesizes the result.",
        sub_agents=[research_agent, synthesis_agent],
    )

    app_name = "tracewell_adk_demo"
    user_id = "local_demo_user"
    session_id = uuid4().hex
    sessions = InMemorySessionService()
    await sessions.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
    runner = Runner(agent=workflow, app_name=app_name, session_service=sessions)
    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    run_config = RunConfig(
        max_llm_calls=8,
        telemetry=TelemetryConfig(
            capture_message_content=ContentCapturingMode.SPAN_AND_EVENT,
            adk_experimental_telemetry_opt_in=True,
        ),
    )

    tracer = trace.get_tracer("tracewell.adk.runner")
    answer = ""
    try:
        with tracer.start_as_current_span("invoke_workflow research_and_synthesis") as root_span:
            context = root_span.get_span_context()
            trace_id = f"{context.trace_id:032x}"
            root_span.set_attributes(
                {
                    "gen_ai.operation.name": "invoke_workflow",
                    "gen_ai.workflow.name": "research_and_synthesis",
                    "gen_ai.request.model": settings.soclaas_model,
                    "gen_ai.provider.name": "soclaas",
                    "input.value": prompt,
                    "tracewell.agent.framework": "google-adk",
                }
            )
            try:
                async for event in runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=message,
                    run_config=run_config,
                ):
                    if event.is_final_response() and event.content:
                        text_parts = [part.text for part in event.content.parts or [] if part.text]
                        if text_parts:
                            answer = "".join(text_parts).strip()
                if not answer:
                    raise RuntimeError("The agent completed without a final text response")
                root_span.set_attribute("output.value", answer)
            except Exception as exc:
                root_span.record_exception(exc)
                root_span.set_status(Status(StatusCode.ERROR, type(exc).__name__))
                root_span.set_attribute("error.type", type(exc).__name__)
                raise
    finally:
        await asyncio.to_thread(provider.force_flush, 10_000)
    return AgentRunResult(trace_id=trace_id, answer=answer, model=settings.soclaas_model)


def _configure_telemetry(settings: Settings) -> TracerProvider:
    global _provider
    if _provider is not None:
        return _provider

    with _telemetry_lock:
        if _provider is not None:
            return _provider
        headers = {}
        if settings.ingest_token:
            headers["Authorization"] = f"Bearer {settings.ingest_token}"
        exporter = OTLPSpanExporter(endpoint=settings.self_otlp_url, headers=headers)
        provider = TracerProvider(
            resource=Resource.create(
                {
                    "service.name": "tracewell-adk-demo",
                    "service.version": "0.1.0",
                    "deployment.environment.name": settings.env,
                    "gen_ai.framework": "google-adk",
                }
            )
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _provider = provider
        return provider
