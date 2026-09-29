"use client";

import { useEffect, useState } from "react";

import { formatDuration, formatStartedAt, formatTokens } from "@/lib/format";
import type { Run } from "@/lib/types";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function RunList() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    const controller = new AbortController();

    async function loadRuns() {
      try {
        const response = await fetch(`${apiUrl}/api/runs`, { signal: controller.signal });
        if (!response.ok) throw new Error(`API returned ${response.status}`);
        const payload = (await response.json()) as { data: Run[] };
        setRuns(payload.data);
        setState("ready");
      } catch (error) {
        if ((error as Error).name !== "AbortError") setState("error");
      }
    }

    void loadRuns();
    return () => controller.abort();
  }, []);

  if (state === "loading") {
    return <div className="empty-state">Connecting to the trace store…</div>;
  }

  if (state === "error") {
    return (
      <div className="empty-state error-state">
        The API is offline. Start the local stack to view ingested runs.
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <div className="empty-state">
        <span className="empty-icon" aria-hidden="true">↗</span>
        <strong>No traces yet</strong>
        <p>Send OTLP data to <code>POST /v1/traces</code> and the run will appear here.</p>
      </div>
    );
  }

  return (
    <div className="run-table" role="table" aria-label="Recent agent runs">
      <div className="run-row run-header" role="row">
        <span>Run</span><span>Status</span><span>Model</span><span>Duration</span><span>Tokens</span>
      </div>
      {runs.map((run) => (
        <div className="run-row" role="row" key={run.trace_id}>
          <span className="run-name">
            <strong>{run.root_name}</strong>
            <small>{formatStartedAt(run.started_at)}</small>
          </span>
          <span><span className={`status status-${run.status}`}>{run.status}</span></span>
          <span className="muted">{run.model ?? "—"}</span>
          <span>{formatDuration(run.duration_ms)}</span>
          <span>{formatTokens(run.total_tokens)}</span>
        </div>
      ))}
    </div>
  );
}

