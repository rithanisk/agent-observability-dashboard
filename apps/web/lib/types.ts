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

