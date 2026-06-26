import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer, TooltipProps } from "recharts";
import { MemoryResponse } from "@/lib/api";
import { calculateCurrentImportance } from "@/lib/decay";

const TYPE_COLORS: Record<string, string> = {
  preference: "#0ea5e9",
  decision: "#8b5cf6",
  bug_fix: "#ef4444",
  pattern: "#10b981",
  general: "#94a3b8",
};

const MAX_BARS = 8;
const BAR_HEIGHT = 36;

interface ChartDatum {
  label: string;
  fullContent: string;
  effectiveImportance: number;
  memoryType: string;
}

function ChartTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }
  const datum = payload[0].payload as ChartDatum;
  return (
    <div className="bg-white border rounded-md shadow-sm px-2 py-1.5 max-w-[240px] text-xs">
      <div className="font-medium mb-1">{datum.fullContent}</div>
      <div className="text-slate-500">{Math.round(datum.effectiveImportance * 100)}% importance</div>
    </div>
  );
}

export function MemoryDecayChart({ memories }: { memories: MemoryResponse[] }) {
  const data: ChartDatum[] = memories
    .map((m) => ({
      label: m.content.length > 28 ? `${m.content.slice(0, 28)}…` : m.content,
      fullContent: m.content,
      effectiveImportance: calculateCurrentImportance({
        importanceScore: m.importance_score,
        decayRate: m.decay_rate,
        lastAccessed: m.last_accessed,
        accessCount: m.access_count,
      }),
      memoryType: m.memory_type,
    }))
    .sort((a, b) => b.effectiveImportance - a.effectiveImportance)
    .slice(0, MAX_BARS);

  if (data.length === 0) {
    return <div className="text-sm text-slate-400 mb-3">No memories yet</div>;
  }

  return (
    <div className="mb-3" style={{ width: "100%", height: data.length * BAR_HEIGHT }}>
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 8 }} barCategoryGap="25%">
          <XAxis type="number" domain={[0, 1]} hide />
          <YAxis type="category" dataKey="label" width={150} tick={{ fontSize: 11 }} />
          <Tooltip content={<ChartTooltip />} />
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
