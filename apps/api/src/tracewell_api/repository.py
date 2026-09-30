from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from tracewell_api.db import get_session
from tracewell_api.models import Run, Span
from tracewell_api.otlp import NormalizedSpan


class TraceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_spans(self, spans: list[NormalizedSpan]) -> int:
        if not spans:
            return 0

        values = [
            {
                "trace_id": span.trace_id,
                "span_id": span.span_id,
                "parent_span_id": span.parent_span_id,
                "name": span.name,
                "operation": span.operation,
                "provider": span.provider,
                "agent_name": span.agent_name,
                "model": span.model,
                "tool_name": span.tool_name,
                "status": span.status,
                "error_type": span.error_type,
                "start_time": span.start_time,
                "end_time": span.end_time,
                "input_tokens": span.input_tokens,
                "output_tokens": span.output_tokens,
                "cost_usd": span.cost_usd,
                "attributes": span.attributes,
                "resource_attributes": span.resource_attributes,
                "events": span.events,
            }
            for span in spans
        ]
        statement = insert(Span).values(values)
        excluded = statement.excluded
        statement = statement.on_conflict_do_update(
            index_elements=[Span.trace_id, Span.span_id],
            set_={
                "parent_span_id": excluded.parent_span_id,
                "name": excluded.name,
                "operation": excluded.operation,
                "provider": excluded.provider,
                "agent_name": excluded.agent_name,
                "model": excluded.model,
                "tool_name": excluded.tool_name,
                "status": excluded.status,
                "error_type": excluded.error_type,
                "start_time": excluded.start_time,
                "end_time": excluded.end_time,
                "input_tokens": excluded.input_tokens,
                "output_tokens": excluded.output_tokens,
                "cost_usd": excluded.cost_usd,
                "attributes": excluded.attributes,
                "resource_attributes": excluded.resource_attributes,
                "events": excluded.events,
            },
        )
        await self.session.execute(statement)

        for trace_id in {span.trace_id for span in spans}:
            await self._refresh_run(trace_id)

        await self.session.commit()
        return len(spans)

    async def _refresh_run(self, trace_id: str) -> None:
        result = await self.session.scalars(
            select(Span).where(Span.trace_id == trace_id).order_by(Span.start_time)
        )
        spans = list(result)
        if not spans:
            return

        root = next((span for span in spans if span.parent_span_id is None), spans[0])
        completed_end_times = [span.end_time for span in spans if span.end_time is not None]
        latest_end = max(completed_end_times) if completed_end_times else None
        duration_ms = (
            int((latest_end - root.start_time).total_seconds() * 1000) if latest_end else None
        )
        status = "error" if any(span.status == "error" for span in spans) else "ok"
        if any(span.end_time is None for span in spans):
            status = "open"

        usage_spans = _usage_spans(spans)
        costs = [span.cost_usd for span in usage_spans if span.cost_usd is not None]
        total_cost = sum(costs, Decimal("0")) if costs else None
        total_tokens = sum(
            (span.input_tokens or 0) + (span.output_tokens or 0) for span in usage_spans
        )
        first_model = next((span.model for span in usage_spans if span.model), None)
        if first_model is None:
            first_model = next((span.model for span in spans if span.model), None)

        statement = insert(Run).values(
            trace_id=trace_id,
            root_name=root.name,
            status=status,
            started_at=root.start_time,
            duration_ms=duration_ms,
            total_tokens=total_tokens,
            cost_usd=total_cost,
            prompt_hash=root.attributes.get("tracewell.prompt.hash"),
            model=first_model,
            git_sha=root.attributes.get("tracewell.git.sha"),
            eval_run_id=root.attributes.get("tracewell.eval.run_id"),
            verdict=None,
        )
        excluded = statement.excluded
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=[Run.trace_id],
                set_={
                    "root_name": excluded.root_name,
                    "status": excluded.status,
                    "started_at": excluded.started_at,
                    "duration_ms": excluded.duration_ms,
                    "total_tokens": excluded.total_tokens,
                    "cost_usd": excluded.cost_usd,
                    "prompt_hash": excluded.prompt_hash,
                    "model": excluded.model,
                    "git_sha": excluded.git_sha,
                    "eval_run_id": excluded.eval_run_id,
                },
            )
        )

    async def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        result = await self.session.scalars(
            select(Run).order_by(Run.started_at.desc()).limit(limit)
        )
        return [_run_dict(run) for run in result]

    async def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        run = await self.session.get(Run, trace_id)
        if run is None:
            return None
        result = await self.session.scalars(
            select(Span).where(Span.trace_id == trace_id).order_by(Span.start_time)
        )
        return {"run": _run_dict(run), "spans": [_span_dict(span) for span in result]}


async def get_repository() -> AsyncIterator[TraceRepository]:
    async for session in get_session():
        yield TraceRepository(session)


def _run_dict(run: Run) -> dict[str, Any]:
    return {
        "trace_id": run.trace_id,
        "root_name": run.root_name,
        "status": run.status,
        "started_at": run.started_at.isoformat(),
        "duration_ms": run.duration_ms,
        "total_tokens": run.total_tokens,
        "cost_usd": float(run.cost_usd) if run.cost_usd is not None else None,
        "prompt_hash": run.prompt_hash,
        "model": run.model,
        "git_sha": run.git_sha,
        "eval_run_id": run.eval_run_id,
        "verdict": run.verdict,
    }


def _span_dict(span: Span) -> dict[str, Any]:
    return {
        "trace_id": span.trace_id,
        "span_id": span.span_id,
        "parent_span_id": span.parent_span_id,
        "name": span.name,
        "operation": span.operation,
        "provider": span.provider,
        "agent_name": span.agent_name,
        "model": span.model,
        "tool_name": span.tool_name,
        "status": span.status,
        "error_type": span.error_type,
        "start_time": span.start_time.isoformat(),
        "end_time": span.end_time.isoformat() if span.end_time else None,
        "input_tokens": span.input_tokens,
        "output_tokens": span.output_tokens,
        "cost_usd": float(span.cost_usd) if span.cost_usd is not None else None,
        "attributes": span.attributes,
        "resource_attributes": span.resource_attributes,
        "events": span.events,
    }


def _usage_spans(spans: list[Span]) -> list[Span]:
    """Prefer semantic model spans over ADK's duplicate call_llm wrapper spans."""
    canonical = [span for span in spans if span.operation in {"chat", "generate_content"}]
    return canonical or [
        span
        for span in spans
        if (
            span.input_tokens is not None
            or span.output_tokens is not None
            or span.cost_usd is not None
        )
    ]
