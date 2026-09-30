export function formatDuration(milliseconds: number | null): string {
  if (milliseconds === null) return "Running";
  if (milliseconds < 1_000) return `${milliseconds} ms`;
  return `${(milliseconds / 1_000).toFixed(2)} s`;
}

export function formatTokens(tokens: number): string {
  return new Intl.NumberFormat("en", { notation: "compact" }).format(tokens);
}

export function formatStartedAt(value: string): string {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function spanDuration(start: string, end: string | null): number | null {
  if (end === null) return null;
  return Math.max(0, new Date(end).getTime() - new Date(start).getTime());
}

export function formatCost(cost: number | null): string {
  if (cost === null) return "—";
  if (cost === 0) return "$0.00";
  if (cost < 0.01) return `$${cost.toFixed(4)}`;
  return `$${cost.toFixed(2)}`;
}

export function humanizeSpanName(name: string): string {
  const cleaned = name
    .replace(/^(invoke_workflow|invoke_agent|execute_tool|generate_content)\s+/, "")
    .replaceAll("_", " ");
  return cleaned ? cleaned.charAt(0).toUpperCase() + cleaned.slice(1) : name;
}
