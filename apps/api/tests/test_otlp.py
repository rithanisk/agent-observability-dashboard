import json
from decimal import Decimal

import pytest
from google.protobuf.json_format import MessageToDict

from tracewell_api.otlp import InvalidOTLPPayload, decode_otlp

from .fixtures import sample_request


def test_decodes_protobuf_and_normalizes_genai_fields() -> None:
    spans = decode_otlp(sample_request().SerializeToString(), "application/x-protobuf")

    assert len(spans) == 1
    span = spans[0]
    assert span.trace_id == "01" * 16
    assert span.span_id == "02" * 8
    assert span.parent_span_id is None
    assert span.operation == "chat"
    assert span.provider == "soclaas"
    assert span.model == "qwen3.5:9b"
    assert span.input_tokens == 30
    assert span.output_tokens == 12
    assert span.cost_usd == Decimal("0.0")
    assert span.resource_attributes["service.name"] == "adk-research-agent"


def test_decodes_otlp_json() -> None:
    payload_dict = MessageToDict(sample_request())
    span_dict = payload_dict["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    span_dict["traceId"] = "01" * 16
    span_dict["spanId"] = "02" * 8
    payload = json.dumps(payload_dict).encode()
    spans = decode_otlp(payload, "application/json; charset=utf-8")

    assert spans[0].name == "chat qwen3.5:9b"
    assert spans[0].status == "ok"
    assert spans[0].trace_id == "01" * 16


def test_maps_openinference_kind_and_legacy_tokens() -> None:
    request = sample_request()
    span = request.resource_spans[0].scope_spans[0].spans[0]
    span.attributes.clear()
    span.attributes.add(key="openinference.span.kind").value.string_value = "TOOL"
    span.attributes.add(key="gen_ai.usage.prompt_tokens").value.int_value = 8
    span.attributes.add(key="gen_ai.usage.completion_tokens").value.int_value = 3

    normalized = decode_otlp(request.SerializeToString(), "application/protobuf")[0]

    assert normalized.operation == "execute_tool"
    assert normalized.input_tokens == 8
    assert normalized.output_tokens == 3


@pytest.mark.parametrize("content_type", ["", "text/plain", "application/octet-stream"])
def test_rejects_unsupported_content_types(content_type: str) -> None:
    with pytest.raises(InvalidOTLPPayload, match="Unsupported content type"):
        decode_otlp(b"{}", content_type)


def test_rejects_malformed_json() -> None:
    with pytest.raises(InvalidOTLPPayload, match="not valid OTLP"):
        decode_otlp(b"{", "application/json")
