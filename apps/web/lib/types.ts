export type Run = {
  trace_id: string;
  root_name: string;
  status: "ok" | "error" | "open";
  started_at: string;
  duration_ms: number | null;
  total_tokens: number;
  cost_usd: number | null;
  prompt_hash: string | null;
  model: string | null;
  git_sha: string | null;
  eval_run_id: string | null;
  verdict: "ok" | "warn" | "fail" | null;
};

export type Span = {
  trace_id: string;
  span_id: string;
  parent_span_id: string | null;
  name: string;
  operation: string | null;
  provider: string | null;
  agent_name: string | null;
  model: string | null;
  tool_name: string | null;
  status: "ok" | "error" | "open";
  error_type: string | null;
  start_time: string;
  end_time: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  cost_usd: number | null;
  attributes: Record<string, unknown>;
  resource_attributes: Record<string, unknown>;
  events: Array<{
    name: string;
    time: string;
    attributes: Record<string, unknown>;
  }>;
};

export type Trace = {
  run: Run;
  spans: Span[];
};
