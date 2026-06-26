import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer } from "recharts";
import { MemoryResponse } from "@/lib/api";
import { calculateCurrentImportance } from "@/lib/decay";

const TYPE_COLORS: Record<string, string> = {
  preference: "#0ea5e9",
  decision: "#8b5cf6",
  bug_fix: "#ef4444",
  pattern: "#10b981",
  general: "#94a3b8",
};

export function MemoryDecayChart({ memories }: { memories: MemoryResponse[] }) {
  const data = memories
    .map((m) => ({
      label: m.content.length > 24 ? `${m.content.slice(0, 24)}…` : m.content,
      effectiveImportance: calculateCurrentImportance({
        importanceScore: m.importance_score,
        decayRate: m.decay_rate,
        lastAccessed: m.last_accessed,
        accessCount: m.access_count,
      }),
      memoryType: m.memory_type,
    }))
    .sort((a, b) => b.effectiveImportance - a.effectiveImportance);

  if (data.length === 0) {
    return <div className="text-sm text-slate-400 mb-3">No memories yet</div>;
  }

  return (
    <div className="mb-3" style={{ width: "100%", height: 180 }}>
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 8 }}>
          <XAxis type="number" domain={[0, 1]} hide />
          <YAxis type="category" dataKey="label" width={120} tick={{ fontSize: 11 }} />
          <Tooltip formatter={(value: number) => value.toFixed(2)} />
          <Bar dataKey="effectiveImportance">
            {data.map((entry, index) => (
              <Cell key={index} fill={TYPE_COLORS[entry.memoryType] || TYPE_COLORS.general} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
