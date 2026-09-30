from types import SimpleNamespace

from tracewell_api.repository import _usage_spans


def test_usage_spans_prefer_semantic_model_spans() -> None:
    wrapper = SimpleNamespace(operation=None, input_tokens=100, output_tokens=20, cost_usd=None)
    semantic = SimpleNamespace(
        operation="generate_content", input_tokens=100, output_tokens=20, cost_usd=None
    )

    assert _usage_spans([wrapper, semantic]) == [semantic]
    assert _usage_spans([wrapper]) == [wrapper]
