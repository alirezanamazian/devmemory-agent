export interface DecayInput {
  importanceScore: number;
  decayRate: number;
  lastAccessed: string;
  accessCount: number;
}

// Mirrors backend/app/core/decay.py DecayEngine.calculate_current_importance —
// keep these two in sync if the formula ever changes server-side.
export function calculateCurrentImportance(input: DecayInput): number {
  const { importanceScore, decayRate, lastAccessed, accessCount } = input;

  const now = Date.now();
  const lastAccessedMs = new Date(lastAccessed).getTime();
  const daysSinceAccess = (now - lastAccessedMs) / 86400000;

  const retentionBonus = Math.log1p(accessCount) * 0.1;
  const effectiveDecay = Math.max(0, decayRate - retentionBonus);

  const current = importanceScore * Math.exp(-effectiveDecay * daysSinceAccess);
  return Math.max(0, Math.min(1, current));
}
