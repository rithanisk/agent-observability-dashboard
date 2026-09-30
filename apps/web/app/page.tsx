import { AgentRunner } from "@/components/agent-runner";
import { RunList } from "@/components/run-list";

export default function Home() {
  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Tracewell home">
          <span className="brand-mark" aria-hidden="true" />
          Tracewell
        </a>
        <div className="live-pill">
          <span /> Live ingestion
        </div>
      </header>

      <section className="hero" id="top">
        <div>
          <p className="eyebrow">Agent observability</p>
          <h1>See every decision.<br />Catch every regression.</h1>
          <p className="lede">
            An OpenTelemetry-native flight recorder for AI agents. Follow tool calls,
            latency, tokens, and failures from the first span to the final answer.
          </p>
        </div>
        <div className="hero-metric" aria-label="Ingest latency target">
          <span className="metric-label">Ingest to screen</span>
          <strong>&lt;500<span>ms</span></strong>
          <span className="metric-caption">p95 target</span>
        </div>
      </section>

      <AgentRunner />

      <section className="runs-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Flight recorder</p>
            <h2>Recent runs</h2>
          </div>
          <p>Historical runs load over REST. Live updates arrive over WebSockets next.</p>
        </div>
        <RunList />
      </section>
    </main>
  );
}
