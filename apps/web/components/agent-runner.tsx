"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const defaultPrompt =
  "What should an early-stage team prioritize when adding observability to an AI agent?";

export function AgentRunner() {
  const router = useRouter();
  const [prompt, setPrompt] = useState(defaultPrompt);
  const [state, setState] = useState<"idle" | "running" | "error">("idle");
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState("running");
    setError("");
    try {
      const response = await fetch(`${apiUrl}/api/agent/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      const payload = (await response.json()) as {
        trace_id?: string;
        detail?: string;
      };
      if (!response.ok || !payload.trace_id) {
        throw new Error(payload.detail ?? `API returned ${response.status}`);
      }
      router.push(`/runs/${payload.trace_id}`);
    } catch (caught) {
      setError((caught as Error).message);
      setState("error");
    }
  }

  return (
    <section className="agent-runner-section" aria-labelledby="agent-runner-title">
      <div className="agent-runner-copy">
        <p className="eyebrow">Live agent lab</p>
        <h2 id="agent-runner-title">Run the real workflow</h2>
        <p>
          Google ADK coordinates a research agent and synthesis agent. Qwen runs through
          SoCLaaS, while native OpenTelemetry spans stream back into Tracewell.
        </p>
        <div className="stack-tags" aria-label="Agent technology stack">
          <span>Google ADK</span><span>SoCLaaS</span><span>Qwen 3.5</span><span>OTLP</span>
        </div>
      </div>
      <form className="agent-runner-form" onSubmit={submit}>
        <label htmlFor="agent-prompt">Ask the research workflow</label>
        <textarea
          id="agent-prompt"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          minLength={3}
          maxLength={4000}
          disabled={state === "running"}
          rows={4}
          required
        />
        <div className="runner-actions">
          <small>Your prompt is sent to the configured NUS SoCLaaS endpoint.</small>
          <button type="submit" disabled={state === "running"}>
            {state === "running" ? <><span className="runner-spinner" /> Running agents…</> : "Run and trace →"}
          </button>
        </div>
        {state === "error" ? <p className="runner-error">{error}</p> : null}
      </form>
    </section>
  );
}
