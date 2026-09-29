from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
from opentelemetry.proto.resource.v1.resource_pb2 import Resource
from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans, ScopeSpans, Span, Status

TRACE_ID = bytes.fromhex("01" * 16)
SPAN_ID = bytes.fromhex("02" * 8)


def sample_request() -> ExportTraceServiceRequest:
    span = Span(
        trace_id=TRACE_ID,
        span_id=SPAN_ID,
        name="chat qwen3.5:9b",
        start_time_unix_nano=1_767_139_200_000_000_000,
        end_time_unix_nano=1_767_139_201_250_000_000,
        status=Status(code=Status.STATUS_CODE_OK),
        attributes=[
            KeyValue(key="gen_ai.operation.name", value=AnyValue(string_value="chat")),
            KeyValue(key="gen_ai.provider.name", value=AnyValue(string_value="soclaas")),
            KeyValue(key="gen_ai.request.model", value=AnyValue(string_value="qwen3.5:9b")),
            KeyValue(key="gen_ai.usage.input_tokens", value=AnyValue(int_value=30)),
            KeyValue(key="gen_ai.usage.output_tokens", value=AnyValue(int_value=12)),
            KeyValue(key="tracewell.cost.usd", value=AnyValue(double_value=0.0)),
        ],
    )
    resource = Resource(
        attributes=[KeyValue(key="service.name", value=AnyValue(string_value="adk-research-agent"))]
    )
    return ExportTraceServiceRequest(
        resource_spans=[ResourceSpans(resource=resource, scope_spans=[ScopeSpans(spans=[span])])]
    )
