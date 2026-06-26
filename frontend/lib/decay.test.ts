import { describe, it, expect } from "vitest";
import { calculateCurrentImportance } from "./decay";

describe("calculateCurrentImportance", () => {
  it("returns the base importance when accessed right now", () => {
    const result = calculateCurrentImportance({
      importanceScore: 1.0,
      decayRate: 0.1,
      lastAccessed: new Date().toISOString(),
      accessCount: 0,
    });
    expect(result).toBeCloseTo(1.0, 2);
  });

  it("decays exponentially over time with no access bonus", () => {
    const tenDaysAgo = new Date(Date.now() - 10 * 86400000).toISOString();
    const result = calculateCurrentImportance({
      importanceScore: 1.0,
      decayRate: 0.1,
      lastAccessed: tenDaysAgo,
      accessCount: 0,
    });
    // 1.0 * exp(-0.1 * 10) = 1.0 * exp(-1) ≈ 0.3679
    expect(result).toBeCloseTo(0.3679, 3);
  });

  it("high access count fully offsets decay rate (clamped at 0)", () => {
    const tenDaysAgo = new Date(Date.now() - 10 * 86400000).toISOString();
    const result = calculateCurrentImportance({
      importanceScore: 1.0,
      decayRate: 0.1,
      lastAccessed: tenDaysAgo,
      accessCount: 10,
    });
    // log1p(10) * 0.1 ≈ 0.2398, exceeds decayRate 0.1 → effectiveDecay clamps to 0 → no decay
    expect(result).toBeCloseTo(1.0, 2);
  });

  it("clamps result to the [0, 1] range", () => {
    const result = calculateCurrentImportance({
      importanceScore: 0.05,
      decayRate: 0.5,
      lastAccessed: new Date(Date.now() - 365 * 86400000).toISOString(),
      accessCount: 0,
    });
    expect(result).toBeGreaterThanOrEqual(0);
    expect(result).toBeLessThanOrEqual(1);
  });
});
