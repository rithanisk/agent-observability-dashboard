import base64
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from google.protobuf.json_format import ParseDict, ParseError
from google.protobuf.message import DecodeError
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue


class InvalidOTLPPayload(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class NormalizedSpan:
    trace_id: str
    span_id: str
    parent_span_id: str | None
    name: str
    operation: str | None
    provider: str | None
    agent_name: str | None
    model: str | None
    tool_name: str | None
    status: str
    error_type: str | None
    start_time: datetime
    end_time: datetime | None
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: Decimal | None
    attributes: dict[str, Any]
    resource_attributes: dict[str, Any]
    events: list[dict[str, Any]]


def decode_otlp(body: bytes, content_type: str) -> list[NormalizedSpan]:
    request = ExportTraceServiceRequest()
    media_type = content_type.partition(";")[0].strip().lower()

    try:
        if media_type in {"application/x-protobuf", "application/protobuf"}:
            request.ParseFromString(body)
        elif media_type == "application/json":
            payload = json.loads(body.decode("utf-8"))
            _normalize_json_ids(payload)
            ParseDict(payload, request)
        else:
            raise InvalidOTLPPayload(f"Unsupported content type: {media_type or 'missing'}")
    except (DecodeError, ParseError, UnicodeDecodeError, ValueError) as exc:
        if isinstance(exc, InvalidOTLPPayload):
            raise
        raise InvalidOTLPPayload("The request body is not valid OTLP trace data") from exc

    spans: list[NormalizedSpan] = []
    for resource_spans in request.resource_spans:
        resource_attributes = _key_values(resource_spans.resource.attributes)
        for scope_spans in resource_spans.scope_spans:
            for span in scope_spans.spans:
                attributes = _key_values(span.attributes)
                spans.append(
                    NormalizedSpan(
                        trace_id=span.trace_id.hex(),
                        span_id=span.span_id.hex(),
                        parent_span_id=span.parent_span_id.hex() or None,
                        name=span.name,
                        operation=_operation(attributes),
                        provider=_string(attributes, "gen_ai.provider.name", "gen_ai.system"),
                        agent_name=_string(attributes, "gen_ai.agent.name"),
                        model=_string(
                            attributes,
                            "gen_ai.request.model",
                            "gen_ai.response.model",
                        ),
                        tool_name=_string(attributes, "gen_ai.tool.name"),
                        status=_status(span.status.code),
                        error_type=_string(attributes, "error.type"),
                        start_time=_timestamp(span.start_time_unix_nano),
                        end_time=(
                            _timestamp(span.end_time_unix_nano) if span.end_time_unix_nano else None
                        ),
                        input_tokens=_integer(
                            attributes,
                            "gen_ai.usage.input_tokens",
                            "gen_ai.usage.prompt_tokens",
                        ),
                        output_tokens=_integer(
                            attributes,
                            "gen_ai.usage.output_tokens",
                            "gen_ai.usage.completion_tokens",
                        ),
                        cost_usd=_decimal(attributes.get("tracewell.cost.usd")),
                        attributes=attributes,
                        resource_attributes=resource_attributes,
                        events=[
                            {
                                "name": event.name,
                                "time": _timestamp(event.time_unix_nano).isoformat(),
                                "attributes": _key_values(event.attributes),
                            }
                            for event in span.events
                        ],
                    )
                )
    return spans


def _normalize_json_ids(payload: Any) -> None:
    """Convert the hex IDs required by OTLP/JSON into protobuf JSON bytes."""
    if not isinstance(payload, dict):
        return
    for resource_spans in payload.get("resourceSpans", []):
        for scope_spans in resource_spans.get("scopeSpans", []):
            for span in scope_spans.get("spans", []):
                for field, length in (
                    ("traceId", 32),
                    ("spanId", 16),
                    ("parentSpanId", 16),
                ):
                    value = span.get(field)
                    if not isinstance(value, str) or len(value) != length:
                        continue
                    try:
                        raw = bytes.fromhex(value)
                    except ValueError:
                        continue
                    span[field] = base64.b64encode(raw).decode("ascii")


def _timestamp(nanoseconds: int) -> datetime:
    return datetime.fromtimestamp(nanoseconds / 1_000_000_000, tz=UTC)


def _status(code: int) -> str:
    return "error" if code == 2 else "ok"


def _operation(attributes: dict[str, Any]) -> str | None:
    operation = _string(attributes, "gen_ai.operation.name")
    if operation:
        return operation

    open_inference_kind = _string(attributes, "openinference.span.kind")
    if not open_inference_kind:
        return None
    return {
        "AGENT": "invoke_agent",
        "CHAIN": "invoke_workflow",
        "LLM": "chat",
        "TOOL": "execute_tool",
    }.get(open_inference_kind.upper(), open_inference_kind.lower())


def _key_values(values: list[KeyValue]) -> dict[str, Any]:
    return {item.key: _any_value(item.value) for item in values}


def _any_value(value: AnyValue) -> Any:
    selected = value.WhichOneof("value")
    if selected is None:
        return None
    if selected == "array_value":
        return [_any_value(item) for item in value.array_value.values]
    if selected == "kvlist_value":
        return _key_values(value.kvlist_value.values)
    if selected == "bytes_value":
        return base64.b64encode(value.bytes_value).decode("ascii")
    return getattr(value, selected)


def _string(attributes: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = attributes.get(key)
        if value is not None:
            return str(value)
    return None


def _integer(attributes: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = attributes.get(key)
        if value is not None and not isinstance(value, bool):
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    return None


def _decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (ValueError, ArithmeticError):
        return None
