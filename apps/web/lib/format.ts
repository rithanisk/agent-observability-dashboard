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

