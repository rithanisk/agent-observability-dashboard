"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { formatCost, formatDuration, formatStartedAt, humanizeSpanName, spanDuration } from "@/lib/format";
import type { Span, Trace } from "@/lib/types";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type TraceState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; trace: Trace };

const operationLabels: Record<string, string> = {
  invoke_agent: "Agent",
  invoke_workflow: "Workflow",
  plan: "Plan",
  chat: "LLM",
  generate_content: "LLM",
  execute_tool: "Tool",
};

function depthFor(span: Span, spansById: Map<string, Span>): number {
  let depth = 0;
  let parentId = span.parent_span_id;
  const visited = new Set<string>();
  while (parentId && spansById.has(parentId) && !visited.has(parentId)) {
    visited.add(parentId);
    depth += 1;
    parentId = spansById.get(parentId)?.parent_span_id ?? null;
  }
  return depth;
}

function displayValue(value: unknown): string {
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

function firstAttribute(span: Span, keys: string[]): unknown {
  for (const key of keys) {
    if (span.attributes[key] !== undefined) return span.attributes[key];
  }
  return undefined;
}

function ContentBlock({ title, value }: { title: string; value: unknown }) {
  if (value === undefined || value === null) return null;
  return (
    <section className="content-block">
      <h4>{title}</h4>
      <pre>{displayValue(value)}</pre>
    </section>
  );
}

export function TraceDetail({ traceId }: { traceId: string }) {
  const [state, setState] = useState<TraceState>({ status: "loading" });
  const [selectedSpanId, setSelectedSpanId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function loadTrace() {
      try {
        const response = await fetch(`${apiUrl}/api/runs/${encodeURIComponent(traceId)}`, {
          signal: controller.signal,
        });
        if (!response.ok) throw new Error(response.status === 404 ? "Trace not found" : `API returned ${response.status}`);
        const trace = (await response.json()) as Trace;
        setState({ status: "ready", trace });
        setSelectedSpanId(trace.spans.find((span) => span.parent_span_id === null)?.span_id ?? trace.spans[0]?.span_id ?? null);
      } catch (error) {
        if ((error as Error).name !== "AbortError") {
          setState({ status: "error", message: (error as Error).message });
        }
      }
    }
    void loadTrace();
    return () => controller.abort();
  }, [traceId]);

  const layout = useMemo(() => {
    if (state.status !== "ready") return null;
    const { spans } = state.trace;
    const starts = spans.map((span) => new Date(span.start_time).getTime());
    const ends = spans.map((span) => new Date(span.end_time ?? span.start_time).getTime());
    const start = Math.min(...starts);
    const end = Math.max(...ends, start + 1);
    const total = Math.max(1, end - start);
    const byId = new Map(spans.map((span) => [span.span_id, span]));
    return { start, total, byId };
  }, [state]);

  if (state.status === "loading") {
    return <main><div className="trace-loading">Reconstructing the trace…</div></main>;
  }

  if (state.status === "error") {
    return (
      <main>
        <nav className="trace-nav"><Link href="/">← Back to runs</Link></nav>
        <div className="empty-state error-state">{state.message}</div>
      </main>
    );
  }

  const { run, spans } = state.trace;
  const selected = spans.find((span) => span.span_id === selectedSpanId) ?? spans[0];
  const agentNames = [...new Set(spans.map((span) => span.agent_name).filter(Boolean))] as string[];
  const toolCount = spans.filter((span) => span.operation === "execute_tool").length;
  const llmCount = spans.filter((span) => ["chat", "generate_content"].includes(span.operation ?? "")).length;

  return (
    <main className="trace-page">
      <nav className="trace-nav">
        <Link className="brand" href="/" aria-label="Back to Tracewell runs">
          <span className="brand-mark" aria-hidden="true" /> Tracewell
        </Link>
        <Link className="back-link" href="/">← All runs</Link>
      </nav>

      <header className="trace-header">
        <div>
          <div className="trace-kicker">
            <span className={`status status-${run.status}`}>{run.status}</span>
            <span>{formatStartedAt(run.started_at)}</span>
            <span className="trace-id">{run.trace_id.slice(0, 12)}…</span>
          </div>
          <h1>{humanizeSpanName(run.root_name)}</h1>
          <p>{agentNames.length ? agentNames.join(" → ") : "Unlabelled agent"} · {spans.length} recorded spans</p>
        </div>
      </header>

      <section className="trace-metrics" aria-label="Run summary">
        <div><span>Duration</span><strong>{formatDuration(run.duration_ms)}</strong></div>
        <div><span>Total tokens</span><strong>{run.total_tokens.toLocaleString()}</strong></div>
        <div><span>Model</span><strong>{run.model ?? "—"}</strong></div>
        <div><span>Agent</span><strong>{agentNames[0] ?? "—"}</strong></div>
        <div><span>Calls</span><strong>{toolCount} tool · {llmCount} LLM</strong></div>
        <div><span>Cost</span><strong>{formatCost(run.cost_usd)}</strong></div>
      </section>

      <section className="trace-workspace">
        <div className="waterfall-card">
          <div className="card-heading">
            <div><p className="eyebrow">Execution path</p><h2>Trace waterfall</h2></div>
            <span>{formatDuration(run.duration_ms)} end to end</span>
          </div>
          <div className="waterfall-axis" aria-hidden="true">
            <span>Span</span><span>0</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span>
          </div>
          <div className="waterfall-list">
            {spans.map((span) => {
              const offset = layout ? ((new Date(span.start_time).getTime() - layout.start) / layout.total) * 100 : 0;
              const duration = spanDuration(span.start_time, span.end_time) ?? Math.max(1, layout?.total ?? 1);
              const width = layout ? Math.max(1.4, (duration / layout.total) * 100) : 100;
              const depth = layout ? depthFor(span, layout.byId) : 0;
              const label = operationLabels[span.operation ?? ""] ?? "Span";
              return (
                <button
                  className={`waterfall-row ${selected?.span_id === span.span_id ? "is-selected" : ""}`}
                  key={span.span_id}
                  onClick={() => setSelectedSpanId(span.span_id)}
                  type="button"
                >
                  <span className="span-label" style={{ paddingLeft: `${depth * 18}px` }}>
                    <span className={`operation-dot operation-${span.operation ?? "span"}`} />
                    <span><strong>{humanizeSpanName(span.name)}</strong><small>{label} · {formatDuration(spanDuration(span.start_time, span.end_time))}</small></span>
                  </span>
                  <span className="timeline-cell">
                    <span className="timeline-grid" />
                    <span
                      className={`duration-bar duration-${span.status}`}
                      style={{ left: `${offset}%`, width: `${Math.min(width, 100 - offset)}%` }}
                    />
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {selected ? (
          <aside className="span-panel">
            <div className="span-panel-header">
              <div><p className="eyebrow">Selected span</p><h3>{humanizeSpanName(selected.name)}</h3></div>
              <span className={`status status-${selected.status}`}>{selected.status}</span>
            </div>
            {selected.error_type ? <div className="span-error">{selected.error_type}</div> : null}
            <dl className="metadata-grid">
              <div><dt>Operation</dt><dd>{operationLabels[selected.operation ?? ""] ?? selected.operation ?? "span"}</dd></div>
              <div><dt>Duration</dt><dd>{formatDuration(spanDuration(selected.start_time, selected.end_time))}</dd></div>
              <div><dt>Agent</dt><dd>{selected.agent_name ?? "—"}</dd></div>
              <div><dt>Tool</dt><dd>{selected.tool_name ?? "—"}</dd></div>
              <div><dt>Model</dt><dd>{selected.model ?? "—"}</dd></div>
              <div><dt>Provider</dt><dd>{selected.provider ?? "—"}</dd></div>
              <div><dt>Input tokens</dt><dd>{selected.input_tokens?.toLocaleString() ?? "—"}</dd></div>
              <div><dt>Output tokens</dt><dd>{selected.output_tokens?.toLocaleString() ?? "—"}</dd></div>
            </dl>
            <ContentBlock title="Input" value={firstAttribute(selected, ["gen_ai.input.messages", "input.value", "tool.arguments", "gen_ai.tool.call.arguments", "gcp.vertex.agent.llm_request", "gcp.vertex.agent.tool_call_args"])} />
            <ContentBlock title="Output" value={firstAttribute(selected, ["gen_ai.output.messages", "output.value", "tool.result", "gen_ai.tool.call.result", "gcp.vertex.agent.llm_response", "gcp.vertex.agent.tool_response"])} />
            {selected.events.length ? <ContentBlock title="Events" value={selected.events} /> : null}
            <details className="raw-attributes">
              <summary>Raw attributes <span>{Object.keys(selected.attributes).length}</span></summary>
              <pre>{JSON.stringify(selected.attributes, null, 2)}</pre>
            </details>
            <details className="raw-attributes">
              <summary>Resource <span>{Object.keys(selected.resource_attributes).length}</span></summary>
              <pre>{JSON.stringify(selected.resource_attributes, null, 2)}</pre>
            </details>
          </aside>
        ) : null}
      </section>
    </main>
  );
}
