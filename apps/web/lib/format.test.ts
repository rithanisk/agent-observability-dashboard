import { describe, expect, it } from "vitest";

import { formatDuration, formatTokens } from "./format";

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
});

