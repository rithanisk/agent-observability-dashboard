import { describe, expect, it } from "vitest";

import { formatCost, formatDuration, formatTokens, humanizeSpanName, spanDuration } from "./format";

describe("run formatters", () => {
  it("formats duration at readable scales", () => {
    expect(formatDuration(null)).toBe("Running");
    expect(formatDuration(420)).toBe("420 ms");
    expect(formatDuration(1250)).toBe("1.25 s");
  });

  it("formats token counts compactly", () => {
    expect(formatTokens(42)).toBe("42");
    expect(formatTokens(1200)).toMatch(/1\.2K/i);
  });

  it("derives span timing and formats small costs", () => {
    expect(spanDuration("2026-09-30T00:00:00Z", "2026-09-30T00:00:01.250Z")).toBe(1250);
    expect(spanDuration("2026-09-30T00:00:00Z", null)).toBeNull();
    expect(formatCost(0.0003)).toBe("$0.0003");
  });

  it("turns semantic span names into readable labels", () => {
    expect(humanizeSpanName("invoke_workflow research_and_synthesis")).toBe("Research and synthesis");
    expect(humanizeSpanName("execute_tool web_search")).toBe("Web search");
  });
});
